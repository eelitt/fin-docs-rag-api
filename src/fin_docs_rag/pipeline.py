import time
from dataclasses import dataclass

from fin_docs_rag.domain.calculate import cited, compare_sentence, lookup_sentence
from fin_docs_rag.domain.isin import is_isin, isins_in
from fin_docs_rag.domain.models import (
    NUMERIC_COLUMNS,
    Answer,
    Chunk,
    RequestEnvelope,
    Route,
    cell_from_dict,
)
from fin_docs_rag.domain.verify import citation_for, grounded_answer
from fin_docs_rag.ports import Chat, DependencyFailure, Embedder, ModelCall, Searcher
from fin_docs_rag.steps.answer import draft_answer
from fin_docs_rag.steps.grade import grade
from fin_docs_rag.steps.retrieve import retrieve
from fin_docs_rag.steps.route import route_question
from fin_docs_rag.trace import root_span


@dataclass
class AskDeps:
    chat: Chat
    embedder: Embedder
    search: Searcher
    sheet: dict


def answer_question(envelope: RequestEnvelope, deps: AskDeps) -> Answer:
    started = time.perf_counter()
    children: list[tuple[str, ModelCall]] = []
    pre_grade: list[str] = []
    deps.chat.last_call = None
    deps.embedder.last_call = None
    try:
        decided, router_call = route_question(envelope.question, envelope.instrument_ids, deps.chat)
        children.append(("router", router_call))
        prose, citations, reason, kept_ids, searched, pre_grade = _after_route(
            envelope, decided, deps, children, pre_grade
        )
    except DependencyFailure as error:
        _capture(error, children, deps)
        error.trace = _span(envelope, children, pre_grade, None, started)
        raise
    return Answer(
        request_id=envelope.request_id,
        reason=reason,
        answer=prose,
        citations=tuple(citations),
        chunk_ids=tuple(kept_ids),
        documents_searched=tuple(searched),
        trace=_span(envelope, children, pre_grade, reason, started),
    )


def _after_route(envelope, decided, deps, children, pre_grade):
    if decided.intent == "advice" and decided.advice_confidence == "high":
        return None, [], "advice_refused", [], [], pre_grade
    rows = {row["isin"]: row for row in deps.sheet["funds"]}
    subjects = list(envelope.instrument_ids) or isins_in(envelope.question)
    field = decided.comparison_field
    if _is_lookup(decided, subjects, rows, field):
        prose, citations = _lookup(subjects[0], field, rows[subjects[0]])
        return prose, citations, None, [], [], pre_grade
    if _is_compare(decided, subjects, rows, field):
        prose, citations = _compare(subjects[0], rows[subjects[0]], subjects[1], rows[subjects[1]], field)
        return prose, citations, None, [], [], pre_grade
    return _search(envelope, decided, subjects, deps, children)


def _search(envelope, decided, subjects, deps, children):
    names = [fund for fund in decided.funds if fund and not is_isin(fund)]
    query = decided.search_query.strip() or envelope.question
    for name in names:
        if name.casefold() not in query.casefold():
            query = f"{query} {name}"
    chunks, embed_call = retrieve(query, subjects or None, deps.embedder, deps.search)
    children.append(("embed", embed_call))
    pre_grade = [chunk.id for chunk in chunks]
    titles = _titles(chunks)
    if not chunks:
        return None, [], "not_in_corpus", [], titles, pre_grade
    kept, grade_call = grade(envelope.question, envelope.instrument_ids, chunks, deps.chat)
    children.append(("grade", grade_call))
    if not subjects and names:
        named = [chunk for chunk in kept if any(name.casefold() in chunk.text.casefold() for name in names)]
        kept = named or kept
    if not kept:
        return None, [], "not_in_corpus", [], titles, pre_grade
    draft, answer_call = draft_answer(envelope.question, envelope.instrument_ids, kept, deps.chat)
    children.append(("answer", answer_call))
    kept_ids = [chunk.id for chunk in kept]
    if draft.get("reason") == "advice_refused":
        return None, [], "advice_refused", [], [], pre_grade
    if not draft.get("can_answer"):
        return None, [], "not_in_corpus", kept_ids, titles, pre_grade
    by_id = {chunk.id: chunk for chunk in kept}
    pairs = [(item["chunk_id"], item["quote"]) for item in draft.get("citations", [])]
    if not grounded_answer(draft.get("answer", ""), pairs, by_id):
        return None, [], "ungrounded", kept_ids, [], pre_grade
    citations = [citation_for(by_id[chunk_id], quote) for chunk_id, quote in pairs]
    return draft["answer"], citations, None, kept_ids, [], pre_grade


def _is_lookup(decided: Route, subjects: list[str], rows: dict, field: str) -> bool:
    return (
        decided.intent == "lookup"
        and field in NUMERIC_COLUMNS
        and len(subjects) == 1
        and subjects[0] in rows
    )


def _is_compare(decided: Route, subjects: list[str], rows: dict, field: str) -> bool:
    return (
        decided.intent == "compare"
        and field in NUMERIC_COLUMNS
        and len(subjects) == 2
        and subjects[0] in rows
        and subjects[1] in rows
    )


def _lookup(isin: str, field: str, row: dict):
    cell = cell_from_dict(row[field])
    holding = cell_from_dict(row["holding_period"]) if field in ("ongoing_charge", "entry_cost", "exit_cost") else None
    return lookup_sentence(isin, field, cell, holding), cited(cell)


def _compare(isin_a: str, row_a: dict, isin_b: str, row_b: dict, field: str):
    cell_a = cell_from_dict(row_a[field])
    cell_b = cell_from_dict(row_b[field])
    holding_a = cell_from_dict(row_a["holding_period"])
    holding_b = cell_from_dict(row_b["holding_period"])
    sentence = compare_sentence(isin_a, cell_a, isin_b, cell_b, field, holding_a, holding_b)
    return sentence, cited(cell_a) + cited(cell_b)


def _titles(chunks: list[Chunk]) -> list[str]:
    titles: list[str] = []
    for chunk in chunks:
        title = chunk.title or chunk.doc_id
        if title not in titles:
            titles.append(title)
    return titles


def _capture(_error: DependencyFailure, children, deps: AskDeps) -> None:
    known = {call for _, call in children}
    if deps.embedder.last_call is not None and deps.embedder.last_call not in known:
        children.append(("embed", deps.embedder.last_call))
    if deps.chat.last_call is not None and deps.chat.last_call not in known:
        children.append((_chat_name(children), deps.chat.last_call))


def _chat_name(children) -> str:
    seen = {name for name, _call in children}
    if "router" not in seen:
        return "router"
    if "grade" not in seen:
        return "grade"
    return "answer"


def _span(envelope, children, pre_grade, reason, started) -> dict:
    elapsed = int((time.perf_counter() - started) * 1000)
    return root_span(
        request_id=envelope.request_id,
        caller=envelope.caller,
        instrument_ids=envelope.instrument_ids,
        latency_ms=elapsed,
        reason=reason,
        chunk_ids=pre_grade,
        children=children,
    )

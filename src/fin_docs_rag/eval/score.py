from fin_docs_rag.domain.calculate import cited, format_number
from fin_docs_rag.domain.models import ADVICE_REFUSED, Answer, cell_from_dict
from fin_docs_rag.domain.verify import figures_in, same_number

PATHS = ("sheet", "retrieve", "refuse")
OUTCOMES = ("number", "source", "reason")


def observed_path(answer: Answer) -> str:
    names = [child["name"] for child in answer.trace["children"]]
    searched = "embed" in names
    if answer.reason == ADVICE_REFUSED and not searched:
        return "refuse"
    if not searched and "grade" not in names and "answer" not in names:
        return "sheet"
    return "retrieve"


def check_item(item: dict, answer: Answer, sheet: dict) -> list[str]:
    errors: list[str] = []
    path = observed_path(answer)
    if path != item["path"]:
        errors.append(f"path is {path}, label is {item['path']}")
    if item["path"] == "refuse" and _has_body(answer):
        errors.append("refusal returned an answer body")
    errors.extend(_outcome(item, answer))
    errors.extend(_faithful(item, answer, sheet))
    return errors


def retrieval_hit(item: dict, answer: Answer, k: int) -> bool | None:
    chunk_id = item.get("chunk_id")
    if not chunk_id:
        return None
    return chunk_id in answer.trace["chunk_ids"][:k]


def summarize(items: list[dict], answers: list[Answer], sheet: dict, k: int, version: str) -> dict:
    failures = []
    hits = 0
    named = 0
    for item, answer in zip(items, answers, strict=True):
        errors = check_item(item, answer, sheet)
        if errors:
            failures.append({"id": item["id"], "errors": errors})
        hit = retrieval_hit(item, answer, k)
        if hit is not None:
            named += 1
            hits += int(hit)
    rate = None if named == 0 else hits / named
    return {
        "ok": not failures,
        "eval_set_version": version,
        "k": k,
        "items": len(items),
        "hit_rate_at_k": rate,
        "hits": hits,
        "hit_items": named,
        "failures": failures,
    }


def _outcome(item: dict, answer: Answer) -> list[str]:
    kind = item["outcome"]["kind"]
    value = item["outcome"]["value"]
    if kind == "reason":
        errors = []
        if answer.reason != value:
            errors.append("reason does not match")
        if item["path"] != "refuse" and _has_body(answer):
            errors.append("abstention returned an answer body")
        return errors
    if _has_body(answer) is False:
        return ["outcome missing an answer body"]
    if kind == "number":
        if not _number_matches(answer.answer or "", float(value)):
            return ["number does not match"]
        return []
    if value not in {citation.source_id for citation in answer.citations}:
        return ["source was not cited"]
    return []


def _faithful(item: dict, answer: Answer, sheet: dict) -> list[str]:
    if item["path"] == "sheet":
        stored = _stored(item, sheet)
        got = sorted((citation.source_id, citation.quote) for citation in answer.citations)
        if stored is None or got != stored:
            return ["citation is not the stored cell"]
        return []
    if item["path"] != "retrieve" or not answer.citations:
        return []
    retrieved = {chunk_id.split(":", 1)[0] for chunk_id in answer.trace["chunk_ids"]}
    if any(citation.source_id not in retrieved for citation in answer.citations):
        return ["citation source was not retrieved this turn"]
    return []


def _stored(item: dict, sheet: dict) -> list[tuple[str, str]] | None:
    rows = {row["isin"]: row for row in sheet["funds"]}
    pairs: list[tuple[str, str]] = []
    for isin in item["instrument_ids"]:
        row = rows.get(isin)
        if row is None or item["field"] not in row:
            return None
        for citation in cited(cell_from_dict(row[item["field"]])):
            pairs.append((citation.source_id, citation.quote))
    return sorted(pairs)


def _number_matches(prose: str, expected: float) -> bool:
    token = format_number(expected)
    if token.startswith("-"):
        return token in prose
    return any(same_number(figure, expected) for figure in figures_in(prose))


def _has_body(answer: Answer) -> bool:
    return answer.answer is not None or bool(answer.citations)

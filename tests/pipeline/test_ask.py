from fin_docs_rag.domain.models import Chunk, RequestEnvelope
from fin_docs_rag.pipeline import AskDeps, answer_question
from fin_docs_rag.ports import ModelCall


def _cite(quote: str, section: str = "costs", page: int = 3, doc: str = "FI0008804729") -> dict:
    return {"source_id": doc, "title": "Kid", "page": page, "section": section, "quote": quote}


def _stated(number, quote: str, section: str = "costs", doc: str = "FI0008804729") -> dict:
    return {"state": "stated", "number": number, "quote": quote, "citation": _cite(quote, section, doc=doc)}


def _row(isin: str, charge: float, quote: str, years: str, year_number: float, exit_state: str) -> dict:
    return {
        "isin": isin,
        "product": {"state": "stated", "quote": "Rahasto sijoittaa korkoihin.", "citation": _cite("Rahasto sijoittaa korkoihin.", "what", 2, isin)},
        "sri": _stated(2 if isin.endswith("4729") else 4, "2" if isin.endswith("4729") else "4", "risks", isin),
        "holding_period": _stated(year_number, years, "holding", isin),
        "ongoing_charge": _stated(charge, quote, "costs", isin),
        "entry_cost": {"state": "not_stated"},
        "exit_cost": {"state": exit_state},
    }


SHEET = {
    "funds": [
        _row("FI0008804729", 0.3, "0,30 %", "5 vuotta", 5, "not_extracted"),
        _row("FI0008804687", 0.9, "0,9 prosenttia", "3 vuotta", 3, "not_stated"),
    ]
}


def _route(intent: str, field: str = "", confidence: str = "low", funds: list[str] | None = None) -> dict:
    return {
        "intent": intent,
        "advice_confidence": confidence,
        "funds": funds or [],
        "comparison_field": field,
        "search_query": "search",
    }


class FakeChat:
    def __init__(self, replies: dict) -> None:
        self.replies = replies
        self.ids: list[str] = []
        self.payloads: list[dict] = []
        self.last_call = None

    def complete(self, prompt_id: str, payload: dict) -> dict:
        self.ids.append(prompt_id)
        self.payloads.append(payload)
        self.last_call = ModelCall(prompt_id, "fake", "fake", 1, 10, 5)
        reply = self.replies[prompt_id]
        return reply(payload) if callable(reply) else reply


class FakeEmbedder:
    def __init__(self) -> None:
        self.calls = 0
        self.last_call = None

    def embed(self, text: str) -> list[float]:
        self.calls += 1
        self.last_call = ModelCall("", "fake", "fake", 1, 8, 0)
        return [0.1]


class FakeSearch:
    def __init__(self, hits: list[Chunk] | None = None) -> None:
        self.hits = hits or []
        self.filters = []

    def hybrid(self, query: str, vector: list[float], isin_filter):
        self.filters.append(None if not isin_filter else list(isin_filter))
        return list(self.hits)


def _ask(chat: FakeChat, question: str, search: FakeSearch | None = None, instrument_ids=(), caller: str = "demo"):
    embedder = FakeEmbedder()
    finder = search or FakeSearch()
    result = answer_question(
        RequestEnvelope("11111111-1111-1111-1111-111111111111", caller, tuple(instrument_ids), question),
        AskDeps(chat, embedder, finder, SHEET),
    )
    return result, chat, embedder, finder


def test_sheet_fact_does_not_call_extract_or_search():
    result, chat, embedder, _search = _ask(
        FakeChat({"router_v1": _route("lookup", "ongoing_charge")}),
        "What is the ongoing cost of FI0008804729?",
    )
    assert chat.ids == ["router_v1"]
    assert embedder.calls == 0
    assert result.reason is None
    assert result.answer is not None
    assert "0.3" in result.answer and "0,30 %" in result.answer and "5 vuotta" in result.answer
    assert result.citations[0].source_id == "FI0008804729"
    assert result.chunk_ids == ()
    assert [child["name"] for child in result.trace["children"]] == ["router"]
    assert "instrument_ids" in result.trace
    assert result.trace["cost_usd"] == 10 * (0.40 / 1_000_000) + 5 * (1.60 / 1_000_000)


def test_sheet_row_serves_each_cell_state():
    chat = FakeChat({"router_v1": _route("lookup", "entry_cost")})
    missing, _, _, _ = _ask(chat, "Entry cost of FI0008804729?")
    assert "no stated entry cost" in missing.answer
    chat.replies["router_v1"] = _route("lookup", "exit_cost")
    failed, _, _, _ = _ask(chat, "Exit cost of FI0008804729?")
    assert "was not extracted" in failed.answer
    assert failed.citations == ()
    chat.replies["router_v1"] = _route("lookup", "sri")
    stated, _, _, _ = _ask(chat, "Risk indicator of FI0008804729?")
    assert stated.citations[0].quote == "2"


def test_comparison_is_computed_without_the_answer_model():
    result, chat, embedder, _search = _ask(
        FakeChat({"router_v1": _route("compare", "ongoing_charge")}),
        "Which is cheaper, FI0008804729 or FI0008804687?",
    )
    assert chat.ids == ["router_v1"]
    assert embedder.calls == 0
    assert result.reason is None
    assert "5 vuotta" in result.answer and "3 vuotta" in result.answer
    assert "-0.6 percentage points" in result.answer
    assert "cheaper" not in result.answer.casefold()
    assert {item.source_id for item in result.citations} == {"FI0008804729", "FI0008804687"}


def test_absence_names_the_documents_and_does_not_answer():
    chunk = Chunk("report-2026-q3:market:2:0", "report-2026-q3", "market", 2, 0, "No such fact.", title="Quarterly review")

    def grade(payload: dict) -> dict:
        return {"chunks": [{"id": item["id"], "relevant": False} for item in payload["chunks"]]}

    result, chat, _embedder, _search = _ask(
        FakeChat({"router_v1": _route("lookup"), "grade_v1": grade}),
        "What was the auditor's middle name?",
        FakeSearch([chunk]),
    )
    assert result.reason == "not_in_corpus"
    assert result.answer is None
    assert result.citations == ()
    assert result.chunk_ids == ()
    assert result.documents_searched == ("Quarterly review",)
    assert result.trace["chunk_ids"] == [chunk.id]
    assert "answer_v1" not in chat.ids
    assert "extract_v1" not in chat.ids


def test_high_confidence_advice_does_not_search():
    result, chat, embedder, search = _ask(
        FakeChat({"router_v1": _route("advice", confidence="high")}),
        "Should I buy this fund?",
    )
    assert result.reason == "advice_refused"
    assert result.answer is None
    assert result.citations == ()
    assert result.chunk_ids == ()
    assert embedder.calls == 0
    assert search.filters == []
    assert chat.ids == ["router_v1"]


def test_long_document_answer_cites_only_a_kept_chunk():
    kept = Chunk(
        "report-2026-q3:market:2:0",
        "report-2026-q3",
        "market",
        2,
        0,
        "The turnover was 12,5 percent in the quarter.",
        title="Quarterly review",
    )
    other = Chunk(
        "report-2026-q3:market:2:1",
        "report-2026-q3",
        "market",
        2,
        1,
        "Unrelated sentence.",
        title="Quarterly review",
    )

    def grade(payload: dict) -> dict:
        return {"chunks": [{"id": item["id"], "relevant": item["id"] == kept.id} for item in payload["chunks"]]}

    def answer(payload: dict) -> dict:
        return {
            "can_answer": True,
            "answer": "Turnover was 12.5 percent.",
            "citations": [{"chunk_id": payload["chunks"][0]["id"], "quote": "12,5 percent"}],
            "reason": "",
        }

    result, chat, _embedder, _search = _ask(
        FakeChat({"router_v1": _route("lookup"), "grade_v1": grade, "answer_v1": answer}),
        "What was turnover in the quarterly review?",
        FakeSearch([kept, other]),
    )
    assert result.reason is None
    assert result.answer == "Turnover was 12.5 percent."
    assert result.citations[0].quote == "12,5 percent"
    assert result.citations[0].source_id == "report-2026-q3"
    assert result.chunk_ids == (kept.id,)
    assert result.trace["chunk_ids"] == [kept.id, other.id]
    assert result.documents_searched == ()
    assert [child["name"] for child in result.trace["children"]] == ["router", "embed", "grade", "answer"]
    assert "extract_v1" not in chat.ids


def test_a_bad_quote_is_ungrounded_and_the_draft_is_dropped():
    chunk = Chunk("report-2026-q3:market:2:0", "report-2026-q3", "market", 2, 0, "Visible fact.", title="Quarterly review")

    def grade(payload: dict) -> dict:
        return {"chunks": [{"id": item["id"], "relevant": True} for item in payload["chunks"]]}

    result, _chat, _embedder, _search = _ask(
        FakeChat(
            {
                "router_v1": _route("lookup"),
                "grade_v1": grade,
                "answer_v1": {
                    "can_answer": True,
                    "answer": "The figure is 4.",
                    "citations": [{"chunk_id": chunk.id, "quote": "not in the chunk"}],
                    "reason": "",
                },
            }
        ),
        "What figure is printed?",
        FakeSearch([chunk]),
    )
    assert result.reason == "ungrounded"
    assert result.answer is None
    assert result.citations == ()
    assert result.chunk_ids == (chunk.id,)


def test_instrument_ids_are_the_only_filter_when_present():
    _result, _chat, _embedder, search = _ask(
        FakeChat({"router_v1": _route("lookup")}),
        "Tell me about FI0008804687",
        FakeSearch(),
        instrument_ids=("FI0008804729",),
    )
    assert search.filters == [["FI0008804729"]]


def test_a_fund_name_prefers_matching_chunks():
    named = Chunk("report-2026-q3:a:1:0", "report-2026-q3", "a", 1, 0, "Eurooppa details.", title="Quarterly review")
    other = Chunk("report-2026-q3:b:1:0", "report-2026-q3", "b", 1, 0, "Other details.", title="Quarterly review")
    seen = []

    def grade(payload: dict) -> dict:
        return {"chunks": [{"id": item["id"], "relevant": True} for item in payload["chunks"]]}

    def answer(payload: dict) -> dict:
        seen.append([item["id"] for item in payload["chunks"]])
        chunk_id = payload["chunks"][0]["id"]
        quote = "Eurooppa" if chunk_id == named.id else "Other"
        return {"can_answer": True, "answer": "Noted.", "citations": [{"chunk_id": chunk_id, "quote": quote}], "reason": ""}

    _ask(
        FakeChat({"router_v1": _route("lookup", funds=["Eurooppa"]), "grade_v1": grade, "answer_v1": answer}),
        "What does the review say?",
        FakeSearch([other, named]),
    )
    assert seen == [[named.id]]


def test_other_callers_keep_instrument_ids_off_the_trace():
    result, _chat, _embedder, _search = _ask(
        FakeChat({"router_v1": _route("advice", confidence="high")}),
        "Should I buy this fund?",
        caller="later",
        instrument_ids=("FI0008804729",),
    )
    assert "instrument_ids" not in result.trace
    assert result.trace["caller"] == "later"

from fin_docs_rag.domain.models import Answer, Citation
from fin_docs_rag.eval.score import check_item, observed_path, summarize


def _answer(reason, prose, citations=(), children=("router",), chunk_ids=()):
    return Answer(
        "item",
        reason,
        prose,
        tuple(citations),
        (),
        (),
        {"children": [{"name": name} for name in children], "chunk_ids": list(chunk_ids), "reason": reason},
    )


def _cite(source_id, quote):
    return Citation(source_id, "KID", quote, 3, "costs")


REFUSE = {
    "id": "advice",
    "path": "refuse",
    "outcome": {"kind": "reason", "value": "advice_refused"},
}


def test_refusal_with_an_answer_body_fails():
    answer = _answer("advice_refused", "Buy the fund.")
    assert observed_path(answer) == "refuse"
    assert "refusal returned an answer body" in check_item(REFUSE, answer, {"funds": []})


def test_path_other_than_the_label_fails():
    item = {
        "id": "sheet-fact",
        "path": "sheet",
        "field": "ongoing_charge",
        "instrument_ids": ["FI0008804729"],
        "outcome": {"kind": "number", "value": 0.3},
    }
    answer = _answer(None, "The ongoing cost for FI0008804729 is 0.3 (0,30 %).", children=("router", "embed"))
    assert "path is retrieve, label is sheet" in check_item(item, answer, {"funds": []})


def test_sheet_citation_must_be_the_stored_cell():
    item = {
        "id": "sheet-fact",
        "path": "sheet",
        "field": "ongoing_charge",
        "instrument_ids": ["FI0008804729"],
        "outcome": {"kind": "number", "value": 0.3},
    }
    sheet = {
        "funds": [
            {
                "isin": "FI0008804729",
                "ongoing_charge": {
                    "state": "stated",
                    "number": 0.3,
                    "quote": "0,30 %",
                    "citation": {"source_id": "FI0008804729", "title": "KID", "quote": "0,30 %"},
                },
            }
        ]
    }
    wrong = _answer(None, "The ongoing cost for FI0008804729 is 0.3 (0,30 %).", (_cite("FI0008804687", "0,30 %"),))
    assert check_item(item, wrong, sheet) == ["citation is not the stored cell"]
    right = _answer(None, "The ongoing cost for FI0008804729 is 0.3 (0,30 %).", (_cite("FI0008804729", "0,30 %"),))
    assert check_item(item, right, sheet) == []


def test_generated_citation_must_have_been_retrieved():
    item = {
        "id": "report",
        "path": "retrieve",
        "outcome": {"kind": "source", "value": "report-2026-q3"},
        "chunk_id": "report-2026-q3:pharos:10:0",
    }
    answer = _answer(
        None,
        "The fund size was 178.9 million euro.",
        (_cite("report-2026-q3", "178,9"),),
        ("router", "embed", "grade", "answer"),
        ["FI0008804729:costs:3:0"],
    )
    assert check_item(item, answer, {"funds": []}) == ["citation source was not retrieved this turn"]


def test_hit_rate_uses_the_first_k_retrieved_ids():
    items = [
        {"id": "hit", "path": "retrieve", "chunk_id": "a:s:1:0", "outcome": {"kind": "source", "value": "a"}},
        {"id": "miss", "path": "retrieve", "chunk_id": "b:s:1:0", "outcome": {"kind": "source", "value": "b"}},
    ]
    answers = [
        _answer(None, "kept", (_cite("a", "1"),), ("router", "embed", "answer"), ["a:s:1:0", "b:s:1:0"]),
        _answer(None, "kept", (_cite("b", "1"),), ("router", "embed", "answer"), ["b:s:1:1", "b:s:1:0"]),
    ]
    report = summarize(items, answers, {"funds": []}, k=1, version="1")
    assert report["hit_rate_at_k"] == 0.5
    assert report["failures"] == []

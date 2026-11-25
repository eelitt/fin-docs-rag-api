from pathlib import Path

from fin_docs_rag.domain.models import Chunk, RequestEnvelope
from fin_docs_rag.eval.run import golden_path, load_golden, run_items
from fin_docs_rag.pipeline import AskDeps, answer_question
from fin_docs_rag.ports import ModelCall

ROOT = Path(__file__).resolve().parents[2]

ROWS = (
    ("FI0008804729", 0.30, "0,30 %", 2, 1, "Suositeltu sijoitusaika: 1 vuosi"),
    ("FI0008801774", 0.44, "0,44 %", 4, 7, "Suositeltu sijoitusaika: 7 vuotta"),
    ("FI0008801758", 0.46, "0,46 %", 4, 7, "Suositeltu sijoitusaika: 7 vuotta"),
    ("FI0008801964", 0.45, "0,45 %", 4, 7, "Suositeltu sijoitusaika: 7 vuotta"),
    ("FI0008801907", 0.53, "0,53 %", 3, 5, "Suositeltu sijoitusaika: 5 vuotta"),
    ("FI0008801733", 0.19, "0,19 %", 1, 3, "Suositeltu sijoitusaika: 3 kuukautta"),
    ("FI0008805486", 0.95, "0,95 %", 3, 7, "Suositeltu sijoitusaika: 7 vuotta"),
    ("FI0008801790", 0.61, "0,61 %", 4, 7, "Suositeltu sijoitusaika: 7 vuotta"),
    ("FI0008804760", 1.52, "1,52 %", 4, 7, "Suositeltu sijoitusaika: 7 vuotta"),
    ("FI0008804687", 0.9, "0,9 prosenttia", 4, 5, "Suositeltu sijoitusaika on 5 vuotta."),
    ("FI0008810866", 0.7, "0,7 prosenttia", 4, 5, "Suositeltu sijoitusaika on 5 vuotta."),
    ("FI4000020656", 1.9, "1,9 prosenttia", 3, 5, "Suositeltu sijoitusaika: 5 vuotta"),
)


def _stated(number, quote, section, isin):
    return {
        "state": "stated",
        "number": number,
        "quote": quote,
        "citation": {"source_id": isin, "title": "KID", "page": 3, "section": section, "quote": quote},
    }


def _sheet():
    funds = []
    for isin, charge, charge_quote, sri, years, holding in ROWS:
        funds.append(
            {
                "isin": isin,
                "product": {"state": "not_stated"},
                "sri": _stated(sri, f"määritetty {sri}", "risks", isin),
                "holding_period": _stated(years, holding, "holding", isin),
                "ongoing_charge": _stated(charge, charge_quote, "costs", isin),
                "entry_cost": {"state": "not_stated"},
                "exit_cost": {"state": "not_stated"},
            }
        )
    return {"funds": funds}


def _chunk(raw: dict) -> Chunk:
    return Chunk(raw["id"], raw["doc_id"], raw["section"], raw["page"], raw["window"], raw["text"], raw["title"])


class ScriptedChat:
    def __init__(self, items):
        self.items = {item["question"]: item for item in items}
        self.last_call = None

    def complete(self, prompt_id, payload):
        item = self.items[payload["question"]]
        self.last_call = ModelCall(prompt_id, "fake", "fake", 1, 10, 5)
        if prompt_id == "router_v1":
            return item["fake"]["route"]
        if prompt_id == "grade_v1":
            relevant = set(item["fake"].get("relevant", []))
            return {"chunks": [{"id": row["id"], "relevant": row["id"] in relevant} for row in payload["chunks"]]}
        if prompt_id == "answer_v1":
            return item["fake"]["draft"]
        raise AssertionError(prompt_id)


class ScriptedEmbedder:
    def __init__(self):
        self.calls = 0
        self.last_call = None

    def embed(self, text):
        self.calls += 1
        self.last_call = ModelCall("", "fake", "fake", 1, 8, 0)
        return [0.1]


class ScriptedSearch:
    def __init__(self, items):
        self.items = items

    def hybrid(self, query, vector, isin_filter):
        matches = [
            item
            for item in self.items
            if item["fake"]["route"]["search_query"] and item["fake"]["route"]["search_query"] in query
        ]
        if len(matches) != 1:
            raise AssertionError(query)
        return [_chunk(raw) for raw in matches[0]["fake"].get("passages", [])]


def _deps(golden):
    return AskDeps(ScriptedChat(golden["items"]), ScriptedEmbedder(), ScriptedSearch(golden["items"]), _sheet())


def test_golden_file_is_checked_in_and_covers_the_five_types():
    golden = load_golden()
    assert golden_path().is_file()
    assert 25 <= len(golden["items"]) <= 40
    assert {item["question_type"] for item in golden["items"]} == {
        "fact",
        "comparison",
        "absence",
        "advice",
        "long_document",
    }
    assert any(item.get("case") == "similar_names" for item in golden["items"])
    assert any(item.get("case") == "different_holding_periods" for item in golden["items"])
    assert any(
        item["outcome"] == {"kind": "reason", "value": "not_in_corpus"} for item in golden["items"]
    )


def test_golden_set_passes_on_fakes():
    golden = load_golden()
    report = run_items(golden, _deps(golden))
    assert report["failures"] == []
    assert report["hit_rate_at_k"] == 1


def test_different_holding_periods_are_both_stated():
    golden = load_golden()
    item = next(row for row in golden["items"] if row["id"] == "compare-charge-different-holding")
    result = answer_question(
        RequestEnvelope(item["id"], "demo", tuple(item["instrument_ids"]), item["question"]),
        _deps(golden),
    )
    assert result.reason is None
    assert "1 vuosi" in result.answer
    assert "5 vuotta" in result.answer
    assert "cheaper" not in result.answer.casefold()


def test_pull_request_workflow_runs_the_fake_tests_only():
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    assert "pull_request:" in workflow
    assert "uv run pytest" in workflow
    assert "eval-run" not in workflow
    live = (ROOT / ".github" / "workflows" / "eval.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in live
    assert "pull_request:" not in live
    assert "uv run eval-run" in live

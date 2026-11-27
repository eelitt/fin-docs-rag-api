from fin_docs_rag.domain.models import Chunk
from fin_docs_rag.ingest.sheet import apply_grammar_sheet, build_sheet, write_grammar_sheet
from fin_docs_rag.ports import ModelCall

_COSTS = (
    "Jatkuvaluonteiset kulut [vuosittain] 0,30 % vuodessa. "
    "Hallinnolliset maksut ja muut hallinto- tai toimintakulut 30 EUR "
    "Liiketoimikulut 0,07 % sijoituksen arvosta."
)
_RISKS = "Tuotteen riskiluokaksi on asteikolla 1–7 määritetty 2, joka on matala riskiluokka."
_HOLDING = "Suositeltu sijoitusaika: 1 vuosi Rahasto ei ehkä sovellu 1 vuoden kuluessa."

_TEXT = "Rahasto sijoittaa korkoihin. Hallinnolliset maksut 0,30 %. määritetty 2. 5 vuotta."


class FakeChat:
    def __init__(self) -> None:
        self.last_call = None
        self.called = 0

    def complete(self, prompt_id: str, payload: dict) -> dict:
        self.called += 1
        self.last_call = ModelCall(prompt_id, "fake", "fake", 1, 1, 1)
        assert prompt_id == "extract_v1"
        chunk_id = payload["chunks"][0]["id"]
        return {
            "columns": [
                {"field": "product", "status": "present", "chunk_id": chunk_id, "quote": "Rahasto sijoittaa korkoihin.", "number": None},
                {"field": "sri", "status": "present", "chunk_id": chunk_id, "quote": "2", "number": 2},
                {"field": "holding_period", "status": "present", "chunk_id": chunk_id, "quote": "5 vuotta", "number": 5},
                {"field": "ongoing_charge", "status": "present", "chunk_id": chunk_id, "quote": "0,30 %", "number": 0.3},
                {"field": "entry_cost", "status": "absent", "chunk_id": "", "quote": "", "number": None},
                {"field": "exit_cost", "status": "present", "chunk_id": chunk_id, "quote": "9,99 %", "number": 9.99},
            ]
        }


def test_one_kid_extract_builds_a_row_for_each_isin():
    chunk = Chunk("FI0008804729:costs:3:0", "FI0008804729", "costs", 3, 0, _TEXT, title="Kid")
    chat = FakeChat()
    document = build_sheet([("FI0008804729", ["FI0008804729", "FI0008804687"], [chunk])], chat)
    assert chat.called == 1
    assert [row["isin"] for row in document["funds"]] == ["FI0008804729", "FI0008804687"]
    row = document["funds"][0]
    assert row["ongoing_charge"]["state"] == "stated"
    assert row["entry_cost"] == {"state": "not_stated"}
    assert row["exit_cost"] == {"state": "not_extracted"}
    assert document["funds"][1]["ongoing_charge"] == row["ongoing_charge"]


def test_a_bad_extract_does_not_return_a_document():
    chunk = Chunk("FI0008804729:costs:3:0", "FI0008804729", "costs", 3, 0, _TEXT, title="Kid")

    class Broken(FakeChat):
        def complete(self, prompt_id: str, payload: dict) -> dict:
            self.last_call = ModelCall(prompt_id, "fake", "fake", 1, 1, 1)
            return {"columns": []}

    try:
        build_sheet([("FI0008804729", ["FI0008804729"], [chunk])], Broken())
    except ValueError as error:
        assert "FI0008804729" in str(error)
    else:
        raise AssertionError("expected ValueError")


def _grammar_chunks(charge: str = _COSTS) -> list[Chunk]:
    return [
        Chunk("FI0008804729:costs:3:0", "FI0008804729", "costs", 3, 0, charge, title="KID"),
        Chunk("FI0008804729:risks:2:0", "FI0008804729", "risks", 2, 0, _RISKS, title="KID"),
        Chunk("FI0008804729:holding:3:0", "FI0008804729", "holding", 3, 0, _HOLDING, title="KID"),
    ]


def _stored_sheet():
    return {
        "funds": [
            {
                "isin": "FI0008804729",
                "product": {"state": "stated", "quote": "Rahasto"},
                "sri": {"state": "not_extracted"},
                "holding_period": {"state": "not_extracted"},
                "ongoing_charge": {"state": "not_extracted"},
                "entry_cost": {"state": "stated", "quote": "0 EUR", "number": 0},
                "exit_cost": {"state": "not_stated"},
            }
        ]
    }


def test_stated_grammar_replaces_the_model_ongoing_charge():
    chunk = _grammar_chunks()[0]
    chat = FakeChat()
    document = build_sheet([("FI0008804729", ["FI0008804729"], [chunk])], chat)
    cell = document["funds"][0]["ongoing_charge"]
    assert cell["quote"] == "0,30 %"
    assert cell["number"] == 0.3
    assert cell["passage"]
    assert chat.called == 1


def test_grammar_sheet_fills_regulated_columns_and_leaves_entry():
    updated = apply_grammar_sheet(_stored_sheet(), [("FI0008804729", ["FI0008804729"], _grammar_chunks())])
    row = updated["funds"][0]
    assert row["ongoing_charge"]["state"] == "stated"
    assert row["sri"]["quote"] == "määritetty 2"
    assert row["holding_period"]["quote"] == "Suositeltu sijoitusaika: 1 vuosi"
    assert row["entry_cost"]["quote"] == "0 EUR"
    assert row["exit_cost"] == {"state": "not_stated"}


def test_a_miss_does_not_replace_the_stored_sheet():
    class Store:
        def __init__(self):
            self.puts = 0

        def get(self, name):
            return b'{"funds": []}'

        def put(self, name, data):
            self.puts += 1

    store = Store()
    try:
        write_grammar_sheet(store, [("FI0008804729", ["FI0008804729"], _grammar_chunks("no charge here"))])
    except ValueError as error:
        assert "was not extracted" in str(error)
    else:
        raise AssertionError("expected ValueError")
    assert store.puts == 0


def test_two_files_that_disagree_leave_the_sheet():
    other = (
        "Hallinnointipalkkio ja muut hallinto- tai toimintakulut 0,9 prosenttia "
        "sijoituksen arvosta vuosittain. 94 euroa Kaupankäyntikulut"
    )
    kids = [
        ("FI0008804729", ["FI0008804729"], _grammar_chunks()),
        ("FI0008804687", ["FI0008804729"], _grammar_chunks(other)),
    ]
    try:
        apply_grammar_sheet(_stored_sheet(), kids)
    except ValueError as error:
        assert "disagree" in str(error)
    else:
        raise AssertionError("expected ValueError")


def test_an_uncovered_isin_leaves_the_sheet():
    try:
        apply_grammar_sheet(_stored_sheet(), [("FI0008804687", ["FI0008804687"], _grammar_chunks())])
    except ValueError as error:
        assert "uncovered ISIN" in str(error)
    else:
        raise AssertionError("expected ValueError")

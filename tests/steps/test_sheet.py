from fin_docs_rag.domain.models import Chunk
from fin_docs_rag.ingest.sheet import build_sheet
from fin_docs_rag.ports import ModelCall

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

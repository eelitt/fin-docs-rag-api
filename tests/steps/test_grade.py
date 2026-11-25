from fin_docs_rag.domain.models import Chunk
from fin_docs_rag.ports import ModelCall
from fin_docs_rag.steps.grade import grade


class FakeChat:
    def __init__(self, relevant: set[str]) -> None:
        self.relevant = relevant
        self.last_call = None

    def complete(self, prompt_id: str, payload: dict) -> dict:
        self.last_call = ModelCall(prompt_id, "fake", "fake", 1, 1, 1)
        return {
            "chunks": [
                {"id": item["id"], "relevant": item["id"] in self.relevant}
                for item in payload["chunks"]
            ]
        }


def _chunk(name: str) -> Chunk:
    return Chunk(name, "doc", "section", 1, 0, name)


def test_grade_keeps_relevant_chunks_in_order_up_to_four():
    chunks = [_chunk(str(index)) for index in range(6)]
    kept, call = grade("question", [], chunks, FakeChat({"0", "1", "2", "3", "5"}))
    assert [chunk.id for chunk in kept] == ["0", "1", "2", "3"]
    assert call.prompt_id == "grade_v1"

from collections.abc import Sequence

from fin_docs_rag.domain.models import Chunk
from fin_docs_rag.ports import Chat, DependencyFailure, ModelCall


def grade(
    question: str,
    instrument_ids: Sequence[str],
    chunks: Sequence[Chunk],
    chat: Chat,
) -> tuple[list[Chunk], ModelCall]:
    payload: dict = {
        "question": question,
        "chunks": [{"id": chunk.id, "text": chunk.text} for chunk in chunks],
    }
    if instrument_ids:
        payload["instrument_ids"] = list(instrument_ids)
    data = chat.complete("grade_v1", payload)
    call = chat.last_call
    if call is None:
        raise DependencyFailure("grade")
    relevant = {item["id"] for item in data["chunks"] if item["relevant"]}
    kept = [chunk for chunk in chunks if chunk.id in relevant][:4]
    return kept, call

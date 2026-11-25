from collections.abc import Sequence

from fin_docs_rag.domain.models import Chunk
from fin_docs_rag.ports import Chat, DependencyFailure, ModelCall


def draft_answer(
    question: str,
    instrument_ids: Sequence[str],
    chunks: Sequence[Chunk],
    chat: Chat,
) -> tuple[dict, ModelCall]:
    payload: dict = {
        "question": question,
        "chunks": [{"id": chunk.id, "text": chunk.text} for chunk in chunks],
    }
    if instrument_ids:
        payload["instrument_ids"] = list(instrument_ids)
    data = chat.complete("answer_v1", payload)
    call = chat.last_call
    if call is None:
        raise DependencyFailure("answer")
    return data, call

from collections.abc import Sequence

from fin_docs_rag.domain.models import Chunk
from fin_docs_rag.ports import Chat, DependencyFailure


def extract_kid(chunks: Sequence[Chunk], chat: Chat) -> dict:
    data = chat.complete(
        "extract_v1",
        {
            "chunks": [
                {"id": chunk.id, "section": chunk.section, "page": chunk.page, "text": chunk.text}
                for chunk in chunks
            ]
        },
    )
    if chat.last_call is None:
        raise DependencyFailure("extract")
    return data

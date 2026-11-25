from collections.abc import Sequence

from fin_docs_rag.domain.models import Chunk
from fin_docs_rag.ports import DependencyFailure, Embedder, ModelCall, Searcher


def retrieve(
    query: str,
    isin_filter: Sequence[str] | None,
    embedder: Embedder,
    search: Searcher,
) -> tuple[list[Chunk], ModelCall]:
    try:
        vector = embedder.embed(query)
    except DependencyFailure:
        raise
    except Exception as error:
        raise DependencyFailure("embed") from error
    call = embedder.last_call
    if call is None:
        raise DependencyFailure("embed")
    try:
        chunks = search.hybrid(query, vector, None if not isin_filter else list(isin_filter))
    except DependencyFailure:
        raise
    except Exception as error:
        raise DependencyFailure("search") from error
    return chunks, call

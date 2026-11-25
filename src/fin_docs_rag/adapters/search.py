from collections.abc import Sequence

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    HnswParameters,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchAlgorithmMetric,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery

from fin_docs_rag.domain.isin import is_isin
from fin_docs_rag.domain.models import Chunk

_TOP = 8
_UPLOAD_BATCH = 50


class AzureSearch:
    def __init__(self, endpoint: str, api_key: str, index_name: str) -> None:
        credential = AzureKeyCredential(api_key)
        self._index_name = index_name
        self._indexes = SearchIndexClient(endpoint, credential)
        self._docs = SearchClient(endpoint, index_name, credential)

    def create_index(self) -> None:
        self._indexes.create_or_update_index(_index(self._index_name))

    def upload(self, documents: Sequence[dict]) -> None:
        for start in range(0, len(documents), _UPLOAD_BATCH):
            results = self._docs.upload_documents(list(documents[start : start + _UPLOAD_BATCH]))
            failed = [item for item in results if not item.succeeded]
            if failed:
                raise RuntimeError(failed[0].error_message or "index upload failed")

    def hybrid(
        self,
        query: str,
        vector: Sequence[float],
        isin_filter: Sequence[str] | None,
    ) -> list[Chunk]:
        results = self._docs.search(
            search_text=query,
            vector_queries=[
                VectorizedQuery(
                    vector=list(vector),
                    k_nearest_neighbors=_TOP,
                    fields="content_vector",
                )
            ],
            filter=_isin_filter(isin_filter),
            top=_TOP,
            select=["id", "content", "doc_id", "source_title", "page", "section"],
        )
        return [
            Chunk(
                id=hit["id"],
                doc_id=hit["doc_id"],
                section=hit["section"],
                page=int(hit["page"]),
                window=_window(hit["id"]),
                text=hit["content"],
                title=hit.get("source_title") or "",
            )
            for hit in results
        ]

    def ping(self) -> None:
        self._indexes.get_index(self._index_name)


def chunk_key(chunk_id: str) -> str:
    """Search document keys cannot contain ':'. The stored id field keeps the colon form."""
    return chunk_id.replace(":", "_")


def _window(chunk_id: str) -> int:
    return int(chunk_id.rsplit(":", 1)[1])


def _isin_filter(isins: Sequence[str] | None) -> str | None:
    if not isins:
        return None
    if any(not is_isin(value) for value in isins):
        raise ValueError("isin filter contains a value that is not an ISIN")
    joined = ",".join(isins)
    return f"isin/any(i: search.in(i, '{joined}', ','))"


def _index(name: str) -> SearchIndex:
    return SearchIndex(
        name=name,
        fields=[
            SimpleField(name="chunk_key", type=SearchFieldDataType.String, key=True),
            SimpleField(name="id", type=SearchFieldDataType.String, filterable=True),
            SearchableField(
                name="content",
                type=SearchFieldDataType.String,
                analyzer_name="fi.microsoft",
            ),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                retrievable=False,
                vector_search_dimensions=1536,
                vector_search_profile_name="content-profile",
            ),
            SimpleField(name="doc_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="source_title", type=SearchFieldDataType.String),
            SimpleField(name="page", type=SearchFieldDataType.Int32),
            SimpleField(name="section", type=SearchFieldDataType.String, filterable=True),
            SearchField(
                name="isin",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                filterable=True,
            ),
            SimpleField(name="language", type=SearchFieldDataType.String, filterable=True),
        ],
        vector_search=VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="content-hnsw",
                    parameters=HnswParameters(metric=VectorSearchAlgorithmMetric.COSINE),
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="content-profile",
                    algorithm_configuration_name="content-hnsw",
                )
            ],
        ),
    )

import os

import pytest

from fin_docs_rag.composition import build_ingest
from fin_docs_rag.config import settings_from_env

QUERY = "Hallinnolliset maksut ja muut hallinto- tai toimintakulut 0,30 %"


@pytest.mark.skipif(not os.environ.get("AZURE_SEARCH_API_KEY"), reason="Azure credentials are not in the environment")
def test_hybrid_query_returns_known_charge():
    settings = settings_from_env()
    _blob, embedder, search = build_ingest(settings)
    hits = search.hybrid(QUERY, embedder.embed(QUERY), ["FI0008804729"])
    assert any("0,30 %" in hit.text and hit.section == "costs" and hit.doc_id == "FI0008804729" for hit in hits)

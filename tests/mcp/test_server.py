import asyncio
import inspect

from mcp import Client

from fin_docs_rag.domain.models import NUMERIC_COLUMNS, Chunk
from fin_docs_rag.http.app import create_app
from fin_docs_rag.mcp_server import build_server
from fin_docs_rag.ports import DependencyFailure, ModelCall

_SHEET = {
    "funds": [
        {
            "isin": "FI0008804729",
            "product": {"state": "not_stated"},
            "sri": {"state": "stated", "number": 2, "quote": "2", "citation": {"source_id": "a", "title": "Kid", "quote": "2"}},
            "holding_period": {
                "state": "stated",
                "number": 5,
                "quote": "5 vuotta",
                "citation": {"source_id": "a", "title": "Kid", "quote": "5 vuotta"},
            },
            "ongoing_charge": {
                "state": "stated",
                "number": 0.3,
                "quote": "0,30 %",
                "citation": {"source_id": "a", "title": "Kid", "quote": "0,30 %"},
            },
            "entry_cost": {"state": "not_stated"},
            "exit_cost": {"state": "not_extracted"},
        },
        {
            "isin": "FI0008804687",
            "product": {"state": "not_stated"},
            "sri": {"state": "stated", "number": 4, "quote": "4", "citation": {"source_id": "b", "title": "Kid", "quote": "4"}},
            "holding_period": {
                "state": "stated",
                "number": 3,
                "quote": "3 vuotta",
                "citation": {"source_id": "b", "title": "Kid", "quote": "3 vuotta"},
            },
            "ongoing_charge": {
                "state": "stated",
                "number": 0.9,
                "quote": "0,9 prosenttia",
                "citation": {"source_id": "b", "title": "Kid", "quote": "0,9 prosenttia"},
            },
            "entry_cost": {"state": "not_stated"},
            "exit_cost": {"state": "not_stated"},
        },
    ]
}


class FakeEmbedder:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.last_call = None

    def embed(self, text: str) -> list[float]:
        self.queries.append(text)
        self.last_call = ModelCall("", "fake", "fake", 1, 8, 0)
        return [0.25, 0.5]


class FakeSearch:
    def __init__(self, hits: list[Chunk] | None = None, fail: bool = False) -> None:
        self.hits = hits or []
        self.fail = fail
        self.calls: list[tuple] = []

    def hybrid(self, query: str, vector: list[float], isin_filter):
        self.calls.append((query, list(vector), None if not isin_filter else list(isin_filter)))
        if self.fail:
            raise DependencyFailure("search")
        return list(self.hits)


def _server(search: FakeSearch | None = None, sheet=None, embedder: FakeEmbedder | None = None):
    finder = search or FakeSearch()
    vectors = embedder or FakeEmbedder()

    def read_sheet():
        if isinstance(sheet, Exception):
            raise sheet
        return _SHEET if sheet is None else sheet

    return build_server(vectors, finder, read_sheet), vectors, finder


def _run(coro):
    return asyncio.run(coro)


def _text(result) -> str:
    if isinstance(result.structured_content, str):
        return result.structured_content
    return result.content[0].text


def test_tool_names_and_schemas_match_the_api_functions():
    server, _, _ = _server()
    tools = {tool.name: tool.input_schema for tool in _run(server.list_tools())}
    assert set(tools) == {"retrieve", "compare_sentence"}
    assert set(tools["retrieve"]["properties"]) == {"query", "isin_filter"}
    assert tools["retrieve"]["required"] == ["query"]
    assert set(tools["compare_sentence"]["properties"]) == {"isin_a", "isin_b", "field"}
    assert set(tools["compare_sentence"]["required"]) == {"isin_a", "isin_b", "field"}
    assert set(tools["compare_sentence"]["properties"]["field"]["enum"]) == set(NUMERIC_COLUMNS)
    assert "expression" not in str(tools)


def test_retrieve_calls_hybrid_search_once():
    chunk = Chunk("FI0008804729:costs:3:0", "FI0008804729", "costs", 3, 0, "0,30 %", "Kid")
    server, embedder, search = _server(FakeSearch([chunk]))

    async def call():
        async with Client(server) as client:
            return await client.call_tool(
                "retrieve",
                {"query": "0,30 %", "isin_filter": ["FI0008804729"]},
            )

    result = _run(call())
    assert result.is_error is False
    assert result.structured_content["result"] == [
        {
            "id": "FI0008804729:costs:3:0",
            "doc_id": "FI0008804729",
            "section": "costs",
            "page": 3,
            "window": 0,
            "text": "0,30 %",
            "title": "Kid",
        }
    ]
    assert embedder.queries == ["0,30 %"]
    assert search.calls == [("0,30 %", [0.25, 0.5], ["FI0008804729"])]
    source = inspect.getsource(build_server)
    assert "VectorizedQuery" not in source
    assert "search_text" not in source


def test_compare_sentence_fills_the_template_from_the_sheet():
    server, embedder, search = _server()

    async def call():
        async with Client(server) as client:
            return await client.call_tool(
                "compare_sentence",
                {
                    "isin_a": "FI0008804729",
                    "isin_b": "FI0008804687",
                    "field": "ongoing_charge",
                },
            )

    result = _run(call())
    sentence = _text(result)
    assert result.is_error is False
    assert "0.3" in sentence and "0,30 %" in sentence
    assert "0.9" in sentence and "0,9 prosenttia" in sentence
    assert "5 vuotta" in sentence and "3 vuotta" in sentence
    assert "The difference, FI0008804729 minus FI0008804687, is -0.6 percentage points." in sentence
    assert embedder.queries == []
    assert search.calls == []


def test_an_expression_is_ignored_and_a_bad_isin_is_rejected():
    server, _, search = _server()

    async def call(arguments):
        async with Client(server) as client:
            return await client.call_tool("compare_sentence", arguments)

    extra = _run(call({"isin_a": "FI0008804729", "isin_b": "FI0008804687", "field": "ongoing_charge", "expression": "a-b"}))
    bad = _run(call({"isin_a": "not-an-isin", "isin_b": "FI0008804687", "field": "ongoing_charge"}))
    unknown = _run(call({"isin_a": "FI0008804729", "isin_b": "FI0008804687", "field": "advice"}))
    assert extra.is_error is False
    assert "a-b" not in _text(extra)
    assert "is -0.6 percentage points." in _text(extra)
    assert bad.is_error is True and "invalid_instrument_id" in _text(bad)
    assert unknown.is_error is True
    assert search.calls == []


def test_a_search_failure_is_unavailable():
    server, _, _ = _server(FakeSearch(fail=True))

    async def call():
        async with Client(server) as client:
            return await client.call_tool("retrieve", {"query": "cost"})

    result = _run(call())
    assert result.is_error is True
    assert "unavailable" in _text(result)


def test_the_public_app_does_not_serve_mcp():
    app = create_app(read_sheet=lambda: {"funds": []}, ping=lambda: None, ask=lambda envelope: None)
    paths = [getattr(route, "path", "") for route in app.routes]
    assert not any("mcp" in path for path in paths)

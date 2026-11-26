import json
from collections.abc import Callable
from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from fin_docs_rag.domain.calculate import compare_sentence as fill_comparison
from fin_docs_rag.domain.isin import is_isin
from fin_docs_rag.domain.models import NUMERIC_COLUMNS, cell_from_dict
from fin_docs_rag.ports import DependencyFailure, Embedder, Searcher
from fin_docs_rag.steps.retrieve import retrieve as search_chunks

_Field = Literal["sri", "holding_period", "ongoing_charge", "entry_cost", "exit_cost"]


def build_server(embedder: Embedder, search: Searcher, read_sheet: Callable[[], dict]) -> MCPServer:
    server = MCPServer("fin-docs-rag")

    @server.tool()
    def retrieve(query: str, isin_filter: list[str] | None = None) -> list[dict]:
        """Embed the query and run hybrid search. This is the search function the API uses."""
        if isin_filter:
            for value in isin_filter:
                if not is_isin(value):
                    raise ToolError("invalid_instrument_id")
        try:
            chunks, _call = search_chunks(query, isin_filter, embedder, search)
        except DependencyFailure as error:
            raise ToolError("unavailable") from error
        return [
            {
                "id": chunk.id,
                "doc_id": chunk.doc_id,
                "section": chunk.section,
                "page": chunk.page,
                "window": chunk.window,
                "text": chunk.text,
                "title": chunk.title,
            }
            for chunk in chunks
        ]

    @server.tool()
    def compare_sentence(isin_a: str, isin_b: str, field: _Field) -> str:
        """Fill the comparison template for one stored sheet column. No expression and no supplied numbers."""
        if field not in NUMERIC_COLUMNS:
            raise ToolError("unknown field")
        if not is_isin(isin_a) or not is_isin(isin_b) or isin_a == isin_b:
            raise ToolError("invalid_instrument_id")
        try:
            document = read_sheet()
        except DependencyFailure as error:
            raise ToolError("unavailable") from error
        rows = {row["isin"]: row for row in document["funds"]}
        cell_a, holding_a = _cells(rows.get(isin_a), field)
        cell_b, holding_b = _cells(rows.get(isin_b), field)
        return fill_comparison(isin_a, cell_a, isin_b, cell_b, field, holding_a, holding_b)

    return server


def _cells(row: dict | None, field: str):
    if row is None:
        return None, None
    return cell_from_dict(row[field]), cell_from_dict(row["holding_period"])


def main() -> None:
    from pathlib import Path

    from fin_docs_rag.composition import build_ingest
    from fin_docs_rag.config import load_env_file, settings_from_env

    load_env_file(Path.cwd() / ".env")
    settings = settings_from_env()
    blob, embedder, search = build_ingest(settings)

    def read_sheet() -> dict:
        try:
            data = json.loads(blob.get("sheet.json"))
        except Exception as error:
            raise DependencyFailure("sheet") from error
        if not isinstance(data, dict) or not isinstance(data.get("funds"), list):
            raise DependencyFailure("sheet")
        return data

    build_server(embedder, search, read_sheet).run(transport="stdio")


if __name__ == "__main__":
    main()

import copy
import json

from fin_docs_rag.domain.kid_cost import holding_from_chunks, ongoing_charge_from_chunks, sri_from_chunks
from fin_docs_rag.domain.models import Chunk, SheetCell, row_dict
from fin_docs_rag.domain.verify import cells_from_claims, same_number
from fin_docs_rag.ports import BlobStore, Chat, DependencyFailure
from fin_docs_rag.steps.extract import extract_kid

_GRAMMAR = (
    ("ongoing_charge", ongoing_charge_from_chunks),
    ("sri", sri_from_chunks),
    ("holding_period", holding_from_chunks),
)


def build_sheet(kids: list[tuple[str, list[str], list[Chunk]]], chat: Chat) -> dict:
    funds = []
    for doc_id, isins, chunks in kids:
        try:
            raw = extract_kid(chunks, chat)
        except DependencyFailure as error:
            raise ValueError(f"{doc_id} extract failed") from error
        columns = raw.get("columns")
        if not isinstance(columns, list):
            raise ValueError(f"{doc_id} extract did not return columns")
        try:
            cells = cells_from_claims(columns, chunks)
        except ValueError as error:
            raise ValueError(f"{doc_id} {error}") from None
        _overlay(cells, chunks)
        for isin in isins:
            funds.append(row_dict(isin, cells))
    return {"funds": funds}


def apply_grammar_sheet(current: dict, kids: list[tuple[str, list[str], list[Chunk]]]) -> dict:
    by_isin: dict[str, dict[str, SheetCell]] = {}
    owners: dict[str, str] = {}
    for doc_id, isins, chunks in kids:
        cells = _required(doc_id, chunks)
        for isin in isins:
            previous = by_isin.get(isin)
            if previous is not None and owners[isin] != doc_id and not _same(previous, cells):
                raise ValueError(f"{isin} is in two files that disagree")
            if previous is None:
                by_isin[isin] = cells
                owners[isin] = doc_id
    updated = copy.deepcopy(current)
    funds = updated.get("funds")
    if not isinstance(funds, list):
        raise ValueError("sheet has no funds")
    seen: set[str] = set()
    for row in funds:
        isin = row.get("isin")
        if not isinstance(isin, str) or isin not in by_isin:
            raise ValueError(f"uncovered ISIN {isin}")
        seen.add(isin)
        for field, cell in by_isin[isin].items():
            row[field] = cell.to_dict()
    extra = set(by_isin) - seen
    if extra:
        raise ValueError(f"uncovered ISIN {sorted(extra)[0]}")
    return updated


def write_grammar_sheet(blob: BlobStore, kids: list[tuple[str, list[str], list[Chunk]]]) -> dict:
    current = json.loads(blob.get("sheet.json"))
    updated = apply_grammar_sheet(current, kids)
    blob.put("sheet.json", sheet_bytes(updated))
    return updated


def _overlay(cells: dict[str, SheetCell], chunks: list[Chunk]) -> None:
    for field, parse in _GRAMMAR:
        cell = parse(chunks)
        if cell.state == "stated":
            cells[field] = cell


def _required(doc_id: str, chunks: list[Chunk]) -> dict[str, SheetCell]:
    cells: dict[str, SheetCell] = {}
    for field, parse in _GRAMMAR:
        cell = parse(chunks)
        if cell.state != "stated":
            raise ValueError(f"{doc_id} {field} was not extracted")
        cells[field] = cell
    return cells


def _same(left: dict[str, SheetCell], right: dict[str, SheetCell]) -> bool:
    for field in left:
        a, b = left[field], right[field]
        if a.quote != b.quote or not same_number(a.number or 0, b.number or 0):
            return False
    return True


def sheet_bytes(document: dict) -> bytes:
    return (json.dumps(document, ensure_ascii=False) + "\n").encode()

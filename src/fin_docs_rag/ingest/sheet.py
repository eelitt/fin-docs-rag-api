import json

from fin_docs_rag.domain.models import Chunk, row_dict
from fin_docs_rag.domain.verify import cells_from_claims
from fin_docs_rag.ports import Chat, DependencyFailure
from fin_docs_rag.steps.extract import extract_kid


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
        for isin in isins:
            funds.append(row_dict(isin, cells))
    return {"funds": funds}


def sheet_bytes(document: dict) -> bytes:
    return (json.dumps(document, ensure_ascii=False) + "\n").encode()

"""Upload the corpus, embed it, and push the search index."""

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from fin_docs_rag.adapters.search import chunk_key
from fin_docs_rag.composition import build_chat, build_ingest
from fin_docs_rag.config import ConfigError, load_env_file, settings_from_env
from fin_docs_rag.domain.chunking import chunk_document
from fin_docs_rag.domain.isin import isins_in
from fin_docs_rag.domain.models import Chunk
from fin_docs_rag.ingest.parse_pdf import NoTextLayer, parse_pdf
from fin_docs_rag.ingest.sheet import build_sheet, sheet_bytes

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "sources" / "manifest.json"
PDFS = ROOT / "data" / "pdfs"
REQUIRED = (
    "id",
    "title",
    "publisher",
    "url",
    "retrieved",
    "license_note",
    "language",
    "kind",
    "file",
    "isins",
)


def index_corpus(blob, embedder, search, chat) -> int:
    documents = json.loads(MANIFEST.read_text(encoding="utf-8"))
    blob.ensure_container()
    search.create_index()
    total = 0
    kids: list[tuple[str, list[str], list[Chunk]]] = []
    for document in documents:
        missing = [field for field in REQUIRED if field not in document]
        if missing:
            raise SystemExit(f"{document.get('id', '?')} is missing {missing}")
        doc_id = document["id"]
        kind = document["kind"]
        if kind not in ("kid", "report"):
            raise SystemExit(f"{doc_id} has unknown kind {kind}")
        path = PDFS / document["file"]
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"{doc_id} is missing {path}. Run scripts/download_sources.py first.")
        data = path.read_bytes()
        try:
            pages = parse_pdf(data)
        except NoTextLayer:
            raise SystemExit(f"{doc_id} has no text layer") from None
        chunks = chunk_document(doc_id, [(page.number, page.text) for page in pages], kind)
        document_isins = isins_in("\n".join(page.text for page in pages))
        if kind == "kid" and not document_isins:
            raise SystemExit(f"{doc_id} has no parseable ISIN")
        blob.put(document["file"], data)
        vectors = embedder.embed_many([chunk.text for chunk in chunks])
        search.upload(
            [
                _document(chunk, vector, document, document_isins if kind == "kid" else isins_in(chunk.text))
                for chunk, vector in zip(chunks, vectors, strict=True)
            ]
        )
        if kind == "kid":
            kids.append((doc_id, document_isins, [replace(chunk, title=document["title"]) for chunk in chunks]))
        total += len(chunks)
        print(f"indexed {doc_id} {len(chunks)}", file=sys.stderr)
    try:
        blob.put("sheet.json", sheet_bytes(build_sheet(kids, chat)))
    except ValueError as error:
        raise SystemExit(f"sheet extract failed: {error}") from None
    return total


def _document(chunk: Chunk, vector: list[float], document: dict, isins: list[str]) -> dict:
    return {
        "chunk_key": chunk_key(chunk.id),
        "id": chunk.id,
        "content": chunk.text,
        "content_vector": vector,
        "doc_id": chunk.doc_id,
        "source_title": document["title"],
        "page": chunk.page,
        "section": chunk.section,
        "isin": isins,
        "language": document["language"],
    }


def main() -> None:
    load_env_file(ROOT / ".env")
    parser = argparse.ArgumentParser(prog="ingest")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("index")
    query = sub.add_parser("query")
    query.add_argument("text")
    query.add_argument("--isin", action="append")
    args = parser.parse_args()
    try:
        settings = settings_from_env()
        blob, embedder, search = build_ingest(settings)
    except ConfigError as error:
        raise SystemExit(str(error)) from None
    if args.command == "index":
        try:
            chat = build_chat(settings)
        except ConfigError as error:
            raise SystemExit(str(error)) from None
        count = index_corpus(blob, embedder, search, chat)
        print(f"indexed {count} chunks")
        return
    hits = search.hybrid(args.text, embedder.embed(args.text), args.isin)
    for hit in hits:
        print(f"{hit.id}\n{hit.text}\n")


if __name__ == "__main__":
    main()

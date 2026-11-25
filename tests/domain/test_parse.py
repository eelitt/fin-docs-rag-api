import json
from pathlib import Path

import pymupdf
import pytest

from fin_docs_rag.domain.chunking import chunk_document
from fin_docs_rag.ingest.parse_pdf import NoTextLayer, parse_pdf

ROOT = Path(__file__).resolve().parents[2]
PDFS = ROOT / "data" / "pdfs"
MANIFEST = json.loads((ROOT / "sources" / "manifest.json").read_text(encoding="utf-8"))


def _chunks(document_id: str):
    document = next(item for item in MANIFEST if item["id"] == document_id)
    pages = parse_pdf((PDFS / document["file"]).read_bytes())
    return chunk_document(document_id, [(page.number, page.text) for page in pages], document["kind"])


def test_blank_pdf_has_no_text_layer():
    blank = pymupdf.open()
    blank.new_page()
    with pytest.raises(NoTextLayer):
        parse_pdf(blank.tobytes())


def test_known_cost_and_risk_indicator_each_sit_in_one_chunk():
    chunks = _chunks("FI0008804729")
    cost = [chunk for chunk in chunks if "0,30 %" in chunk.text]
    risk = [chunk for chunk in chunks if "määritetty 2" in chunk.text]
    assert len(cost) == 1
    assert len(risk) == 1
    assert cost[0].section == "costs"
    assert risk[0].section == "risks"
    assert ":" not in cost[0].section
    assert cost[0].id == f"FI0008804729:costs:{cost[0].page}:{cost[0].window}"


def test_second_kid_keeps_its_cost_and_risk_indicator():
    chunks = _chunks("FI0008804687")
    assert sum("0,9 prosenttia" in chunk.text for chunk in chunks) == 1
    assert sum("määritetty 4" in chunk.text for chunk in chunks) == 1


def test_every_kid_has_a_cost_section_and_a_risk_section():
    for document in MANIFEST:
        if document["kind"] != "kid":
            continue
        chunks = _chunks(document["id"])
        sections = {chunk.section for chunk in chunks}
        assert "costs" in sections, document["id"]
        assert "risks" in sections, document["id"]


def test_longer_report_chunks_on_its_headings():
    chunks = _chunks("report-2026-q3")
    article = [
        chunk
        for chunk in chunks
        if chunk.section == "sijoittamisen-nelja-todellista-riskia"
        and "Sijoittajat pelkäävät usein vääriä asioita" in chunk.text
    ]
    assert article
    assert all(chunk.window == 0 or chunk.id.count(":") == 3 for chunk in chunks)
    assert len(chunks) > 10

import importlib.util
import json
from pathlib import Path

from fin_docs_rag.domain.chunking import chunk_document
from fin_docs_rag.domain.kid_cost import holding_from_chunks, ongoing_charge_from_chunks, sri_from_chunks
from fin_docs_rag.domain.models import Chunk
from fin_docs_rag.domain.verify import same_number
from fin_docs_rag.ingest.parse_pdf import parse_pdf

ROOT = Path(__file__).resolve().parents[2]
PDFS = ROOT / "data" / "pdfs"
MANIFEST = json.loads((ROOT / "sources" / "manifest.json").read_text(encoding="utf-8"))

_NINE = (
    "Jatkuvaluonteiset kulut [vuosittain] 0,30 % vuodessa. "
    "Hallinnolliset maksut ja muut hallinto- tai toimintakulut 30 EUR "
    "Liiketoimikulut 0,07 % sijoituksen arvosta."
)
_FEE = (
    "Hallinnointipalkkio ja muut hallinto- tai toimintakulut 0,9 prosenttia "
    "sijoituksen arvosta vuosittain. 94 euroa Kaupankäyntikulut 0,1 prosenttia"
)
_SPLIT = (
    "Jatkuvaluonteiset kulut Hallinnolliset maksut ja muut hallinto- tai toimin- tamaksut "
    "1,9 prosenttia sijoituksen arvosta vuosittain. 191 euroa Liiketoimikulut 0,1 prosenttia"
)
_EURO_ONLY = (
    "Jatkuvaluonteiset kulut [vuosittain] "
    "Hallinnolliset maksut ja muut hallinto- tai toimintakulut 30 EUR "
    "Liiketoimikulut 0,07 %"
)
_TWO = (
    "Hallinnointipalkkio ja muut hallinto- tai toimintakulut "
    "0,9 prosenttia tai 1,1 prosenttia 94 euroa Kaupankäyntikulut"
)


def _chunk(text: str) -> Chunk:
    return Chunk("FI0008804729:costs:3:0", "FI0008804729", "costs", 3, 0, text, title="KID")


def test_percent_before_the_label_is_the_ongoing_charge():
    cell = ongoing_charge_from_chunks([_chunk(_NINE)])
    assert cell.state == "stated"
    assert cell.quote == "0,30 %"
    assert same_number(cell.number, 0.30)
    assert cell.passage == _NINE


def test_hallinnointipalkkio_uses_prosenttia_before_the_euro_amount():
    cell = ongoing_charge_from_chunks([_chunk(_FEE)])
    assert cell.quote == "0,9 prosenttia"
    assert same_number(cell.number, 0.9)


def test_hyphen_break_and_toimintamaksut_still_match():
    cell = ongoing_charge_from_chunks([_chunk(_SPLIT)])
    assert cell.quote == "1,9 prosenttia"
    assert same_number(cell.number, 1.9)


def test_euro_amount_and_transaction_cost_are_not_the_ongoing_charge():
    cell = ongoing_charge_from_chunks([_chunk(_EURO_ONLY)])
    assert cell.state == "not_extracted"
    assert cell.quote is None


def test_risk_indicator_quote_is_the_printed_level():
    text = "Tuotteen riskiluokaksi on asteikolla 1–7 määritetty 2, joka on matala riskiluokka."
    cell = sri_from_chunks([Chunk("FI0008804729:risks:2:0", "FI0008804729", "risks", 2, 0, text, title="KID")])
    assert cell.quote == "määritetty 2"
    assert same_number(cell.number, 2)
    assert "1–7" not in cell.quote


def test_holding_sentence_keeps_three_months_as_printed():
    text = (
        "Suositeltu sijoitusaika: 3 kuukautta Rahasto ei ehkä sovellu "
        "sijoittajille 0,25 vuoden (3 kk) kuluessa."
    )
    cell = holding_from_chunks([Chunk("FI0008801733:holding:3:0", "FI0008801733", "holding", 3, 0, text)])
    assert cell.quote == "Suositeltu sijoitusaika: 3 kuukautta"
    assert same_number(cell.number, 3)


def test_holding_sentence_keeps_the_printed_period():
    text = "Suositeltu sijoitusaika on 5 vuotta. Tuote on jatkuva."
    cell = holding_from_chunks([Chunk("FI0008804687:holding:3:0", "FI0008804687", "holding", 3, 0, text)])
    assert cell.quote == "Suositeltu sijoitusaika on 5 vuotta."


def test_two_qualifying_percents_raise():
    try:
        ongoing_charge_from_chunks([_chunk(_TWO)])
    except ValueError as error:
        assert "two figures" in str(error)
    else:
        raise AssertionError("expected ValueError")


def _rows():
    path = ROOT / "tests" / "eval" / "test_golden.py"
    spec = importlib.util.spec_from_file_location("golden_rows", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ROWS


def test_manifest_kids_match_the_golden_rows():
    expected = {
        isin: (charge, quote, sri, years, holding)
        for isin, charge, quote, sri, years, holding in _rows()
    }
    for document in MANIFEST:
        if document["kind"] != "kid":
            continue
        pages = parse_pdf((PDFS / document["file"]).read_bytes())
        chunks = chunk_document(document["id"], [(page.number, page.text) for page in pages], "kid")
        cell = ongoing_charge_from_chunks(chunks)
        charge, quote, sri, _years, holding = expected[document["id"]]
        assert cell.state == "stated"
        assert cell.quote == quote
        assert same_number(cell.number, charge)
        risk = sri_from_chunks(chunks)
        period = holding_from_chunks(chunks)
        assert risk.quote == f"määritetty {sri}"
        assert same_number(risk.number, sri)
        assert period.quote == holding
        assert quote in cell.passage
        assert risk.quote in risk.passage
        assert period.quote in period.passage

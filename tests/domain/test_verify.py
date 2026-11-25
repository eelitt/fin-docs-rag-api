from fin_docs_rag.domain.models import COLUMNS, Chunk
from fin_docs_rag.domain.verify import cells_from_claims, quote_in_text

_CHUNK = Chunk(
    id="FI0008804729:costs:3:0",
    doc_id="FI0008804729",
    section="costs",
    page=3,
    window=0,
    text=(
        "Rahasto sijoittaa korkoihin. Hallinnolliset maksut 0,30 %. "
        "määritetty 2. 5 vuotta."
    ),
    title="Kid",
)


def _claim(field: str, status: str, quote: str = "", number=None) -> dict:
    return {
        "field": field,
        "status": status,
        "chunk_id": _CHUNK.id,
        "quote": quote,
        "number": number,
    }


def _claims() -> list[dict]:
    return [
        _claim("product", "present", "Rahasto sijoittaa korkoihin."),
        _claim("sri", "present", "2", 2),
        _claim("holding_period", "present", "5 vuotta", 5),
        _claim("ongoing_charge", "present", "0,30 %", 0.3),
        _claim("entry_cost", "absent"),
        _claim("exit_cost", "present", "9,99 %", 9.99),
    ]


def test_quote_check_folds_case_and_whitespace_and_caps_length():
    assert quote_in_text("HALLINNOLLISET", "hallinnolliset maksut")
    assert quote_in_text("0,30\n%", "cost  0,30 % here")
    assert quote_in_text("a" * 400, "a" * 400)
    assert not quote_in_text("a" * 401, "a" * 401)
    assert not quote_in_text("missing", "hallinnolliset")


def test_one_row_has_each_cell_state():
    cells = cells_from_claims(_claims(), [_CHUNK])
    stated = cells["ongoing_charge"].to_dict()
    assert stated["state"] == "stated"
    assert stated["number"] == 0.3
    assert stated["quote"] == "0,30 %"
    assert stated["citation"]["quote"] == "0,30 %"
    assert stated["citation"]["source_id"] == "FI0008804729"
    assert "number" not in cells["product"].to_dict()
    assert cells["entry_cost"].to_dict() == {"state": "not_stated"}
    assert cells["exit_cost"].to_dict() == {"state": "not_extracted"}
    assert cells["sri"].to_dict()["number"] == 2
    assert set(cells) == set(COLUMNS)


def test_two_figures_or_a_mismatched_number_are_not_extracted():
    text = "0,30 % ja 0,9 prosenttia"
    chunk = Chunk("d:costs:1:0", "d", "costs", 1, 0, text, title="Kid")
    claims = _claims()
    claims[3] = {
        "field": "ongoing_charge",
        "status": "present",
        "chunk_id": chunk.id,
        "quote": text,
        "number": 0.3,
    }
    assert cells_from_claims(claims, [chunk])["ongoing_charge"].state == "not_extracted"
    claims[3]["quote"] = "0,30 %"
    chunk = Chunk("d:costs:1:0", "d", "costs", 1, 0, "0,30 %", title="Kid")
    claims[3]["chunk_id"] = chunk.id
    claims[3]["number"] = 1.2
    assert cells_from_claims(claims, [chunk])["ongoing_charge"].state == "not_extracted"


def test_a_repeated_column_is_rejected():
    claims = _claims()
    claims.append(_claim("sri", "absent"))
    try:
        cells_from_claims(claims, [_CHUNK])
    except ValueError as error:
        assert "each column" in str(error)
    else:
        raise AssertionError("expected ValueError")

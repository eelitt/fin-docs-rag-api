from fin_docs_rag.domain.calculate import compare_sentence, ongoing_comparison
from fin_docs_rag.domain.models import Citation, SheetCell


def _cell(number: float, quote: str) -> SheetCell:
    return SheetCell(
        state="stated",
        quote=quote,
        number=number,
        citation=Citation("doc", "Kid", quote, page=3, section="costs"),
    )


def test_comparison_states_both_periods_and_the_difference():
    sentence = compare_sentence(
        "FI0008804729",
        _cell(0.3, "0,30 %"),
        "FI0008804687",
        _cell(0.9, "0,9 prosenttia"),
        "ongoing_charge",
        _cell(5, "5 vuotta"),
        _cell(3, "3 vuotta"),
    )
    assert "0.3" in sentence and "0,30 %" in sentence
    assert "0.9" in sentence and "0,9 prosenttia" in sentence
    assert "5 vuotta" in sentence and "3 vuotta" in sentence
    assert "The difference, FI0008804729 minus FI0008804687, is -0.6 percentage points." in sentence
    for word in ("cheaper", "better", "prefer", "recommend", "buy"):
        assert word not in sentence.casefold()


def test_a_missing_cell_does_not_invent_a_difference():
    sentence = compare_sentence(
        "FI0008804729",
        SheetCell("not_stated"),
        "FI0008804687",
        SheetCell("not_extracted"),
        "ongoing_charge",
        None,
        None,
    )
    assert "FI0008804729 has no stated ongoing cost." in sentence
    assert "FI0008804687 ongoing cost was not extracted." in sentence
    assert "difference" not in sentence


def test_a_missing_row_is_named():
    sentence = compare_sentence(
        "FI0008804729",
        None,
        "FI0008804687",
        _cell(0.9, "0,9 prosenttia"),
        "ongoing_charge",
        None,
        _cell(3, "3 vuotta"),
    )
    assert "FI0008804729 is not on the sheet." in sentence
    assert "difference" not in sentence


def test_a_holding_sentence_that_ends_with_a_period_is_not_doubled():
    sentence = compare_sentence(
        "FI0008804729",
        _cell(0.3, "0,30 %"),
        "FI0008804687",
        _cell(0.9, "0,9 prosenttia"),
        "ongoing_charge",
        _cell(1, "Suositeltu sijoitusaika: 1 vuosi"),
        _cell(5, "Suositeltu sijoitusaika on 5 vuotta."),
    )
    assert "assumes Suositeltu sijoitusaika: 1 vuosi." in sentence
    assert "assumes Suositeltu sijoitusaika on 5 vuotta." in sentence
    assert "vuotta.." not in sentence


def test_sri_difference_uses_risk_indicator_steps():
    sentence = compare_sentence(
        "A",
        _cell(2, "2"),
        "B",
        _cell(4, "4"),
        "sri",
        _cell(5, "5 vuotta"),
        _cell(5, "5 vuotta"),
    )
    assert "is -2 risk-indicator steps." in sentence


def test_ongoing_comparison_document_uses_the_column_key():
    sheet = {
        "funds": [
            {
                "isin": "FI0008804729",
                "ongoing_charge": _cell(0.3, "0,30 %").to_dict(),
                "holding_period": _cell(5, "5 vuotta").to_dict(),
            },
            {
                "isin": "FI0008804687",
                "ongoing_charge": {"state": "not_stated"},
                "holding_period": {"state": "not_stated"},
            },
        ]
    }
    body = ongoing_comparison(sheet, "FI0008804729", "FI0008801774")
    assert body["field"] == "ongoing_charge"
    assert body["cell_b"] is None
    assert "FI0008801774 is not on the sheet." in body["sentence"]
    assert body["cell_a"]["state"] == "stated"

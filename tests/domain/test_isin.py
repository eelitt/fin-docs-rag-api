from fin_docs_rag.domain.isin import is_isin, isins_in


def test_corpus_isin_passes_the_checksum():
    assert is_isin("FI0008804729")
    assert is_isin("FI0008804687")


def test_bad_check_digit_is_rejected():
    assert not is_isin("FI0008804720")
    assert isins_in("Katso FI0008804720 ja FI0008804729.") == ["FI0008804729"]


def test_scan_is_case_insensitive_and_unique():
    assert isins_in("fi0008804729 ja FI0008804729") == ["FI0008804729"]

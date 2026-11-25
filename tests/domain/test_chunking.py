from fin_docs_rag.domain.chunking import chunk_document


def test_section_under_the_limit_is_one_window():
    pages = [
        (1, "Tarkoitus\nTässä asiakirjassa annetaan avaintiedot."),
        (2, "Mitä kuluja sijoittajalle aiheutuu?\nHallinnolliset maksut 0,30 %."),
    ]
    chunks = chunk_document("FI0000000000", pages, "kid")
    assert [(chunk.section, chunk.page, chunk.window, chunk.id) for chunk in chunks] == [
        ("purpose", 1, 0, "FI0000000000:purpose:1:0"),
        ("costs", 2, 0, "FI0000000000:costs:2:0"),
    ]
    assert chunks[1].text.startswith("Mitä kuluja sijoittajalle aiheutuu?")


def test_wrapped_holding_heading_is_one_section():
    pages = [
        (
            3,
            "Miten pitkäksi aikaa sijoitus olisi tehtävä, ja saako sijoittaja rahansa pois ennen sijoituksen\n"
            "erääntymisaikaa?\n"
            "Suositeltu sijoitusaika on 5 vuotta.",
        )
    ]
    chunks = chunk_document("FI0000000000", pages, "kid")
    assert len(chunks) == 1
    assert chunks[0].section == "holding"
    assert "5 vuotta" in chunks[0].text


def test_long_section_splits_and_ids_stay_stable():
    body = "\n\n".join(f"Kappale {index} " + ("sana " * 200) for index in range(8))
    pages = [(4, "Muut olennaiset tiedot\n" + body)]
    first = chunk_document("FI0000000000", pages, "kid")
    second = chunk_document("FI0000000000", pages, "kid")
    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]
    assert len(first) > 1
    assert [chunk.window for chunk in first] == list(range(len(first)))
    assert all(chunk.page == 4 and chunk.section == "other" for chunk in first)


def test_report_splits_on_its_own_heading():
    pages = [
        (3, "SIJOITTAMISEN NELJÄ TODELLISTA RISKIÄ\nSijoittajat pelkäävät usein vääriä asioita."),
    ]
    chunks = chunk_document("report-2026-q3", pages, "report")
    assert len(chunks) == 1
    assert chunks[0].section == "sijoittamisen-nelja-todellista-riskia"
    assert chunks[0].id == "report-2026-q3:sijoittamisen-nelja-todellista-riskia:3:0"
    assert "vääriä asioita" in chunks[0].text

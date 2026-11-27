import re

from fin_docs_rag.domain.models import Chunk, SheetCell
from fin_docs_rag.domain.verify import citation_for, collapse, figures_in, one_figure_matches, quote_in_text

_LABEL = re.compile(
    r"Hallinnolliset maksut ja muut hallinto-?\s*tai toimin-?\s*ta-?\s*(?:kulut|maksut)"
    r"|Hallinnointipalkkio ja muut hallinto-?\s*tai toimintakulut"
)
_PERCENT = re.compile(r"\d+(?:[.,]\d+)?\s*(?:%|prosenttia)")
_MONEY = re.compile(r"\bEUR\b|\beuroa\b")
_STOP = re.compile(r"Liiketoimikulut|Kaupankäyntikulut")
_BEFORE_LABEL = re.compile(r"(\d+(?:[.,]\d+)?\s*%)\s*vuodessa")
_HEAD = "Jatkuvaluonteiset kulut"


_SRI = re.compile(r"määritetty\s+\d+")
_HOLDING = re.compile(
    r"Suositeltu sijoitusaika(?::| on) \d+(?:[.,]\d+)? (?:kuukautta|vuotta|vuosi)\.?"
)


def ongoing_charge_from_chunks(chunks: list[Chunk]) -> SheetCell:
    return _from_section(chunks, "costs", _quote, "ongoing charge")


def sri_from_chunks(chunks: list[Chunk]) -> SheetCell:
    return _from_section(chunks, "risks", _one_match(_SRI, "risk indicator"), "risk indicator")


def holding_from_chunks(chunks: list[Chunk]) -> SheetCell:
    return _from_section(chunks, "holding", _one_match(_HOLDING, "holding period"), "holding period")


def _from_section(chunks: list[Chunk], section: str, quote_of, label: str) -> SheetCell:
    found: list[tuple[Chunk, str]] = []
    for chunk in chunks:
        if chunk.section != section:
            continue
        quote = quote_of(collapse(chunk.text))
        if quote is not None:
            found.append((chunk, quote))
    if not found:
        return SheetCell(state="not_extracted")
    numbers = {round(figures_in(quote)[0], 4) for _, quote in found}
    if len(numbers) > 1:
        raise ValueError(f"{label} has two figures")
    chunk, quote = found[0]
    number = figures_in(quote)[0]
    if not quote_in_text(quote, chunk.text) or not one_figure_matches(quote, number):
        return SheetCell(state="not_extracted")
    citation = citation_for(chunk, quote)
    return SheetCell(
        state="stated",
        quote=citation.quote,
        number=number,
        citation=citation,
        passage=collapse(chunk.text),
    )


def _one_match(pattern: re.Pattern[str], label: str):
    def quote_of(text: str) -> str | None:
        matches = list(pattern.finditer(text))
        if len(matches) > 1:
            raise ValueError(f"{label} has two figures")
        if len(matches) == 1:
            return matches[0].group(0)
        return None

    return quote_of


def _quote(text: str) -> str | None:
    label = _LABEL.search(text)
    if label is None:
        return None
    window = text[label.end() :]
    stop = _STOP.search(window)
    if stop is not None:
        window = window[: stop.start()]
    percents = list(_PERCENT.finditer(window))
    money = _MONEY.search(window)
    before_money = [item for item in percents if money is None or item.start() < money.start()]
    if len(before_money) > 1:
        raise ValueError("ongoing charge has two figures")
    if len(before_money) == 1:
        return before_money[0].group(0)
    between = text[: label.start()]
    head = between.rfind(_HEAD)
    if head < 0:
        return None
    annual = list(_BEFORE_LABEL.finditer(between[head:]))
    if len(annual) > 1:
        raise ValueError("ongoing charge has two figures")
    if len(annual) == 1:
        return annual[0].group(1)
    return None

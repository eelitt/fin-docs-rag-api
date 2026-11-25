import re

from fin_docs_rag.domain.models import COLUMNS, NUMERIC_COLUMNS, Chunk, Citation, SheetCell

_FIGURE = re.compile(r"\d+(?:[.,]\d+)?")
_QUOTE_CAP = 400


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def figures_in(text: str) -> list[float]:
    return [float(match.replace(",", ".")) for match in _FIGURE.findall(collapse(text))]


def same_number(left: float, right: float) -> bool:
    return round(left, 4) == round(right, 4)


def quote_in_text(quote: str, text: str) -> bool:
    folded = collapse(quote).casefold()
    if not folded or len(folded) > _QUOTE_CAP:
        return False
    return folded in collapse(text).casefold()


def one_figure_matches(quote: str, number: float) -> bool:
    figures = figures_in(quote)
    return len(figures) == 1 and same_number(figures[0], number)


def figures_supported(answer: str, quotes: list[str]) -> bool:
    supported: list[float] = []
    for quote in quotes:
        supported.extend(figures_in(quote))
    return all(any(same_number(figure, item) for item in supported) for figure in figures_in(answer))


def grounded_answer(answer: str, citations: list[tuple[str, str]], chunks: dict[str, Chunk]) -> bool:
    if not answer.strip() or not citations:
        return False
    quotes: list[str] = []
    for chunk_id, quote in citations:
        chunk = chunks.get(chunk_id)
        if chunk is None or not quote_in_text(quote, chunk.text):
            return False
        quotes.append(quote)
    return figures_supported(answer, quotes)


def citation_for(chunk: Chunk, quote: str) -> Citation:
    return Citation(
        source_id=chunk.doc_id,
        title=chunk.title,
        quote=collapse(quote),
        page=chunk.page,
        section=chunk.section or None,
    )


def cells_from_claims(claims: list[dict], chunks: list[Chunk]) -> dict[str, SheetCell]:
    by_field: dict[str, dict] = {}
    for claim in claims:
        field = claim.get("field")
        if not isinstance(field, str) or field in by_field:
            raise ValueError("extract did not return each column once")
        by_field[field] = claim
    if set(by_field) != set(COLUMNS):
        raise ValueError("extract did not return each column once")
    by_id = {chunk.id: chunk for chunk in chunks}
    return {field: _cell(by_field[field], by_id) for field in COLUMNS}


def _cell(claim: dict, chunks: dict[str, Chunk]) -> SheetCell:
    if claim.get("status") == "absent":
        return SheetCell(state="not_stated")
    if claim.get("status") != "present":
        return SheetCell(state="not_extracted")
    chunk = chunks.get(claim.get("chunk_id", ""))
    quote = claim.get("quote", "")
    if not isinstance(quote, str) or chunk is None or not quote_in_text(quote, chunk.text):
        return SheetCell(state="not_extracted")
    field = claim["field"]
    citation = citation_for(chunk, quote)
    if field not in NUMERIC_COLUMNS:
        return SheetCell(state="stated", quote=citation.quote, citation=citation)
    number = claim.get("number")
    if isinstance(number, bool) or not isinstance(number, (int, float)):
        return SheetCell(state="not_extracted")
    if not one_figure_matches(quote, float(number)):
        return SheetCell(state="not_extracted")
    return SheetCell(state="stated", quote=citation.quote, number=float(number), citation=citation)

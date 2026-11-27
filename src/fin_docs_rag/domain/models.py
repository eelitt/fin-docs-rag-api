from dataclasses import dataclass

COLUMNS = (
    "product",
    "sri",
    "holding_period",
    "ongoing_charge",
    "entry_cost",
    "exit_cost",
)
NUMERIC_COLUMNS = (
    "sri",
    "holding_period",
    "ongoing_charge",
    "entry_cost",
    "exit_cost",
)
COST_COLUMNS = ("ongoing_charge", "entry_cost", "exit_cost")

ADVICE_REFUSED = "advice_refused"
NOT_IN_CORPUS = "not_in_corpus"
UNGROUNDED = "ungrounded"


@dataclass(frozen=True)
class Chunk:
    id: str
    doc_id: str
    section: str
    page: int
    window: int
    text: str
    title: str = ""


@dataclass(frozen=True)
class Citation:
    source_id: str
    title: str
    quote: str
    page: int | None = None
    section: str | None = None

    def to_dict(self) -> dict:
        body = {"source_id": self.source_id, "title": self.title, "quote": self.quote}
        if self.page is not None:
            body["page"] = self.page
        if self.section:
            body["section"] = self.section
        return body


@dataclass(frozen=True)
class SheetCell:
    state: str
    quote: str | None = None
    number: float | None = None
    citation: Citation | None = None
    passage: str | None = None

    def to_dict(self) -> dict:
        if self.state != "stated":
            return {"state": self.state}
        body: dict = {"state": "stated"}
        if self.number is not None:
            body["number"] = json_number(self.number)
        body["quote"] = self.quote
        body["citation"] = None if self.citation is None else self.citation.to_dict()
        if self.passage:
            body["passage"] = self.passage
        return body


@dataclass(frozen=True)
class Route:
    intent: str
    advice_confidence: str
    funds: tuple[str, ...]
    comparison_field: str
    search_query: str


@dataclass(frozen=True)
class RequestEnvelope:
    request_id: str
    caller: str
    instrument_ids: tuple[str, ...]
    question: str


@dataclass(frozen=True)
class Answer:
    request_id: str
    reason: str | None
    answer: str | None
    citations: tuple[Citation, ...]
    chunk_ids: tuple[str, ...]
    documents_searched: tuple[str, ...]
    trace: dict

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "reason": self.reason,
            "answer": self.answer,
            "citations": [item.to_dict() for item in self.citations],
            "chunk_ids": list(self.chunk_ids),
            "documents_searched": list(self.documents_searched),
            "trace": self.trace,
        }


def json_number(value: float) -> int | float:
    if value == int(value):
        return int(value)
    return value


def cell_from_dict(data: dict) -> SheetCell:
    if data.get("state") != "stated":
        return SheetCell(state=data.get("state", "not_extracted"))
    raw = data["citation"]
    return SheetCell(
        state="stated",
        quote=data["quote"],
        number=data.get("number"),
        citation=Citation(
            source_id=raw["source_id"],
            title=raw["title"],
            quote=raw["quote"],
            page=raw.get("page"),
            section=raw.get("section"),
        ),
        passage=data.get("passage"),
    )


def row_dict(isin: str, cells: dict[str, SheetCell]) -> dict:
    body = {"isin": isin}
    for field in COLUMNS:
        body[field] = cells[field].to_dict()
    return body

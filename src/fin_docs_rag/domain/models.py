from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    id: str
    doc_id: str
    section: str
    page: int
    window: int
    text: str

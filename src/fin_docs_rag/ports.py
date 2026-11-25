from dataclasses import dataclass
from typing import Protocol

from fin_docs_rag.domain.models import Chunk


class DependencyFailure(Exception):
    def __init__(self, message: str = "unavailable") -> None:
        super().__init__(message)
        self.trace: dict | None = None


@dataclass(frozen=True)
class ModelCall:
    prompt_id: str
    deployment: str
    model_version: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    attempts: int = 1


class Chat(Protocol):
    last_call: ModelCall | None

    def complete(self, prompt_id: str, payload: dict) -> dict: ...


class Embedder(Protocol):
    last_call: ModelCall | None

    def embed(self, text: str) -> list[float]: ...


class Searcher(Protocol):
    def hybrid(self, query: str, vector: list[float], isin_filter: list[str] | None) -> list[Chunk]: ...


class PromptSource(Protocol):
    def load(self, prompt_id: str) -> str: ...


class BlobStore(Protocol):
    def put(self, name: str, data: bytes) -> None: ...

    def get(self, name: str) -> bytes: ...

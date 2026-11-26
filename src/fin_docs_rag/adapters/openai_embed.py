import threading
import time
from collections.abc import Callable

from openai import APIStatusError, AzureOpenAI, RateLimitError

from fin_docs_rag.ports import ModelCall

_BATCH = 16


class OpenAIEmbedder:
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment: str,
        token_provider: Callable[[], str] | None = None,
    ) -> None:
        self._deployment = deployment
        self._local = threading.local()
        self._client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_version="2024-10-21",
            **_auth(api_key, token_provider),
        )

    @property
    def last_call(self) -> ModelCall | None:
        return getattr(self._local, "call", None)

    @last_call.setter
    def last_call(self, value: ModelCall | None) -> None:
        self._local.call = value

    def embed(self, text: str) -> list[float]:
        self._local.tokens = 0
        self._local.model = ""
        started = time.perf_counter()
        vector = self.embed_many([text])[0]
        self.last_call = ModelCall(
            prompt_id="",
            deployment=self._deployment,
            model_version=getattr(self._local, "model", "") or "",
            latency_ms=int((time.perf_counter() - started) * 1000),
            input_tokens=getattr(self._local, "tokens", 0) or 0,
            output_tokens=0,
        )
        return vector

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _BATCH):
            vectors.extend(self._embed_batch(texts[start : start + _BATCH]))
        return vectors

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        delay = 2.0
        for attempt in range(8):
            try:
                response = self._client.embeddings.create(model=self._deployment, input=texts)
            except (RateLimitError, APIStatusError) as error:
                status = getattr(error, "status_code", None)
                if status not in (None, 429) or attempt == 7:
                    raise
                time.sleep(_retry_seconds(error, delay))
                delay = min(delay * 2, 60)
                continue
            ordered = sorted(response.data, key=lambda item: item.index)
            usage = response.usage
            self._local.tokens = getattr(self._local, "tokens", 0) + (getattr(usage, "total_tokens", 0) or 0)
            self._local.model = response.model or ""
            return [item.embedding for item in ordered]
        raise RuntimeError("embedding request was rate limited")


def _auth(api_key: str, token_provider: Callable[[], str] | None) -> dict:
    if api_key:
        return {"api_key": api_key}
    return {"azure_ad_token_provider": token_provider}


def _retry_seconds(error: Exception, fallback: float) -> float:
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return fallback
    raw = headers.get("retry-after")
    if raw is None:
        return fallback
    try:
        return float(raw)
    except ValueError:
        return fallback

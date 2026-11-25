import json
import threading
import time
from typing import Literal

from openai import APIConnectionError, APIStatusError, APITimeoutError, AzureOpenAI
from pydantic import BaseModel, ConfigDict, ValidationError

from fin_docs_rag.ports import DependencyFailure, ModelCall, PromptSource

_COLUMNS = (
    "product",
    "sri",
    "holding_period",
    "ongoing_charge",
    "entry_cost",
    "exit_cost",
)


class RouterOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent: Literal["lookup", "compare", "advice"]
    advice_confidence: Literal["high", "low"]
    funds: list[str]
    comparison_field: Literal["ongoing_charge", "sri", "holding_period", "entry_cost", "exit_cost", ""]
    search_query: str


class GradeItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    relevant: bool


class GradeOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunks: list[GradeItem]


class AnswerCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chunk_id: str
    quote: str


class AnswerOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    can_answer: bool
    answer: str
    citations: list[AnswerCitation]
    reason: Literal["", "not_in_corpus", "ungrounded", "advice_refused"]


class ExtractItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: Literal["product", "sri", "holding_period", "ongoing_charge", "entry_cost", "exit_cost"]
    status: Literal["present", "absent"]
    chunk_id: str
    quote: str
    number: float | None


class ExtractOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    columns: list[ExtractItem]


_MODELS = {
    "router_v1": RouterOut,
    "grade_v1": GradeOut,
    "answer_v1": AnswerOut,
    "extract_v1": ExtractOut,
}

_OBJECT = "object"
_STRING = {"type": "string"}


def _schema(properties: dict, required: list[str]) -> dict:
    return {
        "type": _OBJECT,
        "additionalProperties": False,
        "properties": properties,
        "required": required,
    }


_SCHEMAS = {
    "router_v1": _schema(
        {
            "intent": {"type": "string", "enum": ["lookup", "compare", "advice"]},
            "advice_confidence": {"type": "string", "enum": ["high", "low"]},
            "funds": {"type": "array", "items": _STRING},
            "comparison_field": {
                "type": "string",
                "enum": ["ongoing_charge", "sri", "holding_period", "entry_cost", "exit_cost", ""],
            },
            "search_query": _STRING,
        },
        ["intent", "advice_confidence", "funds", "comparison_field", "search_query"],
    ),
    "grade_v1": _schema(
        {
            "chunks": {
                "type": "array",
                "items": _schema({"id": _STRING, "relevant": {"type": "boolean"}}, ["id", "relevant"]),
            }
        },
        ["chunks"],
    ),
    "answer_v1": _schema(
        {
            "can_answer": {"type": "boolean"},
            "answer": _STRING,
            "citations": {
                "type": "array",
                "items": _schema({"chunk_id": _STRING, "quote": _STRING}, ["chunk_id", "quote"]),
            },
            "reason": {
                "type": "string",
                "enum": ["", "not_in_corpus", "ungrounded", "advice_refused"],
            },
        },
        ["can_answer", "answer", "citations", "reason"],
    ),
    "extract_v1": _schema(
        {
            "columns": {
                "type": "array",
                "items": _schema(
                    {
                        "field": {"type": "string", "enum": list(_COLUMNS)},
                        "status": {"type": "string", "enum": ["present", "absent"]},
                        "chunk_id": _STRING,
                        "quote": _STRING,
                        "number": {"anyOf": [{"type": "number"}, {"type": "null"}]},
                    },
                    ["field", "status", "chunk_id", "quote", "number"],
                ),
            }
        },
        ["columns"],
    ),
}


class OpenAIChat:
    def __init__(self, endpoint: str, api_key: str, deployment: str, prompts: PromptSource) -> None:
        self._deployment = deployment
        self._prompts = prompts
        self._local = threading.local()
        self._client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2024-10-21",
            timeout=60.0,
        )

    @property
    def last_call(self) -> ModelCall | None:
        return getattr(self._local, "call", None)

    @last_call.setter
    def last_call(self, value: ModelCall | None) -> None:
        self._local.call = value

    def complete(self, prompt_id: str, payload: dict) -> dict:
        model = _MODELS[prompt_id]
        prompt = self._prompts.load(prompt_id)
        started = time.perf_counter()
        for attempt in (1, 2):
            try:
                response = self._client.chat.completions.create(
                    model=self._deployment,
                    temperature=0,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {"name": prompt_id, "strict": True, "schema": _SCHEMAS[prompt_id]},
                    },
                )
                content = response.choices[0].message.content or ""
                parsed = model.model_validate(json.loads(content))
            except (APITimeoutError, APIConnectionError, APIStatusError) as error:
                self._save(prompt_id, started, attempt, None)
                kind = "timeout" if isinstance(error, APITimeoutError) else "unavailable"
                raise DependencyFailure(kind) from error
            except (json.JSONDecodeError, ValidationError) as error:
                self._save(prompt_id, started, attempt, None)
                if attempt == 2:
                    raise DependencyFailure("schema") from error
                continue
            self._save(prompt_id, started, attempt, response)
            return parsed.model_dump()
        raise DependencyFailure("schema")

    def _save(self, prompt_id: str, started: float, attempts: int, response) -> None:
        usage = getattr(response, "usage", None) if response is not None else None
        self.last_call = ModelCall(
            prompt_id=prompt_id,
            deployment=self._deployment,
            model_version=getattr(response, "model", "") or "",
            latency_ms=int((time.perf_counter() - started) * 1000),
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            attempts=attempts,
        )

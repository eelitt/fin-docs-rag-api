from fin_docs_rag.ports import ModelCall

_CHAT_INPUT = 0.40 / 1_000_000
_CHAT_OUTPUT = 1.60 / 1_000_000
_EMBED = 0.02 / 1_000_000


def cost_usd(children: list[tuple[str, ModelCall]]) -> float:
    total = 0.0
    for name, call in children:
        if name == "embed":
            total += call.input_tokens * _EMBED
        else:
            total += call.input_tokens * _CHAT_INPUT
            total += call.output_tokens * _CHAT_OUTPUT
    return total


def root_span(
    *,
    request_id: str,
    caller: str,
    instrument_ids: tuple[str, ...] | list[str],
    latency_ms: int,
    reason: str | None,
    chunk_ids: list[str],
    children: list[tuple[str, ModelCall]],
) -> dict:
    span: dict = {
        "request_id": request_id,
        "caller": caller,
        "latency_ms": latency_ms,
        "total_tokens": sum(call.input_tokens + call.output_tokens for _, call in children),
        "cost_usd": cost_usd(children),
        "chunk_ids": list(chunk_ids),
        "reason": reason,
        "children": [_child(name, call) for name, call in children],
    }
    if caller == "demo":
        span["instrument_ids"] = list(instrument_ids)
    return span


def _child(name: str, call: ModelCall) -> dict:
    body = {
        "name": name,
        "prompt_id": call.prompt_id,
        "deployment": call.deployment,
        "model_version": call.model_version,
        "latency_ms": call.latency_ms,
        "input_tokens": call.input_tokens,
        "output_tokens": call.output_tokens,
    }
    if call.attempts != 1:
        body["attempts"] = call.attempts
    return body

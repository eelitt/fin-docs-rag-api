import json
import logging
import os

from fin_docs_rag.adapters.telemetry import _CAPTURE, Telemetry, attributes, child_attributes
from fin_docs_rag.ports import ModelCall
from fin_docs_rag.trace import root_span

_ROOT = {
    "request_id",
    "caller",
    "latency_ms",
    "total_tokens",
    "cost_usd",
    "chunk_ids",
    "reason",
    "children",
    "instrument_ids",
}
_CHILD = {
    "name",
    "prompt_id",
    "deployment",
    "model_version",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "attempts",
}


def _span(caller: str = "demo") -> dict:
    call = ModelCall(
        "router_v1",
        "GPT-4-1-mini",
        "2025-04-14",
        12,
        10,
        5,
        attempts=2,
        attempt_records=((4, 6, 0), (8, 4, 5)),
    )
    return root_span(
        request_id="11111111-1111-1111-1111-111111111111",
        caller=caller,
        instrument_ids=["FI0008804729"],
        latency_ms=20,
        reason=None,
        chunk_ids=["FI0008804729:costs:3:0"],
        children=[("router", call)],
    )


def test_root_span_has_the_trace_fields_and_both_attempts():
    span = _span()
    assert set(span) == _ROOT
    assert span["chunk_ids"] == ["FI0008804729:costs:3:0"]
    assert span["total_tokens"] == 15
    assert span["instrument_ids"] == ["FI0008804729"]
    child = span["children"][0]
    assert set(child) == _CHILD
    assert child["prompt_id"] == "router_v1"
    assert child["model_version"] == "2025-04-14"
    assert child["attempts"] == [
        {"latency_ms": 4, "input_tokens": 6, "output_tokens": 0},
        {"latency_ms": 8, "input_tokens": 4, "output_tokens": 5},
    ]
    dumped = json.dumps(span)
    assert "should I buy" not in dumped
    assert "question" not in span
    assert "completion" not in dumped
    assert "secret" not in dumped


def test_other_callers_omit_instrument_ids():
    span = _span("later")
    assert "instrument_ids" not in span


def test_export_keeps_span_fields_only():
    span = _span()
    span["question"] = "should I buy this"
    span["prompt"] = "system prompt"
    span["completion"] = "the answer"
    kept = attributes(span)
    assert set(kept) == _ROOT - {"children", "reason"}
    assert "question" not in kept
    assert "prompt" not in kept
    child = child_attributes({**span["children"][0], "completion": "the answer", "secret": "x"})
    assert set(child) == _CHILD - {"name", "attempts"}
    assert "completion" not in child
    assert "secret" not in child


def test_local_write_logs_the_same_object(caplog, monkeypatch):
    monkeypatch.delenv(_CAPTURE, raising=False)
    span = {"request_id": "abc", "caller": "demo", "children": [{"name": "router"}]}
    with caplog.at_level(logging.INFO, logger="fin_docs_rag.adapters.telemetry"):
        Telemetry("").write(span)
    assert json.dumps(span) in caplog.text
    assert os.environ[_CAPTURE] == "false"

import json
import logging
import os

logger = logging.getLogger(__name__)

_ROOT = (
    "request_id",
    "caller",
    "latency_ms",
    "total_tokens",
    "cost_usd",
    "chunk_ids",
    "reason",
    "instrument_ids",
)
_CHILD = ("prompt_id", "deployment", "model_version", "latency_ms", "input_tokens", "output_tokens")
_ATTEMPT = ("latency_ms", "input_tokens", "output_tokens")
_CAPTURE = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"


def attributes(span: dict) -> dict:
    return {key: span[key] for key in _ROOT if key in span and span[key] is not None}


def child_attributes(child: dict) -> dict:
    body = {key: child[key] for key in _CHILD if key in child and child[key] is not None}
    attempts = child.get("attempts")
    if isinstance(attempts, int):
        body["attempts"] = attempts
    return body


class Telemetry:
    def __init__(self, connection_string: str) -> None:
        os.environ[_CAPTURE] = "false"
        self._tracer = _tracer(connection_string) if connection_string else None

    def write(self, trace: dict) -> None:
        logger.info("%s", json.dumps(trace, ensure_ascii=False))
        if self._tracer is None:
            return
        try:
            _export(self._tracer, trace)
        except Exception:
            logger.warning("trace export failed")


def _tracer(connection_string: str):
    from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": "fin-docs-rag"}))
    provider.add_span_processor(SimpleSpanProcessor(AzureMonitorTraceExporter(connection_string=connection_string)))
    return provider.get_tracer("fin_docs_rag")


def _export(tracer, span: dict) -> None:
    with tracer.start_as_current_span("ask") as root:
        root.set_attributes(_flat(attributes(span)))
        for child in span.get("children", []):
            with tracer.start_as_current_span(str(child.get("name", "model"))) as current:
                current.set_attributes(_flat(child_attributes(child)))
                for index, attempt in enumerate(_attempt_events(child), start=1):
                    current.add_event(f"attempt_{index}", _flat(attempt))


def _attempt_events(child: dict) -> list[dict]:
    attempts = child.get("attempts")
    if not isinstance(attempts, list):
        return []
    events = []
    for attempt in attempts:
        if not isinstance(attempt, dict):
            continue
        events.append({key: attempt[key] for key in _ATTEMPT if key in attempt})
    return events


def _flat(values: dict) -> dict:
    flat = {}
    for key, value in values.items():
        if isinstance(value, list):
            flat[key] = [str(item) for item in value]
        else:
            flat[key] = value
    return flat

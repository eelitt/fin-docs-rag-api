import json
import logging
import time
import uuid
from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from fin_docs_rag.domain.calculate import ongoing_comparison
from fin_docs_rag.domain.isin import is_isin
from fin_docs_rag.domain.models import Answer, RequestEnvelope
from fin_docs_rag.ports import DependencyFailure

_FIELDS = {"request_id", "caller", "instrument_ids", "question"}
_LIMIT = 20
_WINDOW_S = 600
logger = logging.getLogger(__name__)
_PAGE = """<!doctype html>
<meta charset="utf-8">
<title>fin-docs-rag</title>
<p>Research aid over public fund documents. Not investment advice, and not a product of any bank or fund company.</p>
<p>The fact sheet page is not here yet.</p>
"""


def create_app(
    *,
    read_sheet: Callable[[], dict],
    ping: Callable[[], None],
    ask: Callable[[RequestEnvelope], Answer],
    now: Callable[[], float] = time.monotonic,
    write_trace: Callable[[dict], None] | None = None,
) -> FastAPI:
    record = write_trace or _log_trace
    app = FastAPI()
    accepted: list[float] = []

    @app.get("/")
    def home() -> HTMLResponse:
        return HTMLResponse(_PAGE)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/ready")
    def ready():
        try:
            read_sheet()
            ping()
        except DependencyFailure:
            return JSONResponse(status_code=503, content={"error": "unavailable"})
        return {"status": "ok"}

    @app.get("/sheet")
    def sheet():
        try:
            return read_sheet()
        except DependencyFailure as error:
            _record(record, error)
            return JSONResponse(status_code=503, content={"error": "unavailable"})

    @app.get("/compare")
    def compare(isin_a: str | None = None, isin_b: str | None = None):
        if not isin_a or not isin_b or isin_a == isin_b or not is_isin(isin_a) or not is_isin(isin_b):
            return JSONResponse(status_code=400, content={"error": "invalid_instrument_id"})
        try:
            document = read_sheet()
            return ongoing_comparison(document, isin_a, isin_b)
        except DependencyFailure as error:
            _record(record, error)
            return JSONResponse(status_code=503, content={"error": "unavailable"})

    @app.post("/ask")
    async def ask_route(request: Request):
        body = await _body(request)
        failure = _reject(body)
        if failure is not None:
            status, code = failure
            return JSONResponse(status_code=status, content={"error": code})
        if not _allow(accepted, now):
            return JSONResponse(status_code=429, content={"error": "rate_limited"})
        envelope = _envelope(body)
        try:
            answer = ask(envelope)
        except DependencyFailure as error:
            _record(record, error)
            return JSONResponse(
                status_code=503,
                content={"error": "unavailable", "request_id": envelope.request_id},
            )
        record(answer.trace)
        return answer.to_dict()

    return app


async def _body(request: Request):
    try:
        return await request.json()
    except Exception:
        return None


def _reject(body) -> tuple[int, str] | None:
    if not isinstance(body, dict) or any(key not in _FIELDS for key in body):
        return 400, "unknown_field"
    if "question" in body and not isinstance(body["question"], str):
        return 400, "unknown_field"
    if "request_id" in body and not isinstance(body["request_id"], str):
        return 400, "unknown_field"
    if "caller" in body and not isinstance(body["caller"], str):
        return 400, "unknown_field"
    if "instrument_ids" in body and not _string_list(body["instrument_ids"]):
        return 400, "unknown_field"
    if "question" not in body or not body["question"].strip():
        return 400, "empty_question"
    if len(body["question"].strip()) > 1000:
        return 400, "question_too_long"
    if "request_id" in body and not _uuid(body["request_id"]):
        return 400, "invalid_request_id"
    if "instrument_ids" in body and not _isins(body["instrument_ids"]):
        return 400, "invalid_instrument_id"
    if "caller" in body and body["caller"] != "demo":
        return 401, "unauthorized"
    return None


def _string_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def _isins(values: list[str]) -> bool:
    return len(values) <= 20 and len(values) == len(set(values)) and all(is_isin(item) for item in values)


def _allow(accepted: list[float], now: Callable[[], float]) -> bool:
    current = now()
    accepted[:] = [stamp for stamp in accepted if current - stamp < _WINDOW_S]
    if len(accepted) >= _LIMIT:
        return False
    accepted.append(current)
    return True


def _envelope(body: dict) -> RequestEnvelope:
    question = body["question"].strip()
    request_id = str(uuid.UUID(body["request_id"])) if "request_id" in body else str(uuid.uuid4())
    caller = body.get("caller", "demo")
    instrument_ids = tuple(body.get("instrument_ids", ()))
    return RequestEnvelope(request_id, caller, instrument_ids, question)


def _record(write_trace: Callable[[dict], None], error: DependencyFailure) -> None:
    if error.trace is not None:
        write_trace(error.trace)


def _log_trace(trace: dict) -> None:
    logger.info("%s", json.dumps(trace, ensure_ascii=False))

import uuid

from fastapi.testclient import TestClient

from fin_docs_rag.domain.models import Answer, Citation
from fin_docs_rag.http.app import create_app
from fin_docs_rag.ports import DependencyFailure

_SHEET = {
    "funds": [
        {
            "isin": "FI0008804729",
            "product": {"state": "not_stated"},
            "sri": {"state": "not_stated"},
            "holding_period": {
                "state": "stated",
                "number": 5,
                "quote": "5 vuotta",
                "citation": {"source_id": "FI0008804729", "title": "Kid", "quote": "5 vuotta"},
            },
            "ongoing_charge": {
                "state": "stated",
                "number": 0.3,
                "quote": "0,30 %",
                "citation": {"source_id": "FI0008804729", "title": "Kid", "page": 3, "section": "costs", "quote": "0,30 %"},
            },
            "entry_cost": {"state": "not_stated"},
            "exit_cost": {"state": "not_extracted"},
        }
    ]
}


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def _answer() -> Answer:
    return Answer(
        request_id="11111111-1111-1111-1111-111111111111",
        reason=None,
        answer="Noted.",
        citations=(Citation("doc", "Kid", "Noted."),),
        chunk_ids=(),
        documents_searched=(),
        trace={"children": []},
    )


def _client(sheet=None, ask=None, now=None, ping=None):
    calls = {"n": 0}

    def read_sheet():
        if isinstance(sheet, Exception):
            raise sheet
        return _SHEET if sheet is None else sheet

    def default_ask(envelope):
        calls["n"] += 1
        return _answer()

    app = create_app(
        read_sheet=read_sheet,
        ping=ping or (lambda: None),
        ask=ask or default_ask,
        now=now or Clock(),
    )
    return app, calls


def test_health_does_not_read_the_sheet_and_ready_does():
    app, calls = _client(sheet=DependencyFailure("sheet"))
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503
        assert client.get("/sheet").status_code == 503
    assert calls["n"] == 0


def test_sheet_makes_no_model_call():
    app, calls = _client()
    with TestClient(app) as client:
        response = client.get("/sheet")
    assert response.status_code == 200
    assert response.json()["funds"][0]["isin"] == "FI0008804729"
    assert calls["n"] == 0


def test_compare_validates_isins_and_names_a_missing_row():
    app, calls = _client()
    with TestClient(app) as client:
        missing = client.get("/compare")
        same = client.get("/compare", params={"isin_a": "FI0008804729", "isin_b": "FI0008804729"})
        bad = client.get("/compare", params={"isin_a": "FI0008804729", "isin_b": "FI0008804720"})
        found = client.get("/compare", params={"isin_a": "FI0008804729", "isin_b": "FI0008804687"})
    assert missing.status_code == 400 and missing.json() == {"error": "invalid_instrument_id"}
    assert same.status_code == 400
    assert bad.status_code == 400
    assert found.status_code == 200
    body = found.json()
    assert body["field"] == "ongoing_charge"
    assert body["cell_b"] is None
    assert "FI0008804687 is not on the sheet." in body["sentence"]
    assert calls["n"] == 0


def test_ask_checks_stop_at_the_first_failure_and_do_not_call_the_model():
    app, calls = _client()
    with TestClient(app) as client:
        extra = client.post("/ask", json={"question": "", "email": "a@b.c"})
        empty = client.post("/ask", json={})
        blank = client.post("/ask", json={"question": "  "})
        typed = client.post("/ask", json={"question": 1})
        long = client.post("/ask", json={"question": "x" * 1001})
        bad_id = client.post("/ask", json={"question": "hi", "request_id": "nope"})
        duplicate = client.post("/ask", json={"question": "hi", "instrument_ids": ["FI0008804729", "FI0008804729"]})
        denied = client.post("/ask", json={"question": "hi", "caller": "other"})
        array = client.post("/ask", json=["hi"])
    assert extra.status_code == 400 and extra.json() == {"error": "unknown_field"}
    assert empty.json() == {"error": "empty_question"}
    assert blank.json() == {"error": "empty_question"}
    assert typed.json() == {"error": "unknown_field"}
    assert long.status_code == 400 and long.json() == {"error": "question_too_long"}
    assert bad_id.json() == {"error": "invalid_request_id"}
    assert duplicate.json() == {"error": "invalid_instrument_id"}
    assert denied.status_code == 401 and denied.json() == {"error": "unauthorized"}
    assert array.json() == {"error": "unknown_field"}
    assert calls["n"] == 0


def test_a_rejected_ask_does_not_advance_the_rate_limit():
    clock = Clock()
    seen = []

    def ask(envelope):
        seen.append(envelope.question)
        return Answer(
            envelope.request_id,
            None,
            "Noted.",
            (),
            (),
            (),
            {"request_id": envelope.request_id},
        )

    app, _calls = _client(ask=ask, now=clock)
    with TestClient(app) as client:
        assert client.post("/ask", json={"question": "x" * 1001}).status_code == 400
        for index in range(20):
            response = client.post("/ask", json={"question": f"  q{index}  "})
            assert response.status_code == 200
        assert client.post("/ask", json={"question": "again"}).status_code == 429
        assert client.post("/ask", json={"question": "again"}).json() == {"error": "rate_limited"}
        clock.t = 600
        assert client.post("/ask", json={"question": "later"}).status_code == 200
    assert seen[0] == "q0"
    assert len(seen) == 21


def test_dependency_failure_is_unavailable_and_hides_the_trace():
    request_id = str(uuid.uuid4())

    def ask(envelope):
        error = DependencyFailure("timeout")
        error.trace = {"request_id": envelope.request_id, "hidden": True}
        raise error

    app, _calls = _client(ask=ask)
    with TestClient(app) as client:
        response = client.post("/ask", json={"question": "hi", "request_id": request_id})
    assert response.status_code == 503
    assert response.json() == {"error": "unavailable", "request_id": request_id}
    assert "hidden" not in response.text

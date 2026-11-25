from fin_docs_rag.ports import ModelCall
from fin_docs_rag.steps.route import route_question

_ROUTE = {
    "intent": "lookup",
    "advice_confidence": "low",
    "funds": [],
    "comparison_field": "ongoing_charge",
    "search_query": "ongoing cost",
}


class FakeChat:
    def __init__(self) -> None:
        self.payloads = []
        self.last_call = None

    def complete(self, prompt_id: str, payload: dict) -> dict:
        self.payloads.append((prompt_id, payload))
        self.last_call = ModelCall(prompt_id, "fake", "fake", 1, 1, 1)
        return _ROUTE


def test_router_sees_instrument_ids_only_when_the_list_is_present():
    chat = FakeChat()
    route, _call = route_question("What is the cost?", ["FI0008804729"], chat)
    assert route.comparison_field == "ongoing_charge"
    assert chat.payloads[0][0] == "router_v1"
    assert chat.payloads[0][1]["instrument_ids"] == ["FI0008804729"]
    route_question("What is the cost?", [], chat)
    assert "instrument_ids" not in chat.payloads[1][1]

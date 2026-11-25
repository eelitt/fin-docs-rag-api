from collections.abc import Sequence

from fin_docs_rag.domain.models import Route
from fin_docs_rag.ports import Chat, DependencyFailure, ModelCall


def route_question(question: str, instrument_ids: Sequence[str], chat: Chat) -> tuple[Route, ModelCall]:
    payload: dict = {"question": question}
    if instrument_ids:
        payload["instrument_ids"] = list(instrument_ids)
    data = chat.complete("router_v1", payload)
    call = chat.last_call
    if call is None:
        raise DependencyFailure("router")
    return (
        Route(
            intent=data["intent"],
            advice_confidence=data["advice_confidence"],
            funds=tuple(data["funds"]),
            comparison_field=data["comparison_field"],
            search_query=data["search_query"],
        ),
        call,
    )

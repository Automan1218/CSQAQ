"""Market analysis LangGraph subgraph.

Graph: fetch_market_data -> analyze_market -> prepare_advisor -> advise -> END
"""
from __future__ import annotations

from functools import partial
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph, add_messages

from csqaq.components.agents.advisor import advise_node
from csqaq.components.agents.market import analyze_market_node, fetch_market_data_node
from csqaq.components.models.factory import ModelFactory
from csqaq.infrastructure.csqaq_client.market import MarketAPI


class MarketFlowState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    home_data: dict | None
    sub_data: dict | None
    market_context: str | None
    item_context: dict | None
    scout_context: dict | None
    historical_advice: list | None
    summary: str | None
    action_detail: str | None
    risk_level: str | None
    requires_confirmation: bool
    error: str | None


def _should_continue_after_fetch(state: MarketFlowState) -> str:
    if state.get("error"):
        return "prepare_advisor"
    return "analyze_market"


def _prepare_advisor_context(state: MarketFlowState) -> dict:
    """Bridge node: pack market_context into Advisor's expected format."""
    return {
        "market_context": {"analysis_result": state.get("market_context", "")},
        "item_context": None,
        "scout_context": None,
    }


def build_market_flow(market_api: MarketAPI, model_factory: ModelFactory):
    """Build and compile the market analysis subgraph."""
    graph = StateGraph(MarketFlowState)

    graph.add_node("fetch_market_data", partial(fetch_market_data_node, market_api=market_api))
    graph.add_node("analyze_market", partial(analyze_market_node, model_factory=model_factory))
    graph.add_node("prepare_advisor", _prepare_advisor_context)
    graph.add_node("advise", partial(advise_node, model_factory=model_factory))

    graph.set_entry_point("fetch_market_data")
    graph.add_conditional_edges(
        "fetch_market_data",
        _should_continue_after_fetch,
        {"analyze_market": "analyze_market", "prepare_advisor": "prepare_advisor"},
    )
    graph.add_edge("analyze_market", "prepare_advisor")
    graph.add_edge("prepare_advisor", "advise")
    graph.add_edge("advise", END)

    return graph.compile()

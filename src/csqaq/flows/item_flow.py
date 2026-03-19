"""Item analysis LangGraph subgraph.

Graph: resolve_item → fetch_chart → analyze → prepare_advisor → advise → END
"""
from __future__ import annotations

from functools import partial
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph, add_messages

from csqaq.components.agents.advisor import advise_node
from csqaq.components.agents.item import analyze_node, fetch_chart_node, resolve_item_node
from csqaq.components.models.factory import ModelFactory
from csqaq.infrastructure.csqaq_client.item import ItemAPI


class ItemFlowState(TypedDict):
    messages: Annotated[list, add_messages]
    good_id: int | None
    good_name: str | None
    item_detail: dict | None
    chart_data: dict | None
    kline_data: list | None
    indicators: dict | None
    analysis_result: str | None
    error: str | None
    item_context: dict | None
    market_context: dict | None
    scout_context: dict | None
    historical_advice: list | None
    summary: str | None
    action_detail: str | None
    risk_level: str | None
    requires_confirmation: bool


def _should_continue(state: ItemFlowState) -> str:
    """If error occurred in resolve step, skip to analyze (which will report the error)."""
    if state.get("error"):
        return "analyze"
    return "fetch_chart"


def _prepare_advisor_context(state: ItemFlowState) -> dict:
    return {
        "item_context": {
            "analysis_result": state.get("analysis_result", ""),
            "item_detail": state.get("item_detail"),
            "indicators": state.get("indicators"),
        },
        "market_context": None,
        "scout_context": None,
    }


def build_item_flow(item_api: ItemAPI, model_factory: ModelFactory):
    """Build and compile the item analysis subgraph. Returns a CompiledStateGraph."""
    graph = StateGraph(ItemFlowState)

    # Bind dependencies to node functions
    graph.add_node("resolve_item", partial(resolve_item_node, item_api=item_api))
    graph.add_node("fetch_chart", partial(fetch_chart_node, item_api=item_api))
    graph.add_node("analyze", partial(analyze_node, model_factory=model_factory))
    graph.add_node("prepare_advisor", _prepare_advisor_context)
    graph.add_node("advise", partial(advise_node, model_factory=model_factory))

    graph.set_entry_point("resolve_item")
    graph.add_conditional_edges(
        "resolve_item",
        _should_continue,
        {"analyze": "analyze", "fetch_chart": "fetch_chart"},
    )
    graph.add_edge("fetch_chart", "analyze")
    graph.add_edge("analyze", "prepare_advisor")
    graph.add_edge("prepare_advisor", "advise")
    graph.add_edge("advise", END)

    return graph.compile()

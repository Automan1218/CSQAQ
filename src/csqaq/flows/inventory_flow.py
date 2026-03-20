"""Inventory analysis LangGraph subgraph.

Graph: resolve_item -> fetch_inventory -> analyze_inventory -> interpret_inventory -> prepare_advisor -> advise -> END
"""
from __future__ import annotations

from functools import partial
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph, add_messages

from csqaq.components.agents.advisor import advise_node
from csqaq.components.agents.inventory import (
    analyze_inventory_node,
    fetch_inventory_node,
    interpret_inventory_node,
)
from csqaq.components.agents.item import resolve_item_node
from csqaq.components.models.factory import ModelFactory
from csqaq.infrastructure.csqaq_client.item import ItemAPI


class InventoryFlowState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    good_name: str | None
    good_id: str | None
    item_detail: dict | None
    inventory_stats: list | None
    inventory_report: dict | None
    inventory_context: str | None
    item_context: dict | None
    market_context: dict | None
    scout_context: dict | None
    summary: str | None
    action_detail: str | None
    risk_level: str | None
    requires_confirmation: bool
    error: str | None


def _should_continue_after_resolve(state: InventoryFlowState) -> str:
    if state.get("error"):
        return "prepare_advisor"
    return "fetch_inventory"


def _prepare_advisor_context(state: InventoryFlowState) -> dict:
    """Bridge node: pack inventory_context into Advisor's expected format."""
    return {
        "item_context": {
            "inventory_context": state.get("inventory_context", ""),
            "inventory_report": state.get("inventory_report"),
        },
        "market_context": None,
        "scout_context": None,
    }


def build_inventory_flow(item_api: ItemAPI, model_factory: ModelFactory):
    """Build and compile the inventory analysis subgraph."""
    graph = StateGraph(InventoryFlowState)

    graph.add_node("resolve_item", partial(resolve_item_node, item_api=item_api))
    graph.add_node("fetch_inventory", partial(fetch_inventory_node, item_api=item_api))
    graph.add_node("analyze_inventory", analyze_inventory_node)
    graph.add_node("interpret_inventory", partial(interpret_inventory_node, model_factory=model_factory))
    graph.add_node("prepare_advisor", _prepare_advisor_context)
    graph.add_node("advise", partial(advise_node, model_factory=model_factory))

    graph.set_entry_point("resolve_item")
    graph.add_conditional_edges(
        "resolve_item",
        _should_continue_after_resolve,
        {"fetch_inventory": "fetch_inventory", "prepare_advisor": "prepare_advisor"},
    )
    graph.add_edge("fetch_inventory", "analyze_inventory")
    graph.add_edge("analyze_inventory", "interpret_inventory")
    graph.add_edge("interpret_inventory", "prepare_advisor")
    graph.add_edge("prepare_advisor", "advise")
    graph.add_edge("advise", END)

    return graph.compile()

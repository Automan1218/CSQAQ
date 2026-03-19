"""Advisor LangGraph subgraph.

Phase 1: Simple single-node flow (advise -> END).
Phase 2+ will add HITL interrupt for high-risk recommendations.
"""
from __future__ import annotations

from functools import partial
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph, add_messages

from csqaq.components.agents.advisor import advise_node
from csqaq.components.models.factory import ModelFactory


class AdvisorFlowState(TypedDict):
    messages: Annotated[list, add_messages]
    market_context: dict | None
    item_context: dict | None
    scout_context: dict | None
    historical_advice: list | None
    summary: str | None
    action_detail: str | None
    risk_level: str | None  # "low" | "medium" | "high"
    requires_confirmation: bool
    error: str | None


def build_advisor_flow(model_factory: ModelFactory):
    """Build and compile the advisor subgraph. Returns a CompiledStateGraph."""
    graph = StateGraph(AdvisorFlowState)

    graph.add_node("advise", partial(advise_node, model_factory=model_factory))

    graph.set_entry_point("advise")
    graph.add_edge("advise", END)

    return graph.compile()

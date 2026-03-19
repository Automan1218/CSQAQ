"""Scout (opportunity discovery) LangGraph subgraph.

Graph: fetch_rank_data -> analyze_opportunities -> prepare_advisor -> advise -> END
"""
from __future__ import annotations

from functools import partial
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph, add_messages

from csqaq.components.agents.advisor import advise_node
from csqaq.components.agents.scout import analyze_opportunities_node, fetch_rank_data_node
from csqaq.components.models.factory import ModelFactory
from csqaq.infrastructure.csqaq_client.rank import RankAPI
from csqaq.infrastructure.csqaq_client.vol import VolAPI


class ScoutFlowState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    rank_data: dict | None
    scout_context: str | None
    item_context: dict | None
    market_context: dict | None
    historical_advice: list | None
    summary: str | None
    action_detail: str | None
    risk_level: str | None
    requires_confirmation: bool
    error: str | None


def _should_continue_after_fetch(state: ScoutFlowState) -> str:
    if state.get("error"):
        return "prepare_advisor"
    return "analyze_opportunities"


def _prepare_advisor_context(state: ScoutFlowState) -> dict:
    """Bridge node: pack scout_context into Advisor's expected format."""
    return {
        "scout_context": {"analysis_result": state.get("scout_context", "")},
        "item_context": None,
        "market_context": None,
    }


def build_scout_flow(rank_api: RankAPI, vol_api: VolAPI, model_factory: ModelFactory):
    """Build and compile the scout subgraph."""
    graph = StateGraph(ScoutFlowState)

    graph.add_node(
        "fetch_rank_data",
        partial(fetch_rank_data_node, rank_api=rank_api, vol_api=vol_api),
    )
    graph.add_node("analyze_opportunities", partial(analyze_opportunities_node, model_factory=model_factory))
    graph.add_node("prepare_advisor", _prepare_advisor_context)
    graph.add_node("advise", partial(advise_node, model_factory=model_factory))

    graph.set_entry_point("fetch_rank_data")
    graph.add_conditional_edges(
        "fetch_rank_data",
        _should_continue_after_fetch,
        {"analyze_opportunities": "analyze_opportunities", "prepare_advisor": "prepare_advisor"},
    )
    graph.add_edge("analyze_opportunities", "prepare_advisor")
    graph.add_edge("prepare_advisor", "advise")
    graph.add_edge("advise", END)

    return graph.compile()

"""Router Flow -- main entry graph that dispatches to sub-flows.

Graph: router_node -> conditional -> item/market/scout subflow -> END
"""
from __future__ import annotations

from functools import partial
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph, add_messages

from csqaq.components.models.factory import ModelFactory
from csqaq.components.router import route_query
from csqaq.infrastructure.csqaq_client.item import ItemAPI
from csqaq.infrastructure.csqaq_client.market import MarketAPI
from csqaq.infrastructure.csqaq_client.rank import RankAPI
from csqaq.infrastructure.csqaq_client.vol import VolAPI


class RouterFlowState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    intent: str | None
    item_name: str | None
    result: str | None
    error: str | None


async def _router_node(state: RouterFlowState, *, model_factory: ModelFactory) -> dict:
    """Node: classify query intent."""
    query = state["query"]
    intent_result = await route_query(query, model_factory)
    return {
        "intent": intent_result.intent,
        "item_name": intent_result.item_name,
    }


def _dispatch(state: RouterFlowState) -> str:
    intent = state.get("intent", "item_query")
    if intent == "market_query":
        return "market_subflow"
    elif intent == "scout_query":
        return "scout_subflow"
    return "item_subflow"


async def _item_subflow_node(
    state: RouterFlowState, *, item_api: ItemAPI, model_factory: ModelFactory,
) -> dict:
    """Node: run item flow and format result."""
    from csqaq.flows.item_flow import build_item_flow

    flow = build_item_flow(item_api=item_api, model_factory=model_factory)
    r = await flow.ainvoke({
        "messages": [], "good_id": None,
        "good_name": state.get("item_name") or state["query"],
        "item_detail": None, "chart_data": None, "kline_data": None,
        "indicators": None, "analysis_result": None,
        "item_context": None, "market_context": None, "scout_context": None,
        "historical_advice": None, "summary": None, "action_detail": None,
        "risk_level": None, "requires_confirmation": False, "error": None,
    })
    parts = []
    if r.get("analysis_result"):
        parts.append(f"分析:\n{r['analysis_result']}")
    if r.get("summary"):
        parts.append(f"\n建议 (风险: {r.get('risk_level', 'unknown')}):\n{r['summary']}")
        if r.get("action_detail"):
            parts.append(r["action_detail"])
    return {"result": "\n".join(parts) if parts else f"查询失败: {r.get('error', '未知错误')}"}


async def _market_subflow_node(
    state: RouterFlowState, *, market_api: MarketAPI, model_factory: ModelFactory,
) -> dict:
    """Node: run market flow and format result."""
    from csqaq.flows.market_flow import build_market_flow

    flow = build_market_flow(market_api=market_api, model_factory=model_factory)
    r = await flow.ainvoke({
        "messages": [], "query": state["query"],
        "home_data": None, "sub_data": None, "market_context": None,
        "item_context": None, "scout_context": None, "historical_advice": None,
        "summary": None, "action_detail": None, "risk_level": None,
        "requires_confirmation": False, "error": None,
    })
    parts = []
    if r.get("market_context"):
        parts.append(f"大盘分析:\n{r['market_context']}")
    if r.get("summary"):
        parts.append(f"\n建议 (风险: {r.get('risk_level', 'unknown')}):\n{r['summary']}")
        if r.get("action_detail"):
            parts.append(r["action_detail"])
    return {"result": "\n".join(parts) if parts else f"查询失败: {r.get('error', '未知错误')}"}


async def _scout_subflow_node(
    state: RouterFlowState,
    *, rank_api: RankAPI, vol_api: VolAPI, model_factory: ModelFactory,
) -> dict:
    """Node: run scout flow and format result."""
    from csqaq.flows.scout_flow import build_scout_flow

    flow = build_scout_flow(rank_api=rank_api, vol_api=vol_api, model_factory=model_factory)
    r = await flow.ainvoke({
        "messages": [], "query": state["query"],
        "rank_data": None, "scout_context": None,
        "item_context": None, "market_context": None, "historical_advice": None,
        "summary": None, "action_detail": None, "risk_level": None,
        "requires_confirmation": False, "error": None,
    })
    parts = []
    if r.get("scout_context"):
        parts.append(f"机会发现:\n{r['scout_context']}")
    if r.get("summary"):
        parts.append(f"\n建议 (风险: {r.get('risk_level', 'unknown')}):\n{r['summary']}")
        if r.get("action_detail"):
            parts.append(r["action_detail"])
    return {"result": "\n".join(parts) if parts else f"查询失败: {r.get('error', '未知错误')}"}


def build_router_flow(
    item_api: ItemAPI,
    market_api: MarketAPI,
    rank_api: RankAPI,
    vol_api: VolAPI,
    model_factory: ModelFactory,
):
    """Build and compile the main router graph."""
    graph = StateGraph(RouterFlowState)

    graph.add_node("router", partial(_router_node, model_factory=model_factory))
    graph.add_node("item_subflow", partial(
        _item_subflow_node, item_api=item_api, model_factory=model_factory,
    ))
    graph.add_node("market_subflow", partial(
        _market_subflow_node, market_api=market_api, model_factory=model_factory,
    ))
    graph.add_node("scout_subflow", partial(
        _scout_subflow_node, rank_api=rank_api, vol_api=vol_api, model_factory=model_factory,
    ))

    graph.set_entry_point("router")
    graph.add_conditional_edges(
        "router", _dispatch,
        {"item_subflow": "item_subflow", "market_subflow": "market_subflow", "scout_subflow": "scout_subflow"},
    )
    graph.add_edge("item_subflow", END)
    graph.add_edge("market_subflow", END)
    graph.add_edge("scout_subflow", END)

    return graph.compile()

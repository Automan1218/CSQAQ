"""Parallel item flow — runs item + market + scout in parallel via asyncio.gather."""
from __future__ import annotations

import asyncio
from functools import partial
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph, add_messages

from csqaq.components.agents.advisor import advise_node
from csqaq.components.agents.item import analyze_node, fetch_chart_node, resolve_item_node
from csqaq.components.agents.market import analyze_market_node, fetch_market_data_node
from csqaq.components.agents.scout import analyze_opportunities_node, fetch_rank_data_node
from csqaq.components.models.factory import ModelFactory
from csqaq.infrastructure.csqaq_client.item import ItemAPI
from csqaq.infrastructure.csqaq_client.market import MarketAPI
from csqaq.infrastructure.csqaq_client.rank import RankAPI
from csqaq.infrastructure.csqaq_client.vol import VolAPI


class ParallelItemFlowState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    good_name: str | None
    item_context: dict | None
    market_context: dict | None
    scout_context: dict | None
    item_error: str | None
    market_error: str | None
    scout_error: str | None
    risk_level: str | None
    requires_confirmation: bool
    summary: str | None
    action_detail: str | None


def prepare_queries(state: ParallelItemFlowState) -> dict:
    """Pass-through node: extract good_name from query if not set."""
    good_name = state.get("good_name") or state.get("query")
    return {"good_name": good_name}


async def _run_item_branch(
    good_name: str,
    *,
    item_api: ItemAPI,
    model_factory: ModelFactory,
) -> dict:
    """Run item analysis branch: resolve -> fetch_chart -> analyze.

    Returns a dict with item_context or item_error.
    """
    # Build minimal state for item nodes
    item_state: dict = {
        "good_id": None,
        "good_name": good_name,
        "item_detail": None,
        "chart_data": None,
        "kline_data": None,
        "indicators": None,
        "ta_report": None,
        "analysis_result": None,
        "error": None,
    }

    # Step 1: resolve item
    resolve_result = await resolve_item_node(item_state, item_api=item_api)
    item_state.update(resolve_result)

    # Step 2: fetch chart (skips if error)
    chart_result = await fetch_chart_node(item_state, item_api=item_api)
    item_state.update(chart_result)

    # Step 3: analyze
    analyze_result = await analyze_node(item_state, model_factory=model_factory)
    item_state.update(analyze_result)

    if item_state.get("error"):
        return {"item_error": item_state["error"], "item_context": None}

    return {
        "item_context": {
            "analysis_result": item_state.get("analysis_result", ""),
            "item_detail": item_state.get("item_detail"),
            "indicators": item_state.get("indicators"),
            "ta_report": item_state.get("ta_report"),
        },
        "item_error": None,
    }


async def _run_market_branch(
    query: str,
    *,
    market_api: MarketAPI,
    model_factory: ModelFactory,
) -> dict:
    """Run market analysis branch: fetch_market_data -> analyze_market.

    Returns a dict with market_context or market_error.
    """
    market_state: dict = {
        "query": query,
        "home_data": None,
        "sub_data": None,
        "index_ta_report": None,
        "market_context": None,
        "error": None,
    }

    # Step 1: fetch market data
    fetch_result = await fetch_market_data_node(market_state, market_api=market_api)
    market_state.update(fetch_result)

    if market_state.get("error"):
        return {"market_error": market_state["error"], "market_context": None}

    # Step 2: analyze market
    analyze_result = await analyze_market_node(market_state, model_factory=model_factory)
    market_state.update(analyze_result)

    return {
        "market_context": {
            "analysis_result": market_state.get("market_context", ""),
            "index_ta_report": market_state.get("index_ta_report"),
        },
        "market_error": None,
    }


async def _run_scout_branch(
    query: str,
    *,
    rank_api: RankAPI,
    vol_api: VolAPI,
    model_factory: ModelFactory,
) -> dict:
    """Run scout analysis branch: fetch_rank_data -> analyze_opportunities.

    Returns a dict with scout_context or scout_error.
    """
    scout_state: dict = {
        "query": query,
        "rank_data": None,
        "scout_context": None,
        "error": None,
    }

    # Step 1: fetch rank data
    fetch_result = await fetch_rank_data_node(scout_state, rank_api=rank_api, vol_api=vol_api)
    scout_state.update(fetch_result)

    if scout_state.get("error"):
        return {"scout_error": scout_state["error"], "scout_context": None}

    # Step 2: analyze opportunities
    analyze_result = await analyze_opportunities_node(scout_state, model_factory=model_factory)
    scout_state.update(analyze_result)

    return {
        "scout_context": {"analysis_result": scout_state.get("scout_context", "")},
        "scout_error": None,
    }


async def run_parallel(
    state: ParallelItemFlowState,
    *,
    item_api: ItemAPI,
    market_api: MarketAPI,
    rank_api: RankAPI,
    vol_api: VolAPI,
    model_factory: ModelFactory,
) -> dict:
    """Node: run item, market, scout branches concurrently via asyncio.gather.

    Each branch is isolated: exceptions are caught per-branch and stored as errors.
    """
    good_name = state.get("good_name") or state.get("query", "")
    query = state.get("query", good_name)

    item_task = _run_item_branch(good_name, item_api=item_api, model_factory=model_factory)
    market_task = _run_market_branch(query, market_api=market_api, model_factory=model_factory)
    scout_task = _run_scout_branch(query, rank_api=rank_api, vol_api=vol_api, model_factory=model_factory)

    results = await asyncio.gather(item_task, market_task, scout_task, return_exceptions=True)

    merged: dict = {
        "item_context": None,
        "market_context": None,
        "scout_context": None,
        "item_error": None,
        "market_error": None,
        "scout_error": None,
    }

    error_keys = ["item_error", "market_error", "scout_error"]
    context_keys = ["item_context", "market_context", "scout_context"]

    for i, result in enumerate(results):
        ctx_key = context_keys[i]
        err_key = error_keys[i]
        if isinstance(result, Exception):
            merged[err_key] = str(result)
        else:
            merged[ctx_key] = result.get(ctx_key)
            if result.get(err_key):
                merged[err_key] = result[err_key]

    return merged


def merge_contexts(state: ParallelItemFlowState) -> dict:
    """Node: pack non-None contexts into advisor format.

    This is a pass-through since run_parallel already sets the context keys.
    The advisor node reads item_context, market_context, scout_context directly.
    """
    return {}


def build_parallel_item_flow(
    item_api: ItemAPI,
    market_api: MarketAPI,
    rank_api: RankAPI,
    vol_api: VolAPI,
    model_factory: ModelFactory,
):
    """Build and compile the parallel item analysis flow.

    Graph: prepare_queries -> run_parallel -> merge_contexts -> advise -> END
    """
    graph = StateGraph(ParallelItemFlowState)

    graph.add_node("prepare_queries", prepare_queries)
    graph.add_node("run_parallel", partial(
        run_parallel,
        item_api=item_api,
        market_api=market_api,
        rank_api=rank_api,
        vol_api=vol_api,
        model_factory=model_factory,
    ))
    graph.add_node("merge_contexts", merge_contexts)
    graph.add_node("advise", partial(advise_node, model_factory=model_factory))

    graph.set_entry_point("prepare_queries")
    graph.add_edge("prepare_queries", "run_parallel")
    graph.add_edge("run_parallel", "merge_contexts")
    graph.add_edge("merge_contexts", "advise")
    graph.add_edge("advise", END)

    return graph.compile()

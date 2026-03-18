from __future__ import annotations

import json
from typing import TYPE_CHECKING

from langchain_core.tools import tool

from csqaq.infrastructure.analysis.indicators import TechnicalIndicators

if TYPE_CHECKING:
    from csqaq.infrastructure.csqaq_client.item import ItemAPI


def create_item_tools(item_api: ItemAPI) -> list:
    """Create LangChain tools bound to a specific ItemAPI instance."""

    @tool
    async def search_item(query: str) -> str:
        """Search for CS2 items by name. Returns a list of matching items with IDs."""
        results = await item_api.search_suggest(query)
        if not results:
            return "No items found."
        lines = []
        for item in results[:5]:
            lines.append(f"- ID: {item.good_id} | {item.good_name} ({item.market_hash_name})")
        return "\n".join(lines)

    @tool
    async def get_item_detail(good_id: int) -> str:
        """Get detailed information about a CS2 item including multi-platform prices."""
        detail = await item_api.get_item_detail(good_id)
        return json.dumps(
            {
                "name": detail.good_name,
                "buff_sell": detail.buff_sell_price,
                "buff_buy": detail.buff_buy_price,
                "steam_sell": detail.steam_sell_price,
                "yyyp_sell": detail.yyyp_sell_price,
                "buff_sell_num": detail.buff_sell_num,
                "buff_buy_num": detail.buff_buy_num,
                "daily_change": f"{detail.daily_change_rate}%",
                "weekly_change": f"{detail.weekly_change_rate}%",
                "monthly_change": f"{detail.monthly_change_rate}%",
                "category": detail.category,
                "rarity": detail.rarity,
                "exterior": detail.exterior,
            },
            ensure_ascii=False,
            indent=2,
        )

    @tool
    async def get_price_chart(good_id: int, platform: str = "buff", period: str = "30d") -> str:
        """Get price history chart data for an item on a specific platform."""
        chart = await item_api.get_item_chart(good_id, platform=platform, period=period)
        if not chart.points:
            return "No chart data available."
        lines = [f"Price chart ({chart.platform}, {chart.period}): {len(chart.points)} data points"]
        # Show first, middle, last points for overview
        key_points = [chart.points[0], chart.points[len(chart.points) // 2], chart.points[-1]]
        for p in key_points:
            lines.append(f"  - Price: {p.price}, Volume: {p.volume}")
        return "\n".join(lines)

    @tool
    async def get_technical_analysis(good_id: int, platform: str = "buff", period: str = "30d") -> str:
        """Compute technical indicators (MA, volatility, momentum, spread) for an item."""
        chart = await item_api.get_item_chart(good_id, platform=platform, period=period)
        if not chart.points or len(chart.points) < 3:
            return "Insufficient data for technical analysis."

        prices = [p.price for p in chart.points]
        volumes = [p.volume for p in chart.points]

        ma_7 = TechnicalIndicators.moving_average(prices, window=7)
        ma_30 = TechnicalIndicators.moving_average(prices, window=30)
        vol = TechnicalIndicators.volatility(prices, window=min(len(prices), 30))
        momentum = TechnicalIndicators.price_momentum(prices, period=min(len(prices) - 1, 7))
        vol_trend = TechnicalIndicators.volume_trend(volumes, window=min(len(volumes) // 2, 7))

        # Get latest non-None MA values
        latest_ma7 = next((v for v in reversed(ma_7) if v is not None), None)
        latest_ma30 = next((v for v in reversed(ma_30) if v is not None), None)

        return json.dumps(
            {
                "current_price": prices[-1],
                "MA_7": round(latest_ma7, 2) if latest_ma7 else None,
                "MA_30": round(latest_ma30, 2) if latest_ma30 else None,
                "volatility": round(vol, 2),
                "momentum_7d": round(momentum, 2),
                "volume_trend": vol_trend,
                "price_range": f"{min(prices):.2f} - {max(prices):.2f}",
                "data_points": len(prices),
            },
            ensure_ascii=False,
            indent=2,
        )

    return [search_item, get_item_detail, get_price_chart, get_technical_analysis]

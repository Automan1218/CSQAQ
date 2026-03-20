from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from .inventory_schemas import InventoryStat
from .schemas import ChartData, ItemDetail, KlineBar, SuggestItem

if TYPE_CHECKING:
    from .client import CSQAQClient


class ItemAPI:
    """CSQAQ item-related API endpoints."""

    def __init__(self, client: CSQAQClient):
        self._client = client

    async def search_suggest(self, text: str) -> list[SuggestItem]:
        """Search for items by name. POST /search/suggest"""
        data = await self._client.post("/search/suggest", json={"text": text})
        if isinstance(data, list):
            return [SuggestItem.model_validate(item) for item in data]
        return []

    async def get_item_detail(self, good_id: int) -> ItemDetail:
        """Get full item detail. POST /info/good"""
        data = await self._client.post("/info/good", json={"goodId": good_id})
        return ItemDetail.model_validate(data)

    async def get_item_chart(
        self,
        good_id: int,
        platform: str = "buff",
        period: str = "30d",
        key: str = "sellPrice",
    ) -> ChartData:
        """Get price chart data. POST /info/chart"""
        data = await self._client.post(
            "/info/chart",
            json={
                "goodId": good_id,
                "key": key,
                "platform": platform,
                "period": period,
            },
        )
        return ChartData.model_validate(data)

    async def get_item_kline(
        self,
        good_id: int,
        platform: str = "buff",
        periods: str = "30d",
        max_time: int | None = None,
    ) -> list[KlineBar]:
        """Get K-line data. POST /info/simple/chartAll"""
        body: dict = {
            "goodId": good_id,
            "plat": platform,
            "periods": periods,
        }
        if max_time is not None:
            body["maxTime"] = max_time
        data = await self._client.post("/info/simple/chartAll", json=body)
        if isinstance(data, list):
            return [KlineBar.model_validate(bar) for bar in data]
        return []

    async def get_item_statistic(self, good_id: int) -> list[InventoryStat]:
        """Get 90-day inventory trend. GET /info/good/statistic

        Note: This is the only GET method in ItemAPI — all others use POST.
        This matches the external API spec for this endpoint.
        """
        data = await self._client.get("/info/good/statistic", params={"id": str(good_id)})
        if not isinstance(data, list):
            return []
        stats = [InventoryStat.model_validate(item) for item in data]
        cutoff = (datetime.now() - timedelta(days=90)).isoformat()
        return [s for s in stats if s.created_at >= cutoff]

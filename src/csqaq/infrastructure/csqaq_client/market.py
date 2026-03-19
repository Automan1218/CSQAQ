from __future__ import annotations

from typing import TYPE_CHECKING

from .market_schemas import HomeData, IndexKlineBar, SubData

if TYPE_CHECKING:
    from .client import CSQAQClient


class MarketAPI:
    """CSQAQ market index API endpoints."""

    def __init__(self, client: CSQAQClient):
        self._client = client

    async def get_home_data(self, data_type: str = "init") -> HomeData:
        """Get home page index data. GET /api/v1/current_data"""
        data = await self._client.get("/current_data", params={"type": data_type})
        return HomeData.model_validate(data)

    async def get_sub_data(self, sub_id: int = 1, data_type: str = "daily") -> SubData:
        """Get sub-index detail. GET /api/v1/sub_data"""
        data = await self._client.get("/sub_data", params={"id": str(sub_id), "type": data_type})
        return SubData.model_validate(data)

    async def get_index_kline(self, sub_id: int = 1, period: str = "1day") -> list[IndexKlineBar]:
        """GET /api/v1/sub/kline"""
        data = await self._client.get("/sub/kline", params={"id": str(sub_id), "type": period})
        if isinstance(data, list):
            return [IndexKlineBar.model_validate(bar) for bar in data]
        return []

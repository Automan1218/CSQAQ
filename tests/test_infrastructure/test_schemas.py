import json
from pathlib import Path

import pytest

from csqaq.infrastructure.csqaq_client.schemas import (
    ChartData,
    ChartPoint,
    ItemDetail,
    KlineBar,
    SuggestItem,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_suggest_item_parses_from_api():
    raw = json.loads((FIXTURES / "suggest_response.json").read_text(encoding="utf-8"))
    items = [SuggestItem.model_validate(r) for r in raw]
    assert len(items) == 2
    assert items[0].good_id == 7310
    assert items[0].good_name == "AK-47 | 红线 (久经沙场)"
    assert items[0].market_hash_name == "AK-47 | Redline (Field-Tested)"


def test_item_detail_parses_from_api():
    raw = json.loads((FIXTURES / "item_detail_response.json").read_text(encoding="utf-8"))
    detail = ItemDetail.model_validate(raw)
    assert detail.good_id == 7310
    assert detail.buff_sell_price == 85.50
    assert detail.daily_change_rate == 1.25
    assert detail.category == "步枪"


def test_chart_data_parses_from_api():
    raw = json.loads((FIXTURES / "chart_response.json").read_text(encoding="utf-8"))
    chart = ChartData.model_validate(raw)
    assert chart.good_id == 7310
    assert len(chart.points) == 3
    assert chart.points[0].price == 83.00


def test_kline_bar_parses_from_api():
    raw = json.loads((FIXTURES / "kline_response.json").read_text(encoding="utf-8"))
    bars = [KlineBar.model_validate(r) for r in raw]
    assert len(bars) == 2
    assert bars[0].open == 83.00
    assert bars[1].close == 85.50

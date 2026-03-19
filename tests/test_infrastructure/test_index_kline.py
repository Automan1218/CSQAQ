import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from csqaq.components.analysis.analyzer import analyze_index_kline
from csqaq.infrastructure.csqaq_client.market_schemas import IndexKlineBar


class TestIndexKlineBar:
    def test_parse(self):
        data = {"t": "1700150400000", "o": 1402.74, "c": 1385.55, "h": 1402.74, "l": 1385.55, "v": 0}
        bar = IndexKlineBar.model_validate(data)
        assert bar.o == 1402.74
        assert bar.c == 1385.55
        assert bar.v == 0
        assert bar.timestamp_int == 1700150400000  # validator converts t to int

    def test_parse_list(self):
        data = [
            {"t": "1700150400000", "o": 1402.74, "c": 1385.55, "h": 1402.74, "l": 1385.55, "v": 0},
            {"t": "1700236800000", "o": 1385.55, "c": 1374.73, "h": 1386.72, "l": 1374.73, "v": 0},
        ]
        bars = [IndexKlineBar.model_validate(d) for d in data]
        assert len(bars) == 2


class TestAnalyzeIndexKline:
    def test_skips_volume_divergence(self):
        bars = [
            IndexKlineBar.model_validate({"t": str(1700000000000 + i * 86400000), "o": 1400.0 + i, "c": 1400.0 + i * 1.5, "h": 1410.0 + i, "l": 1390.0 + i, "v": 0})
            for i in range(40)
        ]
        report = analyze_index_kline(bars, period="1day")
        vol_signals = [s for s in report.signals if s.name == "volume_price_divergence"]
        assert len(vol_signals) == 0

    def test_produces_direction(self):
        bars = [
            IndexKlineBar.model_validate({"t": str(1700000000000 + i * 86400000), "o": 1400.0 + i, "c": 1400.0 + i * 1.5, "h": 1410.0 + i, "l": 1390.0 + i, "v": 0})
            for i in range(40)
        ]
        report = analyze_index_kline(bars, period="1day")
        assert report.overall_direction in ("bullish", "bearish", "neutral")

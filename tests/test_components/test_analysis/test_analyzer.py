from csqaq.components.analysis.analyzer import TAReport, analyze_kline
from csqaq.infrastructure.csqaq_client.schemas import KlineBar


def _make_bars(closes: list[float], volume: int = 100) -> list[KlineBar]:
    """Helper: build KlineBar list from close prices."""
    bars = []
    for i, c in enumerate(closes):
        bars.append(KlineBar(
            timestamp=1700000000 + i * 86400,
            open=c - 0.5, close=c, high=c + 1.0, low=c - 1.0, volume=volume,
        ))
    return bars


class TestAnalyzeKline:
    def test_uptrend_report(self):
        closes = [100.0 + i * 1.0 for i in range(40)]
        bars = _make_bars(closes)
        report = analyze_kline(bars, period="1day")
        assert isinstance(report, TAReport)
        assert report.overall_direction in ("bullish", "bearish", "neutral")
        assert len(report.signals) > 0
        assert "ma5" in report.indicators or "rsi" in report.indicators
        assert report.summary  # non-empty

    def test_insufficient_data(self):
        bars = _make_bars([100.0, 101.0, 102.0])
        report = analyze_kline(bars, period="1day")
        assert report.overall_direction == "neutral"
        assert "数据不足" in report.summary

    def test_hourly_strength_penalty(self):
        closes = [100.0 + i * 1.0 for i in range(40)]
        bars = _make_bars(closes)
        daily_report = analyze_kline(bars, period="1day")
        hourly_report = analyze_kline(bars, period="1hour")
        # Hourly signals should have lower strength
        if hourly_report.signals and daily_report.signals:
            max_hourly = max(s.strength for s in hourly_report.signals)
            max_daily = max(s.strength for s in daily_report.signals)
            assert max_hourly <= max_daily

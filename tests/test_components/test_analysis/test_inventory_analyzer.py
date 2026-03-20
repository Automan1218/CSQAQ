import pytest

from csqaq.components.analysis.inventory_analyzer import (
    InventoryReport,
    analyze_inventory,
    detect_acceleration,
    detect_sudden_change,
    detect_inflection,
)
from csqaq.components.analysis.signals import Signal


class TestAnalyzeInventory:
    def test_decreasing_trend(self):
        """Steadily decreasing inventory should report 'decreasing' trend."""
        values = [30000 - i * 50 for i in range(30)]
        report = analyze_inventory(values)
        assert isinstance(report, InventoryReport)
        assert report.trend_direction == "decreasing"
        assert report.velocity < 0  # negative = decreasing
        assert report.summary  # non-empty

    def test_increasing_trend(self):
        values = [20000 + i * 30 for i in range(30)]
        report = analyze_inventory(values)
        assert report.trend_direction == "increasing"
        assert report.velocity > 0

    def test_stable_trend(self):
        values = [25000 + (i % 3 - 1) * 5 for i in range(30)]
        report = analyze_inventory(values)
        assert report.trend_direction == "stable"

    def test_insufficient_data(self):
        report = analyze_inventory([100, 99])
        assert report.trend_direction == "unknown"
        assert "数据不足" in report.summary

    def test_empty_data(self):
        report = analyze_inventory([])
        assert report.trend_direction == "unknown"

    def test_signals_populated(self):
        """Strong decreasing trend should produce signals."""
        values = [30000 - i * 100 for i in range(30)]
        report = analyze_inventory(values)
        assert all(isinstance(s, Signal) for s in report.signals)

    def test_indicators_present(self):
        values = [30000 - i * 50 for i in range(30)]
        report = analyze_inventory(values)
        assert "ma7" in report.indicators
        assert "ma30" in report.indicators or "ma20" in report.indicators
        assert "volatility" in report.indicators
        assert "velocity" in report.indicators


class TestDetectAcceleration:
    def test_accelerating_decrease(self):
        """Inventory decreasing faster in recent period vs earlier."""
        early = [30000 - i * 20 for i in range(15)]
        late = [early[-1] - i * 80 for i in range(1, 16)]
        values = early + late
        signal = detect_acceleration(values)
        assert signal is not None
        assert signal.direction == "bearish"  # accelerating decrease = supply shrinking fast
        assert signal.name == "inventory_acceleration"

    def test_no_acceleration(self):
        values = [30000 - i * 50 for i in range(30)]  # constant rate
        signal = detect_acceleration(values)
        assert signal is None  # no acceleration


class TestDetectSuddenChange:
    def test_sudden_drop(self):
        values = [30000] * 25 + [28000, 27000, 26000, 25500, 25000]
        signal = detect_sudden_change(values)
        assert signal is not None
        assert signal.name == "inventory_sudden_change"

    def test_no_sudden_change(self):
        values = [30000 - i * 50 for i in range(30)]
        signal = detect_sudden_change(values)
        assert signal is None


class TestDetectInflection:
    def test_inflection_decrease_to_increase(self):
        decreasing = [30000 - i * 100 for i in range(15)]
        increasing = [decreasing[-1] + i * 80 for i in range(1, 16)]
        values = decreasing + increasing
        signal = detect_inflection(values)
        assert signal is not None
        assert signal.name == "inventory_inflection"

    def test_no_inflection(self):
        values = [30000 - i * 50 for i in range(30)]
        signal = detect_inflection(values)
        assert signal is None

"""Inventory (存世量) trend analyzer.

Analyzes inventory time series using MA, volatility, and momentum from
TechnicalIndicators. Detects inventory-specific signals: acceleration,
sudden change, and inflection point.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from csqaq.components.analysis.indicators import TechnicalIndicators
from csqaq.components.analysis.signals import Signal

# Minimum data points for meaningful analysis
_MIN_DATA_POINTS = 5


@dataclass
class InventoryReport:
    """Result of inventory trend analysis."""

    signals: list[Signal] = field(default_factory=list)
    indicators: dict = field(default_factory=dict)
    trend_direction: str = "unknown"  # "increasing" | "decreasing" | "stable" | "unknown"
    velocity: float = 0.0             # units/day, negative = decreasing
    summary: str = ""


def analyze_inventory(values: list[int]) -> InventoryReport:
    """Analyze inventory time series and produce an InventoryReport.

    Args:
        values: Daily inventory counts, oldest first.

    Returns:
        InventoryReport with trend, velocity, indicators, and signals.
    """
    if len(values) < _MIN_DATA_POINTS:
        return InventoryReport(
            trend_direction="unknown",
            summary="数据不足，无法进行有效分析" if values else "无数据",
        )

    floats = [float(v) for v in values]

    # Compute indicators
    ma7 = TechnicalIndicators.moving_average(floats, 7)
    ma_long_window = 30 if len(floats) >= 30 else 20 if len(floats) >= 20 else len(floats)
    ma_long = TechnicalIndicators.moving_average(floats, ma_long_window)
    vol = TechnicalIndicators.volatility(floats, min(len(floats), 30))

    # Velocity: average daily change over recent 7 days
    recent_window = min(7, len(values) - 1)
    velocity = (values[-1] - values[-1 - recent_window]) / recent_window

    # Trend direction from velocity relative to current level
    current = values[-1]
    if current > 0:
        daily_pct = velocity / current * 100
    else:
        daily_pct = 0.0

    if daily_pct < -0.05:
        trend_direction = "decreasing"
    elif daily_pct > 0.05:
        trend_direction = "increasing"
    else:
        trend_direction = "stable"

    indicators = {
        "ma7": ma7[-1],
        f"ma{ma_long_window}": ma_long[-1],
        "volatility": vol,
        "velocity": velocity,
    }

    # Detect signals
    signals: list[Signal] = []
    for detector in (detect_acceleration, detect_sudden_change, detect_inflection):
        sig = detector(values)
        if sig is not None:
            signals.append(sig)

    # Build summary
    trend_cn = {"decreasing": "下降", "increasing": "上升", "stable": "稳定", "unknown": "未知"}
    summary = (
        f"存世量趋势: {trend_cn[trend_direction]}，"
        f"近{recent_window}日速率: {velocity:.1f}/天，"
        f"当前值: {current}，"
        f"MA7: {ma7[-1]:.0f}，波动率: {vol:.1f}"
    )
    if signals:
        summary += "。信号: " + "、".join(s.name for s in signals)

    return InventoryReport(
        signals=signals,
        indicators=indicators,
        trend_direction=trend_direction,
        velocity=velocity,
        summary=summary,
    )


def detect_acceleration(values: list[int]) -> Signal | None:
    """Detect acceleration in inventory change rate.

    Compares velocity of first half vs second half. If ratio > 2x, flag it.
    """
    if len(values) < 10:
        return None

    mid = len(values) // 2
    first_half = values[:mid]
    second_half = values[mid:]

    vel_first = (first_half[-1] - first_half[0]) / max(len(first_half) - 1, 1)
    vel_second = (second_half[-1] - second_half[0]) / max(len(second_half) - 1, 1)

    # Both must be in the same direction or second must be significantly stronger
    if abs(vel_first) < 0.1:
        # First half nearly flat, check if second half has strong movement
        if abs(vel_second) > abs(vel_first) * 3 and abs(vel_second) > 1:
            direction = "bearish" if vel_second < 0 else "bullish"
            return Signal(
                name="inventory_acceleration",
                direction=direction,
                strength=0.7,
                description=f"存世量变化加速: 前半段速率{vel_first:.1f}/天，后半段速率{vel_second:.1f}/天",
            )
        return None

    ratio = vel_second / vel_first if vel_first != 0 else 0

    if ratio > 2.0:
        # Same direction, accelerating
        direction = "bearish" if vel_second < 0 else "bullish"
        return Signal(
            name="inventory_acceleration",
            direction=direction,
            strength=0.7,
            description=f"存世量变化加速: 前半段速率{vel_first:.1f}/天，后半段速率{vel_second:.1f}/天",
        )

    return None


def detect_sudden_change(values: list[int]) -> Signal | None:
    """Detect sudden inventory change (single day exceeds 3x average daily change)."""
    if len(values) < 5:
        return None

    daily_changes = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    avg_change = sum(daily_changes) / len(daily_changes)

    if avg_change < 1:
        return None

    for i in range(1, len(values)):
        change = abs(values[i] - values[i - 1])
        if change > avg_change * 3:
            direction = "bearish" if values[i] < values[i - 1] else "bullish"
            return Signal(
                name="inventory_sudden_change",
                direction=direction,
                strength=0.8,
                description=f"存世量异常变动: 单日变化{values[i] - values[i-1]}，均值{avg_change:.0f}",
            )

    return None


def detect_inflection(values: list[int]) -> Signal | None:
    """Detect trend reversal (inflection point).

    Compares MA direction of first half vs second half. If opposite, flag it.
    """
    if len(values) < 10:
        return None

    mid = len(values) // 2
    first_half = values[:mid]
    second_half = values[mid:]

    slope_first = (first_half[-1] - first_half[0]) / max(len(first_half) - 1, 1)
    slope_second = (second_half[-1] - second_half[0]) / max(len(second_half) - 1, 1)

    # Opposite directions and both significant
    threshold = abs(values[0]) * 0.001 if values[0] != 0 else 1
    if (slope_first < -threshold and slope_second > threshold) or \
       (slope_first > threshold and slope_second < -threshold):
        if slope_second > 0:
            direction = "bullish"
            desc = "存世量拐点: 从下降转为上升"
        else:
            direction = "bearish"
            desc = "存世量拐点: 从上升转为下降"
        return Signal(
            name="inventory_inflection",
            direction=direction,
            strength=0.8,
            description=desc,
        )

    return None

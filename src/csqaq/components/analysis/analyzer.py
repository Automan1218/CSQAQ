from __future__ import annotations

from dataclasses import dataclass, field

from csqaq.components.analysis.indicators import TechnicalIndicators
from csqaq.components.analysis.signals import (
    Signal,
    detect_bollinger_breakout,
    detect_ma_crossover,
    detect_macd_crossover,
    detect_rsi_extreme,
    detect_volume_price_divergence,
)
from csqaq.infrastructure.csqaq_client.schemas import KlineBar

_HOURLY_PERIODS = ("1hour", "4hour")


@dataclass
class TAReport:
    """Technical analysis report for a set of K-line bars."""

    signals: list[Signal] = field(default_factory=list)
    indicators: dict = field(default_factory=dict)
    overall_direction: str = "neutral"  # "bullish" | "bearish" | "neutral"
    summary: str = ""


def _build_indicators(closes: list[float]) -> dict:
    """Compute all raw indicator values and return as a dict."""
    indicators: dict = {}

    ma5_series = TechnicalIndicators.moving_average(closes, 5)
    ma20_series = TechnicalIndicators.moving_average(closes, 20)
    ma5 = ma5_series[-1] if ma5_series else None
    ma20 = ma20_series[-1] if ma20_series else None
    indicators["ma5"] = ma5
    indicators["ma20"] = ma20

    rsi = TechnicalIndicators.rsi(closes)
    indicators["rsi"] = rsi

    macd_result = TechnicalIndicators.macd(closes)
    indicators["macd"] = macd_result.macd_line
    indicators["macd_signal"] = macd_result.signal_line
    indicators["macd_histogram"] = macd_result.histogram

    bb_result = TechnicalIndicators.bollinger_bands(closes)
    indicators["bollinger_upper"] = bb_result.upper
    indicators["bollinger_middle"] = bb_result.middle
    indicators["bollinger_lower"] = bb_result.lower

    return indicators


def _compute_direction(signals: list[Signal]) -> str:
    """Weighted vote: sum bullish strengths vs bearish strengths.

    Returns 'neutral' when diff < 0.1.
    """
    bullish_sum = sum(s.strength for s in signals if s.direction == "bullish")
    bearish_sum = sum(s.strength for s in signals if s.direction == "bearish")
    diff = bullish_sum - bearish_sum
    if abs(diff) < 0.1:
        return "neutral"
    return "bullish" if diff > 0 else "bearish"


def _build_summary(
    signals: list[Signal],
    overall_direction: str,
    indicators: dict,
    period: str,
    insufficient: bool,
) -> str:
    """Generate a Chinese-language summary string."""
    parts: list[str] = []

    if insufficient:
        parts.append("数据不足，部分指标未生效")

    direction_map = {"bullish": "看涨", "bearish": "看跌", "neutral": "中性"}
    direction_label = direction_map.get(overall_direction, "中性")
    parts.append(f"综合方向：{direction_label}（周期：{period}）")

    if signals:
        signal_descs = [f"[{s.name}] {s.description}" for s in signals]
        parts.append("信号：" + "；".join(signal_descs))

    rsi_val = indicators.get("rsi")
    if rsi_val is not None:
        parts.append(f"RSI={rsi_val:.1f}")

    ma5 = indicators.get("ma5")
    ma20 = indicators.get("ma20")
    if ma5 is not None and ma20 is not None:
        parts.append(f"MA5={ma5:.2f}，MA20={ma20:.2f}")

    return "；".join(parts)


def analyze_kline(bars: list[KlineBar], period: str = "1day") -> TAReport:
    """Run all 5 TA signal detectors on K-line bars and produce a TAReport.

    For hourly/4-hour periods, each signal's strength is multiplied by 0.4
    because short-term signals are less reliable in the T+7 CS2 skin market.
    """
    closes = [bar.close for bar in bars]
    volumes = [bar.volume for bar in bars]

    # Insufficient data shortcut
    if len(closes) < 2:
        indicators = _build_indicators(closes)
        return TAReport(
            signals=[],
            indicators=indicators,
            overall_direction="neutral",
            summary="数据不足，部分指标未生效；综合方向：中性（周期：" + period + "）",
        )

    # Run signal detectors
    raw_signals: list[Signal | None] = [
        detect_ma_crossover(closes),
        detect_rsi_extreme(closes),
        detect_macd_crossover(closes),
        detect_bollinger_breakout(closes),
        detect_volume_price_divergence(closes, volumes),
    ]
    signals = [s for s in raw_signals if s is not None]

    # Apply hourly strength penalty
    is_short_period = any(period.startswith(p) for p in _HOURLY_PERIODS)
    if is_short_period:
        signals = [
            Signal(
                name=s.name,
                direction=s.direction,
                strength=s.strength * 0.4,
                description=s.description,
            )
            for s in signals
        ]

    # Compute overall direction
    overall_direction = _compute_direction(signals) if signals else "neutral"

    # Build indicators dict
    indicators = _build_indicators(closes)

    # Determine if insufficient data (fewer than 2 signals)
    insufficient = len(signals) < 2

    # Build summary
    summary = _build_summary(signals, overall_direction, indicators, period, insufficient)

    return TAReport(
        signals=signals,
        indicators=indicators,
        overall_direction=overall_direction,
        summary=summary,
    )


def analyze_index_kline(bars: list[KlineBar], period: str = "1day") -> TAReport:
    """Same as analyze_kline but skips volume_price_divergence.

    Indices (e.g. market-wide index) do not have meaningful per-item volume.
    """
    closes = [bar.close for bar in bars]

    if len(closes) < 2:
        indicators = _build_indicators(closes)
        return TAReport(
            signals=[],
            indicators=indicators,
            overall_direction="neutral",
            summary="数据不足，部分指标未生效；综合方向：中性（周期：" + period + "）",
        )

    raw_signals: list[Signal | None] = [
        detect_ma_crossover(closes),
        detect_rsi_extreme(closes),
        detect_macd_crossover(closes),
        detect_bollinger_breakout(closes),
        # volume_price_divergence intentionally omitted for index
    ]
    signals = [s for s in raw_signals if s is not None]

    is_short_period = any(period.startswith(p) for p in _HOURLY_PERIODS)
    if is_short_period:
        signals = [
            Signal(
                name=s.name,
                direction=s.direction,
                strength=s.strength * 0.4,
                description=s.description,
            )
            for s in signals
        ]

    overall_direction = _compute_direction(signals) if signals else "neutral"
    indicators = _build_indicators(closes)
    insufficient = len(signals) < 2
    summary = _build_summary(signals, overall_direction, indicators, period, insufficient)

    return TAReport(
        signals=signals,
        indicators=indicators,
        overall_direction=overall_direction,
        summary=summary,
    )

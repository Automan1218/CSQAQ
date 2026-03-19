import statistics


class TechnicalIndicators:
    """Pure numerical computations for technical analysis.

    Agents don't do math — this module does.
    """

    @staticmethod
    def moving_average(prices: list[float], window: int) -> list[float | None]:
        """Simple Moving Average. Returns None for positions with insufficient data."""
        result: list[float | None] = []
        for i in range(len(prices)):
            if i < window - 1:
                result.append(None)
            else:
                window_slice = prices[i - window + 1 : i + 1]
                result.append(sum(window_slice) / window)
        return result

    @staticmethod
    def exponential_moving_average(
        prices: list[float], window: int, smoothing: int = 2
    ) -> list[float | None]:
        """Exponential Moving Average. Returns None for positions with insufficient data.

        First EMA value is the SMA of the first `window` prices.
        Subsequent values use: EMA = price * multiplier + prev_EMA * (1 - multiplier)
        where multiplier = smoothing / (window + 1).
        """
        result: list[float | None] = [None] * len(prices)
        if len(prices) < window:
            return result
        multiplier = smoothing / (window + 1)
        first_sma = sum(prices[:window]) / window
        result[window - 1] = first_sma
        for i in range(window, len(prices)):
            result[i] = prices[i] * multiplier + result[i - 1] * (1 - multiplier)
        return result

    @staticmethod
    def volatility(prices: list[float], window: int) -> float:
        """Standard deviation of price changes over the window.

        Returns 0.0 if fewer than 2 data points in window.
        """
        if len(prices) < 2:
            return 0.0
        recent = prices[-window:] if len(prices) >= window else prices
        if len(recent) < 2:
            return 0.0
        return statistics.stdev(recent)

    @staticmethod
    def price_momentum(prices: list[float], period: int) -> float:
        """Price change over a period: current - price_N_periods_ago."""
        if len(prices) <= period:
            return prices[-1] - prices[0] if len(prices) >= 2 else 0.0
        return prices[-1] - prices[-1 - period]

    @staticmethod
    def platform_spread(price_a: float, price_b: float) -> float:
        """Percentage spread between two platform prices.

        Returns (a - b) / b * 100. Positive means A is more expensive.
        """
        if price_b == 0:
            return 0.0
        return (price_a - price_b) / price_b * 100

    @staticmethod
    def volume_trend(volumes: list[int], window: int) -> str:
        """Classify recent volume trend as 'increasing', 'decreasing', or 'stable'.

        Compares average of last `window` volumes to the `window` before that.
        Uses a 10% threshold for classification.
        """
        if len(volumes) < window * 2:
            return "stable"
        recent = volumes[-window:]
        previous = volumes[-window * 2 : -window]
        if not previous:
            return "stable"
        avg_recent = sum(recent) / len(recent)
        avg_previous = sum(previous) / len(previous)
        if avg_previous == 0:
            return "stable"
        change_pct = (avg_recent - avg_previous) / avg_previous * 100
        if change_pct > 10:
            return "increasing"
        elif change_pct < -10:
            return "decreasing"
        return "stable"

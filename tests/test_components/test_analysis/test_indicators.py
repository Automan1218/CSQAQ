from csqaq.components.analysis.indicators import TechnicalIndicators


class TestMovingAverage:
    def test_basic(self):
        prices = [10, 20, 30, 40, 50]
        result = TechnicalIndicators.moving_average(prices, window=3)
        assert result == [None, None, 20.0, 30.0, 40.0]

    def test_window_larger_than_data(self):
        result = TechnicalIndicators.moving_average([1, 2], window=5)
        assert result == [None, None]


class TestEMA:
    def test_basic(self):
        prices = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
        result = TechnicalIndicators.exponential_moving_average(prices, window=3)
        assert result[0] is None
        assert result[1] is None
        assert result[2] is not None  # first EMA at index window-1
        # EMA should be between min and max of window
        for v in result[2:]:
            assert 10.0 <= v <= 16.0

    def test_window_larger_than_data(self):
        result = TechnicalIndicators.exponential_moving_average([1.0, 2.0], window=5)
        assert all(v is None for v in result)


class TestVolatility:
    def test_basic(self):
        prices = [100.0, 102.0, 98.0, 101.0, 99.0]
        vol = TechnicalIndicators.volatility(prices, window=5)
        assert vol > 0

    def test_single_value(self):
        assert TechnicalIndicators.volatility([100.0], window=5) == 0.0


class TestPriceMomentum:
    def test_basic(self):
        prices = [100.0, 105.0, 110.0]
        assert TechnicalIndicators.price_momentum(prices, period=2) == 10.0


class TestPlatformSpread:
    def test_basic(self):
        spread = TechnicalIndicators.platform_spread(110.0, 100.0)
        assert spread == 10.0

    def test_zero_denominator(self):
        assert TechnicalIndicators.platform_spread(50.0, 0) == 0.0


class TestVolumeTrend:
    def test_increasing(self):
        vols = [100, 100, 100, 200, 200, 200]
        assert TechnicalIndicators.volume_trend(vols, window=3) == "increasing"

    def test_stable(self):
        vols = [100, 100, 100, 105, 100, 95]
        assert TechnicalIndicators.volume_trend(vols, window=3) == "stable"


class TestRSI:
    def test_basic_uptrend(self):
        # Steadily rising prices → RSI should be high (>50)
        prices = [float(i) for i in range(20)]  # 0,1,2,...,19
        rsi = TechnicalIndicators.rsi(prices, period=14)
        assert 90 <= rsi <= 100  # pure uptrend

    def test_basic_downtrend(self):
        prices = [float(20 - i) for i in range(20)]  # 20,19,...,1
        rsi = TechnicalIndicators.rsi(prices, period=14)
        assert 0 <= rsi <= 10  # pure downtrend

    def test_insufficient_data(self):
        prices = [10.0, 11.0, 10.5]
        rsi = TechnicalIndicators.rsi(prices, period=14)
        assert rsi == 50.0  # default neutral


class TestMACD:
    def test_returns_named_tuple(self):
        # 40 data points for MACD(12,26,9)
        prices = [100.0 + i * 0.5 for i in range(40)]
        result = TechnicalIndicators.macd(prices)
        assert hasattr(result, "macd_line")
        assert hasattr(result, "signal_line")
        assert hasattr(result, "histogram")

    def test_uptrend_positive_macd(self):
        prices = [100.0 + i * 1.0 for i in range(40)]
        result = TechnicalIndicators.macd(prices)
        assert result.macd_line > 0  # uptrend → positive MACD

    def test_insufficient_data(self):
        prices = [10.0, 11.0]
        result = TechnicalIndicators.macd(prices)
        assert result.macd_line == 0.0


class TestBollingerBands:
    def test_returns_named_tuple(self):
        prices = [100.0 + (i % 5) for i in range(25)]
        result = TechnicalIndicators.bollinger_bands(prices)
        assert hasattr(result, "upper")
        assert hasattr(result, "middle")
        assert hasattr(result, "lower")

    def test_band_ordering(self):
        prices = [100.0 + (i % 5) for i in range(25)]
        result = TechnicalIndicators.bollinger_bands(prices)
        assert result.lower < result.middle < result.upper

    def test_insufficient_data(self):
        prices = [10.0, 11.0]
        result = TechnicalIndicators.bollinger_bands(prices)
        assert result.upper == 0.0

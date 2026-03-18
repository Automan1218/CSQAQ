import pytest
from csqaq.infrastructure.analysis.indicators import TechnicalIndicators


class TestMovingAverage:
    def test_basic_ma(self):
        prices = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = TechnicalIndicators.moving_average(prices, window=3)
        # MA(3) for [10,20,30,40,50] = [None, None, 20.0, 30.0, 40.0]
        assert result == [None, None, 20.0, 30.0, 40.0]

    def test_window_larger_than_data(self):
        prices = [10.0, 20.0]
        result = TechnicalIndicators.moving_average(prices, window=5)
        assert result == [None, None]


class TestVolatility:
    def test_constant_prices_zero_volatility(self):
        prices = [100.0, 100.0, 100.0, 100.0]
        assert TechnicalIndicators.volatility(prices, window=3) == pytest.approx(0.0, abs=0.001)

    def test_volatile_prices(self):
        prices = [100.0, 110.0, 90.0, 105.0, 95.0]
        vol = TechnicalIndicators.volatility(prices, window=5)
        assert vol > 0


class TestPriceMomentum:
    def test_positive_momentum(self):
        prices = [100.0, 105.0, 110.0, 115.0]
        mom = TechnicalIndicators.price_momentum(prices, period=3)
        assert mom == pytest.approx(15.0, abs=0.01)  # 115 - 100

    def test_negative_momentum(self):
        prices = [100.0, 95.0, 90.0, 85.0]
        mom = TechnicalIndicators.price_momentum(prices, period=3)
        assert mom == pytest.approx(-15.0, abs=0.01)


class TestPlatformSpread:
    def test_spread_calculation(self):
        spread = TechnicalIndicators.platform_spread(85.5, 80.0)
        assert spread == pytest.approx(6.875, abs=0.01)  # (85.5-80)/80*100


class TestVolumeTrend:
    def test_increasing_volume(self):
        volumes = [100, 100, 100, 300, 400, 500]
        assert TechnicalIndicators.volume_trend(volumes, window=3) == "increasing"

    def test_decreasing_volume(self):
        volumes = [500, 400, 300, 100, 100, 100]
        assert TechnicalIndicators.volume_trend(volumes, window=3) == "decreasing"

    def test_stable_volume(self):
        volumes = [100, 101, 99, 100, 100, 101]
        assert TechnicalIndicators.volume_trend(volumes, window=3) == "stable"

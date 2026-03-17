from pydantic import BaseModel, Field


class SuggestItem(BaseModel):
    """Search suggestion result."""

    model_config = {"populate_by_name": True}

    good_id: int = Field(alias="goodId")
    good_name: str = Field(alias="goodName")
    market_hash_name: str = Field(alias="marketHashName")
    image_url: str = Field(alias="imageUrl")


class ItemDetail(BaseModel):
    """Full item detail with multi-platform prices."""

    model_config = {"populate_by_name": True}

    good_id: int = Field(alias="goodId")
    good_name: str = Field(alias="goodName")
    market_hash_name: str = Field(alias="marketHashName")
    image_url: str = Field(alias="imageUrl")

    buff_sell_price: float = Field(alias="buffSellPrice")
    buff_buy_price: float = Field(alias="buffBuyPrice")
    steam_sell_price: float = Field(alias="steamSellPrice")
    yyyp_sell_price: float = Field(alias="yyypSellPrice")

    buff_sell_num: int = Field(alias="buffSellNum")
    buff_buy_num: int = Field(alias="buffBuyNum")
    steam_sell_num: int = Field(alias="steamSellNum")

    daily_change_rate: float = Field(alias="dailyChangeRate")
    weekly_change_rate: float = Field(alias="weeklyChangeRate")
    monthly_change_rate: float = Field(alias="monthlyChangeRate")

    category: str = ""
    rarity: str = ""
    exterior: str = ""


class ChartPoint(BaseModel):
    """Single data point in a price chart."""

    timestamp: int
    price: float
    volume: int


class ChartData(BaseModel):
    """Price chart for an item on a specific platform."""

    model_config = {"populate_by_name": True}

    good_id: int = Field(alias="goodId")
    platform: str
    period: str
    points: list[ChartPoint]


class KlineBar(BaseModel):
    """Single K-line (candlestick) bar."""

    timestamp: int
    open: float
    close: float
    high: float
    low: float
    volume: int

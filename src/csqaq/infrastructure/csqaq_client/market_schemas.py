from pydantic import BaseModel


class SubIndexItem(BaseModel):
    """Sub-index entry from GET /api/v1/current_data"""
    id: int
    name: str
    name_key: str
    img: str
    market_index: float
    chg_num: float
    chg_rate: float
    open: float
    close: float
    high: float
    low: float
    updated_at: str


class RateData(BaseModel):
    """Rise/fall distribution counts by time period."""
    count_positive_1: int
    count_negative_1: int
    count_zero_1: int
    count_positive_7: int
    count_negative_7: int
    count_zero_7: int
    count_positive_15: int
    count_negative_15: int
    count_zero_15: int
    count_positive_30: int
    count_negative_30: int
    count_zero_30: int
    count_positive_90: int
    count_negative_90: int
    count_zero_90: int
    count_positive_180: int
    count_negative_180: int
    count_zero_180: int


class OnlineNumber(BaseModel):
    """Online player data."""
    current_number: int
    today_peak: int
    month_peak: int
    month_player: int
    same_month_player: int
    same_time_number: int
    rate: float
    same_time_number_week: int
    rate_week: float
    created_at: str


class GreedyStatus(BaseModel):
    """Market sentiment indicator."""
    level: str
    label: str


class HomeData(BaseModel):
    """Home page data from GET /api/v1/current_data?type=init"""
    sub_index_data: list[SubIndexItem]
    chg_type_data: list[dict]
    chg_price_data: list[dict]
    rate_data: RateData
    online_number: OnlineNumber
    greedy_status: GreedyStatus
    online_chart: list[dict] = []
    greedy: list = []
    alteration: list[dict] = []
    view_count: list[dict] = []
    card_price: list[dict] = []


class SubIndexCount(BaseModel):
    """Index summary."""
    name: str
    img: str = ""
    now: float
    amplitude: float
    rate: float
    max_value: float
    min_value: float
    consecutive_days: int


class SubData(BaseModel):
    """Index detail from GET /api/v1/sub_data"""
    timestamp: list[int]
    count: SubIndexCount
    main_data: list[list[float]]
    hourly_list: list[float]

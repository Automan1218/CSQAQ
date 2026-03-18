from pydantic import BaseModel


class VolItem(BaseModel):
    """Trading volume item from POST /api/v1/info/vol_data_info"""
    id: int
    good_id: int
    name: str
    img: str
    group: str
    statistic: int
    updated_at: str
    avg_price: float
    sum_price: float
    special: int

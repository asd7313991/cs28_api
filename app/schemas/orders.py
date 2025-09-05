from pydantic import BaseModel, Field
from typing import List

class BetItemIn(BaseModel):
    play_code: int
    selection: str
    odds: float = Field(gt=0)
    stake_amount: float = Field(gt=0)

class BetIn(BaseModel):
    lottery_code: str
    issue_code: str
    # v2 写法：用 Field 指定最小/最大长度
    items: List[BetItemIn] = Field(min_length=1, max_length=10)

class BetOut(BaseModel):
    order_id: int
    total_amount: float
    status: int

from typing import List, Optional
from pydantic import BaseModel, Field

# 下单入参（前端只传玩法与金额）
class OrderItemIn(BaseModel):
    play: str | int                # '大'/'小'/'单'/'双'/'极大'/'极小' 或 0..27
    amount: float = Field(gt=0)    # 金额

class OrderPlaceIn(BaseModel):
    code: str                      # lottery_code，例如 'jnd28'
    issue: str | int               # issue_code，可字符串或数字
    items: List[OrderItemIn]
    channel: Optional[str] = None  # 可选：渠道
    idempotency_key: Optional[str] = None  # 可选：幂等键

class OrderPlaceOut(BaseModel):
    order_id: int
    total_amount: float
    status: int  # 0: ok

# 历史返回
class OrderItemOut(BaseModel):
    id: int
    play: str
    amount: float
    odds: float

class OrderOut(BaseModel):
    id: int
    lottery_code: str
    issue_code: str
    total_amount: float
    status: int
    items: List[OrderItemOut]

# 撤单
class OrderCancelIn(BaseModel):
    order_id: int

class OrderCancelOut(BaseModel):
    order_id: int
    status: int  # 1: cancelled
    balance: float

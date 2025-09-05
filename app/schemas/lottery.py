from pydantic import BaseModel, Field
from typing import Optional, List

class IssueResult(BaseModel):
    lottery_code: str
    issue_code: str
    n1: int
    n2: int
    n3: int
    sum_value: int
    bs: int
    oe: int
    extreme: int
    open_time: str

class CurrentIssueResp(BaseModel):
    issue_code: str
    lottery_code: str
    open_time: str
    close_time: str
    allow_bet: bool

class HistoryItem(BaseModel):
    issue_code: str
    open_time: str
    n1: int; n2: int; n3: int
    sum_value: int
    bs: int; oe: int; extreme: int

class HistoryResp(BaseModel):
    code: str = Field(..., description="lottery code")
    list: List[HistoryItem]

from fastapi import APIRouter, Depends, Query
from typing import List
from datetime import datetime
import json
from sqlalchemy import select
from app.db.redis import r
from app.db.session import AsyncSession, get_session
from app.constants import k_current_issue, k_last_result, k_history
from app.models.issue import Issue
from app.schemas.lottery import CurrentIssueResp, HistoryResp, HistoryItem
from app.models.play_type import PlayType  # 你的 ORM 模型

router = APIRouter(prefix="/api/lottery", tags=["lottery"])

@router.get("/current", response_model=CurrentIssueResp)
async def current_issue(code: str = Query(...), db: AsyncSession = Depends(get_session)):
    ci = await r.hgetall(k_current_issue(code))
    if ci:
        return {
            "issue_code": ci.get("issue_code",""),
            "lottery_code": ci.get("lottery_code", code),
            "open_time": ci.get("open_time",""),
            "close_time": ci.get("close_time",""),
            "allow_bet": ci.get("allow_bet","0") == "1"
        }
    result = await db.execute(
        Issue.__table__.select()
        .where(Issue.lottery_code == code, Issue.status >= 3)
        .order_by(Issue.open_time.desc())
        .limit(1)
    )
    m = result.mappings().first()
    if m:
        open_time = m["open_time"].strftime("%Y-%m-%d %H:%M:%S")
        close_time = m["close_time"].strftime("%Y-%m-%d %H:%M:%S")
        return {
            "issue_code": m["issue_code"],
            "lottery_code": code,
            "open_time": open_time,
            "close_time": close_time,
            "allow_bet": False
        }

    return {"issue_code":"","lottery_code":code,"open_time":"","close_time":"","allow_bet":False}

@router.get("/last")
async def last_result(code: str):
    lr = await r.get(k_last_result(code))
    if lr:
        try:
            return json.loads(lr)
        except Exception:
            return {"raw": lr}
    return {}

@router.get("/history", response_model=HistoryResp)
async def history(code: str, limit: int = 30):
    raw = await r.lrange(k_history(code), 0, limit - 1)
    items = []
    for s in raw:
        try:
            items.append(HistoryItem(**json.loads(s)))
        except Exception:
            continue
    # 不要反转：因为我们保证了 Redis 列表就是新→旧
    return {"code": code, "list": items}

@router.get("/odds")
async def get_odds(
        code: str = Query(..., description="彩种代码"),
        session: AsyncSession = Depends(get_session),
):
    stmt = select(
        PlayType.name,     # 展示名称
        PlayType.odds,
        PlayType.status
    ).where(PlayType.lottery_code == code)
    rows = (await session.execute(stmt)).all()
    return [
        { "name": k.name, "odds": k.odds, "status": k.status}
        for k in rows
    ]






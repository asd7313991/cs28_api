from datetime import datetime, timedelta
from typing import Dict, Any
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.issue import Issue
from app.models.lottery import Lottery
from app.constants import k_last_result, k_history, k_current_issue
from app.db.redis import r

def calc_fields(n1:int, n2:int, n3:int):
    s = n1 + n2 + n3
    bs = 1 if s >= 14 else 2  # 大/小
    oe = 1 if s % 2 == 1 else 2
    extreme = 1 if s >= 24 else (2 if s <= 3 else 0)
    return s, bs, oe, extreme

async def upsert_issue_from_result(db: AsyncSession, lottery_code: str, issue_code: str, 
                                   n1:int, n2:int, n3:int, open_time: datetime, raw_json: str) -> Issue:
    s, bs, oe, extreme = calc_fields(n1,n2,n3)
    # get lottery for lock_ahead
    lot = (await db.execute(select(Lottery).where(Lottery.code==lottery_code))).scalar_one()
    close_time = open_time - timedelta(seconds=lot.lock_ahead_seconds or 3)

    res = await db.execute(select(Issue).where(Issue.lottery_code==lottery_code, Issue.issue_code==issue_code))
    row = res.scalar_one_or_none()
    if row:
        row.n1, row.n2, row.n3 = n1, n2, n3
        row.sum_value, row.bs, row.oe, row.extreme = s, bs, oe, extreme
        row.open_time = open_time
        row.close_time = close_time
        row.status = 3  # 已开奖
        row.raw_json = (raw_json or "")[:255]
    else:
        row = Issue(
            lottery_code=lottery_code,
            issue_code=issue_code,
            open_time=open_time,
            close_time=close_time,
            status=3,
            n1=n1, n2=n2, n3=n3,
            sum_value=s, bs=bs, oe=oe, extreme=extreme,
            raw_json=(raw_json or "")[:255]
        )
        db.add(row)
    await db.commit()
    return row

# app/services/issue_service.py
async def set_redis_after_issue(lottery_code: str, issue_dict: dict):
    import json
    from app.db.redis import r
    from app.constants import k_history, k_last_result

    h_key = k_history(lottery_code)
    lr_key = k_last_result(lottery_code)

    payload = json.dumps(issue_dict, ensure_ascii=False, sort_keys=True)
    issue_code = issue_dict["issue_code"]

    # 先删除历史里相同期号（避免重复）——按值删除，需用“规范化JSON”（sort_keys=True）
    existing = await r.lrange(h_key, 0, 199)
    if existing:
        pipe = r.pipeline()
        for item in existing:
            try:
                if json.loads(item).get("issue_code") == issue_code:
                    pipe.lrem(h_key, 0, item)
            except Exception:
                continue
        await pipe.execute()

    # 头插 + 限长 + 更新 last_result（保证最新在前）
    pipe = r.pipeline()
    pipe.lpush(h_key, payload)
    pipe.ltrim(h_key, 0, 199)
    pipe.set(lr_key, payload)
    await pipe.execute()



async def set_current_issue_cache(lottery_code:str, issue_code:str, open_time:datetime, close_time:datetime, allow_bet:bool):
    payload = {
        "lottery_code": lottery_code,
        "issue_code": issue_code,
        "open_time": open_time.strftime("%Y-%m-%d %H:%M:%S"),
        "close_time": close_time.strftime("%Y-%m-%d %H:%M:%S"),
        "allow_bet": "1" if allow_bet else "0"
    }
    await r.hset(k_current_issue(lottery_code), mapping=payload)
    await r.expire(k_current_issue(lottery_code), 3600)

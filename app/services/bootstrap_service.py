from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import engine, Base
from app.models.lottery import Lottery
from app.models.issue import Issue
from app.core.config import settings
from app.db.redis import r
from app.constants import k_last_result, k_history
from datetime import datetime
import json

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def ensure_default_lottery(session: AsyncSession):
    res = await session.execute(select(Lottery).where(Lottery.code==settings.LOTTERY_DEFAULT_CODE))
    lot = res.scalar_one_or_none()
    if lot is None:
        lot = Lottery(
            code=settings.LOTTERY_DEFAULT_CODE,
            name=settings.LOTTERY_DEFAULT_NAME,
            period_seconds=settings.LOTTERY_DEFAULT_PERIOD_SECONDS,
            lock_ahead_seconds=3,
            status=1,
            tz="Asia/Shanghai"
        )
        session.add(lot)
        await session.commit()
    return lot

# app/services/bootstrap_service.py
async def warmup_redis_from_db(session: AsyncSession, lottery_code: str, limit: int = 200):
    import json
    from sqlalchemy import select
    from app.models.issue import Issue
    from app.db.redis import r
    from app.constants import k_history, k_last_result

    # 用 open_time 升序取出（旧→新）
    result = await session.execute(
        Issue.__table__.select()
        .where(Issue.lottery_code == lottery_code, Issue.status >= 3)
        .order_by(Issue.open_time.asc())
        .limit(limit)
    )
    rows = result.mappings().all()

    h_key = k_history(lottery_code)
    lr_key = k_last_result(lottery_code)
    await r.delete(h_key)

    last_payload = None
    for d in rows:
        item = {
            "lottery_code": d["lottery_code"],
            "issue_code": d["issue_code"],
            "n1": d["n1"], "n2": d["n2"], "n3": d["n3"],
            "sum_value": d["sum_value"],
            "bs": d["bs"], "oe": d["oe"], "extreme": d["extreme"],
            "open_time": d["open_time"].strftime("%Y-%m-%d %H:%M:%S"),
        }
        payload = json.dumps(item, ensure_ascii=False, sort_keys=True)
        # 旧→新依次 LPUSH，最终列表是 新→旧（最新在索引0）
        await r.lpush(h_key, payload)
        last_payload = payload

    if last_payload:
        await r.set(lr_key, last_payload)




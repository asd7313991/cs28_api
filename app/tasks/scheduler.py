import asyncio, json
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from sqlalchemy import select
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.lottery import Lottery
from app.services.issue_service import upsert_issue_from_result, set_redis_after_issue, set_current_issue_cache
from app.db.redis import r
from app.constants import k_current_issue

scheduler = AsyncIOScheduler()

async def fetch_jnd28_result():
    url = settings.COLLECTOR_JND28_URL
    ts = int(datetime.now().timestamp()*1000)
    url = f"{url}{'&' if '?' in url else '?'}_={ts}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()

async def collector_job():
    async with AsyncSessionLocal() as session:
        lottery_code = settings.LOTTERY_DEFAULT_CODE
        try:
            data = await fetch_jnd28_result()
            issue_code = str(data.get("issue") or data.get("issueCode") or data.get("expect") or "")
            nums = str(data.get("code") or data.get("nums") or data.get("opencode") or "")
            open_time_str = data.get("openTime") or data.get("open_time") or data.get("opentime") or data.get("time")

            if not issue_code or not nums:
                return

            try:
                n1, n2, n3 = [int(x) for x in nums.split(",")[:3]]
            except Exception:
                return

            if open_time_str:
                try:
                    open_time = datetime.strptime(open_time_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    open_time = datetime.fromisoformat(open_time_str.replace("Z","").replace("T"," "))
            else:
                open_time = datetime.now()

            row = await upsert_issue_from_result(session, lottery_code, issue_code, n1, n2, n3, open_time, json.dumps(data, ensure_ascii=False))
            item = {
                "lottery_code": row.lottery_code,
                "issue_code": row.issue_code,
                "n1": row.n1, "n2": row.n2, "n3": row.n3,
                "sum_value": row.sum_value,
                "bs": row.bs, "oe": row.oe, "extreme": row.extreme,
                "open_time": row.open_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            await set_redis_after_issue(lottery_code, item)

            lot = (await session.execute(select(Lottery).where(Lottery.code==lottery_code))).scalar_one()
            next_open = row.open_time + timedelta(seconds=lot.period_seconds or 210)
            close_time = next_open - timedelta(seconds=lot.lock_ahead_seconds or 3)
            now = datetime.now()
            allow_bet = now < close_time
            await set_current_issue_cache(lottery_code, str(int(issue_code)+1) if issue_code.isdigit() else issue_code, next_open, close_time, allow_bet)

        except Exception as e:
            print("[collector_job] error:", e)

async def refresh_current_issue_job():
    lottery_code = settings.LOTTERY_DEFAULT_CODE
    data = await r.hgetall(k_current_issue(lottery_code))
    if not data:
        return
    try:
        close_time = datetime.strptime(data.get("close_time"), "%Y-%m-%d %H:%M:%S")
        open_time = datetime.strptime(data.get("open_time"), "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        allow_bet = now < close_time
        await set_current_issue_cache(lottery_code, data.get("issue_code",""), open_time, close_time, allow_bet)
    except Exception:
        pass

def start_scheduler():
    scheduler.add_job(collector_job, "interval", seconds=settings.COLLECTOR_POLL_SECONDS, id="collector_jnd28", replace_existing=True)
    scheduler.add_job(refresh_current_issue_job, "interval", seconds=1, id="tick_current_issue", replace_existing=True)
    scheduler.start()

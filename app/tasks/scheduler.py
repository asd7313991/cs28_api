# app/tasks/scheduler.py
import asyncio
import json
import logging
from datetime import datetime, timedelta

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.config import settings
from app.db.redis import r
from app.db.session import AsyncSessionLocal
from app.models.lottery import Lottery
from app.services.issue_service import (
    upsert_issue_from_result,
    set_redis_after_issue,
    set_current_issue_cache,
)
from app.constants import k_current_issue
from app.tasks.settlement import settle_orders_job  # ← 新增：结算任务

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()  # 如果你有时区需求，可传 timezone="UTC"/"Asia/Shanghai"


async def fetch_jnd28_result():
    url = settings.COLLECTOR_JND28_URL
    ts = int(datetime.now().timestamp() * 1000)
    url = f"{url}{'&' if '?' in url else '?'}_={ts}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


async def collector_job():
    """
    拉取开奖结果 → 写库（期次/开奖结果）→ 写 Redis 历史缓存 → 计算下一期的 open/close/allow_bet → 写当前期缓存
    """
    async with AsyncSessionLocal() as session:
        lottery_code = settings.LOTTERY_DEFAULT_CODE
        try:
            data = await fetch_jnd28_result()

            # 兼容多种字段命名
            issue_code = str(
                data.get("issue")
                or data.get("issueCode")
                or data.get("expect")
                or ""
            )
            nums = str(
                data.get("code")
                or data.get("nums")
                or data.get("opencode")
                or ""
            )
            open_time_str = (
                    data.get("openTime")
                    or data.get("open_time")
                    or data.get("opentime")
                    or data.get("time")
            )

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
                    # 兼容 ISO 格式
                    open_time = datetime.fromisoformat(open_time_str.replace("Z", "").replace("T", " "))
            else:
                open_time = datetime.now()

            # 写库/更新该期
            row = await upsert_issue_from_result(
                session,
                lottery_code,
                issue_code,
                n1,
                n2,
                n3,
                open_time,
                json.dumps(data, ensure_ascii=False),
            )

            # 写 redis 历史
            item = {
                "lottery_code": row.lottery_code,
                "issue_code": row.issue_code,
                "n1": row.n1,
                "n2": row.n2,
                "n3": row.n3,
                "sum_value": row.sum_value,
                "bs": row.bs,
                "oe": row.oe,
                "extreme": row.extreme,
                "open_time": row.open_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            await set_redis_after_issue(lottery_code, item)

            # 计算下一期开奖/封盘时间并缓存“当前期”
            lot = (
                await session.execute(
                    select(Lottery).where(Lottery.code == lottery_code)
                )
            ).scalar_one()
            next_open = row.open_time + timedelta(seconds=lot.period_seconds or 210)
            close_time = next_open - timedelta(seconds=lot.lock_ahead_seconds or 3)
            now = datetime.now()
            allow_bet = now < close_time

            # 当前期号：如果是纯数字，+1；否则仍用当前字符串（外部也能覆盖）
            next_issue_str = (
                str(int(issue_code) + 1) if issue_code.isdigit() else issue_code
            )
            await set_current_issue_cache(
                lottery_code,
                next_issue_str,
                next_open,
                close_time,
                allow_bet,
            )

        except Exception as e:
            logger.exception("[collector_job] error: %s", e)


async def refresh_current_issue_job():
    """
    每秒刷新一次“当前期”缓存中的 allow_bet 状态（随时间流逝而变化）
    """
    lottery_code = settings.LOTTERY_DEFAULT_CODE
    data = await r.hgetall(k_current_issue(lottery_code))
    if not data:
        return
    try:
        close_time = datetime.strptime(data.get("close_time"), "%Y-%m-%d %H:%M:%S")
        open_time = datetime.strptime(data.get("open_time"), "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        allow_bet = now < close_time
        await set_current_issue_cache(
            lottery_code,
            data.get("issue_code", ""),
            open_time,
            close_time,
            allow_bet,
        )
    except Exception:
        # 容忍解析失败
        pass


def start_scheduler():
    """
    启动调度器：
      - 采集开奖结果
      - 刷新当前期（allow_bet）
      - ✅ 新增：开奖结算任务（扫描未结算订单并派彩）
    """
    # 采集（按你的配置频率）
    scheduler.add_job(
        collector_job,
        "interval",
        seconds=settings.COLLECTOR_POLL_SECONDS,
        id="collector_jnd28",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=10,
    )

    # 刷新当前期
    scheduler.add_job(
        refresh_current_issue_job,
        "interval",
        seconds=1,
        id="tick_current_issue",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=5,
    )

    # ✅ 新增：结算任务（每 2 秒跑一次；你也可以调到 1~5 秒）
    scheduler.add_job(
        settle_orders_job,
        "interval",
        seconds=2,
        id="settle_orders_job",
        replace_existing=True,
        coalesce=True,          # 合并堆积触发
        max_instances=1,        # 防并发重复派彩
        misfire_grace_time=10,  # 允许一定延迟
    )

    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")

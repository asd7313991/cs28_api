# app/tasks/settlement.py
from __future__ import annotations
import datetime as dt
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Tuple, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, Base

# 适配你的 orders 模型（文件名是 orders.py）
try:
    from app.models.orders import Orders, OrderItem
except ModuleNotFoundError:
    # 如仍叫 order.py，可用这个兜底
    from app.models.order import Orders, OrderItem

# user 表（只有 balance，用它派彩）
from app.models.user import User

logger = logging.getLogger(__name__)

# 订单状态
STATUS_SUBMITTED = 1   # 已提交
STATUS_CANCELLED = 2   # 已撤单
STATUS_PENDING   = 3   # 待结算（可选状态）
STATUS_SETTLED   = 4   # 已派彩（中奖）
STATUS_LOST      = 5   # 未中奖
STATUS_VOID      = 9   # 作废

BATCH_LIMIT = 200      # 每轮最多处理 N 笔，避免长事务/大锁


def q2(v: Decimal) -> Decimal:
    return Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ------------------------------
# 开奖结果获取（和值 0..27）
# ------------------------------
def _choose_open_model() -> tuple[type | None, str | None, str | None, Tuple[str, ...], Tuple[str, ...]]:
    """
    尝试在已注册的 ORM 模型里，找到“开奖号码”模型：
      - 必须有列：lottery_code + issue_code（或 issue/issue_no/expect）
      - 且至少满足：
          * 有 sum_value；或
          * 同时有 n1,n2,n3 / num1,num2,num3 / a,b,c；或
          * 有 code/nums/opencode（三球字符串）
    返回：(Model, lot_col_name, issue_col_name, sum_candidates, code_candidates)
    失败返回 (None, None, None, (), ()).
    """
    # 确保常见模块被 import（一些项目直到第一次用到才 import）
    for mod, name in [
        ("app.models.issue", "Issue"),
        ("app.models.issues", "Issue"),
        ("app.models.lottery_issue", "LotteryIssue"),
        ("app.models.open_record", "OpenRecord"),
        ("app.models.issue_record", "IssueRecord"),
        ("app.models.result", "OpenRecord"),
    ]:
        try:
            __import__(mod, fromlist=[name])
        except Exception:
            pass

    # 遍历 mapper，自动发现
    sum_fields = ("sum_value",)
    triple_sets = (("n1", "n2", "n3"), ("num1", "num2", "num3"), ("a", "b", "c"))
    code_fields = ("code", "codes", "nums", "opencode")
    issue_fields = ("issue_code", "issue", "issue_no", "expect")

    for m in Base.registry.mappers:
        cls = m.class_
        cols = cls.__dict__.keys()

        # 必须有 lot + issue
        lot_col = None
        if "lottery_code" in cols:
            lot_col = "lottery_code"
        elif "code" in cols:  # 某些项目用 code 存彩种
            lot_col = "code"

        issue_col = next((f for f in issue_fields if f in cols), None)
        if not lot_col or not issue_col:
            continue

        # 有 sum_value 或 有三球 或 有 "x,y,z"
        has_sum = any(f in cols for f in sum_fields)
        has_triple = any(all(x in cols for x in s3) for s3 in triple_sets)
        has_codestr = any(f in cols for f in code_fields)

        if has_sum or has_triple or has_codestr:
            return cls, lot_col, issue_col, sum_fields, code_fields

    return None, None, None, (), ()


async def get_open_sum(session: AsyncSession, lottery_code: str, issue_code: str | int) -> Optional[int]:
    """
    返回该期的和值 (0..27)。若未开奖返回 None。
    - 优先读 sum_value
    - 否则 n1+n2+n3（或 num1../a..）
    - 否则从 "x,y,z" 字符串解析
    """
    issue_code = str(issue_code)

    Model, lot_col, issue_col, sum_fields, code_fields = _choose_open_model()
    if Model is None:
        logger.error("未找到开奖模型：请确认你的开奖模型已 import，并包含 lottery_code + issue_code + (sum_value or n1..n3 或 code/nums)。")
        return None

    lot_attr = getattr(Model, lot_col)
    issue_attr = getattr(Model, issue_col)

    row = (
        await session.execute(
            select(Model).where(lot_attr == lottery_code, issue_attr == issue_code)
        )
    ).scalar_one_or_none()
    if not row:
        return None

    # 1) sum_value
    if hasattr(row, "sum_value"):
        sv = getattr(row, "sum_value")
        if sv is not None:
            try:
                return int(sv)
            except Exception:
                pass

    # 2) n1+n2+n3（或别名）
    for a, b, c in (("n1", "n2", "n3"), ("num1", "num2", "num3"), ("a", "b", "c")):
        if all(hasattr(row, x) for x in (a, b, c)):
            try:
                return int(getattr(row, a)) + int(getattr(row, b)) + int(getattr(row, c))
            except Exception:
                pass

    # 3) 从 "x,y,z"
    for fld in ("code", "codes", "nums", "opencode"):
        if hasattr(row, fld):
            s = str(getattr(row, fld) or "")
            try:
                parts = [int(x) for x in s.split(",")[:3]]
                if len(parts) == 3:
                    return sum(parts)
            except Exception:
                pass

    logger.error("开奖记录存在，但未找到可用的和值/号码字段，请检查你的开奖模型字段命名。")
    return None


# ------------------------------
# 玩法命中规则
# ------------------------------
def is_hit(selection: str, total_sum: int) -> bool:
    s = str(selection).strip()
    if s.isdigit():
        return int(s) == total_sum
    if s in ("大", "小", "单", "双", "极大", "极小"):
        if s == "大":
            return total_sum >= 14
        if s == "小":
            return total_sum <= 13
        if s == "单":
            return (total_sum % 2) == 1
        if s == "双":
            return (total_sum % 2) == 0
        if s == "极大":
            return total_sum >= 23
        if s == "极小":
            return total_sum <= 4
    return False


# ------------------------------
# 结算一笔订单（单事务）
# ------------------------------
# 原来签名是 -> bool，这里改成返回 dict | None
async def _settle_one_order(session: AsyncSession, order_id: int, sum_value: int):
    """
    结算一笔订单。返回结算详情 dict（用于日志），未处理则返回 None。
    调用方需保证传入 sum_value（该期已开奖）。
    """
    # 锁订单
    order = await session.get(Orders, order_id, with_for_update=True)
    if not order:
        return None

    # 跳过不可结算状态
    if int(order.status) not in (STATUS_SUBMITTED, STATUS_PENDING):
        return None

    # 锁用户
    user = await session.get(User, order.user_id, with_for_update=True)
    if not user:
        order.status = STATUS_VOID
        await session.flush()
        stake_total = Decimal(str(getattr(order, "total_amount", 0) or 0))
        return {
            "order_id": order.id,
            "lottery_code": getattr(order, "lottery_code", ""),
            "issue_code": getattr(order, "issue_code", ""),
            "user_id": None,
            "user_name": f"UID{order.user_id}",
            "stake": float(q2(stake_total)),
            "win": 0.0,
            "status": int(order.status),
        }

    # 取子单
    rs_items = await session.execute(
        select(OrderItem).where(OrderItem.order_id == order.id)
    )
    items = rs_items.scalars().all()
    if not items:
        order.status = STATUS_VOID
        await session.flush()
        stake_total = Decimal(str(getattr(order, "total_amount", 0) or 0))
        return {
            "order_id": order.id,
            "lottery_code": getattr(order, "lottery_code", ""),
            "issue_code": getattr(order, "issue_code", ""),
            "user_id": user.id,
            "user_name": user.nickname or user.username or f"UID{user.id}",
            "stake": float(q2(stake_total)),
            "win": 0.0,
            "status": int(order.status),
        }

    total_win = Decimal("0")
    now = dt.datetime.utcnow()

    for it in items:
        # 幂等：已结算的跳过，同时累计 win_amount
        if int(getattr(it, "result_status", 0)) in (1, 2, 3):
            try:
                total_win += Decimal(str(getattr(it, "win_amount") or 0))
            except Exception:
                pass
            continue

        sel = str(it.selection)
        stake = Decimal(str(it.stake_amount))
        odds = Decimal(str(it.odds))

        if is_hit(sel, sum_value):
            win_amt = q2(stake * odds)
            it.result_status = 1
            it.win_amount = float(win_amt)
            total_win += win_amt
        else:
            it.result_status = 2
            it.win_amount = float(Decimal("0.00"))

        it.settled_at = now

    # 订单状态
    if total_win > 0:
        order.status = STATUS_SETTLED
    else:
        order.status = STATUS_LOST
    order.win_amount = float(q2(total_win))

    # 给用户加钱
    if total_win > 0:
        bal = Decimal(str(user.balance or 0))
        user.balance = float(q2(bal + total_win))

    await session.flush()

    # 返回结算摘要（供外层 commit 成功后打印日志）
    stake_total = Decimal(str(getattr(order, "total_amount", 0) or 0))
    return {
        "order_id": order.id,
        "lottery_code": getattr(order, "lottery_code", ""),
        "issue_code": getattr(order, "issue_code", ""),
        "user_id": user.id,
        "user_name": user.nickname or user.username or f"UID{user.id}",
        "stake": float(q2(stake_total)),
        "win": float(q2(total_win)),
        "status": int(order.status),
    }


# ------------------------------
# 一轮扫描 + 批量结算
# ------------------------------
async def settle_orders_once():
    """
    扫描未结算订单（status in 1/3），对已开奖的期次进行结算。
    读与写分离：读取用一个 session；结算每单用一个新的 session（事务独立，避免嵌套）。
    """
    # 先用一个 session 拉取候选订单，并查每期和值
    async with AsyncSessionLocal() as session:
        rs = await session.execute(
            select(Orders.id, Orders.lottery_code, Orders.issue_code)
            .where(Orders.status.in_([STATUS_SUBMITTED, STATUS_PENDING]))
            .order_by(Orders.id.asc())
            .limit(BATCH_LIMIT)
        )
        rows = rs.all()
        if not rows:
            return

        # 拿到所有 (lottery_code, issue_code) 去重
        pairs: Dict[Tuple[str, str], Optional[int]] = {}
        for _, code, issue in rows:
            pairs[(code, issue)] = None

        # 统一查询每期的和值（在同一只读 session 里）
        for (code, issue) in list(pairs.keys()):
            pairs[(code, issue)] = await get_open_sum(session, code, issue)

    # 对每个订单，用独立的会话做“锁订单/锁用户/更新子单/派彩”
    for oid, code, issue in rows:
        sum_val = pairs.get((code, issue))
        if sum_val is None:
            # 该期还没出结果，跳过
            continue

        details = None
        try:
            async with AsyncSessionLocal() as s:
                async with s.begin():  # 一单一事务
                    details = await _settle_one_order(s, oid, int(sum_val))
            # 只有事务成功提交才会走到这里；打印成功日志
            if details:
                logger.warning(
                    "第%s期：%s，投注 %.2f，赢得 %.2f（订单ID=%s）",
                    details.get("issue_code", ""),
                    details.get("user_name", ""),
                    details.get("stake", 0.0),
                    details.get("win", 0.0),
                    details.get("order_id", ""),
                )
        except Exception as e:
            logger.exception("结算订单异常 order_id=%s: %s", oid, e)
            # 不中断后续订单
            continue

# ------------------------------
# 调度器入口（供 scheduler 调用）
# ------------------------------
async def settle_orders_job():
    try:
        await settle_orders_once()
    except Exception as e:
        logger.exception("settle_orders_job failed: %s", e)

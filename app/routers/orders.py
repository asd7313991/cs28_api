from __future__ import annotations
from typing import Dict, List
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_session
from app.core.auth import get_current_user
from app.models.user import User
from app.models.orders import Orders, OrderItem
from app.models.play_type import PlayType
from app.schemas.orders import (
    OrderPlaceIn, OrderPlaceOut, OrderItemIn,
    OrderOut, OrderItemOut, OrderCancelIn, OrderCancelOut
)

router = APIRouter(prefix="/api/orders", tags=["orders"])

# 输入别名（把 DA/X/D/S/JDA/JX 映射到 DB 的中文 name）
ALIAS_TO_NAME = {
    "DA": "大", "X": "小", "D": "单", "S": "双",
    "JDA": "极大", "JX": "极小",
}

MAX_ITEMS = 10
STATUS_SUBMITTED = 1
STATUS_CANCELLED = 2

def q2(v: Decimal) -> Decimal:
    return Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def q4(v: Decimal) -> Decimal:
    return Decimal(v).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

async def load_enabled_play_map(session: AsyncSession, lottery_code: str) -> Dict[str, dict]:
    """
    读取启用玩法:
      返回 { name(str): { "code": int, "odds": Decimal } }
    """
    rs = await session.execute(
        select(PlayType.name, PlayType.code, PlayType.odds).where(
            PlayType.lottery_code == lottery_code,
            PlayType.status == 1,
            )
    )
    out: Dict[str, dict] = {}
    for name, code, odds in rs.all():
        out[str(name)] = {"code": int(code), "odds": Decimal(str(odds))}
    return out

def normalize_play_to_name(play: str | int, enabled_names: set[str]) -> str:
    """把用户输入统一成 DB 的中文 name；仅允许 DB 启用的项"""
    if play is None:
        raise HTTPException(400, "玩法不能为空")
    p = str(play).strip()
    if not p:
        raise HTTPException(400, "玩法不能为空")
    up = p.upper()

    # 0..27 和值
    if up.isdigit():
        n = int(up)
        if 0 <= n <= 27:
            name = str(n)
            if name in enabled_names:
                return name
            raise HTTPException(400, f"玩法未配置或停用: {name}")
        raise HTTPException(400, f"非法和值: {p}")

    # 英文别名
    if up in ALIAS_TO_NAME:
        name = ALIAS_TO_NAME[up]
        if name in enabled_names:
            return name
        raise HTTPException(400, f"玩法未配置或停用: {name}")

    # 直接中文名
    if p in enabled_names:
        return p

    raise HTTPException(400, f"未知玩法: {p}")

def get_client_ip(req: Request) -> str:
    xff = req.headers.get("X-Forwarded-For") or req.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return req.client.host if req.client else ""

@router.post("/place", response_model=OrderPlaceOut)
async def place_order(
        payload: OrderPlaceIn,
        request: Request,
        session: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_user),
):
    """
    下单：
      - 赔率以 play_type 为准（不信任前端赔率）
      - 扣减 user.balance
      - 写入 Orders / OrderItem（play_code, selection, odds, stake_amount）
    """
    # 基础校验
    if not payload.items:
        raise HTTPException(400, "下注明细不能为空")
    if len(payload.items) > MAX_ITEMS:
        raise HTTPException(400, f"投注种类过多（最多{MAX_ITEMS}条）")

    try:
        # ① 幂等：如果带了 idempotency_key，判断是否已下过单
        if payload.idempotency_key:
            rs = await session.execute(
                select(Orders.id).where(
                    Orders.user_id == current_user.id,
                    Orders.idempotency_key == payload.idempotency_key,
                    )
            )
            existed = rs.scalar_one_or_none()
            if existed:
                # 已存在则直接返回（不重复扣款）
                return OrderPlaceOut(order_id=existed, total_amount=0.0, status=0)

        # ② 玩法/赔率（以 DB 为准）
        play_map = await load_enabled_play_map(session, payload.code)
        if not play_map:
            raise HTTPException(400, "该彩种暂无可用玩法")
        enabled_names = set(play_map.keys())

        # ③ 归一化 & 汇总金额
        normalized: List[OrderItemIn] = []
        total = Decimal("0")
        for it in payload.items:
            name = normalize_play_to_name(it.play, enabled_names)
            amt = Decimal(str(it.amount))
            if amt <= 0:
                raise HTTPException(400, "金额非法")
            normalized.append(OrderItemIn(play=name, amount=float(q2(amt))))
            total += amt

        # ④ 扣款（行级锁）
        u = await session.get(User, current_user.id, with_for_update=True)
        bal = Decimal(str(u.balance or 0))
        if bal < total:
            raise HTTPException(400, "余额不足")
        u.balance = float(q2(bal - total))

        # ⑤ 建单
        order = Orders(
            user_id=current_user.id,
            lottery_code=payload.code,
            issue_code=str(payload.issue),
            total_amount=float(q2(total)),
            total_odds=None,  # 可选：如需汇总赔率可自行定义
            status=STATUS_SUBMITTED,
            ip=get_client_ip(request),
            channel=payload.channel or "web",
            idempotency_key=payload.idempotency_key,
        )
        session.add(order)
        await session.flush()  # 得到 order.id

        # ⑥ 子单
        for it in normalized:
            info = play_map[it.play]   # {'code': int, 'odds': Decimal}
            session.add(OrderItem(
                order_id=order.id,
                play_code=info["code"],
                selection=it.play,                                 # 存中文名/和值
                odds=float(q4(info["odds"])),                      # Numeric(10,4)
                stake_amount=float(q2(Decimal(str(it.amount)))),   # Numeric(16,2)
            ))

        await session.commit()
        return OrderPlaceOut(order_id=order.id, total_amount=float(q2(total)), status=0)

    except HTTPException:
        await session.rollback(); raise
    except Exception:
        await session.rollback(); raise

@router.get("/history", response_model=List[OrderOut])
async def order_history(
        limit: int = 20,
        session: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_user),
):
    # 查订单
    rs = await session.execute(
        select(Orders).where(Orders.user_id == current_user.id)
        .order_by(Orders.id.desc()).limit(limit)
    )
    orders = rs.scalars().all()
    if not orders:
        return []

    order_ids = [o.id for o in orders]

    # 查子单
    rs2 = await session.execute(
        select(OrderItem).where(OrderItem.order_id.in_(order_ids))
    )
    items = rs2.scalars().all()
    by_order: Dict[int, List[OrderItemOut]] = {}
    for it in items:
        by_order.setdefault(it.order_id, []).append(
            OrderItemOut(
                id=it.id,
                play=str(it.selection),
                amount=float(it.stake_amount),
                odds=float(it.odds),
            )
        )

    out: List[OrderOut] = []
    for o in orders:
        out.append(OrderOut(
            id=o.id,
            lottery_code=o.lottery_code,
            issue_code=o.issue_code,
            total_amount=float(o.total_amount),
            status=int(o.status),
            items=by_order.get(o.id, []),
        ))
    return out

@router.post("/cancel", response_model=OrderCancelOut)
async def cancel_order(
        payload: OrderCancelIn,
        session: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_user),
):
    """仅允许 status=1(已提交) 的订单取消并原路退款。"""
    try:
        # 锁用户
        u = await session.get(User, current_user.id, with_for_update=True)
        if u is None:
            raise HTTPException(404, "用户不存在")

        # 找订单
        rs = await session.execute(
            select(Orders).where(Orders.id == payload.order_id, Orders.user_id == u.id)
        )
        order = rs.scalar_one_or_none()
        if order is None:
            raise HTTPException(404, "订单不存在")
        if int(order.status) != STATUS_SUBMITTED:
            raise HTTPException(400, "仅已提交订单可取消")

        # 退款 + 状态更新
        u.balance = float(q2(Decimal(str(u.balance or 0)) + Decimal(str(order.total_amount))))
        order.status = STATUS_CANCELLED

        await session.commit()
        return OrderCancelOut(order_id=order.id, status=1, balance=u.balance)

    except HTTPException:
        await session.rollback(); raise
    except Exception:
        await session.rollback(); raise

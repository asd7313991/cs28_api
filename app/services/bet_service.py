
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.order import Orders, OrderItem
from app.models.wallet import WalletAccount, WalletLedger
from app.models.issue import Issue
from app.models.lottery import Lottery
from app.schemas.orders import BetIn
from fastapi import HTTPException
from datetime import datetime
from sqlalchemy import func

BIZ_BET = 20

async def ensure_wallet(session: AsyncSession, user_id: int) -> WalletAccount:
    acc = await session.scalar(select(WalletAccount).where(WalletAccount.user_id == user_id).with_for_update())
    if not acc:
        acc = WalletAccount(user_id=user_id, available=0, frozen=0, version=0)
        session.add(acc)
        await session.flush()
    return acc

async def place_bet(session: AsyncSession, user_id: int, bet: BetIn, ip: str | None = None, channel: str | None = None) -> Orders:
    # 校验期号是否可投注：必须未开奖且未过封盘时间
    issue = await session.scalar(select(Issue).where(Issue.lottery_code==bet.lottery_code, Issue.issue_code==bet.issue_code))
    if not issue:
        raise HTTPException(status_code=400, detail="期号不存在")
    # close_time 已在 issue 表，要求当前时间 < close_time
    now = func.now()
    # 无法在 SQL 中直接比较 func.now() 与实体，用应用时钟比较更直观，假设 DB 与服务同 TZ
    # 这里我们读取 close_time 值再比较
    # 注意：建议统一以数据库时间为准，可在后续改造。
    from datetime import datetime as pydt
    if issue.close_time and pydt.utcnow() >= issue.close_time.replace(tzinfo=None):
        raise HTTPException(status_code=400, detail="已封盘，禁止下注")

    total_amount = sum(i.stake_amount for i in bet.items)

    # 锁钱包
    acc = await ensure_wallet(session, user_id)
    if float(acc.available) < float(total_amount):
        raise HTTPException(status_code=400, detail="余额不足")

    # 扣可用、加冻结
    acc.available = float(acc.available) - float(total_amount)
    acc.frozen = float(acc.frozen) + float(total_amount)
    acc.version = int(acc.version) + 1

    # 生成订单与明细
    order = Orders(
        user_id=user_id,
        lottery_code=bet.lottery_code,
        issue_code=bet.issue_code,
        total_amount=total_amount,
        status=1,  # 已提交
        ip=ip,
        channel=channel or "h5"
    )
    session.add(order)
    await session.flush()

    items = []
    for it in bet.items:
        item = OrderItem(
            order_id=order.id,
            play_code=it.play_code,
            selection=it.selection,
            odds=it.odds,
            stake_amount=it.stake_amount,
            result_status=0
        )
        items.append(item)
        session.add(item)

    # 写资金流水
    ledger = WalletLedger(
        user_id=user_id,
        direction=2,  # 出
        amount=total_amount,
        balance_after=acc.available,
        biz_type=BIZ_BET,
        ref_table="orders",
        ref_id=order.id,
        remark="下注冻结"
    )
    session.add(ledger)

    # 订单状态切换为待结算（可由下单直接标记为3，也可在开奖时批量切）
    order.status = 3  # 待结算

    return order

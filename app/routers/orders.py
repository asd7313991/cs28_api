
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_session
from app.core.auth import get_current_user
from app.schemas.orders import BetIn, BetOut
from app.services.bet_service import place_bet
from app.models.issue import Issue

router = APIRouter(prefix="/api/orders", tags=["orders"])

@router.post("/bet", response_model=BetOut)
async def bet(
    data: BetIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user = Depends(get_current_user),
):
    # 事务内执行下单
    async with session.begin():
        order = await place_bet(session, current_user.id, data, ip=request.client.host if request.client else None, channel="h5")
    return BetOut(order_id=order.id, total_amount=float(order.total_amount), status=order.status)

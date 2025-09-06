
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Numeric, DateTime, BigInteger, SmallInteger, func
from app.db.session import Base

class Orders(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    lottery_code: Mapped[str] = mapped_column(String(32), nullable=False)
    issue_code: Mapped[str] = mapped_column(String(32), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(16,2), nullable=False)
    total_odds: Mapped[float | None] = mapped_column(Numeric(10,4))
    status: Mapped[int] = mapped_column(SmallInteger, default=1)  # 1已提交 2已撤单 3待结算 4已派彩 5未中奖 9作废
    win_amount: Mapped[float] = mapped_column(Numeric(16,2), default=0)
    ip: Mapped[str | None] = mapped_column(String(64))
    channel: Mapped[str | None] = mapped_column(String(32))
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class OrderItem(Base):
    __tablename__ = "order_item"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    play_code: Mapped[int] = mapped_column(Integer, nullable=False)
    selection: Mapped[str] = mapped_column(String(32), nullable=False)
    odds: Mapped[float] = mapped_column(Numeric(10,4), nullable=False)
    stake_amount: Mapped[float] = mapped_column(Numeric(16,2), nullable=False)
    result_status: Mapped[int] = mapped_column(SmallInteger, default=0)  # 0未结算 1赢 2输 3和/取消
    win_amount: Mapped[float] = mapped_column(Numeric(16,2), default=0)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime)

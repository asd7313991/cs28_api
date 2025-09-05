from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Numeric, DateTime, BigInteger, Boolean, func
from app.db.session import Base

class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(64))
    avatar_url: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[int] = mapped_column(Integer, default=1)
    is_robot: Mapped[bool] = mapped_column(Boolean, default=False)

    balance: Mapped[float] = mapped_column(Numeric(16, 2), default=0)
    frozen_balance: Mapped[float] = mapped_column(Numeric(16, 2), default=0)
    total_bet_amount: Mapped[float] = mapped_column(Numeric(16, 2), default=0)
    total_payout: Mapped[float] = mapped_column(Numeric(16, 2), default=0)
    total_profit: Mapped[float] = mapped_column(Numeric(16, 2), default=0)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)

    last_login_ip: Mapped[str | None] = mapped_column(String(64))
    last_login_time: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

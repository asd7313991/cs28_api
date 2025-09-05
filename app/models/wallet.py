
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Numeric, DateTime, BigInteger, SmallInteger, func
from app.db.session import Base

class WalletAccount(Base):
    __tablename__ = "wallet_account"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    available: Mapped[float] = mapped_column(Numeric(16,2), default=0)
    frozen: Mapped[float] = mapped_column(Numeric(16,2), default=0)
    version: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class WalletLedger(Base):
    __tablename__ = "wallet_ledger"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    direction: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 1入 2出
    amount: Mapped[float] = mapped_column(Numeric(16,2), nullable=False)
    balance_after: Mapped[float] = mapped_column(Numeric(16,2), nullable=False)
    biz_type: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 20下注 21撤单返还 30派彩
    ref_table: Mapped[str | None] = mapped_column(String(32))
    ref_id: Mapped[int | None] = mapped_column(BigInteger)
    remark: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


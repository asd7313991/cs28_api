from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, BigInteger, SmallInteger, func
from app.db.session import Base

class Lottery(Base):
    __tablename__ = "lottery"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    period_seconds: Mapped[int] = mapped_column(Integer, default=210)
    lock_ahead_seconds: Mapped[int] = mapped_column(Integer, default=3)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    tz: Mapped[str] = mapped_column(String(32), default="Asia/Shanghai")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

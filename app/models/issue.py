from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, BigInteger, SmallInteger, func
from sqlalchemy.dialects.mysql import TINYINT
from app.db.session import Base

class Issue(Base):
    __tablename__ = "issue"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    lottery_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    issue_code: Mapped[str] = mapped_column(String(32), nullable=False)

    open_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    close_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)

    n1: Mapped[int | None] = mapped_column(TINYINT(unsigned=True))
    n2: Mapped[int | None] = mapped_column(TINYINT(unsigned=True))
    n3: Mapped[int | None] = mapped_column(TINYINT(unsigned=True))
    sum_value: Mapped[int | None] = mapped_column(TINYINT(unsigned=True))
    bs: Mapped[int | None] = mapped_column(TINYINT(unsigned=True))
    oe: Mapped[int | None] = mapped_column(TINYINT(unsigned=True))
    extreme: Mapped[int | None] = mapped_column(TINYINT(unsigned=True))

    raw_json: Mapped[str | None] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

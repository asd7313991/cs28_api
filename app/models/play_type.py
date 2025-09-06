# app/models/play_type.py
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Numeric
from app.db.session import Base

class PlayType(Base):
    __tablename__ = "play_type"
    id: Mapped[int] = mapped_column(primary_key=True)
    lottery_code: Mapped[str] = mapped_column(String(32), index=True)
    code: Mapped[int] = mapped_column(Integer)            # 玩法编码（管理端可用）
    name: Mapped[str] = mapped_column(String(32), index=True)  # '大' | '小' | '0'..'27' ...
    odds: Mapped[float] = mapped_column(Numeric(10,4))
    status: Mapped[int] = mapped_column(Integer, default=1)     # 1=启用

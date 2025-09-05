
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.models.user import User

security = HTTPBearer(auto_error=False)

async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未授权")
    token = creds.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"], options={"require": ["exp", "iat", "sub"]})
        sub = payload.get("sub")
        if not sub:
            raise ValueError("no sub")
        uid = int(sub)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌") from e

    u = await session.scalar(select(User).where(User.id == uid))
    if not u or u.status != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return u

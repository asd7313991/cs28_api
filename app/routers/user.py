
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.user import User
from app.schemas.user import RegisterIn, LoginIn, TokenOut, UserOut
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/user", tags=["user"])

@router.post("/register", response_model=UserOut)
async def register(data: RegisterIn, session: AsyncSession = Depends(get_session)):
    # 检查重名
    exists = await session.scalar(select(User).where(User.username == data.username))
    if exists:
        raise HTTPException(status_code=400, detail="用户名已存在")

    u = User(
        username=data.username,
        password_hash=hash_password(data.password),
        nickname=data.nickname or data.username,
        status=1,
        is_robot=False,
    )
    session.add(u)
    await session.flush()  # 获取 id
    await session.commit()
    return UserOut(
        id=u.id,
        username=u.username,
        nickname=u.nickname,
        avatar_url=u.avatar_url,
        status=u.status,
    )

@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, session: AsyncSession = Depends(get_session)):
    u = await session.scalar(select(User).where(User.username == data.username))
    if not u:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not verify_password(data.password, u.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if u.status != 1:
        raise HTTPException(status_code=403, detail="用户已禁用")

    token = create_access_token(subject=u.id)
    return TokenOut(access_token=token)

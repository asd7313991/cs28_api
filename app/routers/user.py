from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.user import User
from app.schemas.user import RegisterIn, LoginIn, TokenOut, UserOut
from app.core.security import hash_password, verify_password, create_access_token
from app.core.auth import get_current_user


router = APIRouter(prefix="/api/user", tags=["user"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(data: RegisterIn, session: AsyncSession = Depends(get_session)):
    # 检查用户名是否存在
    exists = await session.scalar(select(User).where(User.username == data.username))
    if exists:
        raise HTTPException(status_code=400, detail="用户名已存在")

    u = User(
        username=data.username,
        password_hash=hash_password(data.password),
        nickname=data.nickname or data.username,
        status=1,
        is_robot=False,
        balance=0,  # 注册时初始化余额
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)

    return UserOut.model_validate(u)


@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, session: AsyncSession = Depends(get_session)):
    u = await session.scalar(select(User).where(User.username == data.username))
    if not u or not verify_password(data.password, u.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if u.status != 1:
        raise HTTPException(status_code=403, detail="用户已禁用")

    token = create_access_token(subject=str(u.id))
    return TokenOut(access_token=token)


@router.get("/profile", response_model=UserOut)
async def profile(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)

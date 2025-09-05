
from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
import jwt

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(raw: str) -> str:
    # 盐可以在 .env 里配置，默认 change_me
    salted = f"{raw}:{settings.PASSWORD_SALT}"
    return pwd_context.hash(salted)

def verify_password(raw: str, hashed: str) -> bool:
    salted = f"{raw}:{settings.PASSWORD_SALT}"
    return pwd_context.verify(salted, hashed)

def create_access_token(subject: str | int, expires_minutes: Optional[int] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes or settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(subject),
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "iss": settings.APP_NAME,
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return token

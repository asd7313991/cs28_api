
from pydantic import BaseModel, Field,ConfigDict

class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=64)
    nickname: str | None = None

class LoginIn(BaseModel):
    username: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    username: str
    nickname: str
    avatar_url: str | None = None
    status: int
    balance: float = 0   # 新增：余额

    model_config = ConfigDict(from_attributes=True)

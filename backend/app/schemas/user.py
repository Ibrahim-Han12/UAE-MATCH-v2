from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str

    # 简单校验：至少要提供 email 或 phone 之一
    def validate_at_least_one_contact(self) -> None:
        if not self.email and not self.phone:
            raise ValueError("必须提供 email 或 phone 至少一个")


class UserRead(UserBase):
    id: int
    is_active: bool
    status: str
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2 用这个代替 orm_mode


class UserLogin(BaseModel):
    username: str  # 可以是 email 或 phone
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

from typing import Optional, Dict, Any

from pydantic import BaseModel


class UserProfileBase(BaseModel):
    display_name: Optional[str] = None
    gender: Optional[str] = None           # male / female / other
    birth_year: Optional[int] = None
    height_cm: Optional[int] = None

    nationality: Optional[str] = None
    current_country: Optional[str] = None
    current_city: Optional[str] = None

    occupation: Optional[str] = None
    company: Optional[str] = None
    education_level: Optional[str] = None

    bio: Optional[str] = None
    is_public: Optional[bool] = True
    extended_info: Optional[Dict[str, Any]] = None  # 扩展信息（JSON格式）


class UserProfileUpdate(UserProfileBase):
    """更新 / 创建用（全部都是可选，方便局部更新）"""
    pass


class UserProfileRead(UserProfileBase):
    id: int

    class Config:
        from_attributes = True

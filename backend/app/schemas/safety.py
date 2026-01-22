from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.profile import UserProfileRead


class BlockUserRequest(BaseModel):
    target_user_id: int
    reason: Optional[str] = None


class BlockedUserItem(BaseModel):
    blocked_user_id: int
    reason: Optional[str] = None
    created_at: datetime
    profile: Optional[UserProfileRead] = None

    class Config:
        from_attributes = True


class ReportRequest(BaseModel):
    reported_user_id: int
    reported_message_id: Optional[int] = None
    category: str
    description: Optional[str] = None


class ReportResponse(BaseModel):
    id: int
    status: str

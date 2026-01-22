from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.profile import UserProfileRead


class ChatMessageCreate(BaseModel):
    match_pair_id: int
    content: str


class ChatMessageSend(BaseModel):
    """发送消息时只需要 content"""
    content: str


class ChatMessageRead(BaseModel):
    id: int
    match_pair_id: int
    sender_user_id: int
    content: str
    is_read: bool
    created_at: datetime
    # 前端需要的字段，用于判断是否是自己发的
    is_me: Optional[bool] = None
    from_me: Optional[bool] = None

    class Config:
        from_attributes = True


class ConversationSummary(BaseModel):
    match_pair_id: int
    other_user_id: int
    other_profile: UserProfileRead
    # 为了兼容前端，同时提供扁平化的字段
    other_nickname: Optional[str] = None
    other_age: Optional[int] = None
    other_city: Optional[str] = None
    other_nationality: Optional[str] = None
    last_message_preview: Optional[str] = None
    last_message_time: Optional[datetime] = None
    # 前端期望的字段名
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: int
    # 拉黑状态
    is_blocked_by_me: bool = False
    is_blocked_by_other: bool = False
    status: Optional[str] = None

    class Config:
        from_attributes = True

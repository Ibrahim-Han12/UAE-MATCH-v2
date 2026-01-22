from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.sql import func

from app.db.session import Base


class ChatMessage(Base):
    """
    配对双方在 MatchPair 内的聊天消息。
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)

    match_pair_id = Column(Integer, ForeignKey("match_pairs.id"), index=True, nullable=False)
    sender_user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

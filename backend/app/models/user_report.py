from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base


class UserReport(Base):
    """
    举报记录：
    - 可以只举报用户（reported_user_id）
    - 也可以附带某条消息（reported_message_id）
    """
    __tablename__ = "user_reports"

    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reported_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reported_message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=True, index=True)

    category = Column(String(50), nullable=False)   # harassment / scam / fake_profile / spam / other
    description = Column(Text, nullable=True)

    status = Column(String(20), default="open", nullable=False)  # open / reviewing / closed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

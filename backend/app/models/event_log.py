from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base


class EventLog(Base):
    """
    用户行为日志：
    - 比如登录、注册、like、发消息、拉黑、举报等
    - meta 字段存 JSON 字符串（数据库列名仍然是 metadata）
    """
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    event_type = Column(String(50), index=True, nullable=False)

    target_user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    match_pair_id = Column(Integer, ForeignKey("match_pairs.id"), index=True, nullable=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id"), index=True, nullable=True)
    report_id = Column(Integer, ForeignKey("user_reports.id"), index=True, nullable=True)

    # 这里重点：Python 属性叫 meta，数据库列名叫 "metadata"
    meta = Column("metadata", Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)

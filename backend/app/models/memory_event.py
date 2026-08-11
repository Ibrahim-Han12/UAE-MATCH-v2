from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, JSON, Index
from sqlalchemy.sql import func
from app.db.session import Base


class MemoryEvent(Base):
    """
    事件层 · 婚恋旅程时间线（BR-202 三层记忆之一；PRD 5.3.1 事件层）。
    每次推荐/反馈、互聊摘要、约会记录与复盘等按时间顺序追加。
    """
    __tablename__ = "memory_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    # 事件类型：recommendation / feedback / chat_summary / date / date_review / ...
    event_type = Column(String(50), nullable=False)

    # 事件负载（结构随类型而异）——Postgres 上映射为 JSONB
    payload = Column(JSON, nullable=True)

    occurred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 来源：system（系统事件自动写）/ conversation（对话提取）
    source = Column(String(20), nullable=False, default="system")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_memory_events_user_time", "user_id", "occurred_at"),
    )

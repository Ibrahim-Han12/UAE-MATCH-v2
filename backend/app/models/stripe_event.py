from sqlalchemy import Column, DateTime, String, Integer
from sqlalchemy.sql import func
from app.db.session import Base


class StripeEvent(Base):
    """
    Webhook 事件去重表（hld-m2-design.md §9.1 铁律：Webhook 按 event id 幂等）。
    收到重复投递的同一事件时直接跳过，防止重复开通/重复降级。
    """
    __tablename__ = "stripe_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(100), unique=True, index=True, nullable=False)
    event_type = Column(String(60), nullable=False)
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

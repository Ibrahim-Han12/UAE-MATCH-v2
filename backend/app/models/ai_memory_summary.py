from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, String, UniqueConstraint
from sqlalchemy.sql import func
from app.db.session import Base


class AIMemorySummary(Base):
    """
    AI红娘的记忆摘要（VIP用户专用）
    - short_term: 短期记忆（最近对话摘要）
    - mid_term: 中期记忆（最近30-90天关键信息）
    - long_term: 长期记忆（用户核心特征和偏好）
    """
    __tablename__ = "ai_memory_summary"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    
    # 记忆类型：short_term/mid_term/long_term
    summary_type = Column(String(20), nullable=False)
    
    # 记忆摘要内容（JSON格式）
    content = Column(Text, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    # 确保每个用户每种记忆类型只有一条记录
    __table_args__ = (
        UniqueConstraint("user_id", "summary_type", name="uq_user_memory_type"),
    )
















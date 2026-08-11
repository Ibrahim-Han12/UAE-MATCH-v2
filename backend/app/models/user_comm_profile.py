from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.sql import func
from app.db.session import Base


class UserCommProfile(Base):
    """
    情感层 · 沟通偏好与情绪模式（BR-202 三层记忆之一；PRD 5.3.1 情感层 + Schema G 元数据）。
    结构化摘要部分；语义化的情感/叙事记忆走 memory_vectors(namespace=emotion/narrative)。
    """
    __tablename__ = "user_comm_profile"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True, nullable=False)

    avoid_topics = Column(JSON, nullable=True)      # 回避话题清单（回避本身即画像信息）
    excite_topics = Column(JSON, nullable=True)     # 兴奋话题清单
    answer_style = Column(String(100), nullable=True)  # 回答风格特征
    emotion_pattern = Column(Text, nullable=True)   # 情绪模式（如"受挫后偏好先共情后建议"）

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

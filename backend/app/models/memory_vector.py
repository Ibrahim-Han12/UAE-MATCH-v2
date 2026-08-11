from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON, Index
from sqlalchemy.sql import func
from app.db.session import Base


class MemoryVector(Base):
    """
    向量记忆库（BR-202 双轨之一；D7=同库不同 namespace）。
    画像向量与情感/叙事记忆向量共表，用 namespace 区分：
      profile   —— 价值观/画像语义向量
      emotion   —— 情感记忆
      narrative —— 原话叙事（PRD Schema F3，仅入向量、不进结构化字段）
    D2=应用层余弦：向量以 JSON 列存，检索时载入内存算 Top-K（<数千用户足够，不上 pgvector）。
    """
    __tablename__ = "memory_vectors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    namespace = Column(String(20), nullable=False)   # profile / emotion / narrative
    vector = Column(JSON, nullable=False)            # list[float]
    dimension = Column(Integer, nullable=False, default=1536)
    source_text = Column(Text, nullable=True)        # 生成该向量的原文

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_memory_vectors_user_ns", "user_id", "namespace"),
    )

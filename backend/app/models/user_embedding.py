"""
用户向量嵌入模型
存储用户的向量化资料，用于相似度匹配
"""
from sqlalchemy import Column, Integer, ForeignKey, Text, DateTime, Index
from sqlalchemy.sql import func
from app.db.session import Base


class UserEmbedding(Base):
    __tablename__ = "user_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True, nullable=False)
    
    # 向量数据（PostgreSQL pgvector 类型，在SQLite中存储为JSON）
    # 注意：SQLite不支持pgvector，需要切换到PostgreSQL
    embedding_vector = Column(Text, nullable=False)  # JSON格式存储向量，或使用pgvector类型
    
    # 用于向量化的原始文本（用于调试和重新生成）
    source_text = Column(Text, nullable=True)  # 拼接后的完整文本
    
    # 向量维度（text-embedding-3-small 是 1536 维）
    dimension = Column(Integer, default=1536, nullable=False)
    
    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    # 索引：在PostgreSQL中使用HNSW索引
    # CREATE INDEX ON user_embeddings USING hnsw (embedding_vector vector_cosine_ops);
    
    __table_args__ = (
        Index('idx_user_embedding_user_id', 'user_id'),
    )













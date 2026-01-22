"""
用户AI长期记忆模型
存储滚动摘要，避免存储全量聊天记录
"""
from sqlalchemy import Column, Integer, ForeignKey, Text, DateTime
from sqlalchemy.sql import func
from app.db.session import Base


class UserAIMemory(Base):
    __tablename__ = "user_ai_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True, nullable=False)
    
    # 滚动摘要（500-800 tokens，压缩后的用户档案）
    summary_text = Column(Text, nullable=False)
    
    # 摘要的token数量（用于监控）
    token_count = Column(Integer, default=0, nullable=False)
    
    # 最后更新时间
    last_updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)













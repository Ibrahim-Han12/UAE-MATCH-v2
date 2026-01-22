from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, String, JSON
from sqlalchemy.sql import func
from app.db.session import Base


class AIConversation(Base):
    """
    AI红娘与用户的对话历史记录
    """
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    
    # 对话角色：user/assistant/system
    role = Column(String(20), nullable=False)
    
    # 对话内容（加密存储）
    content = Column(Text, nullable=False)
    
    # 对话类型：registration/consultation/care/match_recommendation
    conversation_type = Column(String(50), default="consultation", nullable=False)
    
    # 本次对话使用的token数
    tokens_used = Column(Integer, default=0, nullable=False)
    
    # 使用的模型：gpt-4/gpt-3.5-turbo
    model = Column(String(50), default="gpt-3.5-turbo", nullable=False)
    
    # 额外信息（JSON格式）
    # 注意：Python属性名用meta，数据库列名用metadata（metadata是SQLAlchemy保留字段）
    meta = Column("metadata", JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
















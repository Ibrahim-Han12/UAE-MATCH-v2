from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Index
from sqlalchemy.sql import func
from app.db.session import Base


class MatchInsightCache(Base):
    """
    匹配分析报告缓存表
    用于缓存用户对特定匹配对象的AI分析报告，避免重复生成浪费token
    """
    __tablename__ = "match_insight_cache"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True, comment="当前用户ID")
    target_user_id = Column(Integer, nullable=False, index=True, comment="匹配对象用户ID")
    
    # 缓存的分析报告内容
    explanation = Column(Text, nullable=False, comment="总体匹配度分析")
    match_score_breakdown = Column(JSON, nullable=True, comment="多维度兼容性评分")
    opener_suggestions = Column(JSON, nullable=True, comment="推荐开场白列表")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")
    
    # 唯一索引：确保每个用户对每个匹配对象只有一份缓存
    __table_args__ = (
        Index('idx_user_target_unique', 'user_id', 'target_user_id', unique=True),
    )













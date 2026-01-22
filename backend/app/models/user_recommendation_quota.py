from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func
from app.db.session import Base


class UserRecommendationQuota(Base):
    """
    用户推荐额度使用情况（按月统计）
    """
    __tablename__ = "user_recommendation_quota"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    
    # 年月（格式：2025-01）
    month = Column(String(7), nullable=False)
    
    # 本月已用推荐额度
    quota_used = Column(Integer, default=0, nullable=False)
    
    # 本月推荐额度上限（普通用户2，VIP用户10）
    quota_limit = Column(Integer, default=2, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    # 确保每个用户每月只有一条记录
    __table_args__ = (
        UniqueConstraint("user_id", "month", name="uq_user_month_quota"),
    )
















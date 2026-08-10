from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Numeric, JSON, UniqueConstraint
from sqlalchemy.sql import func
from app.db.session import Base


class GlobalAIBudget(Base):
    """
    全局AI预算管理（按月统计）
    """
    __tablename__ = "global_ai_budget"

    id = Column(Integer, primary_key=True, index=True)
    
    # 年月（格式：2025-01）
    month = Column(String(7), unique=True, nullable=False, index=True)
    
    # 预算上限（美元）
    budget_limit = Column(Numeric(10, 2), default=500.00, nullable=False)

    # 已用预算（美元）。用 6 位小数：单次 mini 调用成本常为亚分级（约 0.0003 USD），
    # 若用 2 位小数会被量化为 0.00 导致全局预算永远累加不上、熔断失效（BR-209）。
    budget_used = Column(Numeric(12, 6), default=0.000000, nullable=False)
    
    # 修改人（管理员ID）
    modified_by = Column(Integer, nullable=True)
    
    # 修改历史（JSON格式，记录每次修改）
    modification_history = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
















from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from app.db.session import Base


class MemoryPendingChange(Base):
    """
    画像更新待确认队列（PRD 5.4）。
    日常对话中提取到与库内冲突/新增的信息 → 先入队 → 小缘在自然时机口头确认后才落库，
    防止用户随口一句话就改动画像/搅动匹配池。确认后写入变更历史（事件层）。
    """
    __tablename__ = "memory_pending_changes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    field = Column(String(100), nullable=False)   # 目标字段（如 preferences.max_age）
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    source = Column(String(30), nullable=True)     # 提取来源（对话轮次/场景）

    # pending（待确认）/ confirmed（已确认落库）/ rejected（用户否认）
    status = Column(String(20), nullable=False, default="pending")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

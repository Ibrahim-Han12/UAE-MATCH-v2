from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Index
from sqlalchemy.sql import func
from app.db.session import Base


class UserStateTransition(Base):
    """
    用户状态机转移留痕（hld-m2-design.md §4.1，DEC-006 独立转移表）。
    每次 S0-S7 状态跃迁一条记录：漏斗埋点（PRD 15）与决策回溯（PRD 5.4）的数据源。
    """
    __tablename__ = "user_state_transitions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    from_state = Column(String(10), nullable=False)
    to_state = Column(String(10), nullable=False)

    # 触发原因（如 interview_completed / verification_passed / subscribed / banned）
    reason = Column(String(100), nullable=False)
    # 触发源：system / admin / user
    source = Column(String(20), nullable=False, default="system")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_state_transitions_user_time", "user_id", "created_at"),
    )

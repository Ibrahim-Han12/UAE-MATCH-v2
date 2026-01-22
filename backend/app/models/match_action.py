from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.db.session import Base


class MatchAction(Base):
    """
    记录一个用户对另一个用户的操作：
    like / pass / super_like
    """
    __tablename__ = "match_actions"

    id = Column(Integer, primary_key=True, index=True)

    actor_user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    target_user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    # like / pass / super_like
    action_type = Column(String(20), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # 每对 actor -> target 只保留一条最新记录（后写的会覆盖前面的）
    __table_args__ = (
        UniqueConstraint("actor_user_id", "target_user_id", name="uq_actor_target_once"),
    )

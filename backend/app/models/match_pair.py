from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class MatchPair(Base):
    """
    互相 like/super_like 后形成的配对关系。
    user1_id < user2_id 保证唯一性。
    """
    __tablename__ = "match_pairs"

    id = Column(Integer, primary_key=True, index=True)

    user1_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    user2_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    status = Column(String(20), default="active", nullable=False)  # active / blocked / archived

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user1_id", "user2_id", name="uq_match_pair_unique"),
    )

    # 关系定义
    user1 = relationship("User", foreign_keys=[user1_id], backref="match_pairs_as_user1")
    user2 = relationship("User", foreign_keys=[user2_id], backref="match_pairs_as_user2")

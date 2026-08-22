from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.sql import func

from app.db.session import Base


class InterviewState(Base):
    """
    深访幕状态机（DEC-032 / hld-dialogue-system.md §3）。

    独立表而非塞 user_profiles JSON：状态机语义清晰、可查询（幕停留时长等指标直接出）。
    """
    __tablename__ = "interview_state"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True, nullable=False)

    current_act = Column(String(10), default="act1", nullable=False)   # act1 / act2 / act3
    act_entered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    declined_fields = Column(JSON, nullable=True)   # list[str]：拒答且已放弃追问的字段（DEC-028 计完成度）
    refusal_counts = Column(JSON, nullable=True)    # {field_id: int}：换问法重试的计数（DEC-033 上限 1）

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

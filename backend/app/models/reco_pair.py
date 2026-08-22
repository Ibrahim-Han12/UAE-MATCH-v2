from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, JSON, Index, UniqueConstraint
from sqlalchemy.sql import func
from app.db.session import Base


class RecoPair(Base):
    """
    推荐"用户对"（BR-301, BR-302，推荐信制核心表）。
    一行 = 一对（user_low_id < user_high_id），双方各收到一封指向对方的推荐信。
    生命周期: draft(T-3) → review(T-2 生成后) → approved/rejected(T-1 人工终审)
             → delivered(T0) → matched / closed / expired
    全量 score breakdown 留存（PRD 5.4 决策回溯：无此日志推荐引擎即黑盒）。
    """
    __tablename__ = "reco_pairs"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(10), index=True, nullable=False)     # ISO 周，如 2026-W33

    user_low_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    user_high_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    # ===== 算法输出契约（算法文档 §7）=====
    score = Column(Integer, nullable=False)                       # min(A→B, B→A)
    direction_scores = Column(JSON, nullable=True)                # {a_to_b, b_to_a}
    confidence = Column(Float, nullable=True)
    dimensions = Column(JSON, nullable=True)                      # 五维得分
    semantic_bonus = Column(Integer, nullable=True, default=0)
    triggered_rules = Column(JSON, nullable=True)
    highlight_fields = Column(JSON, nullable=True)                # 推荐语素材源（BR-307 具体性校验）
    friction_point = Column(String(100), nullable=True)           # 诚实差异点（PRD 6.2-④）

    # ===== 推荐信内容（T-2 生成，T-1 可人工改）=====
    letter_for_low = Column(JSON, nullable=True)                  # 给 user_low 的信（介绍 user_high）
    letter_for_high = Column(JSON, nullable=True)

    status = Column(String(20), nullable=False, default="draft", index=True)
    review_note = Column(String(500), nullable=True)              # T-1 人工终审备注

    # ===== 双方回应（PRD 6.3 三动作）=====
    response_low = Column(String(20), nullable=True)              # accept / decline / more_info
    response_high = Column(String(20), nullable=True)
    decline_reason_low = Column(String(50), nullable=True)        # 结构化理由码（回流匹配模型）
    decline_reason_high = Column(String(50), nullable=True)
    more_info_extended = Column(Integer, nullable=False, default=0)  # 延长次数（上限1）

    delivered_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)   # 72h 时限

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("batch_id", "user_low_id", "user_high_id", name="uq_reco_pair_batch"),
        Index("idx_reco_pairs_batch_status", "batch_id", "status"),
    )


class Notification(Base):
    """
    站内信（hld-m2-design.md §8 通知服务·必达底座）。取代 v1.0 的桩实现。
    Web Push / 邮件为触达通道，本表是所有通知的落库真相源。
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    type = Column(String(40), nullable=False)         # reco_delivered / reco_teaser / match_created / ...
    title = Column(String(200), nullable=False)
    body = Column(String(1000), nullable=True)
    payload = Column(JSON, nullable=True)             # 跳转所需数据（如 reco_pair_id）

    is_read = Column(Integer, nullable=False, default=0)   # 0/1（沿用宽兼容）
    channels_sent = Column(JSON, nullable=True)       # ["inapp","push","email"] 实际送达通道

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_notifications_user_read", "user_id", "is_read"),
    )

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, JSON
from sqlalchemy.sql import func
from app.db.session import Base


class UserPsychProfile(Base):
    """
    事实层 · 心理测评区块（BR-202 三层记忆之一；PRD 5.3.6）。
    与 user_profiles / match_preferences 一起构成"结构化画像库"的事实层。
    仅用高效度框架：大五 + 依恋 + 冲突风格 + 金钱观 + 价值观向量；MBTI 仅映射入库。
    评分/权重规则属《匹配算法设计》(C1)，本表只承载结构。
    """
    __tablename__ = "user_psych_profile"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True, nullable=False)

    # 大五人格（OCEAN，0-1；神经质为婚姻质量最强预测因子）
    big_five_openness = Column(Float, nullable=True)
    big_five_conscientiousness = Column(Float, nullable=True)
    big_five_extraversion = Column(Float, nullable=True)
    big_five_agreeableness = Column(Float, nullable=True)
    big_five_neuroticism = Column(Float, nullable=True)

    attachment_style = Column(String(20), nullable=True)   # secure/anxious/avoidant/mixed_unclear (D1)
    conflict_style = Column(String(30), nullable=True)     # Gottman 冲突模式 (D2)
    family_role_expectation = Column(JSON, nullable=True)  # D3: {finance_model, career_priority, housework_expectation}
    money_view = Column(String(30), nullable=True)         # 金钱观 (D4)
    mbti = Column(String(10), nullable=True)               # 自报，仅作沟通语言（已映射大五入库）

    values_vector_id = Column(Integer, nullable=True)      # 指向 memory_vectors(namespace=profile) 的价值观向量

    # 各字段置信度（明说=高/推断=低），供小缘后续自然确认（PRD 5.2 G5）
    field_confidence = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.sql import func

from app.db.session import Base


class MatchPreference(Base):
    __tablename__ = "match_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True, nullable=False)

    # 希望对方的基本条件
    preferred_gender = Column(String(20), nullable=True)       # male / female / any
    min_age = Column(Integer, nullable=True)
    max_age = Column(Integer, nullable=True)
    min_height_cm = Column(Integer, nullable=True)
    max_height_cm = Column(Integer, nullable=True)

    min_income_monthly_aed = Column(Integer, nullable=True)    # 期望对方最低收入（参考 AED）
    education_level = Column(String(50), nullable=True)        # 希望对方的学历

    # 价值观 / 生活方式
    marriage_timeline = Column(String(50), nullable=True)      # within_1_year / 1_3_years / not_sure
    want_children = Column(String(20), nullable=True)          # yes / no / maybe
    plan_settle_in_uae = Column(Boolean, nullable=True)        # 是否计划长期在阿联酋
    plan_return_china = Column(String(20), nullable=True)      # yes / no / maybe

    religion = Column(String(50), nullable=True)               # 宗教偏好，比如 islam / none / any
    mbti = Column(String(10), nullable=True)                   # MBTI 类型，比如 INTJ

    notes = Column(String(500), nullable=True)                 # 其他备注（例如必须喜欢猫等）

    # ===== 深访 Schema v0.3.1 · C 类择偶条件扩展 =====
    # C1/C2 复用上方 min/max_age、min/max_height_cm
    education_floor = Column(String(20), nullable=True)         # C3.education_floor（none/bachelor/master）
    income_floor_band = Column(String(20), nullable=True)       # C3.income_floor_band（枚举档位）
    same_emirate_only = Column(Boolean, nullable=True)          # C4（对方暂在国内容忍度以 B6 为唯一事实源）
    dealbreakers = Column(JSON, nullable=True)                  # C5 [{code, elasticity_value, note}]（per-item 弹性）

    # C1-C4 的弹性系数（PRD 5.2：hard/negotiable/preference），如 {"C1":"hard","C3":"negotiable"}
    elasticity = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

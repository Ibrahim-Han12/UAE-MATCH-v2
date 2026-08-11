from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.sql import func

from app.db.session import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True, nullable=False)

    # 基础展示信息
    display_name = Column(String(100), nullable=True)          # 昵称
    gender = Column(String(20), nullable=True)                 # male / female / other
    birth_year = Column(Integer, nullable=True)                # 出生年份，方便算年龄
    height_cm = Column(Integer, nullable=True)

    nationality = Column(String(50), nullable=True)            # 国籍
    current_country = Column(String(50), nullable=True)        # 当前国家，比如 UAE / China
    current_city = Column(String(100), nullable=True)          # 当前城市，比如 Dubai / Abu Dhabi

    occupation = Column(String(100), nullable=True)            # 职业
    company = Column(String(100), nullable=True)               # 公司（可选）
    education_level = Column(String(50), nullable=True)        # 本科 / 硕士 / 博士 等

    bio = Column(String(500), nullable=True)                   # 个人介绍
    is_public = Column(Boolean, default=True, nullable=False)  # 资料是否对他人可见（后面推荐时会用）
    
    # 扩展信息（JSON格式，存储interests, values, lifestyle等）
    extended_info = Column(JSON, nullable=True)

    # ===== 深访 Schema v0.3.1 · A 类硬性信息扩展（事实层，BR-202）=====
    education_institution = Column(String(200), nullable=True)   # A5.institution（可选）
    occupation_industry = Column(String(50), nullable=True)      # A6.industry（枚举）
    occupation_role_type = Column(String(30), nullable=True)     # A6.role_type（枚举）
    income_band_aed = Column(String(20), nullable=True)          # A7（敏感：仅参与计算，永不展示）
    residence_emirate = Column(String(20), nullable=True)        # A8.emirate
    residence_district = Column(String(100), nullable=True)      # A8.district
    visa_type = Column(String(40), nullable=True)                # A9（敏感：仅参与计算，永不展示）
    has_children = Column(JSON, nullable=True)                   # A10 {has, count, living_arrangement}

    # ===== B 类本地化维度（核心数据资产）=====
    relocation_plan = Column(String(30), nullable=True)          # B1
    return_horizon_years = Column(Integer, nullable=True)        # B1.extra
    marriage_timeline = Column(String(20), nullable=True)        # B2（本人时间线；match_preferences 同名列为遗留）
    children_plan = Column(JSON, nullable=True)                  # B3 {want_children, timeline, accept_partner_with_children}
    parents_care_plan = Column(String(30), nullable=True)        # B4
    cross_cultural_openness = Column(JSON, nullable=True)        # B5（v1 仅采集；religion_constraint 为唯一匹配豁免）
    distance_tolerance = Column(JSON, nullable=True)             # B6 {cross_emirate, partner_in_china_temp}

    # 深访完成时间（必采 A-D 100% 时写入，同时触发 S1→S2）
    interview_completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

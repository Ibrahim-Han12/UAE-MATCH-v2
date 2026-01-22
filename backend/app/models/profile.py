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

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

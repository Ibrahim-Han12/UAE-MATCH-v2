from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.db.session import Base


class UserPhoto(Base):
    __tablename__ = "user_photos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 照片信息
    file_path = Column(String(500), nullable=False)  # 文件存储路径
    file_url = Column(String(1000), nullable=False)  # 访问URL
    file_name = Column(String(255), nullable=True)  # 原始文件名
    file_size = Column(Integer, nullable=True)  # 文件大小（字节）
    mime_type = Column(String(100), nullable=True)  # MIME类型

    # 照片属性
    display_order = Column(Integer, default=0, nullable=False)  # 显示顺序（0为主照片）
    is_primary = Column(Boolean, default=False, nullable=False)  # 是否为主照片
    is_verified = Column(Boolean, default=False, nullable=False)  # 是否通过真人认证

    # 审核状态
    status = Column(
        String(20),
        default="pending",
        nullable=False,
    )  # pending / approved / rejected
    rejection_reason = Column(String(500), nullable=True)  # 拒绝原因

    # 元数据
    width = Column(Integer, nullable=True)  # 图片宽度
    height = Column(Integer, nullable=True)  # 图片高度
    extra_metadata = Column(String(1000), nullable=True)  # JSON格式的额外元数据（metadata是SQLAlchemy保留字段）

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

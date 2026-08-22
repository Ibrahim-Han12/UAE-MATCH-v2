from sqlalchemy import Column, DateTime, Integer, String, Index
from sqlalchemy.sql import func
from app.db.session import Base


class PhoneOtp(Base):
    """
    手机 OTP 验证码（BR-001, BR-108，PRD 3.1）。
    码不存明文（sha256 哈希）；6 位、5 分钟有效、60 秒重发冷却、单号每日 ≤5 条。
    """
    __tablename__ = "phone_otps"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), index=True, nullable=False)

    code_hash = Column(String(64), nullable=False)
    purpose = Column(String(20), nullable=False, default="login")

    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, nullable=False, default=0)   # 校验失败次数，≥5 作废

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_phone_otps_phone_time", "phone", "created_at"),
    )

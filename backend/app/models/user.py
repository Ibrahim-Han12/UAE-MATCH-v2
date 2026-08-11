from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # 可以用 email 或 phone 登录；二选一或都填
    email = Column(String(255), unique=True, index=True, nullable=True)
    phone = Column(String(50), unique=True, index=True, nullable=True)

    hashed_password = Column(String(255), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)  # 管理员标识

    # 用户状态机 S1-S7（PRD 2.2）；一切变更须经 core.state_machine.transition()
    status = Column(String(50), default="S1", nullable=False)

    # 单设备在线（BR-002）：当前有效会话 ID；新登录刷新它 → 旧 token 立即失效
    current_session_id = Column(String(36), nullable=True)

    # 手机验证时间（PRD 15 漏斗起点 phone_verified；OTP 验证即登录时写入）
    phone_verified_at = Column(DateTime(timezone=True), nullable=True)

    # 注销冷静期（PRD 3.4 第四道防线）：非空=冷静期中（不进推荐池、7 天可撤销）
    cancellation_requested_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason_code = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

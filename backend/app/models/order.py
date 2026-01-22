from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.sql import func

from app.db.session import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 订单信息
    order_no = Column(String(64), unique=True, nullable=False, index=True)  # 订单号
    product_type = Column(String(50), nullable=False)  # subscription / premium_feature
    product_id = Column(String(50), nullable=False)  # 产品ID（如：premium_monthly）
    product_name = Column(String(200), nullable=False)  # 产品名称

    # 金额信息
    amount = Column(Numeric(10, 2), nullable=False)  # 订单金额
    currency = Column(String(10), default="CNY", nullable=False)  # 货币

    # 支付信息
    payment_method = Column(String(50), nullable=True)  # alipay / wechat / credit_card
    payment_status = Column(
        String(20), default="pending", nullable=False
    )  # pending / paid / failed / refunded
    payment_transaction_id = Column(String(200), nullable=True)  # 第三方支付交易号
    paid_at = Column(DateTime(timezone=True), nullable=True)  # 支付时间

    # 订单状态
    status = Column(
        String(20), default="pending", nullable=False
    )  # pending / completed / cancelled / refunded

    # 回调信息
    callback_data = Column(String(2000), nullable=True)  # 支付回调原始数据（JSON）

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    # 订阅信息
    plan_type = Column(String(50), nullable=False)  # free / basic / premium
    status = Column(
        String(20), default="active", nullable=False
    )  # active / expired / cancelled

    # 时间信息
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # 过期时间
    cancelled_at = Column(DateTime(timezone=True), nullable=True)  # 取消时间

    # 关联订单
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    # 自动续费
    auto_renew = Column(Boolean, default=True, nullable=False)  # 是否自动续费
    next_billing_date = Column(DateTime(timezone=True), nullable=True)  # 下次扣费日期

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

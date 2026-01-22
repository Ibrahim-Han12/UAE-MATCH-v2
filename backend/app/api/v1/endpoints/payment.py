"""
支付和订阅API
"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.models.order import Order, Subscription
from app.models.user import User
from app.schemas.payment import (
    OrderCreate,
    OrderRead,
    PaymentCallbackRequest,
    PaymentResponse,
    SubscriptionRead,
    SubscriptionStatus,
)

router = APIRouter(prefix="/payment", tags=["payment"])

# 产品配置
PRODUCTS = {
    "basic_monthly": {
        "name": "普通会员（月付）",
        "amount": Decimal("29.00"),
        "plan_type": "basic",
        "duration_days": 30,
    },
    "basic_yearly": {
        "name": "普通会员（年付）",
        "amount": Decimal("299.00"),
        "plan_type": "basic",
        "duration_days": 365,
    },
    "premium_monthly": {
        "name": "高级会员（月付）",
        "amount": Decimal("59.00"),
        "plan_type": "premium",
        "duration_days": 30,
    },
    "premium_yearly": {
        "name": "高级会员（年付）",
        "amount": Decimal("599.00"),
        "plan_type": "premium",
        "duration_days": 365,
    },
    "super_like": {
        "name": "超级喜欢",
        "amount": Decimal("5.00"),
        "plan_type": None,
        "duration_days": None,
    },
    "boost": {
        "name": "提升曝光度",
        "amount": Decimal("19.00"),
        "plan_type": None,
        "duration_days": None,
    },
    "who_liked_me": {
        "name": "查看谁喜欢我",
        "amount": Decimal("9.00"),
        "plan_type": None,
        "duration_days": None,
    },
}


def _generate_order_no() -> str:
    """生成订单号"""
    return f"UAE{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"


@router.post("/create-order", response_model=PaymentResponse)
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    创建订单
    """
    # 验证产品ID
    if order_data.product_id not in PRODUCTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="无效的产品ID"
        )

    product = PRODUCTS[order_data.product_id]

    # 验证金额
    if order_data.amount != product["amount"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="金额不匹配"
        )

    # 创建订单
    order = Order(
        user_id=current_user.id,
        order_no=_generate_order_no(),
        product_type=order_data.product_type,
        product_id=order_data.product_id,
        product_name=product["name"],
        amount=order_data.amount,
        currency=order_data.currency,
        payment_method=order_data.payment_method,
        payment_status="pending",
        status="pending",
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    # 生成支付URL（这里需要集成实际的支付SDK）
    # 示例：返回订单号，前端可以跳转到支付页面
    payment_url = f"/payment/pay?order_no={order.order_no}"

    return PaymentResponse(
        order=OrderRead.model_validate(order),
        payment_url=payment_url,
        message="订单创建成功，请完成支付",
    )


@router.post("/callback", response_model=dict)
def payment_callback(
    callback_data: PaymentCallbackRequest,
    db: Session = Depends(get_db),
) -> Any:
    """
    支付回调（由支付平台调用）
    """
    # 查找订单
    order = db.query(Order).filter(Order.order_no == callback_data.order_no).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在"
        )

    # 验证金额
    if callback_data.amount != order.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="金额不匹配"
        )

    # 更新订单状态
    order.payment_status = callback_data.payment_status
    order.payment_transaction_id = callback_data.transaction_id
    order.status = (
        "completed" if callback_data.payment_status == "paid" else "failed"
    )

    if callback_data.payment_status == "paid":
        order.paid_at = datetime.utcnow()

        # 如果是订阅产品，创建或更新订阅
        if order.product_type == "subscription":
            product = PRODUCTS[order.product_id]
            subscription = (
                db.query(Subscription)
                .filter(Subscription.user_id == order.user_id)
                .first()
            )

            if subscription:
                # 更新现有订阅
                if subscription.status == "active" and subscription.expires_at:
                    # 如果订阅未过期，延长到期时间
                    subscription.expires_at = subscription.expires_at + timedelta(
                        days=product["duration_days"]
                    )
                else:
                    # 如果订阅已过期，重新开始
                    subscription.started_at = datetime.utcnow()
                    subscription.expires_at = datetime.utcnow() + timedelta(
                        days=product["duration_days"]
                    )
                    subscription.status = "active"
                    subscription.cancelled_at = None

                subscription.plan_type = product["plan_type"]
                subscription.order_id = order.id
            else:
                # 创建新订阅
                subscription = Subscription(
                    user_id=order.user_id,
                    plan_type=product["plan_type"],
                    status="active",
                    started_at=datetime.utcnow(),
                    expires_at=datetime.utcnow()
                    + timedelta(days=product["duration_days"]),
                    order_id=order.id,
                    auto_renew=True,
                )
                db.add(subscription)

    db.commit()

    return {"status": "success", "message": "回调处理成功"}


@router.get("/orders/me", response_model=list[OrderRead])
def get_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """获取当前用户的所有订单"""
    orders = (
        db.query(Order)
        .filter(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return orders


@router.get("/orders/{order_no}", response_model=OrderRead)
def get_order(
    order_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """获取订单详情"""
    order = (
        db.query(Order)
        .filter(Order.order_no == order_no, Order.user_id == current_user.id)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在"
        )

    return order


@router.get("/subscription/status", response_model=SubscriptionStatus)
def get_subscription_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """获取当前用户的订阅状态"""
    subscription = (
        db.query(Subscription)
        .filter(Subscription.user_id == current_user.id)
        .first()
    )

    if not subscription or subscription.status != "active":
        return SubscriptionStatus(has_subscription=False, is_premium=False)

    # 检查是否过期
    if subscription.expires_at and subscription.expires_at < datetime.utcnow():
        subscription.status = "expired"
        db.commit()
        return SubscriptionStatus(has_subscription=False, is_premium=False)

    # 计算剩余天数
    days_remaining = None
    if subscription.expires_at:
        delta = subscription.expires_at - datetime.utcnow()
        days_remaining = max(0, delta.days)

    return SubscriptionStatus(
        has_subscription=True,
        subscription=SubscriptionRead.model_validate(subscription),
        is_premium=subscription.plan_type == "premium",
        days_remaining=days_remaining,
    )


@router.get("/products", response_model=dict)
def get_products() -> Any:
    """获取产品列表"""
    return {
        "subscriptions": {
            k: v
            for k, v in PRODUCTS.items()
            if v["plan_type"] is not None
        },
        "premium_features": {
            k: v
            for k, v in PRODUCTS.items()
            if v["plan_type"] is None
        },
    }

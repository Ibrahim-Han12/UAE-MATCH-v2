"""
订阅生命周期服务（BR-501 / PRD 8.2 / A1 裁决）。

激活 → S3→S4；取消 → 周期末生效（无挽留，"取消即体面"）；
支付失败 → past_due + 7 天宽限 → 到期降回候补 S3（数据与配对保留）。
订阅状态以 Stripe 为准，本地 subscriptions 表是投影（webhook 驱动）。
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.core import state_machine as sm
from app.core import notify
from app.core.billing import catalog
from app.core.risk import log_event
from app.models.user import User
from app.models.order import Order, Subscription
from app.models.stripe_event import StripeEvent

logger = logging.getLogger(__name__)

GRACE_DAYS = 7  # 支付失败宽限期（PRD 8.2）


def elite_seats_taken(db: Session) -> int:
    return (
        db.query(Subscription)
        .filter(Subscription.plan_type == "elite", Subscription.status == "active")
        .count()
    )


def check_purchasable(db: Session, sku_id: str) -> Tuple[bool, str]:
    sku = catalog.get_sku(sku_id)
    if sku is None:
        return False, "商品不存在"
    if not sku.get("purchasable"):
        return False, "该档位即将开放，暂未开售"   # A1：高级档 M3 开卖，不收钱
    cap = sku.get("seat_cap")
    if cap is not None and elite_seats_taken(db) >= cap:
        return False, "尊享席位已满，可加入等待列表"   # 席位余量必须真实（PRD 8.3）
    return True, "ok"


def already_processed(db: Session, event_id: str) -> bool:
    return db.query(StripeEvent).filter_by(event_id=event_id).first() is not None


def mark_processed(db: Session, event_id: str, event_type: str) -> None:
    db.add(StripeEvent(event_id=event_id, event_type=event_type))


def activate_subscription(
    db: Session, user: User, sku_id: str, *,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    amount_paid: Optional[float] = None,
    transaction_id: Optional[str] = None,
) -> Subscription:
    """支付成功（webhook）→ 开通/续期订阅 + 订单留痕 + S3→S4。不 commit。"""
    sku = catalog.get_sku(sku_id)
    if sku is None:
        raise ValueError(f"未知 SKU: {sku_id}")
    months = sku["interval_count"]
    now = datetime.utcnow()

    # 订单留痕（AED）
    order = Order(
        user_id=user.id,
        order_no=f"SUB{now.strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}",
        product_type="subscription", product_id=sku_id, product_name=sku["name"],
        amount=amount_paid if amount_paid is not None else sku["price"],
        currency=catalog.currency(),
        payment_method="stripe", payment_status="paid",
        payment_transaction_id=transaction_id, paid_at=now, status="completed",
    )
    db.add(order)
    db.flush()

    sub = db.query(Subscription).filter_by(user_id=user.id).first()
    base = now
    if sub is not None and sub.status == "active" and sub.expires_at:
        exp = sub.expires_at.replace(tzinfo=None)
        if exp > now:
            base = exp  # 续期叠加
    if sub is None:
        sub = Subscription(user_id=user.id, plan_type=sku["tier"], status="active")
        db.add(sub)
    sub.plan_type = sku["tier"]
    sub.status = "active"
    sub.started_at = sub.started_at or now
    sub.expires_at = base + timedelta(days=30 * months)
    sub.cancelled_at = None
    sub.auto_renew = True
    sub.next_billing_date = sub.expires_at
    sub.order_id = order.id
    sub.grace_until = None
    if stripe_customer_id:
        sub.stripe_customer_id = stripe_customer_id
    if stripe_subscription_id:
        sub.stripe_subscription_id = stripe_subscription_id

    # 状态机：S3 → S4（三道闸最后一道）
    if sm.effective_state(user) == sm.S3:
        sm.transition(db, user, sm.S4, reason="subscribed")
    log_event(db, user_id=user.id, event_type="subscribed",
              metadata={"sku": sku_id, "tier": sku["tier"], "amount": float(order.amount)})
    notify.send(db, user.id, type="subscription_activated",
                title="会员已开通",
                body=f"欢迎！{sku['name']} 已生效，你的推荐通道已打开。",
                payload={"sku": sku_id})
    return sub


def cancel_at_period_end(db: Session, user: User) -> Subscription:
    """取消 → 周期末生效；无挽留弹窗（品牌决策），仅一次性原因码由端点收集。不 commit。"""
    sub = db.query(Subscription).filter_by(user_id=user.id).first()
    if sub is None or sub.status != "active":
        raise ValueError("当前没有生效中的订阅")
    sub.auto_renew = False
    sub.cancelled_at = datetime.utcnow()
    log_event(db, user_id=user.id, event_type="subscription_cancelled",
              metadata={"effective_at": str(sub.expires_at)})
    return sub


def handle_payment_failed(db: Session, user: User) -> Subscription:
    """支付失败（webhook）→ past_due + 7 天宽限（权益保留 + 提醒）。不 commit。"""
    sub = db.query(Subscription).filter_by(user_id=user.id).first()
    if sub is None:
        raise ValueError("无订阅记录")
    sub.status = "past_due"
    sub.grace_until = datetime.utcnow() + timedelta(days=GRACE_DAYS)
    log_event(db, user_id=user.id, event_type="subscription_past_due", metadata={})
    notify.send(db, user.id, type="payment_failed",
                title="扣款未成功",
                body=f"请在 {GRACE_DAYS} 天内更新支付方式，期间会员权益保留。",
                channels=["inapp", "push", "email"])
    return sub


def lapse_subscription(db: Session, user: User, sub: Subscription, reason: str) -> None:
    """订阅终止 → 降回候补 S3（数据与配对保留，PRD 8.2 / 5.4-⑭）。不 commit。"""
    sub.status = "expired"
    sub.auto_renew = False
    sub.grace_until = None
    if sm.effective_state(user) == sm.S4:
        sm.transition(db, user, sm.S3, reason="subscription_lapsed")
    log_event(db, user_id=user.id, event_type="subscription_lapsed", metadata={"reason": reason})
    notify.send(db, user.id, type="subscription_lapsed",
                title="会员已到期",
                body="你已回到候补池：仍可被推荐，查看与回应需要重新开通。",
                channels=["inapp", "push"])

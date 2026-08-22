"""
AED 订阅端点（BR-501 / PRD 8 / DEC-001）。

/subscription/products —— 目录（标准可买；高级"即将开放"不可买；尊享席位余量真实）
/subscription/checkout —— 创建支付会话（S3 前置：三道闸顺序）
/subscription/webhook  —— Stripe 回调（按 event id 幂等；mock 通道由 dev/mock-pay 触发）
/subscription/status   —— 当前订阅
/subscription/cancel   —— 周期末取消（无挽留；一次性原因码可跳过）
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user, require_state
from app.core.billing import catalog, service as billing
from app.core.billing.provider import get_payment_provider, is_mock
from app.core.risk import log_event
from app.models.user import User
from app.models.order import Subscription

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.get("/products")
def list_products(db: Session = Depends(get_db)) -> Any:
    """商品目录。冻结的道具不在此列（BR-503）。"""
    cat = catalog.load()
    items = []
    for sku_id, sku in cat["skus"].items():
        item = {"sku": sku_id, "name": sku["name"], "tier": sku["tier"],
                "price": sku["price"], "currency": cat["meta"]["currency"],
                "interval_months": sku["interval_count"],
                "purchasable": bool(sku.get("purchasable"))}
        if sku.get("coming_soon"):
            item["coming_soon"] = True
        if sku.get("seat_cap") is not None:
            item["seats_left"] = max(0, sku["seat_cap"] - billing.elite_seats_taken(db))
        items.append(item)
    return {"currency": cat["meta"]["currency"], "items": items}


class CheckoutIn(BaseModel):
    sku: str
    coupon: Optional[str] = None


@router.post("/checkout")
def create_checkout(
    body: CheckoutIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_state("S3")),   # 付费是第三道闸，前两道须已过
) -> Any:
    ok, reason = billing.check_purchasable(db, body.sku)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)
    sku = catalog.get_sku(body.sku)
    price = sku["price"]
    coupon = None
    if body.coupon:
        c = catalog.get_coupon(body.coupon)
        if c is None or c.get("applies_to") != body.sku:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="优惠券无效或不适用于该商品")
        price = c["price_override"]
        coupon = body.coupon

    session = get_payment_provider().create_checkout_session(
        user_id=current_user.id, sku_id=body.sku, price_aed=price, coupon=coupon)
    log_event(db, user_id=current_user.id, event_type="checkout_created",
              metadata={"sku": body.sku, "price": price, "coupon": coupon})
    db.commit()
    resp = {"checkout_url": session["checkout_url"], "session_id": session["session_id"],
            "amount": price, "currency": catalog.currency()}
    if session.get("mock"):
        resp["dev_note"] = "mock 通道：POST /subscription/dev/mock-pay 完成支付"
    return resp


class MockPayIn(BaseModel):
    sku: str
    coupon: Optional[str] = None


@router.post("/dev/mock-pay")
def dev_mock_pay(
    body: MockPayIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_state("S3")),
) -> Any:
    """【开发专用】模拟支付成功回调。真实通道由 Stripe webhook 取代。"""
    if not is_mock():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    ok, reason = billing.check_purchasable(db, body.sku)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)
    price = catalog.get_sku(body.sku)["price"]
    if body.coupon:
        c = catalog.get_coupon(body.coupon)
        if c and c.get("applies_to") == body.sku:
            price = c["price_override"]
    import uuid
    event_id = f"evt_mock_{uuid.uuid4().hex[:16]}"
    billing.mark_processed(db, event_id, "checkout.session.completed")
    sub = billing.activate_subscription(
        db, current_user, body.sku,
        stripe_customer_id=f"cus_mock_{current_user.id}",
        stripe_subscription_id=f"sub_mock_{current_user.id}",
        amount_paid=price, transaction_id=event_id)
    db.commit()
    db.refresh(current_user)
    return {"message": "支付成功（mock）", "tier": sub.plan_type,
            "expires_at": sub.expires_at, "state": current_user.status}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> Any:
    """
    Stripe Webhook（真实通道）。铁律：验签 + 按 event id 幂等；订阅状态以 Stripe 为准。
    mock 模式下不使用（dev/mock-pay 代替），仍保留以固定契约。
    """
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    event = get_payment_provider().verify_webhook(payload, signature)
    if event is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="签名校验失败")

    event_id = event.get("id", "")
    event_type = event.get("type", "")
    if not event_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少事件 ID")
    if billing.already_processed(db, event_id):
        return {"status": "duplicate_ignored"}   # 幂等

    data = (event.get("data") or {}).get("object") or {}
    user_id = int(data.get("metadata", {}).get("user_id", 0) or 0)
    user = db.query(User).filter_by(id=user_id).first() if user_id else None

    if event_type == "checkout.session.completed" and user is not None:
        billing.activate_subscription(
            db, user, data.get("metadata", {}).get("sku", ""),
            stripe_customer_id=data.get("customer"),
            stripe_subscription_id=data.get("subscription"),
            amount_paid=(data.get("amount_total") or 0) / 100.0 or None,
            transaction_id=event_id)
    elif event_type == "invoice.payment_failed" and user is not None:
        billing.handle_payment_failed(db, user)
    elif event_type == "customer.subscription.deleted" and user is not None:
        sub = db.query(Subscription).filter_by(user_id=user.id).first()
        if sub is not None:
            billing.lapse_subscription(db, user, sub, reason="stripe_deleted")

    billing.mark_processed(db, event_id, event_type)
    db.commit()
    return {"status": "ok"}


@router.get("/status")
def subscription_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    sub = db.query(Subscription).filter_by(user_id=current_user.id).first()
    if sub is None:
        return {"has_subscription": False, "tier": None, "state": current_user.status}
    return {
        "has_subscription": sub.status in ("active", "past_due"),
        "tier": sub.plan_type, "status": sub.status,
        "expires_at": sub.expires_at, "auto_renew": sub.auto_renew,
        "grace_until": sub.grace_until, "state": current_user.status,
    }


class CancelIn(BaseModel):
    reason_code: Optional[str] = None   # 一次性询问，可跳过（PRD 8.2）


@router.post("/cancel")
def cancel_subscription(
    body: CancelIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """取消即体面：周期末生效，无挽留弹窗、无降级优惠轰炸。"""
    try:
        sub = billing.cancel_at_period_end(db, current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if body.reason_code:
        log_event(db, user_id=current_user.id, event_type="cancel_reason",
                  metadata={"reason_code": body.reason_code})
    if sub.stripe_subscription_id:
        get_payment_provider().cancel_subscription_at_period_end(sub.stripe_subscription_id)
    db.commit()
    return {"message": "已设置到期不再续费，当前周期权益保留",
            "effective_until": sub.expires_at}

"""
支付供应商适配器（HLD §9.1 集成边界：平台不碰卡号，全托管 Stripe）。

MockStripeProvider：开发用——生成假 checkout 会话，配合
POST /subscription/dev/mock-pay 模拟支付完成回调。
StripeProvider：真实实现骨架——B5 经营主体 + Stripe 账号就位后填充
（需 pip install stripe，settings.STRIPE_SECRET_KEY/WEBHOOK_SECRET）。
业务代码只依赖本接口，切换只改 settings.PAYMENT_PROVIDER。
"""
import logging
import uuid
from typing import Optional, Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)


class PaymentProvider(Protocol):
    def create_checkout_session(self, *, user_id: int, sku_id: str, price_aed: float,
                                coupon: Optional[str]) -> dict: ...
    def verify_webhook(self, payload: bytes, signature: str) -> Optional[dict]: ...
    def cancel_subscription_at_period_end(self, stripe_subscription_id: str) -> bool: ...


class MockStripeProvider:
    """开发用：不产生真实支付。生产严禁使用。"""

    def create_checkout_session(self, *, user_id, sku_id, price_aed, coupon=None) -> dict:
        session_id = f"cs_mock_{uuid.uuid4().hex[:20]}"
        logger.info("[MOCK STRIPE] checkout user=%s sku=%s price=%s AED coupon=%s",
                    user_id, sku_id, price_aed, coupon)
        return {
            "session_id": session_id,
            "checkout_url": f"https://checkout.stripe.mock/pay/{session_id}",
            "mock": True,
        }

    def verify_webhook(self, payload: bytes, signature: str) -> Optional[dict]:
        import json
        try:
            return json.loads(payload)  # mock 不验签（真实实现必须验签）
        except Exception:
            return None

    def cancel_subscription_at_period_end(self, stripe_subscription_id: str) -> bool:
        logger.info("[MOCK STRIPE] cancel_at_period_end %s", stripe_subscription_id)
        return True


class StripeProvider:
    """真实 Stripe（骨架）。启用前提：B5 主体 + Stripe 账号 + pip install stripe。"""

    def __init__(self):
        if not getattr(settings, "STRIPE_SECRET_KEY", ""):
            raise RuntimeError("STRIPE_SECRET_KEY 未配置，无法启用真实 Stripe 通道")
        raise NotImplementedError(
            "真实 Stripe 通道待 B5 主体就位后实现："
            "stripe.checkout.Session.create(mode='subscription', currency='aed', ...) / "
            "stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)"
        )


_provider: Optional[PaymentProvider] = None


def get_payment_provider() -> PaymentProvider:
    global _provider
    if _provider is None:
        name = getattr(settings, "PAYMENT_PROVIDER", "mock")
        if name == "mock":
            _provider = MockStripeProvider()
        elif name == "stripe":
            _provider = StripeProvider()
        else:
            raise RuntimeError(f"未知支付通道: {name}")
    return _provider


def is_mock() -> bool:
    return getattr(settings, "PAYMENT_PROVIDER", "mock") == "mock"

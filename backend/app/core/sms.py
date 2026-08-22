"""
短信通道适配器（BR-001, BR-108）。

B2（SMS 供应商）商务未定——先以接口边界 + Mock 适配器实现（open-questions B 节约定），
供应商确定后新增一个 Provider 实现并改 settings.SMS_PROVIDER 即可，业务代码不动。
"""
import logging
from typing import Optional, Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)


class SmsProvider(Protocol):
    def send_otp(self, phone: str, code: str) -> bool: ...


class MockSmsProvider:
    """开发用：不真发短信，验证码打进日志。生产严禁使用。"""

    def send_otp(self, phone: str, code: str) -> bool:
        logger.warning("[MOCK SMS] OTP for %s -> %s (dev only)", phone, code)
        print(f"[MOCK SMS] OTP for {phone} -> {code}")
        return True


_provider: Optional[SmsProvider] = None


def get_sms_provider() -> SmsProvider:
    global _provider
    if _provider is None:
        name = getattr(settings, "SMS_PROVIDER", "mock")
        if name == "mock":
            _provider = MockSmsProvider()
        else:
            raise RuntimeError(f"未知 SMS provider: {name}（B2 供应商确定后在此接入）")
    return _provider


def is_mock() -> bool:
    return getattr(settings, "SMS_PROVIDER", "mock") == "mock"

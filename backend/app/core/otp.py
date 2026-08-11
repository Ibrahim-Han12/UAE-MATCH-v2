"""
手机 OTP 服务（BR-001/108，PRD 3.1）。

规则：6 位数字、5 分钟有效、60 秒重发冷却、单号每日上限 5 条、单码错 5 次作废。
码只存 sha256 哈希。发送经 sms 适配器（B2 未定，当前 mock）。
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.core.sms import get_sms_provider
from app.models.phone_otp import PhoneOtp

OTP_LENGTH = 6
OTP_TTL_MINUTES = 5
RESEND_COOLDOWN_SECONDS = 60
DAILY_LIMIT_PER_PHONE = 5
MAX_VERIFY_ATTEMPTS = 5


def _hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def normalize_phone(phone: str) -> str:
    """去空格/连字符；05x 本地写法归一为 +9715x。"""
    p = phone.strip().replace(" ", "").replace("-", "")
    if p.startswith("00"):
        p = "+" + p[2:]
    if p.startswith("05") and len(p) == 10:  # UAE 本地写法 05XXXXXXXX
        p = "+971" + p[1:]
    return p


def validate_phone(phone: str) -> Optional[str]:
    """仅允许 UAE(+971) 与中国(+86) 号段（PRD 3.1）。返回错误信息或 None。"""
    if not phone.startswith("+971") and not phone.startswith("+86"):
        return "仅支持 UAE(+971) 与中国(+86) 手机号"
    digits = phone[1:]
    if not digits.isdigit() or not (10 <= len(digits) <= 14):
        return "手机号格式不正确"
    return None


def request_otp(db: Session, phone: str) -> Tuple[bool, str, Optional[str]]:
    """
    发送验证码。返回 (成功?, 消息, debug_code)。
    debug_code 仅 mock 通道返回（供开发联调），真实通道恒为 None。
    不 commit，由调用方提交。
    """
    now = datetime.utcnow()

    latest = (
        db.query(PhoneOtp)
        .filter(PhoneOtp.phone == phone)
        .order_by(PhoneOtp.created_at.desc())
        .first()
    )
    if latest is not None and latest.created_at is not None:
        elapsed = (now - latest.created_at.replace(tzinfo=None)).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            return False, f"发送过于频繁，请 {int(RESEND_COOLDOWN_SECONDS - elapsed)} 秒后重试", None

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    sent_today = (
        db.query(PhoneOtp)
        .filter(PhoneOtp.phone == phone, PhoneOtp.created_at >= today_start)
        .count()
    )
    if sent_today >= DAILY_LIMIT_PER_PHONE:
        return False, "该手机号今日验证码次数已达上限，请明天再试或改用邮箱登录", None

    code = "".join(secrets.choice("0123456789") for _ in range(OTP_LENGTH))
    db.add(PhoneOtp(
        phone=phone,
        code_hash=_hash(code),
        expires_at=now + timedelta(minutes=OTP_TTL_MINUTES),
    ))

    provider = get_sms_provider()
    if not provider.send_otp(phone, code):
        return False, "短信发送失败，请稍后重试", None

    from app.core.sms import is_mock
    return True, "验证码已发送", (code if is_mock() else None)


def verify_otp(db: Session, phone: str, code: str) -> Tuple[bool, str]:
    """校验验证码。成功后该码即刻作废（expires 置为过去）。不 commit。"""
    now = datetime.utcnow()
    rec = (
        db.query(PhoneOtp)
        .filter(PhoneOtp.phone == phone)
        .order_by(PhoneOtp.created_at.desc())
        .first()
    )
    if rec is None:
        return False, "请先获取验证码"
    if rec.expires_at.replace(tzinfo=None) < now:
        return False, "验证码已过期，请重新获取"
    if rec.attempts >= MAX_VERIFY_ATTEMPTS:
        return False, "错误次数过多，该验证码已作废，请重新获取"
    if _hash(code) != rec.code_hash:
        rec.attempts += 1
        return False, "验证码错误"
    rec.expires_at = now - timedelta(seconds=1)  # 一次性使用
    return True, "验证成功"

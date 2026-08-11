import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt, JWTError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.core import security, otp as otp_service
from app.core.config import settings
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserRead
from app.core.risk import log_event

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_session_tokens(db: Session, user: User) -> Token:
    """签发新会话令牌（单设备在线 BR-002）：新 sid 覆盖旧值 → 旧设备 token 立即失效。"""
    sid = uuid.uuid4().hex[:32]
    user.current_session_id = sid
    return Token(
        access_token=security.create_access_token(subject=str(user.id), session_id=sid),
        refresh_token=security.create_refresh_token(subject=str(user.id), session_id=sid),
    )


@router.post("/register", response_model=UserRead)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)) -> Any:
    """
    用户注册。
    只需提供 password + (email 或 phone 至少一个)。
    """
    # 简单校验：至少有 email 或 phone
    try:
        user_in.validate_at_least_one_contact()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # 查重
    existing_user: Optional[User] = None
    if user_in.email:
        existing_user = db.query(User).filter(User.email == user_in.email).first()
    if not existing_user and user_in.phone:
        existing_user = db.query(User).filter(User.phone == user_in.phone).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱或手机号已注册",
        )

    db_user = User(
        email=user_in.email,
        phone=user_in.phone,
        hashed_password=security.get_password_hash(user_in.password),
        status="S1",  # 状态机起点：已注册（PRD 2.2）
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)) -> Any:
    """
    登录接口。
    username 可以是 email 或 phone。
    """
    user: Optional[User] = db.query(User).filter(User.email == user_in.username).first()
    if user is None:
        user = db.query(User).filter(User.phone == user_in.username).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户不存在或密码错误",
        )

    if not security.verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户不存在或密码错误",
        )

    if not user.is_active or user.status == "S7":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号不可用",
        )

    token = _issue_session_tokens(db, user)

    # 登录成功后记录事件
    log_event(
        db,
        user_id=user.id,
        event_type="auth_login",
        metadata={"login_method": "password"},
    )
    db.commit()

    return token


@router.post("/refresh", response_model=Token)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)) -> Any:
    """
    用 refresh_token 换新 access_token。
    校验 sid（单设备在线）：被新设备踢出的 refresh token 不能续命。
    """
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的 refresh token",
    )
    try:
        payload = jwt.decode(
            refresh_token,
            settings.JWT_REFRESH_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise invalid
        token_sid: Optional[str] = payload.get("sid")
    except JWTError:
        raise invalid

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active or user.status == "S7":
        raise invalid
    if user.current_session_id and token_sid != user.current_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "session_replaced", "message": "账号已在其他设备登录"},
        )

    # 沿用当前 sid 续签，不生成新会话
    sid = user.current_session_id
    return Token(
        access_token=security.create_access_token(subject=user_id, session_id=sid),
        refresh_token=security.create_refresh_token(subject=user_id, session_id=sid),
    )


@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_active_user)) -> Any:
    """
    获取当前登录用户的信息。
    需要在 Header 里带上 Bearer access_token。
    """
    return current_user


# ============ 手机 OTP：主登录路径（BR-001/108，验证即登录） ============

class OtpRequestIn(BaseModel):
    phone: str


class OtpVerifyIn(BaseModel):
    phone: str
    code: str


class OtpTokenOut(Token):
    is_new_user: bool = False


@router.post("/otp/request")
def request_otp(body: OtpRequestIn, db: Session = Depends(get_db)) -> Any:
    """
    发送手机验证码。60 秒冷却、单号每日 5 条（PRD 3.1）。
    仅支持 +971 / +86 号段。
    """
    phone = otp_service.normalize_phone(body.phone)
    err = otp_service.validate_phone(phone)
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    ok, message, debug_code = otp_service.request_otp(db, phone)
    if not ok:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=message)
    db.commit()

    resp: dict = {"message": message, "resend_after": otp_service.RESEND_COOLDOWN_SECONDS}
    if debug_code is not None:  # 仅 mock 通道（开发联调）
        resp["debug_code"] = debug_code
    return resp


@router.post("/otp/verify", response_model=OtpTokenOut)
def verify_otp(body: OtpVerifyIn, db: Session = Depends(get_db)) -> Any:
    """
    校验验证码——验证即登录（无单独注册步骤，PRD 3.1）：
    新手机号自动建号（S1）；老号直接登录。写 phone_verified 漏斗事件（PRD 15 起点）。
    """
    phone = otp_service.normalize_phone(body.phone)
    err = otp_service.validate_phone(phone)
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    ok, message = otp_service.verify_otp(db, phone, body.code)
    if not ok:
        db.commit()  # 保留失败次数计数
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    user = db.query(User).filter(User.phone == phone).first()
    is_new = user is None
    if is_new:
        user = User(
            phone=phone,
            # OTP 用户无密码；占位随机哈希，密码登录路径天然不可用
            hashed_password=security.get_password_hash(uuid.uuid4().hex),
            status="S1",
        )
        db.add(user)
        db.flush()
    if not user.is_active or user.status == "S7":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号不可用")

    if user.phone_verified_at is None:
        user.phone_verified_at = datetime.utcnow()
        log_event(db, user_id=user.id, event_type="phone_verified",
                  metadata={"channel": "uae" if phone.startswith("+971") else "intl"})

    token = _issue_session_tokens(db, user)
    log_event(db, user_id=user.id, event_type="auth_login",
              metadata={"login_method": "otp", "is_new_user": is_new})
    db.commit()

    return OtpTokenOut(
        access_token=token.access_token,
        refresh_token=token.refresh_token,
        is_new_user=is_new,
    )

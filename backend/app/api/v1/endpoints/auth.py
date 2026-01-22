from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.core import security
from app.core.config import settings
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserRead
from app.core.risk import log_event

router = APIRouter(prefix="/auth", tags=["auth"])


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

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用",
        )

    access_token = security.create_access_token(subject=str(user.id))
    refresh_token = security.create_refresh_token(subject=str(user.id))
    
    # 登录成功后记录事件
    log_event(
        db,
        user_id=user.id,
        event_type="auth_login",
        metadata={"login_method": "password"},
    )
    db.commit()

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=Token)
def refresh_token(refresh_token: str) -> Any:
    """
    用 refresh_token 换新 access_token（简单版本）。
    """
    try:
        payload = jwt.decode(
            refresh_token,
            settings.JWT_REFRESH_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的 refresh token",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 refresh token",
        )

    access_token = security.create_access_token(subject=user_id)
    new_refresh_token = security.create_refresh_token(subject=user_id)

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_active_user)) -> Any:
    """
    获取当前登录用户的信息。
    需要在 Header 里带上 Bearer access_token。
    """
    return current_user

from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 使用 HTTP Bearer，而不是 OAuth2 Password
bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    """
    从 Authorization: Bearer <token> 中解析当前用户。
    """
    token = credentials.credentials  # 这里拿到的就是纯 token 字符串

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_sid: Optional[str] = payload.get("sid")
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    # 单设备在线（BR-002）：账号已在新设备登录后，旧 token 的 sid 与库中不一致即失效。
    # user.current_session_id 为空（历史账号从未新式登录）时不启用检查。
    if user.current_session_id and token_sid != user.current_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "session_replaced", "message": "账号已在其他设备登录"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    基础可用性检查：is_active 且非封禁（S7）。
    状态机门禁（深访/核验/付费三道闸）用 require_state()，不在这里做。
    """
    from app.core.state_machine import effective_state, S7

    if not current_user.is_active or effective_state(current_user) == S7:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "banned", "message": "账号已被封禁，仅可申诉"},
        )
    return current_user


def require_state(min_state: str):
    """
    状态机门禁依赖工厂（hld-m2-design.md §4.2）。用法：
        @router.get("/recommendations", dependencies=[Depends(require_state("S4"))])
    或   user: User = Depends(require_state("S3"))
    不满足时返回 403 结构化响应（code=gate_blocked, gate=interview/verification/payment），
    前端据此导流到对应闸。
    """
    def _dep(current_user: User = Depends(get_current_active_user)) -> User:
        from app.core.state_machine import meets_min_state, gate_error

        if not meets_min_state(current_user, min_state):
            raise gate_error(current_user, min_state)
        return current_user

    return _dep


def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    检查：当前用户是否为管理员。
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user

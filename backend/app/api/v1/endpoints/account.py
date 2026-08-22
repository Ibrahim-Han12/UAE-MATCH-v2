"""
账号管理端点：注销四道防线（PRD 3.4 / BR-004 / DEC-005）。

第一道(入口防误·后果说明页)与第二道(毕业问询)在前端；
本文件承接第三道(双确认：二次 OTP + 手动输入"注销")与第四道(7 天冷静期)。
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core import account_cancellation as cancel_service
from app.core import otp as otp_service
from app.core import state_machine as sm
from app.models.user import User

router = APIRouter(prefix="/account", tags=["account"])


class CancelRequestIn(BaseModel):
    confirm_text: str                 # 必须手动输入"注销"（禁一键确认）
    otp_code: Optional[str] = None    # 有手机号的账号必填（二次 OTP）
    reason_code: Optional[str] = None # 可选原因码（注销漏斗数据）


@router.post("/cancel/request")
def request_cancellation(
    body: CancelRequestIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    提交注销（第三道防线）→ 进入 7 天冷静期（第四道）。
    S7 封禁用户不可自助注销（仅申诉，hld-m2-design.md §4.3 冲突裁决）。
    """
    if sm.effective_state(current_user) == sm.S7:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "banned", "message": "封禁账号不可自助注销，请走申诉通道"},
        )
    if current_user.cancellation_requested_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已在注销冷静期中")

    # 意图确认：手动输入"注销"
    if body.confirm_text.strip() != cancel_service.CONFIRM_TEXT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"请输入“{cancel_service.CONFIRM_TEXT}”二字确认",
        )

    # 二次 OTP（防他人持已登录设备代注销，与 BR-002 同一威胁模型）
    if current_user.phone:
        if not body.otp_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="请先获取并填写手机验证码")
        ok, message = otp_service.verify_otp(db, current_user.phone, body.otp_code)
        if not ok:
            db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    execute_at = cancel_service.request_cancellation(db, current_user, body.reason_code)
    db.commit()
    return {
        "message": "已进入 7 天冷静期，期间可随时撤销；到期后将执行不可恢复的删除",
        "execute_at": execute_at,
        "days": cancel_service.COOLING_DAYS,
    }


@router.post("/cancel/withdraw")
def withdraw_cancellation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """冷静期内一键撤销（登录首屏横幅入口）。"""
    if current_user.cancellation_requested_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前不在注销冷静期")
    cancel_service.withdraw_cancellation(db, current_user)
    db.commit()
    return {"message": "已撤销注销申请，欢迎回来"}


@router.get("/cancel/status")
def get_cancellation_status(
    current_user: User = Depends(get_current_user),
) -> Any:
    """冷静期状态（首屏横幅数据源：剩余天数 + 一键撤销）。"""
    return cancel_service.cancellation_status(current_user)

"""
深访端点（BR-201 / PRD 5.1-5.3）。取代旧 AIOnboardingChat 的 registration 流。

分层同意（PRD 5.1 / PDPL）：basic 为对话前置；sensitive+ai_processing 未授权时
编排器只采非高敏字段（可先闲聊）。同意书文案为 C5 资产（待法务），接口先行。
"""
from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.core import state_machine as sm
from app.core.interview import orchestrator
from app.core.interview.report import get_latest_report
from app.models.user import User
from app.models.profile_report import UserConsent

router = APIRouter(prefix="/interview", tags=["interview"])

CONSENT_TYPES = ("basic", "sensitive", "ai_processing")


def _active_consents(db: Session, user_id: int) -> set:
    rows = (
        db.query(UserConsent)
        .filter(UserConsent.user_id == user_id, UserConsent.revoked_at.is_(None))
        .all()
    )
    return {r.consent_type for r in rows}


class ConsentIn(BaseModel):
    consent_types: List[str]   # 授予的同意类型（子集）


@router.post("/consent")
def grant_consent(
    body: ConsentIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """记录分层同意（可分别授予；撤回走 revoke）。"""
    invalid = [t for t in body.consent_types if t not in CONSENT_TYPES]
    if invalid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"未知同意类型: {invalid}")
    existing = _active_consents(db, current_user.id)
    for t in body.consent_types:
        if t not in existing:
            db.add(UserConsent(user_id=current_user.id, consent_type=t))
    db.commit()
    return {"granted": sorted(_active_consents(db, current_user.id))}


@router.post("/consent/revoke")
def revoke_consent(
    body: ConsentIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """撤回同意（PDPL：可分别撤回）。"""
    rows = (
        db.query(UserConsent)
        .filter(UserConsent.user_id == current_user.id,
                UserConsent.consent_type.in_(body.consent_types),
                UserConsent.revoked_at.is_(None))
        .all()
    )
    for r in rows:
        r.revoked_at = datetime.utcnow()
    db.commit()
    return {"granted": sorted(_active_consents(db, current_user.id))}


@router.get("/consent")
def get_consents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    return {"granted": sorted(_active_consents(db, current_user.id)), "types": CONSENT_TYPES}


@router.post("/start")
def start_interview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """开始/恢复深访。basic 同意为前置。"""
    if "basic" not in _active_consents(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "consent_required", "required": ["basic"],
                    "message": "开始对话前需要同意基础服务数据使用"},
        )
    result = orchestrator.start_interview(db, current_user)
    db.commit()
    return result


class MessageIn(BaseModel):
    message: str


@router.post("/message")
def send_message(
    body: MessageIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """深访主循环单轮。"""
    if not body.message.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="消息不能为空")
    consents = _active_consents(db, current_user.id)
    if "basic" not in consents:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "consent_required", "required": ["basic"]},
        )
    sensitive_ok = {"sensitive", "ai_processing"} <= consents

    result = orchestrator.handle_message(db, current_user, body.message.strip(), sensitive_ok)
    db.commit()
    return result


@router.get("/progress")
def get_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """"我已经了解你 X%"（G4；禁用表单语言由前端文案遵守）。"""
    progress = orchestrator.compute_progress(db, current_user.id)
    return {**progress, "state": sm.effective_state(current_user)}


@router.get("/report")
def get_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """最新画像报告（基础版免费，A4 裁决）。"""
    report = get_latest_report(db, current_user.id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告尚未生成")
    return {"version": report.version, "tier": report.tier,
            "sections": report.sections, "created_at": report.created_at}

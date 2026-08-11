"""
EID 核验端点（BR-107 / PRD 4.1）。

用户视角流程：说明页(前端) → KYC SDK 会话 → 服务商回传结论 → 照片审核 → S3。
真实服务商回传走 webhook（B1 定型后实现签名校验）；开发期用 mock-complete 模拟。
"""
from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user, require_state
from app.core import kyc as kyc_service
from app.core import state_machine as sm
from app.models.user import User

router = APIRouter(prefix="/verification", tags=["verification"])


@router.get("/status")
def verification_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """核验进度：KYC 是否通过、照片是否过审、当前状态。前端据此渲染核验中心。"""
    return {
        "state": sm.effective_state(current_user),
        "kyc_passed": kyc_service.has_passed_kyc(db, current_user.id),
        "photo_approved": kyc_service.has_approved_photo(db, current_user.id),
        "phone_verified": current_user.phone_verified_at is not None,
    }


@router.post("/kyc/start")
def start_kyc(
    current_user: User = Depends(require_state("S2")),
) -> Any:
    """发起 KYC 会话（须已完成深访 S2——三道闸顺序）。返回 SDK 会话参数。"""
    return kyc_service.create_session(current_user)


class MockKycCompleteIn(BaseModel):
    transaction_id: str
    result: str = "passed"           # passed / failed / needs_review
    full_name: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None      # male / female
    document_expiry: Optional[date] = None
    eid_number: Optional[str] = None  # 仅用于单向哈希，不落明文


@router.post("/kyc/mock-complete")
def mock_complete_kyc(
    body: MockKycCompleteIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_state("S2")),
) -> Any:
    """
    【开发专用】模拟服务商回传结论。仅 KYC_PROVIDER=mock 时可用；
    真实服务商接入后此端点由带签名校验的 webhook 取代。
    """
    if not kyc_service.is_mock():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    outcome = kyc_service.process_kyc_result(
        db, current_user,
        provider="mock", transaction_id=body.transaction_id,
        result=body.result, full_name=body.full_name,
        birth_date=body.birth_date, gender=body.gender,
        document_expiry=body.document_expiry, eid_number=body.eid_number,
    )
    if not outcome["accepted"]:
        db.commit()  # 拦截事件也要留痕
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=outcome["reason"])
    db.commit()
    return {"result": outcome["reason"], "promoted_to_s3": outcome["promoted"]}

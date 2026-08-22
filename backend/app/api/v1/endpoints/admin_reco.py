"""
推荐信质检队列（T-1 人工终审，PRD 11.1 / DEC-003：P2 阶段 100% 人工终审）。
收件箱式视图：低置信度 pair 优先看（算法 §4.6）。
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_admin_user
from app.core.risk import log_event
from app.models.user import User
from app.models.reco_pair import RecoPair

router = APIRouter(prefix="/admin/reco", tags=["admin-reco"])


@router.get("/queue")
def review_queue(
    batch_id: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
) -> Any:
    """待终审队列（低置信度优先）。"""
    q = db.query(RecoPair).filter(RecoPair.status == "review")
    if batch_id:
        q = q.filter(RecoPair.batch_id == batch_id)
    pairs = q.order_by(RecoPair.confidence.asc().nullsfirst(), RecoPair.score.desc()).all()
    return {"count": len(pairs), "items": [{
        "id": p.id, "batch_id": p.batch_id,
        "user_low_id": p.user_low_id, "user_high_id": p.user_high_id,
        "score": p.score, "confidence": p.confidence,
        "dimensions": p.dimensions, "triggered_rules": p.triggered_rules,
        "friction_point": p.friction_point,
        "letter_for_low": p.letter_for_low, "letter_for_high": p.letter_for_high,
        "review_note": p.review_note,
    } for p in pairs]}


class ReviewIn(BaseModel):
    action: str                        # approve / reject
    note: Optional[str] = None
    letter_for_low: Optional[dict] = None    # 人工改写后的信（可选）
    letter_for_high: Optional[dict] = None


@router.post("/{pair_id}/review")
def review_pair(
    pair_id: int,
    body: ReviewIn,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
) -> Any:
    pair = db.query(RecoPair).filter_by(id=pair_id).first()
    if pair is None or pair.status != "review":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="待审 pair 不存在")
    if body.letter_for_low is not None:
        pair.letter_for_low = body.letter_for_low
    if body.letter_for_high is not None:
        pair.letter_for_high = body.letter_for_high
    if body.action == "approve":
        if not (pair.letter_for_low and pair.letter_for_high):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="信件不完整，不能通过")
        pair.status = "approved"
    elif body.action == "reject":
        pair.status = "rejected"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="action 须为 approve/reject")
    pair.review_note = body.note or pair.review_note
    # 人机分歧标定数据（算法 §8：S2=参数标定期）
    log_event(db, user_id=admin.id, event_type="reco_review",
              metadata={"reco_pair_id": pair.id, "action": body.action,
                        "score": pair.score, "note": body.note})
    db.commit()
    return {"id": pair.id, "status": pair.status}

"""照片人工审核（BR-101/102 · DEC-002 种子期人工核验）。

三道闸第二道的最后一环：`kyc.py` 的 try_promote_to_verified() 需要"至少一张照片
人工过审"，而在此之前**没有任何代码能把照片从 pending 变成 approved**——
真实用户因此永远过不了第二道闸。本模块补上这个动作。

约定：本模块不 commit，由调用方提交。
"""
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.kyc import try_promote_to_verified
from app.core.risk import log_event
from app.models.user import User
from app.models.user_photo import UserPhoto

logger = logging.getLogger(__name__)

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
ACTIONS = ("approve", "reject")


def pending_queue(db: Session, limit: int = 200) -> List[UserPhoto]:
    """待审队列，先提交的先看（人工审核按到达顺序，不做优先级）。"""
    return (
        db.query(UserPhoto)
        .filter(UserPhoto.status == PENDING)
        .order_by(UserPhoto.created_at.asc(), UserPhoto.id.asc())
        .limit(limit)
        .all()
    )


def review(db: Session, photo: UserPhoto, action: str,
           reason: Optional[str] = None, admin_id: Optional[int] = None) -> dict:
    """过审 / 打回。过审后尝试推进 S2→S3。

    打回必须给理由——用户要知道重拍什么，否则只能反复瞎试。
    已审过的照片不允许再审：避免重复触发状态升级与埋点。
    """
    if action not in ACTIONS:
        raise ValueError(f"未知审核动作: {action}（只接受 {ACTIONS}）")
    if photo.status != PENDING:
        raise ValueError(f"照片 {photo.id} 已是 {photo.status}，不可重复审核")
    if action == "reject" and not (reason or "").strip():
        raise ValueError("打回必须填写理由")

    promoted = False
    if action == "approve":
        photo.status = APPROVED
        photo.is_verified = True
        photo.rejection_reason = None
        db.add(photo)
        user = db.query(User).filter_by(id=photo.user_id).first()
        if user is not None:
            promoted = try_promote_to_verified(db, user)
    else:
        photo.status = REJECTED
        photo.is_verified = False
        photo.rejection_reason = reason.strip()
        db.add(photo)

    log_event(db, user_id=photo.user_id, event_type="photo_reviewed",
              metadata={"photo_id": photo.id, "action": action,
                        "reason": photo.rejection_reason, "admin_id": admin_id,
                        "promoted": promoted})
    return {"status": photo.status, "promoted": promoted}

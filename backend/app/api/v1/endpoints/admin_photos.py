"""照片人工审核队列（BR-101/102 · DEC-002：种子期人工核验）。

判定逻辑在 app.core.photo_review；本文件只做鉴权、取数、提交。
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user, get_db
from app.core import photo_review
from app.models.profile import UserProfile
from app.models.user import User
from app.models.user_photo import UserPhoto

router = APIRouter(prefix="/admin/photos", tags=["admin-photos"])


@router.get("/queue")
def review_queue(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
) -> Any:
    """待审队列，先提交的先看。带上最少的画像上下文，便于判断"是不是本人"。"""
    photos = photo_review.pending_queue(db)
    items = []
    for p in photos:
        prof = db.query(UserProfile).filter_by(user_id=p.user_id).first()
        items.append({
            "id": p.id,
            "user_id": p.user_id,
            "file_url": p.file_url,
            "file_name": p.file_name,
            "width": p.width,
            "height": p.height,
            "is_primary": p.is_primary,
            "created_at": p.created_at,
            # 审核依据：核验带入的性别/年龄用于比对照片是否本人（敏感字段不外泄）
            "declared_gender": getattr(prof, "gender", None) if prof else None,
            "declared_age": getattr(prof, "age", None) if prof else None,
        })
    return {"count": len(items), "items": items}


class PhotoReviewIn(BaseModel):
    action: str                       # approve / reject
    reason: Optional[str] = None      # reject 必填


@router.post("/{photo_id}/review")
def review_photo(
    photo_id: int,
    body: PhotoReviewIn,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
) -> Any:
    photo = db.query(UserPhoto).filter_by(id=photo_id).first()
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="照片不存在")
    try:
        result = photo_review.review(db, photo, action=body.action,
                                     reason=body.reason, admin_id=admin.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    db.commit()
    return result

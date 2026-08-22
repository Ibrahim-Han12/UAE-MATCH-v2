"""照片展示口径（BR-101/102）。

铁律：**只有人工过审的照片才能被展示。** 推荐信里"先理由后照片"（PRD 6.2）要展示的
那张必须过审——否则谁都能上传一张陌生人照片直接出现在别人的推荐信里，第二道闸形同虚设。

约定：本模块不 commit，由调用方提交。
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.core.photo_review import APPROVED, REJECTED
from app.models.user_photo import UserPhoto


def primary_photo_url(db: Session, user_id: int) -> Optional[str]:
    """该用户对外展示的主照片 URL；没有过审照片时返回 None（由前端给空态）。"""
    photo = (
        db.query(UserPhoto)
        .filter(UserPhoto.user_id == user_id, UserPhoto.status == APPROVED)
        .order_by(UserPhoto.is_primary.desc(), UserPhoto.display_order.asc(),
                  UserPhoto.id.asc())
        .first()
    )
    return photo.file_url if photo is not None else None


def ensure_primary(db: Session, user_id: int) -> Optional[UserPhoto]:
    """没有主图时，把最靠前的一张非打回照片设为主图。

    首张上传即自动成为主图——用户不必先理解"主图"这个概念。
    已有主图则不覆盖用户的选择。
    """
    candidates = (
        db.query(UserPhoto)
        .filter(UserPhoto.user_id == user_id, UserPhoto.status != REJECTED)
        .order_by(UserPhoto.display_order.asc(), UserPhoto.id.asc())
        .all()
    )
    if not candidates:
        return None
    for p in candidates:
        if p.is_primary:
            return p
    first = candidates[0]
    first.is_primary = True
    db.add(first)
    return first

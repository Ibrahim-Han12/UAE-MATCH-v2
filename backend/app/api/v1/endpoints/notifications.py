"""
通知端点（hld-m2-design.md §8 站内信必达底座）。v1.0 桩实现已由真实落库取代。
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.reco_pair import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    count = db.query(Notification).filter_by(user_id=current_user.id, is_read=0).count()
    return {"unread_count": count}


@router.get("")
def list_notifications(
    page: int = 1,
    page_size: int = 20,
    is_read: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    q = db.query(Notification).filter_by(user_id=current_user.id)
    if is_read is not None:
        q = q.filter(Notification.is_read == (1 if is_read else 0))
    total = q.count()
    rows = (
        q.order_by(Notification.created_at.desc())
        .offset(max(0, (page - 1) * page_size)).limit(min(page_size, 100)).all()
    )
    items = [{
        "id": n.id, "type": n.type, "title": n.title, "body": n.body,
        "payload": n.payload, "is_read": bool(n.is_read), "created_at": n.created_at,
    } for n in rows]
    unread = db.query(Notification).filter_by(user_id=current_user.id, is_read=0).count()
    return {"items": items, "total": total, "unread_count": unread}


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    n = db.query(Notification).filter_by(id=notification_id, user_id=current_user.id).first()
    if n is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在")
    n.is_read = 1
    db.commit()
    return {"message": "已标记为已读"}


@router.post("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    db.query(Notification).filter_by(user_id=current_user.id, is_read=0).update({"is_read": 1})
    db.commit()
    return {"message": "全部已读"}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    n = db.query(Notification).filter_by(id=notification_id, user_id=current_user.id).first()
    if n is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在")
    db.delete(n)
    db.commit()
    return {"message": "已删除"}

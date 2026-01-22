from typing import Any, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.event_log import EventLog
from app.schemas.event import EventLogRead

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/my", response_model=List[EventLogRead])
def list_my_events(
    event_type: str = Query(
        "",
        description="可选，按 event_type 过滤，比如 auth_login / match_like / message_send 等",
    ),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    查看当前用户自己的行为日志（按时间倒序）。
    这对调试风控、AI 分析都很有用。
    """
    q = (
        db.query(EventLog)
        .filter(EventLog.user_id == current_user.id)
        .order_by(EventLog.created_at.desc())
    )

    if event_type:
        q = q.filter(EventLog.event_type == event_type)

    events = q.limit(limit).all()
    return [EventLogRead.model_validate(e) for e in events]

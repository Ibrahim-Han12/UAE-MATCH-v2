import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.event_log import EventLog

def log_event(
    db: Session,
    *,
    user_id: int,
    event_type: str,
    target_user_id: Optional[int] = None,
    match_pair_id: Optional[int] = None,
    message_id: Optional[int] = None,
    report_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EventLog:
    """
    写一条 EventLog。
    metadata 会被序列化为 JSON 字符串，存到 EventLog.meta（列名 metadata）。
    """
    meta_str = json.dumps(metadata, ensure_ascii=False) if metadata else None

    ev = EventLog(
        user_id=user_id,
        event_type=event_type,
        target_user_id=target_user_id,
        match_pair_id=match_pair_id,
        message_id=message_id,
        report_id=report_id,
        meta=meta_str,   # ← 改成 meta
    )
    db.add(ev)
    return ev



def check_rate_limit(
    db: Session,
    *,
    user_id: int,
    event_type: str,
    window_seconds: int,
    max_count: int,
    error_message: str,
) -> None:
    """
    简单限流：
    - 在 window_seconds 时间窗口内，某个 user 对某 event_type 最多 max_count 次
    - 超过则抛 429 HTTPException
    """
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=window_seconds)

    recent_count = (
        db.query(EventLog)
        .filter(
            EventLog.user_id == user_id,
            EventLog.event_type == event_type,
            EventLog.created_at >= window_start,
        )
        .count()
    )

    if recent_count >= max_count:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error_message,
        )

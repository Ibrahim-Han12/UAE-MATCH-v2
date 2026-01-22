"""
管理员后台API
用于管理举报、风控事件等
"""
from typing import Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.api.deps import get_db, get_current_admin_user
from app.models.user import User
from app.models.user_report import UserReport
from app.models.event_log import EventLog
from app.models.chat_message import ChatMessage
from app.models.match_pair import MatchPair
from app.models.profile import UserProfile
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["admin"])


class ReportListItem(BaseModel):
    id: int
    reporter_id: int
    reported_user_id: int
    reported_message_id: Optional[int] = None
    category: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    reporter_nickname: Optional[str] = None
    reported_user_nickname: Optional[str] = None
    reported_message_content: Optional[str] = None

    class Config:
        from_attributes = True


class EventLogListItem(BaseModel):
    id: int
    user_id: int
    event_type: str
    target_user_id: Optional[int] = None
    match_pair_id: Optional[int] = None
    message_id: Optional[int] = None
    report_id: Optional[int] = None
    meta: Optional[str] = None
    created_at: datetime
    user_nickname: Optional[str] = None
    target_user_nickname: Optional[str] = None

    class Config:
        from_attributes = True


class UpdateReportStatusRequest(BaseModel):
    status: str  # open / reviewing / closed / resolved


class LinkEventsRequest(BaseModel):
    report_id: int
    event_log_ids: List[int]


@router.get("/reports", response_model=List[ReportListItem])
def list_reports(
    status_filter: Optional[str] = Query(None, alias="status", description="筛选状态: open/reviewing/closed"),
    category_filter: Optional[str] = Query(None, alias="category", description="筛选类别"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    获取举报列表（管理员）
    """
    query = db.query(UserReport)
    
    if status_filter:
        query = query.filter(UserReport.status == status_filter)
    if category_filter:
        query = query.filter(UserReport.category == category_filter)
    
    reports = query.order_by(UserReport.created_at.desc()).offset(skip).limit(limit).all()
    
    results = []
    for report in reports:
        # 获取举报人昵称
        reporter_profile = db.query(UserProfile).filter(
            UserProfile.user_id == report.reporter_id
        ).first()
        reporter_nickname = reporter_profile.display_name if reporter_profile else None
        
        # 获取被举报人昵称
        reported_profile = db.query(UserProfile).filter(
            UserProfile.user_id == report.reported_user_id
        ).first()
        reported_user_nickname = reported_profile.display_name if reported_profile else None
        
        # 获取被举报消息内容
        reported_message_content = None
        if report.reported_message_id:
            msg = db.query(ChatMessage).filter(
                ChatMessage.id == report.reported_message_id
            ).first()
            if msg:
                reported_message_content = msg.content[:100]  # 只取前100字符
        
        results.append(ReportListItem(
            id=report.id,
            reporter_id=report.reporter_id,
            reported_user_id=report.reported_user_id,
            reported_message_id=report.reported_message_id,
            category=report.category,
            description=report.description,
            status=report.status,
            created_at=report.created_at,
            reporter_nickname=reporter_nickname,
            reported_user_nickname=reported_user_nickname,
            reported_message_content=reported_message_content,
        ))
    
    return results


@router.get("/reports/{report_id}")
def get_report_detail(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    获取举报详情（管理员）
    """
    report = db.query(UserReport).filter(UserReport.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="举报不存在",
        )
    
    # 获取相关用户信息
    reporter_profile = db.query(UserProfile).filter(
        UserProfile.user_id == report.reporter_id
    ).first()
    reported_profile = db.query(UserProfile).filter(
        UserProfile.user_id == report.reported_user_id
    ).first()
    
    # 获取相关消息
    reported_message = None
    if report.reported_message_id:
        reported_message = db.query(ChatMessage).filter(
            ChatMessage.id == report.reported_message_id
        ).first()
    
    # 获取相关的风控事件
    related_events = db.query(EventLog).filter(
        EventLog.report_id == report_id
    ).order_by(EventLog.created_at.desc()).all()
    
    return {
        "report": {
            "id": report.id,
            "reporter_id": report.reporter_id,
            "reported_user_id": report.reported_user_id,
            "reported_message_id": report.reported_message_id,
            "category": report.category,
            "description": report.description,
            "status": report.status,
            "created_at": report.created_at,
        },
        "reporter": {
            "id": report.reporter_id,
            "nickname": reporter_profile.display_name if reporter_profile else None,
            "profile": reporter_profile.__dict__ if reporter_profile else None,
        },
        "reported_user": {
            "id": report.reported_user_id,
            "nickname": reported_profile.display_name if reported_profile else None,
            "profile": reported_profile.__dict__ if reported_profile else None,
        },
        "reported_message": {
            "id": reported_message.id,
            "content": reported_message.content,
            "created_at": reported_message.created_at,
        } if reported_message else None,
        "related_events": [
            {
                "id": ev.id,
                "event_type": ev.event_type,
                "created_at": ev.created_at,
                "meta": ev.meta,
            }
            for ev in related_events
        ],
    }


@router.patch("/reports/{report_id}/status")
def update_report_status(
    report_id: int,
    body: UpdateReportStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    更新举报状态（管理员）
    """
    if body.status not in ["open", "reviewing", "closed", "resolved"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的状态值",
        )
    
    report = db.query(UserReport).filter(UserReport.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="举报不存在",
        )
    
    report.status = body.status
    db.commit()
    db.refresh(report)
    
    return {"detail": "状态已更新", "status": report.status}


@router.post("/reports/{report_id}/link-events")
def link_events_to_report(
    report_id: int,
    body: LinkEventsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    将风控事件关联到举报（管理员）
    """
    report = db.query(UserReport).filter(UserReport.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="举报不存在",
        )
    
    # 更新事件日志的report_id
    events = db.query(EventLog).filter(EventLog.id.in_(body.event_log_ids)).all()
    for event in events:
        event.report_id = report_id
    
    db.commit()
    
    return {"detail": f"已关联 {len(events)} 个事件到举报"}


@router.get("/events", response_model=List[EventLogListItem])
def list_events(
    event_type_filter: Optional[str] = Query(None, alias="event_type", description="筛选事件类型"),
    user_id_filter: Optional[int] = Query(None, alias="user_id", description="筛选用户ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    获取风控事件列表（管理员）
    """
    query = db.query(EventLog)
    
    if event_type_filter:
        query = query.filter(EventLog.event_type == event_type_filter)
    if user_id_filter:
        query = query.filter(EventLog.user_id == user_id_filter)
    
    events = query.order_by(EventLog.created_at.desc()).offset(skip).limit(limit).all()
    
    results = []
    for event in events:
        # 获取用户昵称
        user_profile = db.query(UserProfile).filter(
            UserProfile.user_id == event.user_id
        ).first()
        user_nickname = user_profile.display_name if user_profile else None
        
        # 获取目标用户昵称
        target_user_nickname = None
        if event.target_user_id:
            target_profile = db.query(UserProfile).filter(
                UserProfile.user_id == event.target_user_id
            ).first()
            target_user_nickname = target_profile.display_name if target_profile else None
        
        results.append(EventLogListItem(
            id=event.id,
            user_id=event.user_id,
            event_type=event.event_type,
            target_user_id=event.target_user_id,
            match_pair_id=event.match_pair_id,
            message_id=event.message_id,
            report_id=event.report_id,
            meta=event.meta,
            created_at=event.created_at,
            user_nickname=user_nickname,
            target_user_nickname=target_user_nickname,
        ))
    
    return results


@router.get("/events/{event_id}")
def get_event_detail(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    获取风控事件详情（管理员）
    """
    event = db.query(EventLog).filter(EventLog.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="事件不存在",
        )
    
    # 获取用户信息
    user_profile = db.query(UserProfile).filter(
        UserProfile.user_id == event.user_id
    ).first()
    
    target_user_profile = None
    if event.target_user_id:
        target_user_profile = db.query(UserProfile).filter(
            UserProfile.user_id == event.target_user_id
        ).first()
    
    # 获取相关消息
    message = None
    if event.message_id:
        message = db.query(ChatMessage).filter(
            ChatMessage.id == event.message_id
        ).first()
    
    # 获取相关配对
    match_pair = None
    if event.match_pair_id:
        match_pair = db.query(MatchPair).filter(
            MatchPair.id == event.match_pair_id
        ).first()
    
    return {
        "event": {
            "id": event.id,
            "user_id": event.user_id,
            "event_type": event.event_type,
            "target_user_id": event.target_user_id,
            "match_pair_id": event.match_pair_id,
            "message_id": event.message_id,
            "report_id": event.report_id,
            "meta": event.meta,
            "created_at": event.created_at,
        },
        "user": {
            "id": event.user_id,
            "nickname": user_profile.display_name if user_profile else None,
            "profile": user_profile.__dict__ if user_profile else None,
        },
        "target_user": {
            "id": event.target_user_id,
            "nickname": target_user_profile.display_name if target_user_profile else None,
            "profile": target_user_profile.__dict__ if target_user_profile else None,
        } if event.target_user_id else None,
        "message": {
            "id": message.id,
            "content": message.content,
            "created_at": message.created_at,
        } if message else None,
        "match_pair": {
            "id": match_pair.id,
            "user1_id": match_pair.user1_id,
            "user2_id": match_pair.user2_id,
            "status": match_pair.status,
        } if match_pair else None,
    }


@router.get("/stats")
def get_admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Any:
    """
    获取管理员统计信息
    """
    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    
    # 举报统计
    total_reports = db.query(UserReport).count()
    open_reports = db.query(UserReport).filter(UserReport.status == "open").count()
    reports_24h = db.query(UserReport).filter(UserReport.created_at >= last_24h).count()
    reports_7d = db.query(UserReport).filter(UserReport.created_at >= last_7d).count()
    
    # 事件统计
    total_events = db.query(EventLog).count()
    events_24h = db.query(EventLog).filter(EventLog.created_at >= last_24h).count()
    events_7d = db.query(EventLog).filter(EventLog.created_at >= last_7d).count()
    
    # 按类别统计举报
    category_stats = {}
    for category in ["harassment", "scam", "fake_profile", "spam", "other"]:
        count = db.query(UserReport).filter(UserReport.category == category).count()
        category_stats[category] = count
    
    # 按事件类型统计
    event_type_stats = {}
    event_types = db.query(EventLog.event_type).distinct().all()
    for (event_type,) in event_types:
        count = db.query(EventLog).filter(EventLog.event_type == event_type).count()
        event_type_stats[event_type] = count
    
    return {
        "reports": {
            "total": total_reports,
            "open": open_reports,
            "last_24h": reports_24h,
            "last_7d": reports_7d,
            "by_category": category_stats,
        },
        "events": {
            "total": total_events,
            "last_24h": events_24h,
            "last_7d": events_7d,
            "by_type": event_type_stats,
        },
    }

from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.profile import UserProfile
from app.models.match_preference import MatchPreference
from app.models.match_action import MatchAction
from app.models.match_pair import MatchPair
from app.models.chat_message import ChatMessage
from app.models.user_report import UserReport
from app.models.user_block import UserBlock
from app.schemas.analytics import UserSnapshot, UserStats, MatchContextForLLM
from app.schemas.profile import UserProfileRead
from app.schemas.match_preference import MatchPreferenceRead
from app.schemas.chat import ChatMessageRead

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/me/snapshot", response_model=UserSnapshot)
def get_my_snapshot(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    返回当前用户的整体画像：
    - Profile + Preference
    - 一些基础统计数据（like 数、match 数、消息数、举报数等）
    """
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )
    pref = (
        db.query(MatchPreference)
        .filter(MatchPreference.user_id == current_user.id)
        .first()
    )

    # 统计 likes_sent
    total_likes_sent = (
        db.query(MatchAction)
        .filter(
            MatchAction.actor_user_id == current_user.id,
            MatchAction.action_type.in_(["like", "super_like"]),
        )
        .count()
    )

    # 统计 likes_received
    total_likes_received = (
        db.query(MatchAction)
        .filter(
            MatchAction.target_user_id == current_user.id,
            MatchAction.action_type.in_(["like", "super_like"]),
        )
        .count()
    )

    # 统计 active matches
    total_matches = (
        db.query(MatchPair)
        .filter(
            (MatchPair.user1_id == current_user.id) | (MatchPair.user2_id == current_user.id),
            MatchPair.status == "active",
        )
        .count()
    )

    # 消息统计
    total_messages_sent = (
        db.query(ChatMessage)
        .filter(ChatMessage.sender_user_id == current_user.id)
        .count()
    )

    # 收到的消息：只能通过“配对里但不是我发的”粗略估算
    total_messages_received = (
        db.query(ChatMessage)
        .join(
            MatchPair,
            ChatMessage.match_pair_id == MatchPair.id,
        )
        .filter(
            (MatchPair.user1_id == current_user.id) | (MatchPair.user2_id == current_user.id),
            ChatMessage.sender_user_id != current_user.id,
        )
        .count()
    )

    # 举报：我发起的
    total_reports_made = (
        db.query(UserReport)
        .filter(UserReport.reporter_id == current_user.id)
        .count()
    )

    # 举报：别人举报我
    total_reports_received = (
        db.query(UserReport)
        .filter(UserReport.reported_user_id == current_user.id)
        .count()
    )

    stats = UserStats(
        total_likes_sent=total_likes_sent,
        total_likes_received=total_likes_received,
        total_matches=total_matches,
        total_messages_sent=total_messages_sent,
        total_messages_received=total_messages_received,
        total_reports_made=total_reports_made,
        total_reports_received=total_reports_received,
    )

    return UserSnapshot(
        user_id=current_user.id,
        profile=UserProfileRead.model_validate(profile) if profile else None,
        preference=MatchPreferenceRead.model_validate(pref) if pref else None,
        stats=stats,
    )


@router.get("/me/match-context", response_model=MatchContextForLLM)
def get_match_context_for_llm(
    target_user_id: int = Query(..., description="要分析的对象用户 ID"),
    recent_message_limit: int = Query(30, ge=5, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    给 LLM/AI 使用的上下文接口：
    - 我 & 目标用户的 Profile & Preference
    - 当前是否有拉黑关系
    - 是否有 MatchPair
    - 最近的一段聊天记录
    - 最近一次举报的信息（我对 TA / 别人对 TA）
    """
    if target_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不需要对自己生成配对上下文",
        )

    target_user = (
        db.query(User)
        .filter(User.id == target_user_id, User.is_active == True)  # noqa: E712
        .first()
    )
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="目标用户不存在或不可用",
        )

    # Profiles & Preferences
    me_profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )
    me_pref = (
        db.query(MatchPreference)
        .filter(MatchPreference.user_id == current_user.id)
        .first()
    )

    target_profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == target_user_id)
        .first()
    )
    target_pref = (
        db.query(MatchPreference)
        .filter(MatchPreference.user_id == target_user_id)
        .first()
    )

    # 是否存在拉黑关系
    block = (
        db.query(UserBlock)
        .filter(
            ((UserBlock.blocker_id == current_user.id) & (UserBlock.blocked_id == target_user_id))
            | ((UserBlock.blocker_id == target_user_id) & (UserBlock.blocked_id == current_user.id))
        )
        .first()
    )
    has_block_relation = block is not None

    # 是否存在配对关系
    pair = (
        db.query(MatchPair)
        .filter(
            ((MatchPair.user1_id == current_user.id) & (MatchPair.user2_id == target_user_id))
            | ((MatchPair.user1_id == target_user_id) & (MatchPair.user2_id == current_user.id))
        )
        .first()
    )
    has_match_pair = pair is not None
    match_pair_id = pair.id if pair else None

    # 最近聊天记录（如果有配对）
    recent_messages: List[ChatMessageRead] = []
    if pair:
        msgs = (
            db.query(ChatMessage)
            .filter(ChatMessage.match_pair_id == pair.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(recent_message_limit)
            .all()
        )
        # 倒序改为时间正序，方便 LLM 理解
        msgs = list(reversed(msgs))
        recent_messages = [ChatMessageRead.model_validate(m) for m in msgs]

    # 最近一次：我对 TA 的举报
    last_report_by_me: Optional[str] = None
    me_report = (
        db.query(UserReport)
        .filter(
            UserReport.reporter_id == current_user.id,
            UserReport.reported_user_id == target_user_id,
        )
        .order_by(UserReport.created_at.desc())
        .first()
    )
    if me_report:
        last_report_by_me = f"{me_report.category}: {me_report.description or ''}".strip()

    # 最近一次：别人对 TA 的举报（非必需，更多偏风险）
    last_report_against_target: Optional[str] = None
    other_report = (
        db.query(UserReport)
        .filter(
            UserReport.reporter_id != current_user.id,
            UserReport.reported_user_id == target_user_id,
        )
        .order_by(UserReport.created_at.desc())
        .first()
    )
    if other_report:
        last_report_against_target = f"{other_report.category}: {other_report.description or ''}".strip()

    return MatchContextForLLM(
        me_user_id=current_user.id,
        target_user_id=target_user_id,
        me_profile=UserProfileRead.model_validate(me_profile) if me_profile else None,
        me_preference=MatchPreferenceRead.model_validate(me_pref) if me_pref else None,
        target_profile=UserProfileRead.model_validate(target_profile) if target_profile else None,
        target_preference=MatchPreferenceRead.model_validate(target_pref) if target_pref else None,
        has_block_relation=has_block_relation,
        has_match_pair=has_match_pair,
        match_pair_id=match_pair_id,
        recent_messages=recent_messages,
        last_report_by_me=last_report_by_me,
        last_report_against_target=last_report_against_target,
        generated_at=datetime.utcnow(),
    )

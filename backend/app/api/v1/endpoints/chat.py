from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.match_pair import MatchPair
from app.models.chat_message import ChatMessage
from app.models.profile import UserProfile
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageRead,
    ChatMessageSend,
    ConversationSummary,
)
from app.schemas.profile import UserProfileRead
from app.models.user_block import UserBlock
from app.models.user_report import UserReport
from app.core.risk import log_event, check_rate_limit
from app.core.safety import get_moderation_result

router = APIRouter(prefix="/chats", tags=["chats"])


class ReportRequestInChat(BaseModel):
    reason: Optional[str] = None


def _get_other_user_id(pair: MatchPair, current_user_id: int) -> int:
    return pair.user1_id if pair.user2_id == current_user_id else pair.user2_id


def _ensure_user_in_pair(
    db: Session,
    current_user: User,
    match_pair_id: int,
) -> MatchPair:
    """
    确认：
    - 配对存在
    - 当前用户在这对配对里
    - 配对状态为 active
    - 双方之间不存在拉黑关系
    """
    pair: Optional[MatchPair] = (
        db.query(MatchPair)
        .filter(MatchPair.id == match_pair_id)
        .first()
    )
    if pair is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配对不存在",
        )

    if current_user.id not in (pair.user1_id, pair.user2_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="你不在该配对中，无法访问聊天",
        )

    if pair.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该配对已不可用",
        )

    other_user_id = _get_other_user_id(pair, current_user.id)

    # 检查是否有任意方向的拉黑
    block = (
        db.query(UserBlock)
        .filter(
            ((UserBlock.blocker_id == current_user.id) & (UserBlock.blocked_id == other_user_id))
            | ((UserBlock.blocker_id == other_user_id) & (UserBlock.blocked_id == current_user.id))
        )
        .first()
    )
    if block:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="你或对方已拉黑，当前配对已不可聊天",
        )

    return pair


@router.get("/my-conversations", response_model=List[ConversationSummary])
def get_my_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    获取当前用户所有 active 的配对会话列表：
    - 对方资料
    - 最后一条消息
    - 未读数量
    """
    pairs: List[MatchPair] = (
        db.query(MatchPair)
        .filter(
            (MatchPair.user1_id == current_user.id)
            | (MatchPair.user2_id == current_user.id)
        )
        .filter(MatchPair.status == "active")
        .all()
    )

    results: List[ConversationSummary] = []

    for pair in pairs:
        other_user_id = _get_other_user_id(pair, current_user.id)

        profile: Optional[UserProfile] = (
            db.query(UserProfile)
            .filter(UserProfile.user_id == other_user_id)
            .first()
        )
        if profile is None:
            # 对方没资料，就先跳过
            continue

        profile_read = UserProfileRead.model_validate(profile)

        # 最后一条消息
        last_message: Optional[ChatMessage] = (
            db.query(ChatMessage)
            .filter(ChatMessage.match_pair_id == pair.id)
            .order_by(ChatMessage.created_at.desc())
            .first()
        )

        # 未读数量（对方发的、我还没读的）
        unread_count = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.match_pair_id == pair.id,
                ChatMessage.sender_user_id == other_user_id,
                ChatMessage.is_read == False,  # noqa: E712
            )
            .count()
        )

        preview = None
        last_time = None
        if last_message:
            preview = last_message.content[:50]
            last_time = last_message.created_at

        # 检查拉黑状态
        is_blocked_by_me = (
            db.query(UserBlock)
            .filter(
                UserBlock.blocker_id == current_user.id,
                UserBlock.blocked_id == other_user_id,
            )
            .first()
            is not None
        )
        is_blocked_by_other = (
            db.query(UserBlock)
            .filter(
                UserBlock.blocker_id == other_user_id,
                UserBlock.blocked_id == current_user.id,
            )
            .first()
            is not None
        )

        # 计算年龄
        other_age = None
        if profile.birth_year:
            from datetime import datetime
            other_age = datetime.utcnow().year - profile.birth_year

        results.append(
            ConversationSummary(
                match_pair_id=pair.id,
                other_user_id=other_user_id,
                other_profile=profile_read,
                other_nickname=profile.display_name or None,
                other_age=other_age,
                other_city=profile.current_city,
                other_nationality=profile.nationality,
                last_message_preview=preview,
                last_message_time=last_time,
                last_message=preview,  # 前端期望的字段名
                last_message_at=last_time,  # 前端期望的字段名
                unread_count=unread_count,
                is_blocked_by_me=is_blocked_by_me,
                is_blocked_by_other=is_blocked_by_other,
                status=pair.status,
            )
        )

    return results


@router.get("/{match_pair_id}/messages", response_model=List[ChatMessageRead])
def list_messages(
    match_pair_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    mark_as_read: bool = Query(
        True,
        description="是否将对方发给你的消息标记为已读",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    拉取某个配对下的聊天记录（按时间顺序）。
    """
    pair = _ensure_user_in_pair(db, current_user, match_pair_id)

    msgs: List[ChatMessage] = (
        db.query(ChatMessage)
        .filter(ChatMessage.match_pair_id == match_pair_id)
        .order_by(ChatMessage.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    # 把"对方发给我的"全部标记为已读
    if mark_as_read and msgs:
        db.query(ChatMessage).filter(
            ChatMessage.match_pair_id == match_pair_id,
            ChatMessage.sender_user_id != current_user.id,
            ChatMessage.is_read == False,  # noqa: E712
        ).update({"is_read": True})
        db.commit()

    # 构建返回结果，添加 is_me 字段
    result = []
    for m in msgs:
        msg_dict = ChatMessageRead.model_validate(m).model_dump()
        msg_dict["is_me"] = m.sender_user_id == current_user.id
        msg_dict["from_me"] = m.sender_user_id == current_user.id
        result.append(ChatMessageRead(**msg_dict))
    
    return result


@router.post("/{match_pair_id}/messages", response_model=ChatMessageRead)
def send_message(
    match_pair_id: int,
    msg_body: ChatMessageSend,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    在某个配对会话中发送一条消息。
    只允许配对双方使用。
    """
    pair = _ensure_user_in_pair(db, current_user, match_pair_id)
    
    # 简单长度校验
    content = msg_body.content.strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="消息内容不能为空",
        )
    if len(content) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="消息太长了，请控制在 1000 字以内",
        )
    # AI内容审核
    moderation_result = get_moderation_result(content)
    if moderation_result["should_block"]:
        log_event(
            db,
            user_id=current_user.id,
            event_type="content_blocked",
            match_pair_id=pair.id,
            metadata={
                "reason": moderation_result["message"],
                "categories": moderation_result["categories"],
                "risk_level": moderation_result["risk_level"],
                "content_preview": content[:50],
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"消息包含违规内容：{moderation_result['message']}",
        )
    
    # 限流：10 秒内最多发送 20 条消息
    check_rate_limit(
        db,
        user_id=current_user.id,
        event_type="message_send",
        window_seconds=10,
        max_count=20,
        error_message="你的发言速度有点快，请稍微歇一歇。",
    )

    msg = ChatMessage(
        match_pair_id=pair.id,
        sender_user_id=current_user.id,
        content=content,
        is_read=False,
    )
    db.add(msg)
    db.flush()  # 先拿到 msg.id 再日志

    log_event(
        db,
        user_id=current_user.id,
        event_type="message_send",
        match_pair_id=pair.id,
        message_id=msg.id,
    )

    db.commit()
    db.refresh(msg)

    # 添加 is_me 字段
    msg_dict = ChatMessageRead.model_validate(msg).model_dump()
    msg_dict["is_me"] = True
    msg_dict["from_me"] = True
    return ChatMessageRead(**msg_dict)


@router.post("/{match_pair_id}/block")
def block_user_in_chat(
    match_pair_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    在聊天中拉黑对方。
    前端传入 match_pair_id，后端自动找到对方 user_id。
    """
    # 检查配对是否存在且当前用户在其中
    pair: Optional[MatchPair] = (
        db.query(MatchPair)
        .filter(MatchPair.id == match_pair_id)
        .first()
    )
    if pair is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配对不存在",
        )
    if current_user.id not in (pair.user1_id, pair.user2_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="你不在该配对中",
        )
    
    other_user_id = _get_other_user_id(pair, current_user.id)

    # 检查是否已经拉黑
    existing_block = (
        db.query(UserBlock)
        .filter(
            UserBlock.blocker_id == current_user.id,
            UserBlock.blocked_id == other_user_id,
        )
        .first()
    )

    if not existing_block:
        block = UserBlock(
            blocker_id=current_user.id,
            blocked_id=other_user_id,
            reason="用户在前端主动拉黑",
        )
        db.add(block)
        pair.status = "blocked"
        log_event(
            db,
            user_id=current_user.id,
            event_type="user_block",
            target_user_id=other_user_id,
            match_pair_id=match_pair_id,
        )
        db.commit()

    return {"detail": "已拉黑对方"}


@router.post("/{match_pair_id}/unblock")
def unblock_user_in_chat(
    match_pair_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    在聊天中取消拉黑对方。
    """
    # 检查配对是否存在且当前用户在其中（允许 blocked 状态）
    pair: Optional[MatchPair] = (
        db.query(MatchPair)
        .filter(MatchPair.id == match_pair_id)
        .first()
    )
    if pair is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配对不存在",
        )
    if current_user.id not in (pair.user1_id, pair.user2_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="你不在该配对中",
        )
    
    other_user_id = _get_other_user_id(pair, current_user.id)

    block = (
        db.query(UserBlock)
        .filter(
            UserBlock.blocker_id == current_user.id,
            UserBlock.blocked_id == other_user_id,
        )
        .first()
    )

    if block:
        db.delete(block)
        # 检查是否还有其他方向的拉黑
        remaining_block = (
            db.query(UserBlock)
            .filter(
                ((UserBlock.blocker_id == current_user.id) & (UserBlock.blocked_id == other_user_id))
                | ((UserBlock.blocker_id == other_user_id) & (UserBlock.blocked_id == current_user.id))
            )
            .first()
        )
        if not remaining_block and pair.status == "blocked":
            pair.status = "active"
        log_event(
            db,
            user_id=current_user.id,
            event_type="user_unblock",
            target_user_id=other_user_id,
            match_pair_id=match_pair_id,
        )
        db.commit()

    return {"detail": "已取消拉黑"}


@router.post("/{match_pair_id}/report")
def report_user_in_chat(
    match_pair_id: int,
    body: ReportRequestInChat,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    在聊天中举报对方。
    """
    # 检查配对是否存在且当前用户在其中（允许 blocked 状态）
    pair: Optional[MatchPair] = (
        db.query(MatchPair)
        .filter(MatchPair.id == match_pair_id)
        .first()
    )
    if pair is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配对不存在",
        )
    if current_user.id not in (pair.user1_id, pair.user2_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="你不在该配对中",
        )
    
    other_user_id = _get_other_user_id(pair, current_user.id)

    reason = body.reason or "用户举报"
    
    report = UserReport(
        reporter_id=current_user.id,
        reported_user_id=other_user_id,
        category="other",
        description=reason,
        status="open",
    )
    db.add(report)
    log_event(
        db,
        user_id=current_user.id,
        event_type="user_report",
        target_user_id=other_user_id,
        match_pair_id=match_pair_id,
        metadata={"reason": reason},
    )
    db.commit()
    db.refresh(report)

    return {"detail": "已提交举报", "id": report.id}

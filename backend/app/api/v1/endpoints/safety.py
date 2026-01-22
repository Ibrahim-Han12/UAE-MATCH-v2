from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.user_block import UserBlock
from app.models.user_report import UserReport
from app.models.match_pair import MatchPair
from app.models.chat_message import ChatMessage
from app.models.profile import UserProfile
from app.schemas.safety import (
    BlockUserRequest,
    BlockedUserItem,
    ReportRequest,
    ReportResponse,
)
from app.schemas.profile import UserProfileRead
from app.core.risk import log_event

router = APIRouter(prefix="/safety", tags=["safety"])


def _normalize_pair(user_a_id: int, user_b_id: int) -> tuple[int, int]:
    return (user_a_id, user_b_id) if user_a_id < user_b_id else (user_b_id, user_a_id)


@router.post("/block", response_model=BlockedUserItem)
def block_user(
    body: BlockUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    拉黑某个用户：
    - 后续匹配中不会再看到对方
    - 聊天也会被禁止
    - 现有配对（MatchPair）会标记为 blocked
    """
    if body.target_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没必要拉黑自己",
        )

    target_user = db.query(User).filter(User.id == body.target_user_id).first()
    if target_user is None or not target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="目标用户不存在或不可用",
        )

    block: Optional[UserBlock] = (
        db.query(UserBlock)
        .filter(
            UserBlock.blocker_id == current_user.id,
            UserBlock.blocked_id == body.target_user_id,
        )
        .first()
    )

    if block:
        block.reason = body.reason
    else:
        block = UserBlock(
            blocker_id=current_user.id,
            blocked_id=body.target_user_id,
            reason=body.reason,
        )
        db.add(block)

    # 若已有配对，则标记为 blocked
    user1_id, user2_id = _normalize_pair(current_user.id, body.target_user_id)
    pair: Optional[MatchPair] = (
        db.query(MatchPair)
        .filter(
            MatchPair.user1_id == user1_id,
            MatchPair.user2_id == user2_id,
        )
        .first()
    )
    if pair and pair.status != "blocked":
        pair.status = "blocked"
    log_event(
        db,
        user_id=current_user.id,
        event_type="user_block",
        target_user_id=body.target_user_id,
        match_pair_id=pair.id if "pair" in locals() and pair else None,
        metadata={"reason": body.reason},
    )
    db.commit()
    db.refresh(block)

    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == body.target_user_id)
        .first()
    )
    profile_read = UserProfileRead.model_validate(profile) if profile else None

    return BlockedUserItem(
        blocked_user_id=body.target_user_id,
        reason=block.reason,
        created_at=block.created_at,
        profile=profile_read,
    )


def _normalize_pair(user_a_id: int, user_b_id: int) -> tuple[int, int]:
    return (user_a_id, user_b_id) if user_a_id < user_b_id else (user_b_id, user_a_id)


@router.delete("/block/{target_user_id}")
def unblock_user(
    target_user_id: int = Path(..., description="要取消拉黑的用户 ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    取消拉黑（解除 block）。
    同时，如果双方之间已经没有任何拉黑记录了，并且存在被 blocked 的 MatchPair，
    则将该 MatchPair 恢复为 active，聊天和“我的配对”都会重新生效。
    """
    if target_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没必要给自己解封",
        )

    block = (
        db.query(UserBlock)
        .filter(
            UserBlock.blocker_id == current_user.id,
            UserBlock.blocked_id == target_user_id,
        )
        .first()
    )
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="你并没有拉黑这个用户",
        )

    # 1. 删除当前这条拉黑记录
    db.delete(block)
    db.flush()  # 先不立刻 commit，方便后面再查一遍是否还存在其他方向的拉黑

    # 2. 检查双方之间是否还存在任意方向的拉黑
    remaining_block = (
        db.query(UserBlock)
        .filter(
            ((UserBlock.blocker_id == current_user.id) & (UserBlock.blocked_id == target_user_id))
            | ((UserBlock.blocker_id == target_user_id) & (UserBlock.blocked_id == current_user.id))
        )
        .first()
    )

    # 3. 如果已经没有任何拉黑记录了，则尝试恢复 MatchPair 为 active
    if remaining_block is None:
        user1_id, user2_id = _normalize_pair(current_user.id, target_user_id)
        pair = (
            db.query(MatchPair)
            .filter(
                MatchPair.user1_id == user1_id,
                MatchPair.user2_id == user2_id,
            )
            .first()
        )
        if pair and pair.status == "blocked":
            pair.status = "active"

    log_event(
        db,
        user_id=current_user.id,
        event_type="user_unblock",
        target_user_id=target_user_id,
    )
    db.commit()

    return {"detail": "已取消拉黑，若存在配对关系且未被其他拉黑，则已恢复为可用状态"}



@router.get("/blocked", response_model=List[BlockedUserItem])
def list_blocked_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    查看我拉黑过的所有用户。
    """
    blocks: List[UserBlock] = (
        db.query(UserBlock)
        .filter(UserBlock.blocker_id == current_user.id)
        .all()
    )

    results: List[BlockedUserItem] = []

    for block in blocks:
        profile = (
            db.query(UserProfile)
            .filter(UserProfile.user_id == block.blocked_id)
            .first()
        )
        profile_read = UserProfileRead.model_validate(profile) if profile else None

        results.append(
            BlockedUserItem(
                blocked_user_id=block.blocked_id,
                reason=block.reason,
                created_at=block.created_at,
                profile=profile_read,
            )
        )

    return results


@router.post("/report", response_model=ReportResponse)
def report_user_or_message(
    body: ReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    举报用户 / 某条消息。
    目前只是记录在数据库中，未来可以接管理后台做处理。
    """
    if body.reported_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="暂不支持举报自己",
        )

    target_user = db.query(User).filter(User.id == body.reported_user_id).first()
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="被举报用户不存在",
        )

    if body.reported_message_id is not None:
        msg = (
            db.query(ChatMessage)
            .filter(ChatMessage.id == body.reported_message_id)
            .first()
        )
        if msg is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="被举报的消息不存在",
            )

    if body.category not in ("harassment", "scam", "fake_profile", "spam", "other"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的举报类别",
        )

    report = UserReport(
        reporter_id=current_user.id,
        reported_user_id=body.reported_user_id,
        reported_message_id=body.reported_message_id,
        category=body.category,
        description=body.description,
        status="open",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    log_event(
        db,
        user_id=current_user.id,
        event_type="user_report",
        target_user_id=body.reported_user_id,
        message_id=body.reported_message_id,
        report_id=report.id,
        metadata={"category": body.category},
    )
    db.commit()
    

    return ReportResponse(id=report.id, status=report.status)

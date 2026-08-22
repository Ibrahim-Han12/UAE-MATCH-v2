"""
账号注销（PRD 3.4 四道防线 / BR-004 / DEC-005）。

前两道（入口防误、毕业问询）在前端；本模块承接：
  第三道·双确认：二次 OTP + 手动输入"注销"（端点层校验）
  第四道·冷静期：7 天可撤销（冷静期中不进推荐池——匹配 Stage 0.7 读 cancellation_requested_at）
  到期执行：级联删除（画像/对话/向量记忆/照片/KYC 结论）+ 最小审计（A5：脱敏哈希+时间+原因码+KYC事务ID，留 12 个月）

冲突裁决（hld-m2-design.md §4.3）：S7 封禁用户不可自助注销，仅申诉。
"""
import hashlib
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.risk import log_event
from app.models.user import User
from app.models.profile import UserProfile
from app.models.match_preference import MatchPreference
from app.models.user_photo import UserPhoto
from app.models.user_embedding import UserEmbedding
from app.models.ai_conversation import AIConversation
from app.models.user_ai_memory import UserAIMemory
from app.models.ai_memory_summary import AIMemorySummary
from app.models.user_psych_profile import UserPsychProfile
from app.models.user_comm_profile import UserCommProfile
from app.models.memory_event import MemoryEvent
from app.models.memory_vector import MemoryVector
from app.models.memory_pending_change import MemoryPendingChange
from app.models.phone_otp import PhoneOtp
from app.models.kyc_result import KycResult, AccountDeletionAudit

COOLING_DAYS = 7
CONFIRM_TEXT = "注销"


def request_cancellation(db: Session, user: User, reason_code: Optional[str] = None) -> datetime:
    """进入冷静期。返回执行日期。不 commit。"""
    user.cancellation_requested_at = datetime.utcnow()
    user.cancel_reason_code = reason_code
    log_event(db, user_id=user.id, event_type="cancel_requested",
              metadata={"reason_code": reason_code})
    return user.cancellation_requested_at + timedelta(days=COOLING_DAYS)


def withdraw_cancellation(db: Session, user: User) -> None:
    """冷静期内一键撤销。不 commit。"""
    user.cancellation_requested_at = None
    user.cancel_reason_code = None
    log_event(db, user_id=user.id, event_type="cancel_withdrawn", metadata={})


def cancellation_status(user: User) -> dict:
    if user.cancellation_requested_at is None:
        return {"in_cooling_period": False}
    due = user.cancellation_requested_at.replace(tzinfo=None) + timedelta(days=COOLING_DAYS)
    remaining = max(0, (due - datetime.utcnow()).days)
    return {"in_cooling_period": True, "requested_at": user.cancellation_requested_at,
            "execute_at": due, "days_remaining": remaining}


def execute_cancellation(db: Session, user: User) -> None:
    """
    冷静期到期后的级联删除（由 jobs/process_cancellations 调用）。不 commit。
    删除：画像库、对话记录、向量记忆库、照片（含磁盘文件）、KYC 结论；
    保留：最小审计记录 + users 墓碑行（PII 清空，保外键完整）。
    """
    uid = user.id

    # 审计记录先落（DEC-005）
    last_kyc = (
        db.query(KycResult).filter_by(user_id=uid)
        .order_by(KycResult.created_at.desc()).first()
    )
    contact = user.phone or user.email or f"user-{uid}"
    db.add(AccountDeletionAudit(
        contact_hash=hashlib.sha256(contact.encode()).hexdigest(),
        reason_code=user.cancel_reason_code,
        kyc_transaction_id=last_kyc.transaction_id if last_kyc else None,
        cancelled_at=user.cancellation_requested_at or datetime.utcnow(),
    ))

    # 照片：先删磁盘文件再删记录
    photos = db.query(UserPhoto).filter_by(user_id=uid).all()
    for p in photos:
        try:
            if p.file_path and os.path.exists(p.file_path):
                os.remove(p.file_path)
        except OSError:
            pass
    db.query(UserPhoto).filter_by(user_id=uid).delete()

    # 画像库 + 择偶偏好 + 三层记忆 + 向量库（含 PRD "注销级联删除含向量库"）
    for model in (UserProfile, MatchPreference, UserEmbedding,
                  UserPsychProfile, UserCommProfile,
                  MemoryEvent, MemoryVector, MemoryPendingChange):
        db.query(model).filter_by(user_id=uid).delete()

    # AI 对话与旧记忆
    for model in (AIConversation, UserAIMemory, AIMemorySummary):
        db.query(model).filter_by(user_id=uid).delete()

    # KYC 结论（BannedIdentity 拦截名单不动——A5：违规者哈希永久保留）
    db.query(KycResult).filter_by(user_id=uid).delete()

    # OTP 记录
    if user.phone:
        db.query(PhoneOtp).filter_by(phone=user.phone).delete()

    # users 墓碑化：PII 清空、账号停用（保留行以维持 event_logs 等外键完整）
    user.email = None
    user.phone = None
    user.hashed_password = hashlib.sha256(uuid.uuid4().hex.encode()).hexdigest()
    user.current_session_id = None
    user.phone_verified_at = None
    user.is_active = False
    user.cancellation_requested_at = None

    log_event(db, user_id=uid, event_type="account_deleted", metadata={})


def find_due_cancellations(db: Session):
    """冷静期已到、待执行的用户。"""
    cutoff = datetime.utcnow() - timedelta(days=COOLING_DAYS)
    return (
        db.query(User)
        .filter(User.cancellation_requested_at.isnot(None),
                User.cancellation_requested_at <= cutoff,
                User.is_active.is_(True))
        .all()
    )

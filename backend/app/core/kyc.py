"""
EID 核验服务（BR-107 / hld-m2-design.md §9.2 / DEC-002）。

B1（KYC 服务商 Uqudo/IDWise 类）商务未定——按接口边界 + Mock 适配器实现：
真实 SDK 接入 = 新增 Provider 实现（create_session + webhook 解析），业务流程不动。
合规红线：本模块只处理"结论 + 最小字段 + 事务 ID"，任何证件图像/活体数据不落平台。

流程：process_kyc_result() → 拦截名单/一人多号检查 → 落 kyc_results
     → 年龄/性别带入 user_profiles 并锁定 → try_promote_to_verified()（KYC通过+照片过审 → S2→S3）
"""
import hashlib
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core import state_machine as sm
from app.core.config import settings
from app.core.risk import log_event
from app.models.user import User
from app.models.profile import UserProfile
from app.models.user_photo import UserPhoto
from app.models.kyc_result import KycResult, BannedIdentity

MIN_AGE = 18  # 18+ 硬门槛（PRD 14.2），在核验环节执行


def hash_eid(eid_number: str) -> str:
    return hashlib.sha256(eid_number.strip().encode()).hexdigest()


def is_mock() -> bool:
    return getattr(settings, "KYC_PROVIDER", "mock") == "mock"


def create_session(user: User) -> dict:
    """发起核验会话。真实服务商返回 SDK 会话参数；mock 返回本地事务 ID。"""
    if is_mock():
        return {"provider": "mock", "transaction_id": f"mock-{uuid.uuid4().hex[:16]}",
                "note": "开发模式：用 /verification/kyc/mock-complete 模拟服务商回传"}
    raise RuntimeError(f"未知 KYC provider: {settings.KYC_PROVIDER}（B1 供应商确定后在此接入）")


def process_kyc_result(
    db: Session, user: User, *,
    provider: str, transaction_id: str, result: str,
    full_name: Optional[str], birth_date: Optional[date],
    gender: Optional[str], document_expiry: Optional[date],
    eid_number: Optional[str],
) -> dict:
    """
    处理服务商回传结论。返回 {accepted, reason, promoted}。不 commit。
    """
    eid_h = hash_eid(eid_number) if eid_number else None

    # 1) 永久拦截名单（封禁者换号重注册，PRD 3.5）
    if eid_h and db.query(BannedIdentity).filter_by(eid_hash=eid_h).first():
        log_event(db, user_id=user.id, event_type="kyc_blocked_banned_identity",
                  metadata={"transaction_id": transaction_id})
        return {"accepted": False, "reason": "该身份已被平台永久限制", "promoted": False}

    # 2) 一人多号：同一 EID 已绑定其他账号
    if eid_h:
        dup = (
            db.query(KycResult)
            .filter(KycResult.eid_hash == eid_h, KycResult.result == "passed",
                    KycResult.user_id != user.id)
            .first()
        )
        if dup:
            log_event(db, user_id=user.id, event_type="kyc_blocked_duplicate_identity",
                      metadata={"transaction_id": transaction_id})
            return {"accepted": False, "reason": "该身份已绑定其他账号", "promoted": False}

    # 3) 18+ 硬门槛
    if result == "passed" and birth_date:
        age = (date.today() - birth_date).days // 365
        if age < MIN_AGE:
            result = "failed"
            log_event(db, user_id=user.id, event_type="kyc_rejected_underage",
                      metadata={"transaction_id": transaction_id})

    rec = KycResult(
        user_id=user.id, provider=provider, transaction_id=transaction_id,
        result=result, full_name_verified=full_name, birth_date=birth_date,
        gender=gender, document_expiry=document_expiry, eid_hash=eid_h,
    )
    db.add(rec)

    promoted = False
    if result == "passed":
        # 年龄/性别自核验值带入并锁定（BR-107；资料页不可改，锁定由 profile 端点执行）
        profile = db.query(UserProfile).filter_by(user_id=user.id).first()
        if profile is None:
            profile = UserProfile(user_id=user.id)
            db.add(profile)
        if birth_date:
            profile.birth_year = birth_date.year
        if gender:
            profile.gender = gender
        log_event(db, user_id=user.id, event_type="kyc_passed",
                  metadata={"provider": provider, "transaction_id": transaction_id})
        promoted = try_promote_to_verified(db, user)
    elif result == "failed":
        log_event(db, user_id=user.id, event_type="kyc_failed",
                  metadata={"provider": provider, "transaction_id": transaction_id})

    return {"accepted": True, "reason": result, "promoted": promoted}


def has_passed_kyc(db: Session, user_id: int) -> bool:
    return db.query(KycResult).filter_by(user_id=user_id, result="passed").first() is not None


def has_approved_photo(db: Session, user_id: int) -> bool:
    return db.query(UserPhoto).filter_by(user_id=user_id, status="approved").first() is not None


def try_promote_to_verified(db: Session, user: User) -> bool:
    """
    验证完成判定：KYC 通过 + 至少一张照片人工过审 → S2→S3（进入候补池）。
    照片过审回调处（admin 审核）与 KYC 回传处都调用本函数，谁后到谁触发。
    """
    db.flush()  # autoflush=False：先落同事务内刚写入的 KYC/照片行，否则下面的查询看不见
    if sm.effective_state(user) != sm.S2:
        return False
    if has_passed_kyc(db, user.id) and has_approved_photo(db, user.id):
        sm.transition(db, user, sm.S3, reason="verification_passed")
        return True
    return False

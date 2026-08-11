"""
用户状态机（PRD 2.2 / HLD §4）。

S0 访客(无账号,不落库) → S1 已注册 → S2 深访完成 → S3 已验证候补 → S4 付费会员
→ S5 配对中；S6 已毕业；S7 封禁。
S1→S2→S3→S4 为"信任三道闸"（深访/核验/付费），顺序不可跳过。

本模块是修改 users.status 的唯一合法入口：一切跃迁经 transition() 校验 + 留痕。
"""
from typing import Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_state_transition import UserStateTransition

S1, S2, S3, S4, S5, S6, S7 = "S1", "S2", "S3", "S4", "S5", "S6", "S7"

ALL_STATES = (S1, S2, S3, S4, S5, S6, S7)

# 线性序（用于 require_state 门禁比较）；S6/S7 不参与线性比较
STATE_ORDER = {S1: 1, S2: 2, S3: 3, S4: 4, S5: 5}

# 合法跃迁：(from, to) → 语义
ALLOWED_TRANSITIONS = {
    (S1, S2): "interview_completed",       # 必采字段 100%
    (S2, S3): "verification_passed",       # EID 核验 + 照片交叉比对通过
    (S3, S2): "verification_revoked",      # 核验徽章被撤销（PRD 5.4-⑮）
    (S3, S4): "subscribed",                # 订阅生效
    (S4, S3): "subscription_lapsed",       # 订阅失效降回候补（PRD 5.4-⑭）
    (S4, S5): "match_created",             # 进入活跃配对
    (S5, S4): "match_archived",            # 配对归档，恢复推荐（PRD 5.4-⑫）
    (S5, S6): "graduated",                 # 荣誉毕业
    (S4, S6): "graduated",
    (S6, S3): "reactivated",               # 12 个月内复访（PRD 10.3）
    (S7, S3): "unbanned",                  # 申诉成功（仅 admin）
}
# 任意状态可被封禁
for _s in (S1, S2, S3, S4, S5, S6):
    ALLOWED_TRANSITIONS[(_s, S7)] = "banned"

# 门禁未过时告诉前端该去哪道闸（结构化响应用）
GATE_FOR_REQUIRED = {S2: "interview", S3: "verification", S4: "payment"}


def effective_state(user: User) -> str:
    """归一化：兼容历史值 'active'（视为 S1）。"""
    s = user.status or S1
    return s if s in ALL_STATES else S1


def can_transition(from_state: str, to_state: str) -> bool:
    return (from_state, to_state) in ALLOWED_TRANSITIONS


def transition(
    db: Session, user: User, to_state: str,
    reason: Optional[str] = None, source: str = "system",
) -> UserStateTransition:
    """
    执行状态跃迁：校验合法性 → 更新 users.status → 写转移留痕。
    不 commit，由调用方提交。非法跃迁抛 ValueError（编程错误，不是用户错误）。
    """
    from_state = effective_state(user)
    if to_state not in ALL_STATES:
        raise ValueError(f"未知状态: {to_state}")
    if from_state == to_state:
        raise ValueError(f"状态未变化: {from_state}")
    if not can_transition(from_state, to_state):
        raise ValueError(f"非法跃迁: {from_state} → {to_state}（三道闸顺序不可跳过）")

    user.status = to_state
    rec = UserStateTransition(
        user_id=user.id,
        from_state=from_state,
        to_state=to_state,
        reason=reason or ALLOWED_TRANSITIONS[(from_state, to_state)],
        source=source,
    )
    db.add(rec)
    return rec


def meets_min_state(user: User, min_state: str) -> bool:
    """线性门禁判断：S7 一律不过；S6 仅当要求 ≤S1 时过（毕业休眠仅保留基础访问）。"""
    current = effective_state(user)
    if current == S7:
        return False
    if current == S6:
        return STATE_ORDER.get(min_state, 99) <= STATE_ORDER[S1]
    return STATE_ORDER.get(current, 0) >= STATE_ORDER.get(min_state, 99)


def gate_error(user: User, min_state: str) -> HTTPException:
    """构造结构化"闸门未过"响应，前端据此导流（HLD §4.2）。"""
    current = effective_state(user)
    if current == S7:
        return HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail={"code": "banned", "message": "账号已被封禁，仅可申诉"},
        )
    return HTTPException(
        status_code=http_status.HTTP_403_FORBIDDEN,
        detail={
            "code": "gate_blocked",
            "current_state": current,
            "required_state": min_state,
            "gate": GATE_FOR_REQUIRED.get(min_state, "unknown"),
            "message": "需要先完成前置步骤",
        },
    )

"""
记忆写入原语（BR-202 / hld-m2-design.md §5.3 写管线）。

三层落库：
  事实层  → user_psych_profile（心理测评区块；user_profiles/match_preferences 扩展属 BR-001 / BR-201）
  事件层  → memory_events（婚恋旅程时间线，只追加）
  情感层  → user_comm_profile（结构化摘要）+ memory_vectors（语义向量）

约定：与全仓一致，本模块不 commit，由调用方提交。
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.ai.gateway import get_ai_gateway
from app.models.user_psych_profile import UserPsychProfile
from app.models.user_comm_profile import UserCommProfile
from app.models.memory_event import MemoryEvent
from app.models.memory_vector import MemoryVector

# 允许写入 psych profile 的字段白名单（防抽取器输出意外键）
PSYCH_FIELDS = {
    "big_five_openness", "big_five_conscientiousness", "big_five_extraversion",
    "big_five_agreeableness", "big_five_neuroticism",
    "attachment_style", "conflict_style", "family_role_expectation",
    "money_view", "mbti",
}
COMM_FIELDS = {"avoid_topics", "excite_topics", "answer_style", "emotion_pattern"}

VALID_NAMESPACES = ("profile", "emotion", "narrative")


def upsert_psych_profile(
    db: Session, user_id: int, values: Dict[str, Any],
    confidence: Optional[Dict[str, str]] = None,
) -> UserPsychProfile:
    """事实层·心理测评 upsert。values 只接受白名单字段；confidence 合并进 field_confidence。"""
    row = db.query(UserPsychProfile).filter_by(user_id=user_id).first()
    if row is None:
        row = UserPsychProfile(user_id=user_id)
        db.add(row)
        db.flush()
    for k, v in values.items():
        if k in PSYCH_FIELDS and v is not None:
            setattr(row, k, v)
    if confidence:
        merged = dict(row.field_confidence or {})
        merged.update(confidence)
        row.field_confidence = merged
    return row


def upsert_comm_profile(db: Session, user_id: int, values: Dict[str, Any]) -> UserCommProfile:
    """情感层·沟通画像 upsert（G1/G2/G3 + 情绪模式）。列表型字段做去重合并而非覆盖。"""
    row = db.query(UserCommProfile).filter_by(user_id=user_id).first()
    if row is None:
        row = UserCommProfile(user_id=user_id)
        db.add(row)
        db.flush()
    for k, v in values.items():
        if k not in COMM_FIELDS or v is None:
            continue
        if k in ("avoid_topics", "excite_topics") and isinstance(v, list):
            existing = list(getattr(row, k) or [])
            for item in v:
                if item not in existing:
                    existing.append(item)
            setattr(row, k, existing)
        else:
            setattr(row, k, v)
    return row


def append_event(
    db: Session, user_id: int, event_type: str,
    payload: Optional[Dict[str, Any]] = None, source: str = "system",
) -> MemoryEvent:
    """事件层·时间线追加（推荐/反馈/互聊摘要/约会/复盘/画像变更……）。"""
    ev = MemoryEvent(user_id=user_id, event_type=event_type, payload=payload, source=source)
    db.add(ev)
    return ev


def add_vector(
    db: Session, user_id: int, namespace: str, text: str,
    scene: str = "memory_vectorize",
) -> MemoryVector:
    """向量记忆写入：调 gateway.embed（自动计量），落 memory_vectors。"""
    if namespace not in VALID_NAMESPACES:
        raise ValueError(f"非法 namespace: {namespace}，须为 {VALID_NAMESPACES}")
    vector = get_ai_gateway().embed(db, user_id=user_id, text=text, scene=scene)
    row = MemoryVector(
        user_id=user_id, namespace=namespace,
        vector=vector, dimension=len(vector), source_text=text,
    )
    db.add(row)
    return row

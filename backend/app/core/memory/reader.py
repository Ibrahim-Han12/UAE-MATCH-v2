"""
记忆读取原语（BR-202 / HLD §5.3 读管线）。

小缘每轮注入 = 系统 prompt(人格) + 结构化画像摘要(build_profile_summary)
             + 向量检索 top-3 相关记忆(retrieve_memories, CLAUDE §4 成本纪律)。

D2 决策：应用层余弦（向量 JSON 列存，内存 Top-K），v1 量级不设向量索引。
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.ai.gateway import get_ai_gateway
from app.core.embedding_service import get_embedding_service
from app.models.profile import UserProfile
from app.models.match_preference import MatchPreference
from app.models.user_psych_profile import UserPsychProfile
from app.models.user_comm_profile import UserCommProfile
from app.models.memory_event import MemoryEvent
from app.models.memory_vector import MemoryVector

TOP_K = 3  # 记忆注入 top-3（CLAUDE §4）


def retrieve_memories(
    db: Session, user_id: int, query_text: str,
    namespaces: Optional[List[str]] = None, top_k: int = TOP_K,
    scene: str = "memory_retrieve",
) -> List[Dict[str, Any]]:
    """向量检索：query 向量化后与该用户记忆向量做余弦，返回 top_k 条。"""
    q = db.query(MemoryVector).filter(MemoryVector.user_id == user_id)
    if namespaces:
        q = q.filter(MemoryVector.namespace.in_(namespaces))
    rows = q.all()
    if not rows:
        return []

    query_vec = get_ai_gateway().embed(db, user_id=user_id, text=query_text, scene=scene)
    svc = get_embedding_service()
    scored = []
    for r in rows:
        try:
            sim = svc.cosine_similarity(query_vec, r.vector)
        except Exception:
            continue
        scored.append({"id": r.id, "namespace": r.namespace, "text": r.source_text,
                       "similarity": round(sim, 4), "created_at": r.created_at})
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]


def recent_events(db: Session, user_id: int, limit: int = 5) -> List[MemoryEvent]:
    """最近的婚恋旅程事件（时间线尾部）。"""
    return (
        db.query(MemoryEvent)
        .filter(MemoryEvent.user_id == user_id)
        .order_by(MemoryEvent.occurred_at.desc())
        .limit(limit)
        .all()
    )


def build_profile_summary(db: Session, user_id: int, max_events: int = 3) -> str:
    """
    结构化画像摘要（注入 prompt 用，非 LLM 生成——零成本、确定性）。
    汇集：基础资料 + 择偶偏好 + 心理测评 + 沟通偏好 + 最近事件。
    取代旧滚动摘要的 memory_summary 注入位。
    """
    parts: List[str] = []

    p = db.query(UserProfile).filter_by(user_id=user_id).first()
    if p:
        basics = []
        if p.display_name: basics.append(f"称呼:{p.display_name}")
        if p.birth_year: basics.append(f"出生年:{p.birth_year}")
        if p.gender: basics.append(f"性别:{p.gender}")
        if p.current_city: basics.append(f"城市:{p.current_city}")
        if p.occupation: basics.append(f"职业:{p.occupation}")
        if p.education_level: basics.append(f"学历:{p.education_level}")
        marital = {"never_married": "未婚", "divorced": "离异", "widowed": "丧偶"}.get(p.marital_history or "")
        if marital: basics.append(f"婚史:{marital}")
        if p.has_children: basics.append(f"孩子:{'有' if p.has_children.get('has') == 'yes' else '无'}")
        if basics:
            parts.append("【基础】" + "；".join(basics))
        if p.bio:
            parts.append(f"【自述】{p.bio[:120]}")

    pref = db.query(MatchPreference).filter_by(user_id=user_id).first()
    if pref:
        wants = []
        if pref.preferred_gender: wants.append(f"期望性别:{pref.preferred_gender}")
        if pref.min_age or pref.max_age: wants.append(f"年龄:{pref.min_age or '?'}-{pref.max_age or '?'}")
        if pref.marriage_timeline: wants.append(f"结婚时间线:{pref.marriage_timeline}")
        if pref.want_children: wants.append(f"子女:{pref.want_children}")
        if pref.plan_settle_in_uae is not None: wants.append(f"UAE定居:{pref.plan_settle_in_uae}")
        if wants:
            parts.append("【择偶】" + "；".join(wants))

    psych = db.query(UserPsychProfile).filter_by(user_id=user_id).first()
    if psych:
        traits = []
        if psych.attachment_style: traits.append(f"依恋:{psych.attachment_style}")
        if psych.conflict_style: traits.append(f"冲突风格:{psych.conflict_style}")
        if psych.money_view: traits.append(f"金钱观:{psych.money_view}")
        if psych.mbti: traits.append(f"MBTI:{psych.mbti}")
        if traits:
            parts.append("【心理】" + "；".join(traits))

    comm = db.query(UserCommProfile).filter_by(user_id=user_id).first()
    if comm:
        notes = []
        if comm.avoid_topics: notes.append(f"回避话题:{','.join(comm.avoid_topics[:5])}")
        if comm.emotion_pattern: notes.append(f"情绪模式:{comm.emotion_pattern[:60]}")
        if comm.answer_style: notes.append(f"回答风格:{comm.answer_style}")
        if notes:
            parts.append("【沟通】" + "；".join(notes))

    evs = recent_events(db, user_id, limit=max_events)
    if evs:
        lines = [f"{e.occurred_at.strftime('%m-%d') if e.occurred_at else '?'} {e.event_type}" for e in evs]
        parts.append("【近期】" + "；".join(lines))

    return "\n".join(parts) if parts else ""

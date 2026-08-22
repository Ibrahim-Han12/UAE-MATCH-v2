"""interview_state 读写原语。约定：本模块不 commit，由调用方提交。"""
from datetime import datetime, timezone
from typing import Set

from sqlalchemy.orm import Session

from app.core.dialogue import acts
from app.models.interview_state import InterviewState


def get_or_create(db: Session, user_id: int) -> InterviewState:
    st = db.query(InterviewState).filter_by(user_id=user_id).first()
    if st is None:
        st = InterviewState(user_id=user_id, current_act="act1",
                            act_entered_at=datetime.now(timezone.utc),
                            declined_fields=[], refusal_counts={})
        db.add(st)
        db.flush()
    return st


def declined_set(st: InterviewState) -> Set[str]:
    return set(st.declined_fields or [])


def mark_declined(db: Session, st: InterviewState, field_id: str) -> None:
    current = list(st.declined_fields or [])
    if field_id not in current:
        current.append(field_id)
        st.declined_fields = current
        db.add(st)


def refusal_count(st: InterviewState, field_id: str) -> int:
    return int((st.refusal_counts or {}).get(field_id, 0))


def bump_refusal(db: Session, st: InterviewState, field_id: str) -> int:
    counts = dict(st.refusal_counts or {})
    counts[field_id] = int(counts.get(field_id, 0)) + 1
    st.refusal_counts = counts
    db.add(st)
    return counts[field_id]


def sync_act(db: Session, st: InterviewState, handled: Set[str]) -> str:
    """按已处理字段重算当前幕；只在真正切幕时刷新 act_entered_at。"""
    act = acts.current_act(handled)
    if act != st.current_act:
        st.current_act = act
        st.act_entered_at = datetime.now(timezone.utc)
        db.add(st)
    return act

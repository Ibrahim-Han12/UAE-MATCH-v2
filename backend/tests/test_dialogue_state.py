"""interview_state 读写原语（DEC-032：状态机语义清晰、可查询）。

db fixture 见 tests/conftest.py（内存 SQLite + 自动登记全部模型）。
"""
from app.core.dialogue import acts, state


def test_get_or_create_is_idempotent(db):
    a = state.get_or_create(db, user_id=1)
    db.flush()
    b = state.get_or_create(db, user_id=1)

    assert a.id == b.id
    assert a.current_act == "act1"


def test_mark_declined_accumulates(db):
    st = state.get_or_create(db, user_id=1)

    state.mark_declined(db, st, "A7")
    state.mark_declined(db, st, "A9")
    state.mark_declined(db, st, "A7")   # 重复不应产生重复项

    assert state.declined_set(st) == {"A7", "A9"}


def test_bump_refusal_returns_running_count(db):
    st = state.get_or_create(db, user_id=1)

    assert state.bump_refusal(db, st, "C1") == 1
    assert state.bump_refusal(db, st, "C1") == 2
    assert state.refusal_count(st, "C5") == 0


def test_sync_act_advances_and_stamps_entry_time(db):
    st = state.get_or_create(db, user_id=1)
    first_stamp = st.act_entered_at

    handled = set(acts.act_field_ids("act1"))
    assert state.sync_act(db, st, handled) == "act2"
    assert st.current_act == "act2"
    assert st.act_entered_at != first_stamp

    # 幕不变时不重新盖时间戳（否则"幕停留时长"指标失真）
    stamp_in_act2 = st.act_entered_at
    assert state.sync_act(db, st, handled) == "act2"
    assert st.act_entered_at == stamp_in_act2

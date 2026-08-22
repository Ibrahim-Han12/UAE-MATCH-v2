"""幕状态机与地板字段（DEC-033）。"""
from app.core.interview import config as ic


def test_floor_fields_come_from_schema_not_code():
    """DEC-033 的三个地板字段必须由 Schema 的 refusal_floor 标记推导，不得硬编码。"""
    assert ic.floor_field_ids() == {"C1", "C5", "B3"}

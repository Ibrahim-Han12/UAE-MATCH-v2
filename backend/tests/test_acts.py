"""幕状态机与地板字段（DEC-033）。"""
from app.core.interview import config as ic


def test_floor_fields_come_from_schema_not_code():
    """DEC-033 的三个地板字段必须由 Schema 的 refusal_floor 标记推导，不得硬编码。"""
    assert ic.floor_field_ids() == {"C1", "C5", "B3"}


from app.core.dialogue import acts


def test_act_field_ids_are_derived_from_schema_categories():
    """幕字段集从 Schema 的 category 推导：act1=A/B、act2=C、act3=D，只取必采访谈字段。"""
    assert acts.act_field_ids("act2") == ["C1", "C2", "C3", "C4", "C5"]
    assert acts.act_field_ids("act3") == ["D1", "D2", "D3", "D4"]
    # A1/A2/A3 来源是 eid/declaration，不由访谈采集，不该进 act1
    act1 = acts.act_field_ids("act1")
    assert "A4" in act1 and "B6" in act1
    assert "A1" not in act1 and "A2" not in act1 and "A3" not in act1


def test_current_act_is_first_incomplete_act():
    """A+B 全部处理完才进 act2；C 全部处理完才进 act3。"""
    assert acts.current_act(set()) == "act1"

    act1_done = set(acts.act_field_ids("act1"))
    assert acts.current_act(act1_done) == "act2"

    act2_done = act1_done | set(acts.act_field_ids("act2"))
    assert acts.current_act(act2_done) == "act3"


def test_declined_counts_as_handled_for_act_exit():
    """DEC-028：declined 视为已处理，否则拒答一个字段就永远卡在这一幕。"""
    handled = set(acts.act_field_ids("act1"))
    assert acts.act_complete("act1", handled) is True

    partial = handled - {"A4"}
    assert acts.act_complete("act1", partial) is False


def test_next_target_stays_within_current_act():
    """幕内按 Schema 顺序取缺口；不得跨幕取。"""
    act1_done = set(acts.act_field_ids("act1"))
    target = acts.next_target(act1_done, sensitive_ok=True)

    assert target is not None
    assert target["id"] == "C1"


def test_next_target_skips_high_sensitivity_without_consent():
    """未获敏感授权时跳过 sensitivity: high 字段（沿用既有行为）。"""
    act1_done = set(acts.act_field_ids("act1"))
    act2_done = act1_done | set(acts.act_field_ids("act2"))
    target = acts.next_target(act2_done, sensitive_ok=False)

    assert target is None or target.get("sensitivity") != "high"


def test_extraction_scope_covers_adjacent_acts():
    """抽取范围 = 当前幕 + 前后相邻幕。

    只取当前幕会丢跨幕答案（实测：用户在 act1 就说了择偶条件，C1/C2 全丢）；
    每轮取全 Schema 又让 prompt 变长、命中散。相邻幕是二者的平衡。
    """
    scope = acts.extraction_scope("act1")
    assert "A4" in scope and "B1" in scope      # 当前幕
    assert "C1" in scope and "C5" in scope      # 下一幕
    assert "D1" not in scope                    # 隔一幕不进，控成本

    scope2 = acts.extraction_scope("act2")
    assert "A4" in scope2 and "C1" in scope2 and "D1" in scope2   # 前后都在

    scope3 = acts.extraction_scope("act3")
    assert "C1" in scope3 and "D1" in scope3
    assert "A4" not in scope3

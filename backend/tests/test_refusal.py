"""字段级拒答决策（DEC-028 豁免 + DEC-033 地板线）。"""
from app.core.dialogue import output_check as oc
from app.core.dialogue import refusal
from app.core.interview import config as ic


def test_normal_field_first_refusal_triggers_rephrase():
    assert refusal.decide("A7", prior_refusals=0) == refusal.RETRY


def test_normal_field_second_refusal_is_declined():
    """DEC-028：重试一次后不再问，标 declined 并视为已处理。"""
    assert refusal.decide("A7", prior_refusals=1) == refusal.DECLINE


def test_floor_field_also_gets_exactly_one_rephrase():
    assert refusal.decide("C1", prior_refusals=0) == refusal.RETRY


def test_floor_field_second_refusal_blocks_instead_of_declining():
    """DEC-033：地板字段不允许 declined，否则 25 项全拒也能过闸。"""
    for fid in sorted(ic.floor_field_ids()):
        assert refusal.decide(fid, prior_refusals=1) == refusal.BLOCK, fid


def test_floor_and_normal_field_decisions_must_diverge():
    """验收 #12 的单元层对应：同样是二次拒答，行为必须分叉。"""
    assert refusal.decide("A7", prior_refusals=1) != refusal.decide("B3", prior_refusals=1)


def test_block_instruction_states_impact_without_pressure():
    field = ic.field_by_id("C1")
    text = refusal.instruction_for(refusal.BLOCK, field)

    assert "没法" in text or "无法" in text
    for pressure in ("必须", "请您配合", "否则无法继续使用"):
        assert pressure not in text


def test_retry_instruction_demands_one_different_phrasing():
    field = ic.field_by_id("A7")
    text = refusal.instruction_for(refusal.RETRY, field)

    assert "换一种" in text
    assert "只" in text or "一次" in text


def test_decline_instruction_drops_topic_permanently():
    field = ic.field_by_id("A7")
    text = refusal.instruction_for(refusal.DECLINE, field)

    assert "跳过" in text or "翻篇" in text
    assert "不再" in text


def test_refusal_instructions_are_themselves_clean():
    """指令会进 prompt，若含"您/请问"模型会照抄。"""
    for decision in (refusal.RETRY, refusal.DECLINE, refusal.BLOCK):
        text = refusal.instruction_for(decision, ic.field_by_id("C1"))
        assert oc.check(text).has_hard is False, f"{decision} 指令含禁用表达"

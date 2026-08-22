"""D 类抽取必须携带行为编码规则（hld-dialogue-system.md §4）。"""
from app.core.interview import config as ic
from app.core.memory import extractor


def test_d_class_extraction_contract_includes_coding_rubric():
    d1 = ic.field_by_id("D1")
    prompt = extractor._build_extraction_prompt("用户: 他不回我我就一直看手机", [d1])

    rubric = ic.bank_entry_for("D1")["coding_rubric"]
    assert rubric["anxious"] in prompt
    assert rubric["secure"] in prompt


def test_d_class_extraction_requires_unclear_when_uncertain():
    """强行编码比留空更糟：会污染匹配算法的心理维度。"""
    d2 = ic.field_by_id("D2")
    prompt = extractor._build_extraction_prompt("用户: 看情况吧", [d2])

    # 不能只断言子串 "unclear"——它是 D1 枚举值 mixed_unclear 的子串，会假通过
    assert "不确定就输出 unclear" in prompt


def test_non_d_class_field_gets_no_rubric():
    """成本纪律：A 类事实字段没有编码规则，不该被撑长。"""
    a7 = ic.field_by_id("A7")
    prompt = extractor._build_extraction_prompt("用户: 月薪三万多", [a7])

    assert "行为编码" not in prompt

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


def test_extraction_prompt_forbids_inferring_unmentioned_fields():
    """实测缺陷：用户从没提去留规划，库里却写了 B1=undecided。

    「未提及不输出」原本只在开头说了一句，模型仍然推断了。必须点名最容易被推断的
    形态：不确定、没想好、undecided 这类"看起来无害"的默认值——它们会直接污染
    匹配算法的硬约束（B1 喂 R6 去留冲突过滤）。
    """
    b1 = ic.field_by_id("B1")
    prompt = extractor._build_extraction_prompt("用户: 我在迪拜做金融，硕士毕业", [b1])

    assert "宁缺勿猜" in prompt
    assert "undecided" in prompt          # 点名这类默认值不许当抽取结果

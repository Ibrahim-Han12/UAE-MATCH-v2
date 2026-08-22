"""编排器的幕交互模式指令与意图指令。

这些文本都会拼进 prompt，所以除了内容断言，每条都必须自身过语气闸——
指令里出现敬语或客服腔，模型会照抄，我们自己就成了客服腔的来源。
"""
from app.core.dialogue import output_check as oc
from app.core.interview import orchestrator


def test_act2_instruction_announces_stage_and_bans_mechanical_transitions():
    text = orchestrator.act_instruction("act2")

    assert "择偶条件" in text
    assert "机械过渡" in text or "好的" in text
    assert "弹性" in text


def test_act3_instruction_demands_casual_tone_without_naming_banned_words():
    """act3 指令要传达"别像测评"，但**不能写出**那些词。

    在指令里点名"评估/测试/量表"等于给模型做近距离示范——与 Voice Guide 的 ❌ 列
    不能进 prompt 同理。禁止哪些词由 voice_rules.yaml 的 assessment_words 组在
    输出侧兜住，指令只负责正面描述该用的口吻。
    """
    text = orchestrator.act_instruction("act3")

    assert "情境" in text or "场景" in text
    assert "闲聊" in text or "日常" in text
    for banned in ("评估", "测试", "量表", "题目", "性格分析"):
        assert banned not in text


def test_all_act_instructions_are_themselves_clean():
    for act in ("act1", "act2", "act3"):
        result = oc.check(orchestrator.act_instruction(act))
        assert result.has_hard is False, f"{act} 指令含禁用表达：{result.violations}"


def test_intent_routing_covers_hld_table():
    """HLD §2 的路由表里由指令承载的三种意图必须都有指令。"""
    for kind in ("correction", "ask_ai", "smalltalk"):
        assert orchestrator.intent_instruction(kind)


def test_intent_instructions_are_themselves_clean():
    for kind in ("correction", "ask_ai", "smalltalk"):
        result = oc.check(orchestrator.intent_instruction(kind))
        assert result.has_hard is False, f"{kind} 指令含禁用表达：{result.violations}"

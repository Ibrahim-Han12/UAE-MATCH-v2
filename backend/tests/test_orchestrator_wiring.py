"""编排器接线的集成测试：意图 → 幕 → 拒答 → 指令注入 走一遍真实通路。

用假网关替掉三处模型调用（意图分类、抽取、生成），其余全用真实代码与真实配置。
这是唯一能证明"接线正确"的测试——单元测试只能证明各零件正确。
"""
import json

import pytest

from app.core.dialogue import state as dstate
from app.core.interview import orchestrator
from app.models.user import User


class RecordingGateway:
    """按 task 分派：意图分类返回指定意图，抽取返回空，生成返回干净回复。"""

    def __init__(self, intent_kind="answer", intent_field=None):
        self.intent_kind = intent_kind
        self.intent_field = intent_field
        self.calls = []          # [(task, messages)]

    def chat(self, db, *, user_id, task, messages, **kw):
        self.calls.append((task, messages))
        if task == "intent_classify":
            payload = {"intent": self.intent_kind, "field_id": self.intent_field,
                       "confidence": 0.95}
            content = json.dumps(payload, ensure_ascii=False)
        elif task == "memory_extraction":
            content = "{}"
        else:
            content = "来了？我是小缘。你来迪拜几年了？"
        return {"content": content, "tokens_used": 10, "tokens_in": 5, "tokens_out": 5,
                "cache_hit": False, "model": "fake", "cost_usd": 0.0, "tier": "mini",
                "budget_degraded": False}

    def generation_prompt(self) -> str:
        """最后一次生成调用注入的全部 system 文本。"""
        for task, messages in reversed(self.calls):
            if task == "deep_interview":
                return "\n".join(m["content"] for m in messages if m["role"] == "system")
        return ""


@pytest.fixture()
def user(db):
    u = User(email="t@example.com", hashed_password="x", status="S1", is_active=True)
    db.add(u)
    db.flush()
    return u


def _install(monkeypatch, gw):
    """三处模型调用点都要换掉，否则会真的打网络。"""
    from app.core.dialogue import intent as intent_mod
    from app.core.memory import extractor as extractor_mod

    for mod in (orchestrator, intent_mod, extractor_mod):
        monkeypatch.setattr(mod, "get_ai_gateway", lambda: gw)


def test_act1_turn_injects_act_instruction_and_a_target(monkeypatch, db, user):
    """默认路径：注入本幕模式 + 目标字段的问法建议。"""
    gw = RecordingGateway(intent_kind="answer")
    _install(monkeypatch, gw)

    result = orchestrator.handle_message(db, user, "我来迪拜六年了", sensitive_ok=True)

    assert result["crisis"] is False
    prompt = gw.generation_prompt()
    assert "【本幕模式·自由对话】" in prompt
    assert "【本轮建议】" in prompt
    # 新用户从 act1 起
    assert dstate.get_or_create(db, user.id).current_act == "act1"


def test_floor_field_refused_twice_blocks_and_is_not_declined(monkeypatch, db, user):
    """DEC-033 的核心行为：地板字段拒两次 → block，且绝不进 declined。"""
    gw = RecordingGateway(intent_kind="refusal_field", intent_field="C1")
    _install(monkeypatch, gw)

    orchestrator.handle_message(db, user, "没想过", sensitive_ok=True)
    st = dstate.get_or_create(db, user.id)
    assert dstate.refusal_count(st, "C1") == 1
    assert "C1" not in dstate.declined_set(st)
    assert "换一种" in gw.generation_prompt()          # 第一次 = 换问法

    orchestrator.handle_message(db, user, "还是不想说", sensitive_ok=True)
    st = dstate.get_or_create(db, user.id)
    assert dstate.refusal_count(st, "C1") == 2
    assert "C1" not in dstate.declined_set(st), "地板字段绝不能被标 declined"
    assert "没法给他介绍人" in gw.generation_prompt()   # 第二次 = 说明影响


def test_normal_field_refused_twice_is_declined_and_counts_as_handled(monkeypatch, db, user):
    """DEC-028：普通字段拒两次 → declined，且计入完成度（否则永远卡住）。"""
    gw = RecordingGateway(intent_kind="refusal_field", intent_field="A7")
    _install(monkeypatch, gw)

    orchestrator.handle_message(db, user, "不想说收入", sensitive_ok=True)
    orchestrator.handle_message(db, user, "真的不想说", sensitive_ok=True)

    st = dstate.get_or_create(db, user.id)
    assert "A7" in dstate.declined_set(st)

    progress = orchestrator.compute_progress(db, user.id, declined=dstate.declined_set(st))
    assert "A7" in progress["handled"]
    assert "A7" not in progress["missing_must"]


def test_floor_and_normal_field_behaviour_diverges(monkeypatch, db, user):
    """验收 #12 的集成层对应：同样拒两次，地板与普通字段结局必须不同。"""
    long_1 = "这个话题我现在还不太想聊，可以先跳过去吗"
    long_2 = "抱歉这个我还是不太想说，我们聊别的好不好"

    gw_floor = RecordingGateway(intent_kind="refusal_field", intent_field="B3")
    _install(monkeypatch, gw_floor)
    orchestrator.handle_message(db, user, long_1, sensitive_ok=True)
    orchestrator.handle_message(db, user, long_2, sensitive_ok=True)

    gw_normal = RecordingGateway(intent_kind="refusal_field", intent_field="A9")
    _install(monkeypatch, gw_normal)
    orchestrator.handle_message(db, user, long_1, sensitive_ok=True)
    orchestrator.handle_message(db, user, long_2, sensitive_ok=True)

    declined = dstate.declined_set(dstate.get_or_create(db, user.id))
    assert "A9" in declined
    assert "B3" not in declined


def test_proceed_intent_reports_real_gap_and_survives_voice_gate(monkeypatch, db, user):
    """前进意图：走进度答复指令，且该场景豁免进度语言与长度（否则被判缺陷）。"""
    gw = RecordingGateway(intent_kind="proceed")
    _install(monkeypatch, gw)

    orchestrator.handle_message(db, user, "我还差多少能进下一步", sensitive_ok=True)

    prompt = gw.generation_prompt()
    assert "【进度答复指令】" in prompt
    # 生成只调一次说明没触发重生成：即语气闸没把正确行为判成 hard 违规
    generations = [t for t, _ in gw.calls if t == "deep_interview"]
    assert len(generations) == 1


def test_extraction_is_scoped_to_current_act(monkeypatch, db, user):
    """act-scoped 抽取：act1 轮次的抽取契约不该出现 act3 的 D 类字段。"""
    gw = RecordingGateway(intent_kind="answer")
    _install(monkeypatch, gw)

    orchestrator.handle_message(db, user, "我来迪拜六年了", sensitive_ok=True)

    extraction = [m for t, ms in gw.calls if t == "memory_extraction" for m in ms]
    contract = "\n".join(m["content"] for m in extraction)
    assert "A4" in contract or "B1" in contract
    assert "D1 (" not in contract and "D4 (" not in contract


def test_terse_refusal_is_still_accounted_when_fatigue_wraps_up(monkeypatch, db, user):
    """疲劳收尾不能吞掉拒答记账。

    用户连续短句拒答会触发疲劳（三条 ≤6 字），本轮指令走收尾——但拒答**必须照记**。
    否则他下次回来再短句拒答，又触发疲劳，字段永远不被 declined，完成度永远到不了
    100%，深访无法完成。
    """
    gw = RecordingGateway(intent_kind="refusal_field", intent_field="A9")
    _install(monkeypatch, gw)

    for msg in ("不想说", "不说", "不想"):
        orchestrator.handle_message(db, user, msg, sensitive_ok=True)

    st = dstate.get_or_create(db, user.id)
    assert dstate.refusal_count(st, "A9") == 3, "疲劳收尾期间拒答未被记账"
    assert "A9" in dstate.declined_set(st), "重试一次后仍拒，应已标 declined"


def test_ask_ai_still_carries_the_next_question(monkeypatch, db, user):
    """反问不能吃掉下一个问题。

    实测缺陷：用户问"你想知道什么"被分类为 ask_ai，而该分支替换掉了幕指令与本轮建议，
    prompt 里没有目标字段也没有问法 —— 模型只能如实说"我没有具体问题要问你"。
    HLD §2 的路由是"先答用户的问题，**再回到当前幕**"，回到当前幕要求幕目标仍在。
    """
    gw = RecordingGateway(intent_kind="ask_ai")
    _install(monkeypatch, gw)

    orchestrator.handle_message(db, user, "你想知道什么", sensitive_ok=True)

    prompt = gw.generation_prompt()
    assert "【反问指令】" in prompt          # 先答他
    assert "【本幕模式" in prompt            # 再回到当前幕
    assert "【本轮建议】" in prompt          # 且带着具体目标字段与问法
    # 顺序：先答问题，再回到幕
    assert prompt.index("【反问指令】") < prompt.index("【本轮建议】")


def test_correction_and_smalltalk_also_carry_the_next_question(monkeypatch, db, user):
    for kind, marker in (("correction", "【纠正指令】"), ("smalltalk", "【闲聊指令】")):
        gw = RecordingGateway(intent_kind=kind)
        _install(monkeypatch, gw)

        orchestrator.handle_message(db, user, "顺便说一句，我其实住阿布扎比", sensitive_ok=True)

        prompt = gw.generation_prompt()
        assert marker in prompt, kind
        assert "【本轮建议】" in prompt, f"{kind} 分支丢了下一个问题"


def test_extraction_covers_adjacent_acts_not_just_current(monkeypatch, db, user):
    """跨幕答案不能丢。

    实测缺陷：用户在 act1 就说了"年龄 28-32、身高 160-170"（C1/C2，属 act2），
    抽取被限定在 act1 → 数据库里 C1/C2 全空，而小缘回了"我记下来了"。
    HLD §3 明确要求"用户跑题聊到其他幕字段照常顺势采集"。
    """
    gw = RecordingGateway(intent_kind="answer")
    _install(monkeypatch, gw)

    orchestrator.handle_message(db, user, "我想找 28 到 32 岁、身高 160 到 170 的", sensitive_ok=True)

    extraction = [m for t, ms in gw.calls if t == "memory_extraction" for m in ms]
    contract = "\n".join(m["content"] for m in extraction)
    assert "C1 (" in contract, "act1 轮次的抽取契约必须能接住 act2 的 C1"
    assert "C2 (" in contract, "act1 轮次的抽取契约必须能接住 act2 的 C2"


class NoQuestionGateway(RecordingGateway):
    """生成永远不带问号，用来验证 V1 会触发重生成。"""

    def chat(self, db, *, user_id, task, messages, **kw):
        r = super().chat(db, user_id=user_id, task=task, messages=messages, **kw)
        if task == "deep_interview":
            # 只缺问号，不含任何其他违规（避免第一轮就因别的规则重生成）
            r["content"] = "这些我先放在心里，慢慢来，不着急。"
        return r


def test_v1_triggers_regeneration_when_two_turns_lack_a_question(monkeypatch, db, user):
    """连着两轮不提问必须触发重生成（V1 接线验证）。"""
    gw = NoQuestionGateway(intent_kind="answer")
    _install(monkeypatch, gw)

    orchestrator.handle_message(db, user, "我来迪拜六年了", sensitive_ok=True)
    gens_turn1 = len([t for t, _ in gw.calls if t == "deep_interview"])

    orchestrator.handle_message(db, user, "在 DIFC 做 audit", sensitive_ok=True)
    gens_total = len([t for t, _ in gw.calls if t == "deep_interview"])

    assert gens_turn1 == 1, "第一轮没有上一轮可比，不该重生成"
    assert gens_total == 3, "第二轮应重生成一次（1 + 2 = 3 次生成调用）"

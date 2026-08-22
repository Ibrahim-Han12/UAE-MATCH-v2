"""输出校验层测试（persona_xiaoyuan v1.1 交付物 3/4 的可自动化条目）。

规格来源：docs/persona-voice-guide.md §二 验收规格 —— 标注"自动（禁词）"的条目。
"""
from app.core.dialogue import output_check as oc


def test_honorific_is_hard_violation():
    """验收 #17：回复里出现"您"必须被判为 hard 违规。"""
    result = oc.check("您好，我来帮你介绍。")

    assert result.has_hard is True
    assert "honorific" in [v.group for v in result.violations]


def test_clean_xiaoyuan_reply_passes():
    """Voice Guide #13（act2 反应带信息量）的 ✅ 句必须零违规。"""
    reply = "不介意比你大一两岁——这个在这边其实反而好找。学历和经济上呢，你是有底线那种？"

    result = oc.check(reply)

    assert result.violations == []
    assert result.has_hard is False


def test_progress_scene_exempts_progress_language():
    """进度答复场景：编排器要求如实报百分比，不得判为违规。"""
    reply = "到现在我已经了解你 60% 了，还差几个话题我们边聊边补。"

    result = oc.check(reply, scene="progress")

    assert [v.group for v in result.violations if v.group == "progress_language"] == []


def test_percent_outside_progress_scene_is_review_only():
    """非进度场景出现百分号：记为 review（人工复核），不阻断生成。"""
    result = oc.check("你的资料完成了 60%。")

    assert "progress_language" in [v.group for v in result.violations]
    assert result.has_hard is False


def test_overlong_reply_is_review_violation():
    """单条回复超字数上限：长度即腔调，记为 review。"""
    long_reply = "我在这边做红娘很多年了，见过的人也不算少。" * 8

    result = oc.check(long_reply)

    assert "length" in [v.group for v in result.violations]
    assert result.has_hard is False


def test_line_leading_list_marker_is_hard_violation():
    """聊天中禁止列表：行首"- "判为 hard。"""
    result = oc.check("你可以考虑这几点：\n- 年龄放宽一点\n- 学历别设死")

    assert "markdown" in [v.group for v in result.violations]
    assert result.has_hard is True


def test_mid_sentence_dash_is_not_flagged_as_markdown():
    """中文行内破折号与连字符不得误报为 markdown（锚定行首的意义）。"""
    result = oc.check("三十到三十五 - 挺实在的区间，身高呢？")

    assert "markdown" not in [v.group for v in result.violations]


def test_crisis_scene_bypasses_all_checks():
    """危机固定话术不走生成（PRD 9.2），既不检测更不重生成。"""
    text = "您好，这里是可以立刻联系到专业帮助的渠道。"

    assert oc.check(text, scene="crisis").violations == []
    # 反证：同一段文本在非危机场景确实违规，证明上面的通过来自豁免而非文本本身干净
    assert oc.check(text).has_hard is True


def test_shipped_crisis_copy_is_itself_clean():
    """回归守卫：crisis.yaml 的固定话术即便不豁免也不该违规（改文案时会被拦住）。"""
    from pathlib import Path

    import yaml

    conf = yaml.safe_load(
        (Path(oc.__file__).resolve().parents[3] / "config" / "safety" / "crisis.yaml")
        .read_text(encoding="utf-8")
    )

    result = oc.check(conf["fixed_response"].strip())

    assert result.violations == [], f"危机话术命中禁用规则：{result.violations}"


def test_regenerate_only_once_and_only_for_hard():
    """成本纪律：hard 才重生成，且最多 regenerate_max 次（默认 1）。"""
    hard = oc.check("您好")
    review_only = oc.check("你的资料完成了 60%。")

    assert oc.should_regenerate(hard, attempt=0) is True
    assert oc.should_regenerate(hard, attempt=1) is False
    assert oc.should_regenerate(review_only, attempt=0) is False


def test_generate_checked_calls_once_when_clean():
    """干净回复：只调一次模型，不浪费成本。"""
    calls = []

    def fake_llm(hint):
        calls.append(hint)
        return "三十到三十五，挺实在的区间。身高呢？"

    text, result, attempts = oc.generate_checked(fake_llm)

    assert attempts == 1
    assert calls == [None]
    assert result.violations == []
    assert text.startswith("三十到三十五")


def test_generate_checked_retries_once_on_hard_violation():
    """hard 违规：重生成一次，并把违规说明回传给模型。"""
    outputs = ["您好，我来了解一下你的情况。", "来了？我是小缘。你来迪拜几年了？"]
    hints = []

    def fake_llm(hint):
        hints.append(hint)
        return outputs[len(hints) - 1]

    text, result, attempts = oc.generate_checked(fake_llm)

    assert attempts == 2
    assert hints[0] is None
    assert "您" in hints[1]          # 违规说明必须点出命中的模式
    assert text == outputs[1]
    assert result.violations == []


def test_generate_checked_passes_through_after_max_retries():
    """重生成后仍违规：放行并把违规结果交回调用方埋点，不再无限重试。"""
    def fake_llm(hint):
        return "您好，请问您的学历是？"

    text, result, attempts = oc.generate_checked(fake_llm)

    assert attempts == 2
    assert result.has_hard is True
    assert text == "您好，请问您的学历是？"


def test_scene_mapping_from_orchestrator_flags():
    """场景推导：进度答复与收尾必须映射到有豁免的场景，否则正确行为会被判成缺陷。"""
    assert oc.scene_for(proceed_intent=True) == "progress"
    assert oc.scene_for(wrap_up=True) == "wrapup"
    assert oc.scene_for(stop_intent=True) == "wrapup"
    assert oc.scene_for(completed=True) == "wrapup"
    assert oc.scene_for() == "interview"
    # 进度答复优先级高于收尾：用户问"还差多少"时不能被当成要收尾
    assert oc.scene_for(proceed_intent=True, wrap_up=True) == "progress"

"""
深访编排器（PRD 5.1/5.3.5 · BR-201，三层分离的"编排层"）。

每轮：算字段缺口(Schema) → 取问法(问法库) → 注入建议 → LLM 组织语言(旗舰档)
     → 抽取本轮信息落库(事实层直写) → 更新完成度/疲劳信号 → 完成即 S1→S2 + 生成报告。
危机识别最小版挂载于本层（关键词 → 固定话术，不走生成）。
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml
from sqlalchemy.orm import Session

from app.core import state_machine as sm
from app.core.ai import get_ai_gateway, Task
from app.core.dialogue import acts, intent, output_check, refusal
from app.core.dialogue import state as dstate
from app.core.interview import config as ic
from app.core.interview import field_mapping
from app.core.memory import extractor, reader
from app.core.risk import log_event
from app.models.user import User
from app.models.profile import UserProfile
from app.models.ai_conversation import AIConversation

logger = logging.getLogger(__name__)

CONV_TYPE = "interview"
HISTORY_WINDOW = 12          # 注入最近 N 条对话
SESSION_SOFT_CAP_TURNS = 18  # 首次会话软上限（PRD 5.1：15-20 个提问点，先到先停）
FATIGUE_SHORT_LEN = 6        # 疲劳信号：连续短回答阈值（字符）
FATIGUE_WORDS = ("嗯", "都行", "随便", "还好", "不知道", "哦")

# 停止／前进等意图判定已迁至 app.core.dialogue.intent（关键词表降级为分类失败兜底）

_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"


def _load_persona_prompt() -> str:
    f = _CONFIG_DIR / "persona" / "xiaoyuan.md"
    if f.exists():
        text = f.read_text(encoding="utf-8")
        # 去掉文件头的 HTML 注释（工程说明不进 prompt）
        if text.lstrip().startswith("<!--"):
            end = text.find("-->")
            if end != -1:
                text = text[end + 3:]
        return text.strip()
    return "你是 UAE Match 的 AI 红娘'小缘'。单轮单问，语气温暖，身份透明（你是 AI）。"


def _load_crisis_config() -> dict:
    f = _CONFIG_DIR / "safety" / "crisis.yaml"
    if f.exists():
        return yaml.safe_load(f.read_text(encoding="utf-8"))
    return {"crisis_keywords": [], "fixed_response": "", "resources": []}


def detect_crisis(text: str) -> bool:
    kws = _load_crisis_config().get("crisis_keywords", [])
    return any(kw in text for kw in kws)


def crisis_response() -> str:
    conf = _load_crisis_config()
    lines = [conf.get("fixed_response", "").strip(), ""]
    for r in conf.get("resources", []):
        lines.append(f"· {r['name']}：{r['contact']}")
    return "\n".join(lines).strip()


def _recent_history(db: Session, user_id: int, limit: int = HISTORY_WINDOW) -> List[AIConversation]:
    rows = (
        db.query(AIConversation)
        .filter_by(user_id=user_id, conversation_type=CONV_TYPE)
        .order_by(AIConversation.created_at.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(rows))


def detect_fatigue(history: List[AIConversation]) -> bool:
    """连续短回答 / 敷衍词频升 → 疲劳（PRD 5.1：触发即主动收尾，不得追问）。"""
    user_msgs = [h.content for h in history if h.role == "user"][-3:]
    if len(user_msgs) < 3:
        return False
    short = sum(1 for m in user_msgs if len(m.strip()) <= FATIGUE_SHORT_LEN)
    perfunctory = sum(1 for m in user_msgs if any(w == m.strip() or m.strip().startswith(w) for w in FATIGUE_WORDS))
    return short >= 3 or perfunctory >= 2


def compute_progress(db: Session, user_id: int,
                     declined: Optional[Set[str]] = None) -> Dict[str, Any]:
    """完成度按 filled ∪ declined 计（DEC-028：declined 视为已处理）。

    地板字段（DEC-033）永远不进 declined，因此永远计入缺口——这是堵住
    "25 项全拒也能过闸"的那道口子。
    """
    filled = field_mapping.get_filled_field_ids(db, user_id)
    handled = set(filled) | set(declined or ())
    completion = ic.compute_completion(handled)
    missing = [
        f["id"] for f in ic.completion_fields()
        if f.get("source") == "interview" and f["id"] not in handled
    ]
    return {"completion": completion, "filled": sorted(filled),
            "handled": sorted(handled), "missing_must": missing}


def _known_facts_block(db: Session, user_id: int) -> str:
    """关键已知事实——问法选择的依据（防止预设错误事实，如对未婚用户问"之前的婚姻"）。"""
    p = db.query(UserProfile).filter_by(user_id=user_id).first()
    facts = []
    if p is not None:
        marital = {"never_married": "未婚", "divorced": "离异", "widowed": "丧偶"}.get(p.marital_history)
        facts.append(f"婚史：{marital or '未知'}")
        if p.has_children:
            facts.append(f"有无孩子：{'有' if p.has_children.get('has') == 'yes' else '无'}")
        if p.gender:
            facts.append(f"性别：{p.gender}")
    else:
        facts.append("婚史：未知")
    return "；".join(facts)


_ACT_INSTRUCTIONS = {
    "act1": (
        "【本幕模式·自由对话】现在是了解他基本情况的阶段。顺着他的话聊，"
        "一轮一个问题，先回应再问。他跑题聊到别的照常顺势采集，不用拉回来。"
    ),
    "act2": (
        "【本幕模式·择偶条件】现在进入最关键的一段：他想找什么样的人。"
        "这一段有几项要连着聊，所以每两项之间必须垫一句有信息量的反应——"
        "对他上一个答案的判断、你的经验、或者本地的实际情况。"
        "禁止机械过渡：不要用「好的」这类空话做衔接。"
        "每项采到值之后，追加确认一次弹性：这条是硬线，还是遇到合适的人可以松一松。"
    ),
    "act3": (
        "【本幕模式·情境题】最后几个轻松的小场景。"
        "用闲聊的口吻抛出情境（「问个日常的」「聊个场景」），一题一答，答完自然接一句就好。"
        "绝不能让他觉得自己在被打分、被分析，也不要用任何带考核意味的说法。"
    ),
}

# 意图 → 轮指令（HLD §2 路由表中由指令承载的三种；stop/proceed/refusal_field 有专门分支）
_INTENT_INSTRUCTIONS = {
    "correction": (
        "【纠正指令】用户在更正之前的信息或你的假设。先明确确认这个更正"
        "（说清你记下的是什么），绝不装作没听见、也不要辩解。确认之后再自然地"
        "接着往下聊，本轮可以不提新问题。"
    ),
    "ask_ai": (
        "【反问指令】用户在问你本人的事。先如实、简短地答他这个问题——"
        "不要绕开，不要反过来先问他。答完再自然回到刚才的话题。"
    ),
    "smalltalk": (
        "【闲聊指令】用户聊的是与当前话题无关的事。接住它，给一句短而有内容的回应，"
        "然后顺势回到刚才的话题——不要生硬拉回，也不要陪着无目的地聊下去。"
    ),
}


def act_instruction(act: str) -> str:
    return _ACT_INSTRUCTIONS[act]


def intent_instruction(kind: str) -> str:
    return _INTENT_INSTRUCTIONS[kind]


def _build_suggestion_block(db: Session, user_id: int, field: dict) -> str:
    """把目标字段的问法建议装配为注入指令（LLM 须改写，禁止照读）。"""
    entry = ic.bank_entry_for(field["id"]) or {}
    lines = [f"【本轮建议】目标信息：{field.get('label_zh')}（{field['id']}）"]
    lines.append(
        f"【已知事实·仅作背景】{_known_facts_block(db, user_id)}"
        "（这些是资料库中的既有信息，不是用户本轮说的话——禁止对其表示感谢或当作用户刚确认的内容；"
        "回应只针对用户本轮实际说的内容）"
    )
    if entry.get("sensitivity_strategy"):
        lines.append(f"敏感策略：{entry['sensitivity_strategy']}")
    for a in (entry.get("approaches") or [])[:3]:
        if a.get("text"):
            hint = a.get("context_hint", "")
            lines.append(f"- 可选问法（{a.get('style')}）：{a['text']}（适用：{hint}）")
    post = entry.get("post_step")
    if post:
        lines.append(f"追加确认（采到值后必须问）：{post.get('text')}")
    probe = entry.get("probe") or {}
    if probe.get("probe_text"):
        lines.append(f"追问（仅当 {probe.get('trigger')}，最多 1 层）：{probe['probe_text']}")
    lines.append(
        "执行要求："
        "①先用一两句自然回应用户刚才说的内容——若用户纠正了信息或你的假设，必须先确认更正，绝不装作没听见；"
        "②问法的适用条件必须对照【已知事实】选择——事实未知或与问法前提不符时，禁用预设该事实的问法，改用中性问法；"
        "③结合语境改写，禁止照读，禁止重复你之前用过的过渡句式；"
        "④单轮只问一个问题；用户聊到其他话题可顺势采集不必拉回。"
    )
    return "\n".join(lines)


def _save_msg(db: Session, user_id: int, role: str, content: str,
              tokens: int = 0, model: str = "") -> AIConversation:
    row = AIConversation(user_id=user_id, role=role, content=content,
                         conversation_type=CONV_TYPE, tokens_used=tokens, model=model)
    db.add(row)
    return row


def start_interview(db: Session, user: User) -> Dict[str, Any]:
    """开场（价值先行由 persona prompt 约束）。已有历史则返回续聊提示。"""
    history = _recent_history(db, user.id, limit=2)
    progress = compute_progress(db, user.id)
    if history:
        return {"message": None, "resumed": True, "progress": progress}

    base = [
        {"role": "system", "content": _load_persona_prompt()},
        {"role": "user", "content": "【系统指令】这是与该用户的第一次见面。请按'价值先行'原则开场：介绍你是谁、你怎么工作、节奏由用户掌控。本轮不提任何采集问题。"},
    ]
    last: Dict[str, Any] = {}

    def _generate(hint: Optional[str]) -> str:
        msgs = base if hint is None else base + [{"role": "system", "content": hint}]
        r = get_ai_gateway().chat(
            db, user_id=user.id, task=Task.DEEP_INTERVIEW,
            messages=msgs, scene="interview", temperature=0.8,
        )
        last.update(r)
        return r["content"]

    # 开场是"您好！我是您的专属AI红娘"这类客服腔的高发处，必须过语气闸
    content, voice_result, voice_attempts = output_check.generate_checked(
        _generate, scene="interview")
    _save_msg(db, user.id, "assistant", content,
              last.get("tokens_used", 0), last.get("model", ""))
    log_event(db, user_id=user.id, event_type="interview_started", metadata={})
    if voice_result.violations:
        log_event(db, user_id=user.id, event_type="quality_event",
                  metadata={"scene": "interview_opening", "attempts": voice_attempts,
                            "violations": [{"group": v.group, "type": v.type,
                                            "pattern": v.pattern}
                                           for v in voice_result.violations]})
    return {"message": content, "resumed": False, "progress": progress}


def handle_message(db: Session, user: User, message: str, sensitive_ok: bool) -> Dict[str, Any]:
    """深访主循环单轮。返回 {message, progress, completed, crisis}。不 commit。"""
    # 1) 危机识别最小版：固定话术，不走生成，本轮不继续深访
    if detect_crisis(message):
        _save_msg(db, user.id, "user", message)
        reply = crisis_response()
        _save_msg(db, user.id, "assistant", reply)
        log_event(db, user_id=user.id, event_type="crisis_referral",
                  metadata={"stage": "interview", "level": "keyword_minimal"})
        return {"message": reply, "progress": compute_progress(db, user.id),
                "completed": False, "crisis": True}

    history = _recent_history(db, user.id)
    _save_msg(db, user.id, "user", message)

    # 2) 幕状态（DEC-032）与本轮意图（DEC-031）——都要在抽取之前：抽取按幕限定范围
    st = dstate.get_or_create(db, user.id)
    declined = dstate.declined_set(st)
    pre = compute_progress(db, user.id, declined=declined)
    current_act = dstate.sync_act(db, st, set(pre["handled"]))
    pre_target = acts.next_target(set(pre["handled"]), sensitive_ok)
    turn_intent = intent.classify(db, user.id, message,
                                  current_field_id=(pre_target or {}).get("id"))

    # 3) 抽取本轮信息（mini 档，系统侧不占配额）——只抽当前幕 + 上一幕补漏
    #    现状每轮抽全 Schema 25+ 项，prompt 长且命中散（hld-dialogue-system.md §4）
    recent_text = "\n".join(
        f"{'用户' if h.role == 'user' else '小缘'}: {h.content}" for h in history[-4:]
    ) + f"\n用户: {message}"
    scoped = acts.act_field_ids(current_act)
    _idx = acts.ACTS.index(current_act)
    if _idx > 0:
        scoped = acts.act_field_ids(acts.ACTS[_idx - 1]) + scoped
    try:
        extracted = extractor.extract_from_conversation(
            db, user.id, recent_text, field_ids=scoped)
        if extracted:
            extractor.apply_extracted(db, user.id, extracted, mode="interview")
            db.flush()
    except Exception:
        logger.exception("深访抽取失败（不阻塞对话） user_id=%s", user.id)

    # 4) 抽取后重算缺口与幕，并落本轮意图
    progress = compute_progress(db, user.id, declined=declined)
    current_act = dstate.sync_act(db, st, set(progress["handled"]))
    target = acts.next_target(set(progress["handled"]), sensitive_ok)
    stop_intent = turn_intent.kind == "stop"
    proceed_intent = turn_intent.kind == "proceed"

    # 5) 拒答记账 —— 与"本轮说什么"解耦。即便本轮要收尾，账也必须记：
    #    否则用户用短句拒答会一路触发疲劳收尾，字段永远不被 declined，
    #    完成度永远到不了 100%，深访无法完成。
    refusal_decision = None
    if turn_intent.kind == "refusal_field" and turn_intent.field_id:
        refused_fid = turn_intent.field_id
        prior_refusals = dstate.refusal_count(st, refused_fid)
        refusal_decision = refusal.decide(refused_fid, prior_refusals=prior_refusals)
        dstate.bump_refusal(db, st, refused_fid)
        if refusal_decision == refusal.DECLINE:
            dstate.mark_declined(db, st, refused_fid)
            declined = dstate.declined_set(st)
            progress = compute_progress(db, user.id, declined=declined)
            current_act = dstate.sync_act(db, st, set(progress["handled"]))
            target = acts.next_target(set(progress["handled"]), sensitive_ok)
        log_event(db, user_id=user.id, event_type="field_refused",
                  metadata={"field_id": refused_fid, "decision": refusal_decision,
                            "prior_refusals": prior_refusals, "act": current_act})
    fatigue = detect_fatigue(history + [type("M", (), {"role": "user", "content": message})()])
    session_turns = sum(1 for h in history if h.role == "user") + 1
    wrap_up = stop_intent or fatigue or session_turns >= SESSION_SOFT_CAP_TURNS

    completed = False
    if not progress["missing_must"]:
        completed = _complete_interview(db, user)
        progress = compute_progress(db, user.id, declined=declined)

    # 6) 组装本轮指令
    system_prompt = _load_persona_prompt()
    memory_block = reader.build_profile_summary(db, user.id)
    if memory_block:
        system_prompt += f"\n\n=== 已了解的用户信息（勿重复提问）===\n{memory_block}"

    if completed:
        instruction = "【收尾指令】必采信息已全部完成。感谢用户的坦诚，告诉用户：画像报告正在生成、下一步是身份核验。语气要有仪式感。"
    elif proceed_intent:
        missing_labels = [
            (ic.field_by_id(fid) or {}).get("label_zh", fid)
            for fid in progress["missing_must"][:12]
        ]
        pct = round(progress["completion"] * 100)
        instruction = (
            f"【进度答复指令】用户想知道能否进入下一步。如实、具体地回答，禁止答非所问："
            f"①当前我已经了解用户 {pct}%；②还需要聊的话题（用自然的话概括，不要报表单字段名）："
            f"{('、'.join(missing_labels)) or '（无）'}；"
            f"③说明这些聊完会自动进入下一步（身份核验），不需要用户手动跳转；"
            f"④然后立刻自然地从缺口里挑一个话题继续问（单轮单问），保持推进的势头，不要让用户再问一次。"
        )
    elif stop_intent:
        instruction = (
            "【收尾指令·用户明确要停】用户表达了不想继续/想离开的意愿。本轮绝对禁止再提任何问题。"
            "回应要点：①爽快答应，不挽留不解释价值；②告诉用户进度已保存，随时回来接着聊，页面右上角可以'稍后继续'；"
            "③若用户问能否进入下一步/下一个页面：如实说明完成基本了解后会自动进入身份核验环节，现在可以先休息，不需要一次聊完。"
        )
    elif wrap_up:
        instruction = "【收尾指令】检测到用户疲劳或本次会话已到软上限。立即温和收尾并给正反馈（如'今天已经够我为你准备第一步了，剩下的我们边处边聊'），本轮不再提任何新问题。"
    elif refusal_decision is not None:
        # 记账已在上面完成；本分支只决定"怎么说"
        instruction = refusal.instruction_for(
            refusal_decision,
            ic.field_by_id(turn_intent.field_id) or {"id": turn_intent.field_id},
        )
    elif turn_intent.kind in _INTENT_INSTRUCTIONS:
        instruction = intent_instruction(turn_intent.kind)
    else:
        if target is not None:
            instruction = (act_instruction(current_act) + "\n"
                           + _build_suggestion_block(db, user.id, target))
        else:
            instruction = "【本轮建议】剩余待采信息均为敏感项，但用户尚未授权敏感画像采集。自然地聊当前话题，并在合适时机说明授权的价值（不施压）。"

    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-HISTORY_WINDOW:]:
        messages.append({"role": h.role, "content": h.content})
    messages.append({"role": "user", "content": message})
    messages.append({"role": "system", "content": instruction})

    # 7) 生成 + 语气闸（output_check）：hard 违规重生成一次并携带违规说明，仍违规则放行 + 埋点
    last: Dict[str, Any] = {}

    def _generate(hint: Optional[str]) -> str:
        msgs = messages if hint is None else messages + [{"role": "system", "content": hint}]
        r = get_ai_gateway().chat(
            db, user_id=user.id, task=Task.DEEP_INTERVIEW,
            messages=msgs, scene="interview", temperature=0.8,
        )
        last.update(r)
        return r["content"]

    voice_scene = output_check.scene_for(
        proceed_intent=proceed_intent, wrap_up=wrap_up,
        stop_intent=stop_intent, completed=completed,
    )
    content, voice_result, voice_attempts = output_check.generate_checked(
        _generate, scene=voice_scene)

    _save_msg(db, user.id, "assistant", content,
              last.get("tokens_used", 0), last.get("model", ""))

    if voice_result.violations:
        log_event(db, user_id=user.id, event_type="quality_event",
                  metadata={"scene": voice_scene, "attempts": voice_attempts,
                            "violations": [{"group": v.group, "type": v.type,
                                            "pattern": v.pattern}
                                           for v in voice_result.violations]})

    if fatigue:
        log_event(db, user_id=user.id, event_type="fatigue_triggered",
                  metadata={"session_turns": session_turns})
    if stop_intent:
        log_event(db, user_id=user.id, event_type="interview_paused",
                  metadata={"session_turns": session_turns})

    return {"message": content, "progress": progress,
            "completed": completed, "crisis": False}


def _complete_interview(db: Session, user: User) -> bool:
    """必采 100%：写完成时间 + S1→S2 + 埋点 + 生成基础版报告。幂等。"""
    profile = db.query(UserProfile).filter_by(user_id=user.id).first()
    if profile is not None and profile.interview_completed_at is not None:
        return False  # 已完成过
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
    profile.interview_completed_at = datetime.utcnow()

    if sm.effective_state(user) == sm.S1:
        sm.transition(db, user, sm.S2, reason="interview_completed")
    log_event(db, user_id=user.id, event_type="interview_completed", metadata={})

    try:
        from app.core.interview.report import generate_report
        generate_report(db, user)
    except Exception:
        logger.exception("画像报告生成失败（可重试） user_id=%s", user.id)

    # 画像向量（推荐引擎 Stage 3 语义调整的输入）
    try:
        from app.core.embedding_service import get_embedding_service
        get_embedding_service().create_or_update_embedding(db, user.id)
    except Exception:
        logger.exception("画像向量生成失败（不阻塞完成） user_id=%s", user.id)
    return True

"""
深访编排器（PRD 5.1/5.3.5 · BR-201，三层分离的"编排层"）。

每轮：算字段缺口(Schema) → 取问法(问法库) → 注入建议 → LLM 组织语言(旗舰档)
     → 抽取本轮信息落库(事实层直写) → 更新完成度/疲劳信号 → 完成即 S1→S2 + 生成报告。
危机识别最小版挂载于本层（关键词 → 固定话术，不走生成）。
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from sqlalchemy.orm import Session

from app.core import state_machine as sm
from app.core.ai import get_ai_gateway, Task
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

_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"


def _load_persona_prompt() -> str:
    f = _CONFIG_DIR / "persona" / "interview_system_prompt.md"
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


def compute_progress(db: Session, user_id: int) -> Dict[str, Any]:
    filled = field_mapping.get_filled_field_ids(db, user_id)
    completion = ic.compute_completion(filled)
    missing = [
        f["id"] for f in ic.completion_fields()
        if f.get("source") == "interview" and f["id"] not in filled
    ]
    return {"completion": completion, "filled": sorted(filled), "missing_must": missing}


def _pick_target(missing_must: List[str], sensitive_ok: bool) -> Optional[dict]:
    """按 Schema 顺序取第一个缺口；未获敏感授权时跳过 high 字段。"""
    for fid in missing_must:
        f = ic.field_by_id(fid)
        if f is None:
            continue
        if not sensitive_ok and f.get("sensitivity") == "high":
            continue
        return f
    return None


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


def _build_suggestion_block(db: Session, user_id: int, field: dict) -> str:
    """把目标字段的问法建议装配为注入指令（LLM 须改写，禁止照读）。"""
    entry = ic.bank_entry_for(field["id"]) or {}
    lines = [f"【本轮建议】目标信息：{field.get('label_zh')}（{field['id']}）"]
    lines.append(f"【已知事实】{_known_facts_block(db, user_id)}")
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

    resp = get_ai_gateway().chat(
        db, user_id=user.id, task=Task.DEEP_INTERVIEW,
        messages=[
            {"role": "system", "content": _load_persona_prompt()},
            {"role": "user", "content": "【系统指令】这是与该用户的第一次见面。请按'价值先行'原则开场：介绍你是谁、你怎么工作、节奏由用户掌控。本轮不提任何采集问题。"},
        ],
        scene="interview", temperature=0.8,
    )
    _save_msg(db, user.id, "assistant", resp["content"], resp["tokens_used"], resp["model"])
    log_event(db, user_id=user.id, event_type="interview_started", metadata={})
    return {"message": resp["content"], "resumed": False, "progress": progress}


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

    # 2) 抽取本轮信息（mini 档，系统侧不占配额）——先抽再问，缺口计算才准确
    recent_text = "\n".join(
        f"{'用户' if h.role == 'user' else '小缘'}: {h.content}" for h in history[-4:]
    ) + f"\n用户: {message}"
    try:
        extracted = extractor.extract_from_conversation(db, user.id, recent_text)
        if extracted:
            extractor.apply_extracted(db, user.id, extracted, mode="interview")
            db.flush()
    except Exception:
        logger.exception("深访抽取失败（不阻塞对话） user_id=%s", user.id)

    # 3) 缺口与状态
    progress = compute_progress(db, user.id)
    fatigue = detect_fatigue(history + [type("M", (), {"role": "user", "content": message})()])
    session_turns = sum(1 for h in history if h.role == "user") + 1
    wrap_up = fatigue or session_turns >= SESSION_SOFT_CAP_TURNS

    completed = False
    if not progress["missing_must"]:
        completed = _complete_interview(db, user)
        progress = compute_progress(db, user.id)

    # 4) 组装本轮指令
    system_prompt = _load_persona_prompt()
    memory_block = reader.build_profile_summary(db, user.id)
    if memory_block:
        system_prompt += f"\n\n=== 已了解的用户信息（勿重复提问）===\n{memory_block}"

    if completed:
        instruction = "【收尾指令】必采信息已全部完成。感谢用户的坦诚，告诉用户：画像报告正在生成、下一步是身份核验。语气要有仪式感。"
    elif wrap_up:
        instruction = "【收尾指令】检测到用户疲劳或本次会话已到软上限。立即温和收尾并给正反馈（如'今天已经够我为你准备第一步了，剩下的我们边处边聊'），本轮不再提任何新问题。"
    else:
        target = _pick_target(progress["missing_must"], sensitive_ok)
        if target is not None:
            instruction = _build_suggestion_block(db, user.id, target)
        else:
            instruction = "【本轮建议】剩余待采信息均为敏感项，但用户尚未授权敏感画像采集。自然地聊当前话题，并在合适时机说明授权的价值（不施压）。"

    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-HISTORY_WINDOW:]:
        messages.append({"role": h.role, "content": h.content})
    messages.append({"role": "user", "content": message})
    messages.append({"role": "system", "content": instruction})

    resp = get_ai_gateway().chat(
        db, user_id=user.id, task=Task.DEEP_INTERVIEW,
        messages=messages, scene="interview", temperature=0.8,
    )
    _save_msg(db, user.id, "assistant", resp["content"], resp["tokens_used"], resp["model"])

    if fatigue:
        log_event(db, user_id=user.id, event_type="fatigue_triggered",
                  metadata={"session_turns": session_turns})

    return {"message": resp["content"], "progress": progress,
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

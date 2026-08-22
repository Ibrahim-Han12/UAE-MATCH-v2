"""
画像报告生成（BR-201 / PRD 5.3 / DEC-004：基础版免费）。

铁律：只喂结构化画像数据，禁止从对话原文一步直出（防报告与库内画像不一致）。
基础版四板块（PRD 5.3.2）：story(你的故事) / sketch(画像速写) / seeking(你在寻找的人) / strategy(匹配策略)。
规格卡细则为 C4 产品资产（待终稿）——当前按 PRD 5.3.1 的板块定义生成，C4 到位后收紧校验。
旗舰模型（PRD 5.6.4：画像质量不省钱）。
"""
import json
import logging
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.core.ai import get_ai_gateway, Task
from app.core.memory import reader
from app.core.risk import log_event
from app.models.user import User
from app.models.profile_report import ProfileReport

logger = logging.getLogger(__name__)

SECTIONS = ("story", "sketch", "seeking", "strategy")

_PROMPT = """基于以下结构化画像数据，为用户生成婚恋画像报告（JSON，键为 story/sketch/seeking/strategy）：

- story（你的故事，3-4 句）：复述用户的核心叙事——来 UAE 的缘由、这些年的变化、此刻为什么认真想成家。让用户确认"你真的听懂了"。
- sketch（画像速写，1 段）：人格化描述，禁止字段罗列；写"这个人是什么样的人"。
- seeking（你在寻找的人，1 段）：把择偶观整理为清晰陈述，区分底线与加分项。
- strategy（匹配策略，2-3 句）：说明推荐节奏预期（每周 1-3 个、宁缺毋滥）与优先匹配的维度。

要求：中文；温暖专业不奉承；禁止判断句式的批评；只依据给出的数据，不编造。

=== 结构化画像 ===
{profile_data}

只返回 JSON，不要其他文字。"""


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            pass
    return {}


def generate_report(db: Session, user: User) -> Optional[ProfileReport]:
    """生成基础版报告并落库（版本递增）。不 commit。"""
    profile_data = reader.build_profile_summary(db, user.id, max_events=0)
    if not profile_data:
        logger.warning("画像为空，跳过报告生成 user_id=%s", user.id)
        return None

    resp = get_ai_gateway().chat(
        db, user_id=user.id, task=Task.DEEP_INTERVIEW,  # 旗舰档（报告质量不省钱）
        messages=[
            {"role": "system", "content": "你是专业而温暖的 AI 红娘'小缘'，为用户撰写婚恋画像报告。只返回 JSON。"},
            {"role": "user", "content": _PROMPT.format(profile_data=profile_data)},
        ],
        scene="profile_report", temperature=0.7,
        count_user_quota=False,
    )
    sections = _extract_json(resp["content"])
    # 程序校验点：四板块齐全才算合格（规格卡校验的最小版，C4 到位后收紧）
    if not all(k in sections and isinstance(sections[k], str) and sections[k].strip() for k in SECTIONS):
        logger.error("报告板块不齐，拒绝落库 user_id=%s keys=%s", user.id, list(sections.keys()))
        return None

    latest = (
        db.query(ProfileReport).filter_by(user_id=user.id)
        .order_by(ProfileReport.version.desc()).first()
    )
    report = ProfileReport(
        user_id=user.id,
        version=(latest.version + 1) if latest else 1,
        tier="basic",
        sections={k: sections[k].strip() for k in SECTIONS},
    )
    db.add(report)
    log_event(db, user_id=user.id, event_type="report_generated",
              metadata={"version": report.version, "tier": "basic"})
    return report


def get_latest_report(db: Session, user_id: int) -> Optional[ProfileReport]:
    return (
        db.query(ProfileReport).filter_by(user_id=user_id)
        .order_by(ProfileReport.version.desc()).first()
    )

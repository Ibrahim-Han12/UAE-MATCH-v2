"""
推荐信生成（T-2 阶段；BR-302, BR-307 / PRD 6.2）。

信件结构（展示顺序为产品铁律：先理由后照片，前端遵守）：
  reco_text(小缘推荐语 3-5 句) + sketch(对方画像速写,经确认版本) +
  compatibility(三亮点+一个诚实差异点) + basic_info(收入区间双向对等)。
具体性校验（BR-307）：推荐语须引用双方画像细节 ≥2 处；未过校验重新生成，
连续 3 次失败转人工（status 仍 review，标记 review_note）。
"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.ai import get_ai_gateway, Task
from app.core.interview import config as ic
from app.core.interview.report import get_latest_report
from app.models.reco_pair import RecoPair
from app.models.profile import UserProfile

logger = logging.getLogger(__name__)

MAX_GENERATION_ATTEMPTS = 3


def _human_value(profile: UserProfile, field_id: str) -> Optional[str]:
    """把 highlight 字段转成可校验的人话素材。"""
    if field_id.startswith("E8:"):
        return field_id.split(":", 1)[1]
    mapping = {
        "B1": {"long_term_stay": "长期定居", "return_within_years": "几年内回国",
               "depends_on_marriage": "视婚姻而定", "undecided": None}.get(profile.relocation_plan),
        "B2": {"within_1y": "一年内结婚", "1_2y": "一两年内结婚", "2_3y": "两三年内结婚",
               "no_rush": "顺其自然"}.get(profile.marriage_timeline),
    }
    return mapping.get(field_id)


def _facts_block(p: UserProfile) -> str:
    lines = []
    if p.display_name: lines.append(f"称呼: {p.display_name}")
    if p.birth_year: lines.append(f"出生年: {p.birth_year}")
    if p.occupation_industry: lines.append(f"行业: {p.occupation_industry}")
    if p.occupation_role_type: lines.append(f"角色: {p.occupation_role_type}")
    if p.education_level: lines.append(f"学历: {p.education_level}")
    if p.residence_emirate: lines.append(f"区域: {p.residence_emirate} {p.residence_district or ''}")
    if p.relocation_plan: lines.append(f"去留规划: {p.relocation_plan}")
    if p.marriage_timeline: lines.append(f"结婚时间线: {p.marriage_timeline}")
    ext = p.extended_info or {}
    if ext.get("interest_tags"): lines.append(f"兴趣: {','.join(ext['interest_tags'][:5])}")
    if p.bio: lines.append(f"自述: {p.bio[:100]}")
    return "\n".join(lines)


def _specificity_check(text: str, materials: List[str]) -> bool:
    """具体性校验：推荐语中出现 ≥2 个画像素材（BR-307 最小实现，C4 到位后收紧）。"""
    hits = sum(1 for m in materials if m and m in text)
    return hits >= 2


def _generate_direction(db: Session, pair: RecoPair, receiver: UserProfile,
                        target: UserProfile) -> Optional[Dict[str, Any]]:
    """为 receiver 生成介绍 target 的推荐信。"""
    materials = [m for m in (
        [_human_value(target, f) for f in (pair.highlight_fields or [])] +
        [target.occupation_industry, target.residence_district,
         (target.extended_info or {}).get("interest_tags", [None])[0]]
    ) if m]

    prompt = f"""为用户写一封推荐信的推荐语（3-5 句，小缘第一人称，如"这周我为你找到了……"）。
要求：必须具体引用下面对方画像中的至少 2 处细节（原词出现）；不提"算法/相似度"等技术词；不夸大。

=== 对方画像 ===
{_facts_block(target)}

=== 你们的契合点素材 ===
{', '.join(materials) if materials else '(以画像为准)'}

只返回推荐语文本，不要其他内容。"""

    for attempt in range(MAX_GENERATION_ATTEMPTS):
        resp = get_ai_gateway().chat(
            db, user_id=receiver.user_id, task=Task.RECOMMENDATION_ANALYSIS,
            messages=[
                {"role": "system", "content": "你是 AI 红娘'小缘'，为你的用户撰写每周推荐信。语气郑重而温暖。"},
                {"role": "user", "content": prompt},
            ],
            scene="reco_letter", temperature=0.8,
            count_user_quota=False,
        )
        text = resp["content"].strip()
        if _specificity_check(text, materials):
            break
        logger.warning("推荐语具体性校验未过 attempt=%d pair=%s", attempt + 1, pair.id)
    else:
        return None  # 3 次失败 → 转人工

    # 对方画像速写（经确认版本 = 最新报告 sketch 板块，PRD 6.5）
    target_report = get_latest_report(db, target.user_id)
    sketch = (target_report.sections or {}).get("sketch") if target_report else None

    dims = pair.dimensions or {}
    top_dims = sorted(dims.items(), key=lambda kv: -kv[1])[:3]
    return {
        "reco_text": text,
        "sketch": sketch,
        "compatibility": {
            "highlights": [k for k, _ in top_dims],
            "friction_point": pair.friction_point,   # 诚实差异点（信任设计，兼作破冰话题）
        },
        "basic_info": {   # 收入仅区间且双向对等（PRD 6.2-⑤）
            "birth_year": target.birth_year,
            "height_cm": target.height_cm,
            "education_level": target.education_level,
            "occupation_industry": target.occupation_industry,
            "residence_emirate": target.residence_emirate,
            "income_band": target.income_band_aed,
        },
    }


def run_stage_t2(db: Session, batch_id: str) -> Dict[str, int]:
    """T-2：为草稿队列生成双向推荐信 → status review（幂等：已有信不重生成）。"""
    pairs = db.query(RecoPair).filter_by(batch_id=batch_id, status="draft").all()
    done, manual = 0, 0
    for pair in pairs:
        p_low = db.query(UserProfile).filter_by(user_id=pair.user_low_id).first()
        p_high = db.query(UserProfile).filter_by(user_id=pair.user_high_id).first()
        if p_low is None or p_high is None:
            continue
        if pair.letter_for_low is None:
            pair.letter_for_low = _generate_direction(db, pair, p_low, p_high)
        if pair.letter_for_high is None:
            pair.letter_for_high = _generate_direction(db, pair, p_high, p_low)
        if pair.letter_for_low and pair.letter_for_high:
            pair.status = "review"
            done += 1
        else:
            pair.status = "review"
            pair.review_note = "推荐语生成 3 次未过具体性校验，需人工撰写"
            manual += 1
    logger.info("T-2 batch=%s generated=%d manual=%d", batch_id, done, manual)
    return {"generated": done, "manual_needed": manual}

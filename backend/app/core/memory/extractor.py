"""
深访/对话抽取器（BR-201 双产物之"内部画像"入口；Schema 驱动）。

流程（HLD §5.3 写管线）：
  对话文本 → LLM 按 Schema 字段契约抽取 JSON → 枚举校验 → 路由落库：
    D 类 + E1/E2        → user_psych_profile（事实层·心理测评）
    G1/G2/G3            → user_comm_profile（情感层·结构化）
    F3 感情叙事          → memory_vectors(namespace=narrative)（仅向量，不进结构化字段）
    A/B/C 类            → 暂存 memory_events(interview_extract)——user_profiles/
                          match_preferences 的字段扩展属 ③/④，扩展后由资料模块消费
  全程记录置信度（stated/inferred，Schema G5）。

抽取走 Task.MEMORY_EXTRACTION（mini 档）、不占用户配额（系统侧）。
"""
import json
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.ai import get_ai_gateway, Task
from app.core.interview import config as interview_config
from app.core.memory import writer

# Schema 字段 → psych profile 列的映射（D 类 + E1/E2）
PSYCH_ROUTING = {
    "D1": ("attachment_tendency", "attachment_style"),
    "D2": ("conflict_style", "conflict_style"),
    "D3": ("family_role_expectation", "family_role_expectation"),
    "D4": ("money_attitude", "money_view"),
    "E2": ("mbti_self_report", "mbti"),
}
BIG5_KEYS = {  # E1 大五对象 → 五列
    "openness": "big_five_openness",
    "conscientiousness": "big_five_conscientiousness",
    "extraversion": "big_five_extraversion",
    "agreeableness": "big_five_agreeableness",
    "neuroticism": "big_five_neuroticism",
}


def _extract_json(text: str) -> dict:
    """宽容解析 LLM 输出中的 JSON（直接 / markdown 代码块 / 首尾大括号）。"""
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


def _build_extraction_prompt(conversation_text: str, target_fields: List[dict]) -> str:
    """按 Schema 生成抽取契约（字段 key/类型/枚举），禁止清单进系统 prompt——契约在 user 消息里。"""
    lines = []
    for f in target_fields:
        desc = f"- {f['id']} ({f['key']}): {f.get('label_zh','')}"
        if f.get("type") == "enum" and f.get("enum"):
            desc += f" 枚举: {f['enum']}"
        elif f.get("type") == "object" and f.get("schema"):
            desc += f" 对象: {json.dumps(f['schema'], ensure_ascii=False, default=str)[:200]}"
        elif f.get("type") == "array":
            desc += " 数组"
        lines.append(desc)
    fields_block = "\n".join(lines)
    return f"""从以下对话中抽取用户信息。只抽取对话中确实出现的信息，未提及的字段一律不输出（禁止编造）。

目标字段（以字段 ID 为键输出）：
{fields_block}

另需输出（有则给，无则省略）：
- G1: 用户明显回避的话题（数组）
- G2: 用户明显兴奋/展开的话题（数组）
- F3: 用户讲述的感情经历叙事原文片段（字符串，尽量保留原话）
- _confidence: 各字段置信度映射，值为 stated（用户明说）或 inferred（推断）

对话内容：
{conversation_text}

只返回 JSON，键为字段 ID（如 "B1"、"D1"、"G1"），不要其他文字。"""


def _validate_enum(field: dict, value: Any) -> bool:
    if field.get("type") == "enum" and field.get("enum"):
        return value in field["enum"]
    return True


def extract_from_conversation(
    db: Session, user_id: int, conversation_text: str,
    field_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    LLM 抽取 + 枚举校验。field_ids 缺省 = 全部必采访谈字段 + E 类。
    返回 {field_id: value, "_confidence": {...}}（仅含通过校验的字段）。
    """
    all_fields = interview_config.schema_fields()
    if field_ids:
        targets = [f for f in all_fields if f["id"] in field_ids]
    else:
        targets = [
            f for f in all_fields
            if f.get("source") == "interview"
            and f.get("required_level") in ("must", "should")
        ]
        # A3 婚史例外：申报环节(BR-109)未建前，用户主动明说时允许抽取
        # （如"我没结过婚"必须被听见——否则问法选择会预设错误婚史）
        a3 = interview_config.field_by_id("A3")
        if a3 is not None and not any(f["id"] == "A3" for f in targets):
            targets.insert(0, a3)

    resp = get_ai_gateway().chat(
        db, user_id=user_id, task=Task.MEMORY_EXTRACTION,
        messages=[
            {"role": "system", "content": "你是严谨的结构化信息抽取器。只依据对话内容抽取，绝不编造；只返回 JSON。"},
            {"role": "user", "content": _build_extraction_prompt(conversation_text, targets)},
        ],
        scene="interview_extract", temperature=0.2,
        count_user_quota=False,
    )
    raw = _extract_json(resp["content"])
    if not raw:
        return {}

    confidence = raw.pop("_confidence", {}) or {}
    validated: Dict[str, Any] = {}
    for fid, value in raw.items():
        if value in (None, "", [], {}):
            continue
        field = interview_config.field_by_id(fid)
        if field is None and fid not in ("G1", "G2", "F3"):
            continue  # 丢弃 Schema 外的键
        if field is not None and not _validate_enum(field, value):
            continue  # 枚举校验失败：宁缺勿错，留待下轮再采
        validated[fid] = value
    if confidence:
        validated["_confidence"] = {k: v for k, v in confidence.items() if k in validated}
    return validated


def apply_extracted(
    db: Session, user_id: int, extracted: Dict[str, Any],
    mode: str = "interview",
) -> Dict[str, List[str]]:
    """
    抽取结果路由落库。返回 {routed_to: [field_ids]} 的落库报告。不 commit。

    mode="interview"：深访初采——A/B/C/D 直接落库（field_mapping 路由）。
    mode="incremental"：日常对话增量修正（PRD 5.4）——Schema 字段的冲突/新增
      一律进 memory_pending_changes 待小缘口头确认，不直接改画像；
      G 类元数据与 F3 叙事仍直写（系统侧观察，非用户申明的事实变更）。
    """
    if not extracted:
        return {}
    import json as _json
    from app.core.interview import field_mapping
    from app.core.memory import pending as pending_service

    confidence: Dict[str, str] = extracted.get("_confidence", {})
    report: Dict[str, List[str]] = {"psych": [], "comm": [], "vector": [], "facts": [], "pending": []}

    psych_values: Dict[str, Any] = {}
    psych_conf: Dict[str, str] = {}
    comm_values: Dict[str, Any] = {}
    audit_fields: Dict[str, Any] = {}

    for fid, value in extracted.items():
        if fid == "_confidence":
            continue
        if fid in ("G1", "G2", "G3"):
            key = {"G1": "avoid_topics", "G2": "excite_topics", "G3": "answer_style"}[fid]
            comm_values[key] = value
            report["comm"].append(fid)
            continue
        if fid == "F3" and isinstance(value, str) and value.strip():
            writer.add_vector(db, user_id, "narrative", value.strip(), scene="narrative_vectorize")
            report["vector"].append(fid)
            continue

        if mode == "incremental":
            # 增量修正：入待确认队列（值序列化保存），确认后由调用方走 field_mapping 落库
            serialized = value if isinstance(value, str) else _json.dumps(value, ensure_ascii=False)
            pending_service.enqueue_change(db, user_id, fid, None, serialized, source="conversation")
            report["pending"].append(fid)
            continue

        # interview 直写
        if fid in PSYCH_ROUTING:
            _, column = PSYCH_ROUTING[fid]
            psych_values[column] = value
            psych_conf[column] = confidence.get(fid, "inferred")
            report["psych"].append(fid)
        elif fid == "E1" and isinstance(value, dict):
            for k, col in BIG5_KEYS.items():
                if value.get(k) is not None:
                    psych_values[col] = value[k]
            psych_conf["big_five"] = confidence.get(fid, "inferred")
            report["psych"].append(fid)
        elif field_mapping.apply_field(db, user_id, fid, value):
            audit_fields[fid] = value
            report["facts"].append(fid)

    if psych_values:
        writer.upsert_psych_profile(db, user_id, psych_values, confidence=psych_conf)
    if comm_values:
        writer.upsert_comm_profile(db, user_id, comm_values)
    if audit_fields:
        # 审计留痕：深访抽取写入了哪些事实字段（决策回溯素材）
        writer.append_event(
            db, user_id, "interview_extract",
            payload={"fields": list(audit_fields.keys()),
                     "confidence": {k: confidence.get(k, "inferred") for k in audit_fields}},
            source="conversation",
        )
    return report

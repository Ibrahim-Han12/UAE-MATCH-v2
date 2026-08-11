"""
深访配置加载器（PRD 5.3.5 三层分离之 L1 Schema + L2 问法库）。

铁律：字段清单与问法只存在于 backend/config/interview/*.yaml，
禁止写入系统 prompt；本模块是编排器/抽取器读取配置的唯一入口。

职责：
1. 加载并缓存 interview_schema.yaml / question_bank.yaml；
2. 交叉校验（field ID 对账、必采访谈字段须有问法、高敏字段须有迂回策略）；
3. 提供字段缺口计算与问法查询的辅助函数。
"""
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# backend/config/interview/（从 app/core/interview/config.py 上溯到 backend/）
CONFIG_DIR = Path(__file__).resolve().parents[3] / "config" / "interview"

SCHEMA_FILE = CONFIG_DIR / "interview_schema.yaml"
QUESTION_BANK_FILE = CONFIG_DIR / "question_bank.yaml"

# 完成度只计 A-D 类（Schema meta.governance.completion_scope）
COMPLETION_CATEGORIES = ("A", "B", "C", "D")


class InterviewConfigError(Exception):
    """配置缺失或交叉校验失败。"""


@lru_cache(maxsize=1)
def load_schema() -> Dict[str, Any]:
    if not SCHEMA_FILE.exists():
        raise InterviewConfigError(f"interview_schema.yaml 不存在: {SCHEMA_FILE}")
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def load_question_bank() -> Dict[str, Any]:
    if not QUESTION_BANK_FILE.exists():
        raise InterviewConfigError(f"question_bank.yaml 不存在: {QUESTION_BANK_FILE}")
    with open(QUESTION_BANK_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def schema_fields() -> List[Dict[str, Any]]:
    return load_schema()["fields"]


def field_by_id(field_id: str) -> Optional[Dict[str, Any]]:
    for f in schema_fields():
        if f["id"] == field_id:
            return f
    return None


def must_interview_fields() -> List[Dict[str, Any]]:
    """必采且需访谈采集的字段（source=interview；eid/declaration 带入的不占提问预算）。"""
    return [
        f for f in schema_fields()
        if f.get("required_level") == "must" and f.get("source") == "interview"
    ]


def completion_fields() -> List[Dict[str, Any]]:
    """完成度分母：A-D 类必采字段全集（含系统带入项，它们默认已完成）。"""
    return [
        f for f in schema_fields()
        if f.get("required_level") == "must" and f.get("category") in COMPLETION_CATEGORIES
    ]


def compute_completion(filled_field_ids: set) -> float:
    """访谈完成度（G4）：仅计 A-D 必采；eid/declaration 来源视为天然已填。"""
    denom_fields = completion_fields()
    if not denom_fields:
        return 0.0
    filled = 0
    for f in denom_fields:
        if f.get("source") in ("eid", "declaration") or f["id"] in filled_field_ids:
            filled += 1
    return round(filled / len(denom_fields), 4)


def _bank_entries() -> List[Dict[str, Any]]:
    return load_question_bank()["question_bank"]


def bank_entry_for(field_id: str) -> Optional[Dict[str, Any]]:
    """按字段 ID 查问法条目（兼容 fields: [E3,E5,E7] 打包条目）。"""
    for entry in _bank_entries():
        if entry.get("field") == field_id:
            return entry
        if field_id in (entry.get("fields") or []):
            return entry
    return None


def validate() -> List[str]:
    """交叉校验，返回问题清单（空列表 = 通过）。启动时调用。"""
    problems: List[str] = []
    schema_ids = {f["id"] for f in schema_fields()}

    # 1) 问法库引用的字段 ID 必须存在于 Schema
    referenced: set = set()
    for entry in _bank_entries():
        ids = [entry["field"]] if "field" in entry else list(entry.get("fields") or [])
        for fid in ids:
            referenced.add(fid)
            if fid not in schema_ids:
                problems.append(f"问法库引用了 Schema 不存在的字段: {fid}")

    # 2) 必采访谈字段必须有问法条目，且 ≥2 种问法（PRD 5.2）
    for f in must_interview_fields():
        entry = bank_entry_for(f["id"])
        if entry is None:
            problems.append(f"必采访谈字段缺问法: {f['id']} ({f.get('label_zh')})")
            continue
        approaches = entry.get("approaches") or []
        if len(approaches) < 2:
            problems.append(f"必采字段 {f['id']} 问法不足 2 种（现 {len(approaches)}）")

    # 3) 高敏字段的问法条目必须带迂回策略或场景化问法
    for f in schema_fields():
        if f.get("sensitivity") == "high" and f.get("source") == "interview":
            entry = bank_entry_for(f["id"])
            if entry is None:
                continue  # E/F 类可无条目（顺带采集），已在 2) 中约束必采项
            has_strategy = bool(entry.get("sensitivity_strategy"))
            scenario_based = f.get("collection_method") == "scenario_coding"
            if not has_strategy and not scenario_based:
                problems.append(f"高敏字段 {f['id']} 的问法条目缺 sensitivity_strategy")

    # 4) 必采字段数与治理上限
    meta = load_schema().get("meta", {})
    cap = (meta.get("governance") or {}).get("must_field_cap", 25)
    must_count = len([f for f in schema_fields() if f.get("required_level") == "must"])
    if must_count > cap:
        problems.append(f"必采字段 {must_count} 项超过治理上限 {cap}")

    return problems

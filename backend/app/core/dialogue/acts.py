"""幕状态机的幕定义与切幕策略（hld-dialogue-system.md §3）。

纯函数、无 DB 依赖：幕字段集从 Schema 的 category 推导，不在代码里重复字段清单。
act1 = A/B 类事实（自由对话）｜act2 = C 类择偶条件（逐项快问）｜act3 = D 类情境题。
"""
from typing import Dict, List, Optional, Set

from app.core.interview import config as ic

ACTS = ("act1", "act2", "act3")

# 幕 → Schema category。act1 合并 A/B 两类（同为事实层，交互模式相同）。
_ACT_CATEGORIES: Dict[str, tuple] = {
    "act1": ("A", "B"),
    "act2": ("C",),
    "act3": ("D",),
}


def act_field_ids(act: str) -> List[str]:
    """该幕的必采访谈字段，按 Schema 顺序。系统带入字段（eid/declaration）不计。"""
    cats = _ACT_CATEGORIES[act]
    return [
        f["id"] for f in ic.schema_fields()
        if f.get("category") in cats
        and f.get("source") == "interview"
        and f.get("required_level") == "must"
    ]


def act_of(field_id: str) -> Optional[str]:
    for act in ACTS:
        if field_id in act_field_ids(act):
            return act
    return None


def act_complete(act: str, handled: Set[str]) -> bool:
    """handled = filled ∪ declined（DEC-028：declined 视为已处理）。"""
    return all(fid in handled for fid in act_field_ids(act))


def current_act(handled: Set[str]) -> str:
    for act in ACTS:
        if not act_complete(act, handled):
            return act
    return ACTS[-1]


def next_target(handled: Set[str], sensitive_ok: bool) -> Optional[dict]:
    """当前幕内 Schema 顺序的第一个缺口字段；未获敏感授权时跳过 high。"""
    act = current_act(handled)
    for fid in act_field_ids(act):
        if fid in handled:
            continue
        field = ic.field_by_id(fid)
        if field is None:
            continue
        if not sensitive_ok and field.get("sensitivity") == "high":
            continue
        return field
    return None

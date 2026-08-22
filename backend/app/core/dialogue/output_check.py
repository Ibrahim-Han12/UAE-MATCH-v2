"""输出校验层：生成后的纯代码语气闸（零模型成本）。

规则全部来自 config/persona/voice_rules.yaml（DEC-018 活资产，产品负责人可自行增删）。
本模块不含任何业务内容——新增禁用词改配置，不改代码。
"""
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import yaml

_CONFIG = Path(__file__).resolve().parents[3] / "config" / "persona" / "voice_rules.yaml"

HARD = "hard"
REVIEW = "review"


@dataclass(frozen=True)
class Violation:
    group: str
    type: str
    pattern: str


@dataclass
class CheckResult:
    violations: List[Violation] = field(default_factory=list)

    @property
    def has_hard(self) -> bool:
        return any(v.type == HARD for v in self.violations)


@lru_cache(maxsize=1)
def load_rules() -> dict:
    return yaml.safe_load(_CONFIG.read_text(encoding="utf-8"))


_SENTENCE_END = re.compile(r"[。！？!?…]+")


def _count_sentences(text: str) -> int:
    return len([s for s in _SENTENCE_END.split(text) if s.strip()])


def check(text: str, scene: Optional[str] = None) -> CheckResult:
    """校验一条生成回复。scene 用于按 voice_rules.yaml 的 scene_exemptions 豁免分组。"""
    rules = load_rules()
    meta = rules.get("meta", {})
    result = CheckResult()

    if scene and scene in set(rules.get("bypass_scenes") or []):
        return result   # 内容不走生成，不检测也不重生成

    exempt = set(rules.get("scene_exemptions", {}).get(scene, []) if scene else [])

    for group in rules.get("groups", []):
        gid = group["id"]
        if gid in exempt:
            continue
        mode, gtype = group.get("mode"), group["type"]

        if mode == "substring":
            for pat in group.get("patterns", []):
                if pat in text:
                    result.violations.append(Violation(gid, gtype, pat))
        elif mode == "regex":
            for pat in group.get("patterns", []):
                if re.search(pat, text):
                    result.violations.append(Violation(gid, gtype, pat))
        elif mode == "length":
            max_chars = meta.get("max_chars")
            max_sentences = meta.get("max_sentences")
            if max_chars and len(text) > max_chars:
                result.violations.append(Violation(gid, gtype, f"chars>{max_chars}"))
            if max_sentences and _count_sentences(text) > max_sentences:
                result.violations.append(Violation(gid, gtype, f"sentences>{max_sentences}"))

    return result


def should_regenerate(result: CheckResult, attempt: int) -> bool:
    """是否值得为这条回复重新生成一次。

    成本纪律（PRD 5.6 / BR-209）：只有 hard 违规才重生成，且不超过 regenerate_max 次；
    review 违规只埋点、不额外花钱。
    """
    if not result.has_hard:
        return False
    return attempt < load_rules().get("meta", {}).get("regenerate_max", 1)


def violation_hint(result: CheckResult) -> str:
    """把 hard 违规转成给模型的重生成说明（点名命中的模式与原因）。"""
    rules = {g["id"]: g.get("reason", "") for g in load_rules().get("groups", [])}
    items = [f"「{v.pattern}」（{rules.get(v.group, v.group)}）"
             for v in result.violations if v.type == HARD]
    return ("上一版回复命中了禁用表达：" + "；".join(items)
            + "。请重写这一轮回复，避开这些表达，其余要求不变。")


def generate_checked(call, scene: Optional[str] = None):
    """带语气闸的生成：hard 违规重生成（携带违规说明），仍违规则放行。

    call(hint) -> str —— 由调用方注入的生成函数；首轮 hint 为 None。
    返回 (最终文本, 最终校验结果, 实际调用次数)。放行时结果里仍带违规，供调用方埋点。
    """
    hint: Optional[str] = None
    attempt = 0
    text, result = "", CheckResult()
    while True:
        text = call(hint)
        result = check(text, scene=scene)
        attempt += 1
        if not should_regenerate(result, attempt - 1):
            return text, result, attempt
        hint = violation_hint(result)


def scene_for(proceed_intent: bool = False, wrap_up: bool = False,
              stop_intent: bool = False, completed: bool = False) -> str:
    """把编排器的本轮状态映射为校验场景（决定豁免哪些组，见 voice_rules.yaml）。

    进度答复优先于收尾：用户问"还差多少"时编排器要求如实报百分比，
    若误判为收尾场景，进度语言组不被豁免，正确行为会被判成缺陷。
    """
    if proceed_intent:
        return "progress"
    if wrap_up or stop_intent or completed:
        return "wrapup"
    return "interview"

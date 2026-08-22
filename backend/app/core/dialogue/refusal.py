"""字段级拒答决策（hld-dialogue-system.md §2）。

DEC-028：普通必采字段拒答 → 换问法重试一次 → 仍拒则标 declined，视为已处理。
DEC-033：地板字段（C1/C5/B3）不允许 declined → 仍拒则明确告知影响，完成度不推进。
本模块是纯函数，不碰 DB；轮指令文本由编排器注入生成层。

指令文本本身会进 prompt，因此必须过语气闸（见 tests/test_refusal.py 末条）——
指令里出现敬语或客服腔，模型会照抄。
"""
from app.core.interview import config as ic

RETRY = "retry"
DECLINE = "decline"
BLOCK = "block"

MAX_REPHRASE = 1   # 换问法重试上限（与问法库 global_rules.max_probe_depth 同轨）


def decide(field_id: str, prior_refusals: int) -> str:
    """prior_refusals = 本次拒答之前该字段已累计的拒答次数。"""
    if prior_refusals < MAX_REPHRASE:
        return RETRY
    if field_id in ic.floor_field_ids():
        return BLOCK
    return DECLINE


def instruction_for(decision: str, field: dict) -> str:
    label = field.get("label_zh", field.get("id", ""))
    if decision == RETRY:
        return (
            f"【拒答处理·换问法】用户回避了「{label}」。先一句自然带过，不追问、不评价；"
            "然后换一种完全不同的问法再问一次——只这一次。"
            "可用更具体的情境或更小的切口，禁止重复刚才被拒的那种问法。"
        )
    if decision == DECLINE:
        return (
            f"【拒答处理·翻篇】用户第二次回避「{label}」。一句轻轻跳过，"
            "明确表示这个不影响什么，此后整段对话不再提这个话题（也不要变相打探）。"
            "本轮接着聊下一个话题。"
        )
    return (
        f"【拒答处理·说明影响】「{label}」是你干活的地基之一，用户第二次回避。"
        "老实告诉他：这一项你不知道就没法给他介绍人；今天不想说没关系，"
        "什么时候想说了再跟你讲。语气是诚实，不是施压——不要说教，不要重复劝，"
        "不要暗示他不配合。说完本轮就停在这里，不要再问别的。"
    )

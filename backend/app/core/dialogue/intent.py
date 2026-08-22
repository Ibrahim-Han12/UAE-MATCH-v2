"""意图层（hld-dialogue-system.md §2）：每轮一次 mini 分类，取代关键词 if-else。

意图先于生成——先知道用户这轮想干什么，再决定问什么。分类失败一律回落关键词兜底，
绝不因分类不可用而中断对话。危机识别是硬规则，由编排器在进入本层之前前置处理。
成本：每轮 +1 次 mini，全程深访约 +0.05 AED（DEC-031），系统侧不占用户配额。
"""
import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

from app.core.ai import get_ai_gateway, Task

logger = logging.getLogger(__name__)

KINDS = ("answer", "correction", "refusal_field", "stop",
         "proceed", "ask_ai", "smalltalk", "crisis")

# 关键词兜底词表（原编排器的 STOP/PROCEED 词表降级至此，仅用于分类失败时兜底）
STOP_PHRASES = ("不想聊", "不想回答", "不聊了", "不说了", "先到这里", "改天", "下次再",
                "暂停", "停一下", "别问了")
PROCEED_PHRASES = ("下一步", "下一个页面", "换个页面", "进入下一", "还差什么", "还差多少",
                   "还要聊多久", "什么时候能", "进度怎么", "跳过")

_SYSTEM = (
    "你是对话意图分类器。判断用户这一轮想做什么，只返回 JSON，不要解释。\n"
    "intent 取值：answer(在回答问题) / correction(在纠正之前的信息) / "
    "refusal_field(不愿回答当前这个问题) / stop(想结束本次对话) / "
    "proceed(想知道进度或想进入下一步) / ask_ai(在反问红娘本人) / "
    "smalltalk(闲聊，与当前问题无关) / crisis(表达自伤或严重情绪危机)。\n"
    "输出格式：{\"intent\":\"...\",\"field_id\":\"当前问题的字段号或 null\","
    "\"confidence\":0.0-1.0}"
)


@dataclass(frozen=True)
class Intent:
    kind: str
    field_id: Optional[str] = None
    confidence: float = 0.0
    source: str = "model"          # model | keyword_fallback


def classify_by_keyword(message: str) -> Intent:
    """纯函数兜底。停止优先于前进：把"想停"误判成"想推进"的代价更大。"""
    if any(p in message for p in STOP_PHRASES):
        return Intent("stop", source="keyword_fallback")
    if any(p in message for p in PROCEED_PHRASES):
        return Intent("proceed", source="keyword_fallback")
    return Intent("answer", source="keyword_fallback")


def _parse(content: str, current_field_id: Optional[str]) -> Optional[Intent]:
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    kind = data.get("intent")
    if kind not in KINDS:
        return None
    field_id = data.get("field_id") or current_field_id
    try:
        conf = float(data.get("confidence", 0.0))
    except (ValueError, TypeError):
        conf = 0.0
    return Intent(kind, field_id, conf, source="model")


def classify(db, user_id: int, message: str,
             current_field_id: Optional[str] = None) -> Intent:
    """每轮 +1 次 mini 调用（DEC-031）。系统侧调用，不占用户配额。"""
    prompt = f"当前正在问的字段：{current_field_id or '无'}\n用户这一轮说：{message}"
    try:
        resp = get_ai_gateway().chat(
            db, user_id=user_id, task=Task.INTENT_CLASSIFY,
            messages=[{"role": "system", "content": _SYSTEM},
                      {"role": "user", "content": prompt}],
            scene="intent_classify", temperature=0.0, count_user_quota=False,
        )
    except Exception:
        logger.exception("意图分类失败，回落关键词 user_id=%s", user_id)
        return classify_by_keyword(message)

    parsed = _parse(resp.get("content", ""), current_field_id)
    if parsed is None:
        logger.warning("意图分类结果不可用，回落关键词 user_id=%s", user_id)
        return classify_by_keyword(message)
    return parsed

"""
模型价格表（USD / 1M tokens，(输入价, 输出价)）。

价格基线 2026-07（PRD 5.6.1），**季度复审更新**。global_ai_budget 以 USD 计量，
故此处用 USD；1 USD = 3.6725 AED（联系汇率）便于换算 AED 成本目标。

与 routing.py 同为"允许出现模型名"的配置点。
"""

# USD per 1,000,000 tokens: (input, output)
PRICING = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-3.5-turbo": (0.50, 1.50),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4": (30.00, 60.00),
    "text-embedding-3-small": (0.02, 0.0),
    "text-embedding-3-large": (0.13, 0.0),
}

_DEFAULT = PRICING["gpt-4o-mini"]  # 未知模型按 mini 估（保守，避免高估熔断）

USD_TO_AED = 3.6725


def _match(model: str):
    """OpenAI 返回的 model 可能带日期后缀（如 gpt-4o-2024-08-06），按最长前缀匹配。"""
    if not model:
        return _DEFAULT
    if model in PRICING:
        return PRICING[model]
    best = None
    for key in PRICING:
        if model.startswith(key) and (best is None or len(key) > len(best)):
            best = key
    return PRICING[best] if best else _DEFAULT


def estimate_cost_usd(model: str, tokens_in: int, tokens_out: int = 0) -> float:
    pin, pout = _match(model)
    cost = (tokens_in or 0) / 1_000_000 * pin + (tokens_out or 0) / 1_000_000 * pout
    return round(cost, 6)


def usd_to_aed(usd: float) -> float:
    return round(usd * USD_TO_AED, 4)

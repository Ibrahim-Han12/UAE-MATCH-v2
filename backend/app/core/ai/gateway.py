"""
AI 网关（模型抽象层门面，PRD 5.6.4 / BR-209）。

业务代码调用 gateway.chat(task=...) / gateway.embed(...)，网关负责：
1. 按 task 解析模型档位（routing）——业务代码不碰模型名；
2. 全局预算 100% 熔断 → 强制降级 mini（PRD 5.6.5）；
3. 调用 provider（当前 OpenAI）并计量（metering, BR-209）。

注：与现有代码约定一致，本层**不 commit**，由调用方提交。
迁移策略：新代码一律走网关；存量端点（ai_chat/coach/vip_care 等仍自行记 token）
逐个迁移，迁移时须移除其旧计量以免与网关重复计量。
"""
from typing import List, Dict, Optional, Any

from sqlalchemy.orm import Session

from app.core.openai_client import get_openai_client
from app.core.ai import routing, metering


class AIGateway:
    def chat(
        self,
        db: Session,
        *,
        user_id: Optional[int],
        task: str,
        messages: List[Dict[str, str]],
        scene: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        count_user_quota: bool = True,
    ) -> Dict[str, Any]:
        """按任务路由模型 → 调用 → 计量。返回 {content, tokens_used, tokens_in, tokens_out, cache_hit, model, cost_usd, tier, budget_degraded}。"""
        scene = scene or task
        # 全局预算熔断：100% → 全线降级 mini
        force_tier = "mini" if metering.is_budget_exceeded(db) else None
        r = routing.resolve(task, force_tier=force_tier)

        client = get_openai_client()
        resp = client.chat_completion(
            messages=messages,
            model=r["model"],
            fallback_model=r["fallback"],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        meter = metering.record_ai_call(
            db,
            user_id=user_id,
            scene=scene,
            task=task,
            model=resp.get("model") or r["model"],
            tokens_in=resp.get("tokens_in", 0),
            tokens_out=resp.get("tokens_out", 0),
            cache_hit=resp.get("cache_hit", False),
            count_user_quota=count_user_quota,
        )
        resp["cost_usd"] = meter["cost_usd"]
        resp["tier"] = r["tier"]
        resp["budget_degraded"] = force_tier is not None
        return resp

    def embed(
        self,
        db: Session,
        *,
        user_id: Optional[int],
        text: str,
        scene: str = "embedding",
    ) -> List[float]:
        """向量化 + 计量。"""
        client = get_openai_client()
        result = client.client.embeddings.create(model=routing.EMBEDDING_MODEL, input=text)
        vector = result.data[0].embedding
        usage = getattr(result, "usage", None)
        tokens_in = 0
        if usage is not None:
            tokens_in = getattr(usage, "prompt_tokens", 0) or getattr(usage, "total_tokens", 0) or 0
        metering.record_ai_call(
            db,
            user_id=user_id,
            scene=scene,
            task="embedding",
            model=routing.EMBEDDING_MODEL,
            tokens_in=tokens_in,
            tokens_out=0,
        )
        return vector


_gateway: Optional[AIGateway] = None


def get_ai_gateway() -> AIGateway:
    global _gateway
    if _gateway is None:
        _gateway = AIGateway()
    return _gateway

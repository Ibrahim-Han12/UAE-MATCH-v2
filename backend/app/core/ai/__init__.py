"""
AI 模型抽象层（PRD 5.6.4 / BR-209）。

对外入口：
    from app.core.ai import get_ai_gateway, Task
    gw = get_ai_gateway()
    resp = gw.chat(db, user_id=uid, task=Task.COMPANIONSHIP, messages=msgs, scene="ai_chat")

子模块：
    routing  —— 任务→档位→模型（唯一允许模型名处之一）
    pricing  —— 模型价格表与成本估算
    metering —— 计量与全局预算（BR-209）
    gateway  —— 门面：路由 + 熔断 + 调用 + 计量
"""
from app.core.ai import routing, pricing, metering  # noqa: F401
from app.core.ai.routing import Task  # noqa: F401
from app.core.ai.gateway import AIGateway, get_ai_gateway  # noqa: F401

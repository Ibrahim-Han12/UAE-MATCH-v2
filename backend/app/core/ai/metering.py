"""
AI 计量与预算（BR-209 / PRD 5.6.6 / 15 章 ai_call）。

每次 AI 调用记录：user / scene / task / model / tokens(in/out) / cache_hit / cost_usd。
- 明细：写 event_logs 的 ai_call 事件（复用 risk.log_event）—— 供成本看板按 scene×model 聚合。
- 汇总：累加 user_token_usage.tokens_used（用户月度）与 global_ai_budget.budget_used（全局月度 USD）。

约定：本模块**不 commit**，由调用方（端点/任务）统一提交，与 risk.log_event 一致。
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.risk import log_event
from app.core.ai.pricing import estimate_cost_usd
from app.models.user_token_usage import UserTokenUsage
from app.models.global_ai_budget import GlobalAIBudget


def current_month() -> str:
    return datetime.utcnow().strftime("%Y-%m")


def record_ai_call(
    db: Session,
    *,
    user_id: int | None,
    scene: str,
    task: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    cache_hit: bool = False,
    count_user_quota: bool = True,
) -> dict:
    """记录一次 AI 调用的计量。返回 {cost_usd, total_tokens}。

    count_user_quota=False：系统侧调用（主动关怀/记忆压缩/后台抽取）——仍记明细事件与全局成本，
    但**不占用用户月度 token 配额**（PRD：主动关怀不计入用户配额）。
    """
    tokens_in = tokens_in or 0
    tokens_out = tokens_out or 0
    total = tokens_in + tokens_out
    cost = estimate_cost_usd(model, tokens_in, tokens_out)
    month = current_month()

    # 1) 明细事件（PRD 15 章 ai_call）——需要 user_id
    if user_id is not None:
        log_event(
            db,
            user_id=user_id,
            event_type="ai_call",
            metadata={
                "scene": scene,
                "task": task,
                "model": model,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "total_tokens": total,
                "cache_hit": bool(cache_hit),
                "cost_usd": cost,
            },
        )
        # 2) 用户月度 token 累计（仅计入用户配额时）
        if count_user_quota:
            usage = (
                db.query(UserTokenUsage)
                .filter_by(user_id=user_id, month=month)
                .first()
            )
            if usage is None:
                usage = UserTokenUsage(
                    user_id=user_id,
                    month=month,
                    tokens_used=0,
                    tokens_limit=settings.DEFAULT_USER_TOKEN_LIMIT,
                )
                db.add(usage)
                db.flush()  # 立即持久化：同一事务内多次计量+autoflush=False 时避免重复创建当月行
            usage.tokens_used = (usage.tokens_used or 0) + total

    # 3) 全局预算累计（USD）
    budget = db.query(GlobalAIBudget).filter_by(month=month).first()
    if budget is None:
        budget = GlobalAIBudget(
            month=month,
            budget_limit=Decimal(str(settings.GLOBAL_BUDGET_LIMIT)),
            budget_used=Decimal("0"),
        )
        db.add(budget)
        db.flush()  # 立即持久化：同一事务内多次计量+autoflush=False 时避免重复创建当月行
    budget.budget_used = (budget.budget_used or Decimal("0")) + Decimal(str(cost))

    return {"cost_usd": cost, "total_tokens": total}


def get_budget_status(db: Session) -> dict:
    """全局预算状态：ok / alert(≥80%) / exceeded(≥100%)（PRD 5.6.5）。"""
    month = current_month()
    budget = db.query(GlobalAIBudget).filter_by(month=month).first()
    limit = float(budget.budget_limit) if budget else float(settings.GLOBAL_BUDGET_LIMIT)
    used = float(budget.budget_used) if budget else 0.0
    ratio = (used / limit) if limit else 0.0
    if ratio >= 1.0:
        state = "exceeded"
    elif ratio >= 0.8:
        state = "alert"
    else:
        state = "ok"
    return {"month": month, "limit": limit, "used": round(used, 4), "ratio": round(ratio, 4), "state": state}


def is_budget_exceeded(db: Session) -> bool:
    return get_budget_status(db)["state"] == "exceeded"

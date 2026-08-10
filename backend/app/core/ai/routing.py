"""
模型路由配置（CLAUDE §4 / PRD 5.6.4）。

这是**全系统唯一允许出现具体模型名的地方之一**（另一个是 pricing.py）。
业务代码只声明"任务(task)"，由本模块解析为"档位(tier)→模型(model)+降级(fallback)"，
从而实现"供应商可替换"（换模型/供应商只改这里，不动业务代码）。

后续可迁移为 YAML 外部配置；当前用 Python 常量，零新增依赖。
"""
from app.core.config import settings


class Task:
    """任务常量（业务代码引用这些，而非模型名）。"""
    DEEP_INTERVIEW = "deep_interview"                # L1 深访 —— 旗舰
    RECOMMENDATION_ANALYSIS = "recommendation_analysis"  # 推荐/兼容性分析 —— 旗舰
    COACH_COMPLEX = "coach_complex"                  # 军师复杂咨询 —— 旗舰 + 缓存
    COACH_SIMPLE = "coach_simple"                    # 军师简单咨询 —— mini
    COMPANIONSHIP = "companionship"                  # 日常陪伴 —— mini
    PROACTIVE_CARE = "proactive_care"                # L3 主动关怀 —— mini
    MEMORY_EXTRACTION = "memory_extraction"          # 记忆抽取 —— mini
    MODERATION = "moderation"                        # 内容审核 —— mini
    REGISTRATION = "registration"                    # 引导注册对话 —— mini


# 档位 → 模型 + 降级模型（价差约 17 倍，模型分层路由是成本第一杠杆 —— PRD 5.6.1）
TIERS = {
    "flagship": {"model": "gpt-4o", "fallback": settings.OPENAI_MODEL_GPT4O_MINI},
    "mini": {"model": settings.OPENAI_MODEL_GPT4O_MINI, "fallback": settings.OPENAI_MODEL_GPT35},
}

EMBEDDING_MODEL = settings.OPENAI_MODEL_EMBEDDING

# 任务 → 档位（PRD 5.6.4 模型选型矩阵）
TASK_TIER = {
    Task.DEEP_INTERVIEW: "flagship",
    Task.RECOMMENDATION_ANALYSIS: "flagship",
    Task.COACH_COMPLEX: "flagship",
    Task.COACH_SIMPLE: "mini",
    Task.COMPANIONSHIP: "mini",
    Task.PROACTIVE_CARE: "mini",
    Task.MEMORY_EXTRACTION: "mini",
    Task.MODERATION: "mini",
    Task.REGISTRATION: "mini",
}

DEFAULT_TIER = "mini"


def resolve(task: str, force_tier: str | None = None) -> dict:
    """
    task → {tier, model, fallback}
    force_tier 用于全局预算熔断时强制降级到 mini（PRD 5.6.5）。
    """
    tier = force_tier or TASK_TIER.get(task, DEFAULT_TIER)
    conf = TIERS.get(tier) or TIERS["mini"]
    return {"tier": tier, "model": conf["model"], "fallback": conf["fallback"]}

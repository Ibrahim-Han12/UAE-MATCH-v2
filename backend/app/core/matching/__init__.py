"""
推荐流水线（BR-301, BR-302, BR-307）。

config   —— matching_config.yaml 加载（权重/阈值唯一来源）
engine   —— T-3 四段漏斗计算（Stage0-3 + min双向 + 分配约束）
letters  —— T-2 推荐语生成 + 具体性校验
delivery —— T0 送达（三通道）+ 到期关闭
调度：cron 独立脚本 app/jobs/reco_stage.py（D4 决策）。
"""
from app.core.matching import config, engine, letters, delivery  # noqa: F401

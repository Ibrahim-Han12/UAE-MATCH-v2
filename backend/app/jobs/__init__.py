"""
cron 独立任务脚本（决策 D4=B：OS cron 触发 `python -m app.jobs.<job>`，与 Web 进程解耦）。
推荐流水线四阶段（T-3~T0）后续也落在本包。
"""

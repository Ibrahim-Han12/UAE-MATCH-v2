"""
深访三层架构（PRD 5.3.5）。

config —— Schema 层 + 问法库层的加载/校验/查询（唯一读取入口）
（编排器 orchestrator 属 BR-201 深访重建，后续加入）
"""
from app.core.interview import config  # noqa: F401

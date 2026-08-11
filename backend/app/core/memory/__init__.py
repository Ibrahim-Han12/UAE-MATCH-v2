"""
三层记忆体系（BR-202，取代旧滚动摘要 memory_service/user_ai_memory）。

writer    —— 写入原语：psych/comm upsert、事件追加、向量写入
reader    —— 读取原语：结构化画像摘要 + 向量检索 top-3（注入 prompt）
pending   —— 画像更新待确认队列（PRD 5.4：小缘口头确认后才落库）
extractor —— Schema 驱动的对话抽取 + 字段路由落库

旧 memory_service（滚动摘要）在调用点切换到本包后废弃。
"""
from app.core.memory import writer, reader, pending, extractor  # noqa: F401

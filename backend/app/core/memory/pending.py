"""
画像更新待确认队列（PRD 5.4）。

对话中检出与库内冲突/新增的信息 → enqueue → 小缘自然时机口头确认
→ confirm(落库+变更留痕) / reject。防止随口一句话直接改画像、搅动匹配池。

注意：confirm 只做"留痕 + 标记 + 重算标记"，字段真正写入哪张表由调用方
（拥有字段→表路由知识的抽取/资料模块）执行——本模块不做字段路由。
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.interview import config as interview_config
from app.core.memory.writer import append_event
from app.models.memory_pending_change import MemoryPendingChange


def enqueue_change(
    db: Session, user_id: int, field: str,
    old_value: Optional[str], new_value: Optional[str], source: str = "conversation",
) -> MemoryPendingChange:
    """入队一条待确认变更；同字段已有 pending 则更新其 new_value（不重复排队）。"""
    row = (
        db.query(MemoryPendingChange)
        .filter_by(user_id=user_id, field=field, status="pending")
        .first()
    )
    if row:
        row.new_value = new_value
        row.source = source
        return row
    row = MemoryPendingChange(
        user_id=user_id, field=field,
        old_value=old_value, new_value=new_value,
        source=source, status="pending",
    )
    db.add(row)
    return row


def list_pending(db: Session, user_id: int) -> List[MemoryPendingChange]:
    return (
        db.query(MemoryPendingChange)
        .filter_by(user_id=user_id, status="pending")
        .order_by(MemoryPendingChange.created_at)
        .all()
    )


def confirm_change(db: Session, change_id: int) -> Dict[str, Any]:
    """
    用户口头确认后调用：标记 confirmed + 写变更留痕（事件层）+
    依 Schema recalc_trigger 返回是否需触发匹配池重算（PRD 5.4 A/B 类）。
    """
    row = db.query(MemoryPendingChange).filter_by(id=change_id).first()
    if row is None or row.status != "pending":
        raise ValueError(f"待确认变更不存在或已处理: {change_id}")
    row.status = "confirmed"

    # 变更留痕（PRD 5.4：字段/旧值/新值/触发来源——重算批次 ID 由推荐流水线回填）
    append_event(
        db, row.user_id, "profile_change_confirmed",
        payload={"field": row.field, "old": row.old_value, "new": row.new_value,
                 "source": row.source, "change_id": row.id},
        source="system",
    )

    # 字段是否触发匹配池重算（Schema recalc_trigger）
    needs_recalc = False
    schema_field = interview_config.field_by_id(row.field.split(".")[0])
    if schema_field and schema_field.get("recalc_trigger") is True:
        needs_recalc = True

    return {"change": row, "needs_pool_recalc": needs_recalc}


def reject_change(db: Session, change_id: int) -> MemoryPendingChange:
    """用户否认：标记 rejected，不落库、不留变更事件。"""
    row = db.query(MemoryPendingChange).filter_by(id=change_id).first()
    if row is None or row.status != "pending":
        raise ValueError(f"待确认变更不存在或已处理: {change_id}")
    row.status = "rejected"
    return row

"""
注销冷静期到期执行任务（PRD 3.4 第四道防线的执行端）。

用法（OS cron / Windows 任务计划，建议每日一次）：
    python -m app.jobs.process_cancellations
幂等：execute_cancellation 后 cancellation_requested_at 置空，重复运行不重复删除。
"""
import logging

from app.db.session import SessionLocal
from app.core import account_cancellation as svc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jobs.process_cancellations")


def run() -> dict:
    db = SessionLocal()
    done, failed = 0, 0
    try:
        due = svc.find_due_cancellations(db)
        logger.info("到期待执行注销: %d 个", len(due))
        for user in due:
            try:
                svc.execute_cancellation(db, user)
                db.commit()
                done += 1
            except Exception:
                db.rollback()
                failed += 1
                logger.exception("执行注销失败 user_id=%s", user.id)
        return {"due": len(due), "done": done, "failed": failed}
    finally:
        db.close()


if __name__ == "__main__":
    result = run()
    logger.info("完成: %s", result)

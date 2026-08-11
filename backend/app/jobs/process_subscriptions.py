"""
订阅到期/宽限期处理任务（PRD 8.2 / 5.4-⑭）。cron 每日一次：
    python -m app.jobs.process_subscriptions
处理两类：
  1) past_due 且宽限期已过 → 终止 + S4→S3；
  2) active 且已过期且不续费（取消周期末生效）→ 终止 + S4→S3。
幂等：终止后 status=expired，重复运行不重复处理。
"""
import logging
from datetime import datetime

from app.db.session import SessionLocal
from app.core.billing import service as billing
from app.models.order import Subscription
from app.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jobs.process_subscriptions")


def run() -> dict:
    db = SessionLocal()
    lapsed = 0
    try:
        now = datetime.utcnow()
        subs = (
            db.query(Subscription)
            .filter(Subscription.status.in_(("active", "past_due")))
            .all()
        )
        for sub in subs:
            due = False
            if sub.status == "past_due" and sub.grace_until and sub.grace_until.replace(tzinfo=None) <= now:
                due, reason = True, "grace_expired"
            elif (sub.status == "active" and not sub.auto_renew
                  and sub.expires_at and sub.expires_at.replace(tzinfo=None) <= now):
                due, reason = True, "period_ended"
            if not due:
                continue
            user = db.query(User).filter_by(id=sub.user_id).first()
            if user is None:
                continue
            try:
                billing.lapse_subscription(db, user, sub, reason=reason)
                db.commit()
                lapsed += 1
            except Exception:
                db.rollback()
                logger.exception("降级失败 user_id=%s", sub.user_id)
        return {"checked": len(subs), "lapsed": lapsed}
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("完成: %s", run())

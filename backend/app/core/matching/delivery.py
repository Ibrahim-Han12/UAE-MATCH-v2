"""
T0 送达与到期处理（PRD 6.1/6.3/6.4）。

送达：approved pair → 双方通知（S4+ 全文；S3 候补只收"有人想认识你"teaser——付费墙核心触发器）。
到期：72h 未响应 → 礼貌关闭（视同婉拒不采集理由）。"想再了解"延长 48h 仅一次。
"""
import logging
from datetime import datetime, timedelta
from typing import Dict

from sqlalchemy.orm import Session

from app.core import notify
from app.core.matching.config import load as load_config
from app.core.risk import log_event
from app.models.reco_pair import RecoPair
from app.models.user import User

logger = logging.getLogger(__name__)


def _deliver_to(db: Session, user_id: int, pair: RecoPair) -> None:
    user = db.query(User).filter_by(id=user_id).first()
    if user is None:
        return
    if user.status in ("S4", "S5"):
        notify.send(
            db, user_id, type="reco_delivered",
            title="本周的推荐信到了",
            body="小缘为你准备了一封新的推荐信，72 小时内回应有效。",
            payload={"reco_pair_id": pair.id},
            channels=["inapp", "push", "email"],   # 周五送达=仪式感承诺，三通道
        )
    else:
        # S3 候补：teaser 不含对方详情（PRD 6.4 付费墙触发器）
        notify.send(
            db, user_id, type="reco_teaser",
            title="有人想认识你",
            body="本周的推荐里出现了你。开通会员即可查看对方并回应。",
            payload={"reco_pair_id": pair.id},
            channels=["inapp", "push", "email"],
        )
    log_event(db, user_id=user_id, event_type="reco_delivered",
              metadata={"reco_pair_id": pair.id, "batch_id": pair.batch_id})


def run_stage_t0(db: Session, batch_id: str) -> Dict[str, int]:
    """T0 周五 20:00：approved → delivered + 双方通知（幂等：delivered 不重发）。"""
    cfg = load_config()
    window = cfg["allocation"]["response_window_hours"]
    pairs = db.query(RecoPair).filter_by(batch_id=batch_id, status="approved").all()
    delivered = 0
    for pair in pairs:
        pair.status = "delivered"
        pair.delivered_at = datetime.utcnow()
        pair.expires_at = pair.delivered_at + timedelta(hours=window)
        _deliver_to(db, pair.user_low_id, pair)
        _deliver_to(db, pair.user_high_id, pair)
        delivered += 1
    logger.info("T0 batch=%s delivered=%d", batch_id, delivered)
    return {"delivered": delivered}


def run_expire(db: Session) -> Dict[str, int]:
    """到期关闭：72h（或延长后）未双方接受 → expired，视同婉拒不采集理由。"""
    now = datetime.utcnow()
    pairs = (
        db.query(RecoPair)
        .filter(RecoPair.status == "delivered", RecoPair.expires_at.isnot(None))
        .all()
    )
    expired = 0
    for pair in pairs:
        if pair.expires_at.replace(tzinfo=None) > now:
            continue
        pair.status = "expired"
        for uid in (pair.user_low_id, pair.user_high_id):
            log_event(db, user_id=uid, event_type="reco_expired",
                      metadata={"reco_pair_id": pair.id})
        expired += 1
    logger.info("expire: closed=%d", expired)
    return {"expired": expired}

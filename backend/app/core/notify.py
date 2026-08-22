"""
通知服务（hld-m2-design.md §8）：站内信必达底座 + Web Push 主通道 + 邮件兜底。

M2 范围：站内信真实落库（废除 v1.0 桩）；Push/Email 为适配器骨架（mock 记日志），
供应商/VAPID 就绪后换实现不动业务代码。每次发送记 notification_sent 事件（到达率埋点）。
"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.risk import log_event
from app.models.reco_pair import Notification

logger = logging.getLogger(__name__)


class MockPushProvider:
    def send(self, user_id: int, title: str, body: str) -> bool:
        logger.info("[MOCK PUSH] user=%s title=%s", user_id, title)
        return True


class MockEmailProvider:
    def send(self, user_id: int, title: str, body: str) -> bool:
        logger.info("[MOCK EMAIL] user=%s title=%s", user_id, title)
        return True


_push = MockPushProvider()
_email = MockEmailProvider()


def send(
    db: Session, user_id: int, *,
    type: str, title: str, body: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    channels: Optional[List[str]] = None,
) -> Notification:
    """
    发送通知：站内信必落库；push 主通道；email 仅在显式要求时兜底
    （如周五推荐信 T0：channels=["inapp","push","email"]）。不 commit。
    """
    channels = channels or ["inapp", "push"]
    sent = ["inapp"]

    row = Notification(user_id=user_id, type=type, title=title, body=body, payload=payload)
    db.add(row)

    if "push" in channels:
        try:
            if _push.send(user_id, title, body or ""):
                sent.append("push")
        except Exception:
            logger.exception("push 发送失败 user=%s", user_id)
            if "email" in channels:
                try:
                    if _email.send(user_id, title, body or ""):
                        sent.append("email")
                except Exception:
                    logger.exception("email 兜底失败 user=%s", user_id)
    elif "email" in channels:
        try:
            if _email.send(user_id, title, body or ""):
                sent.append("email")
        except Exception:
            logger.exception("email 发送失败 user=%s", user_id)

    row.channels_sent = sent
    log_event(db, user_id=user_id, event_type="notification_sent",
              metadata={"type": type, "channels": sent})
    return row

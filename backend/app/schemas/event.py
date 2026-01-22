from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EventLogRead(BaseModel):
    id: int
    event_type: str
    user_id: int
    target_user_id: Optional[int] = None
    match_pair_id: Optional[int] = None
    message_id: Optional[int] = None
    report_id: Optional[int] = None
    meta: Optional[str] = None      # ← 对应 EventLog.meta
    created_at: datetime

    class Config:
        from_attributes = True

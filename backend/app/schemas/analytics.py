from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.profile import UserProfileRead
from app.schemas.match_preference import MatchPreferenceRead
from app.schemas.chat import ChatMessageRead


class UserStats(BaseModel):
    total_likes_sent: int
    total_likes_received: int
    total_matches: int
    total_messages_sent: int
    total_messages_received: int
    total_reports_made: int
    total_reports_received: int


class UserSnapshot(BaseModel):
    user_id: int
    profile: Optional[UserProfileRead] = None
    preference: Optional[MatchPreferenceRead] = None
    stats: UserStats


class MatchContextForLLM(BaseModel):
    me_user_id: int
    target_user_id: int

    me_profile: Optional[UserProfileRead] = None
    me_preference: Optional[MatchPreferenceRead] = None

    target_profile: Optional[UserProfileRead] = None
    target_preference: Optional[MatchPreferenceRead] = None

    has_block_relation: bool
    has_match_pair: bool
    match_pair_id: Optional[int] = None

    recent_messages: List[ChatMessageRead]
    last_report_by_me: Optional[str] = None
    last_report_against_target: Optional[str] = None

    generated_at: datetime

from typing import Optional

from pydantic import BaseModel


class MatchActionRequest(BaseModel):
    target_user_id: int
    action_type: str  # like / pass / super_like


class MatchActionResponse(BaseModel):
    target_user_id: int
    action_type: str
    is_mutual_match: bool
    match_pair_id: Optional[int] = None

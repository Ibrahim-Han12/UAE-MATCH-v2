from datetime import datetime

from pydantic import BaseModel

from app.schemas.profile import UserProfileRead


class MyMatchItem(BaseModel):
    match_pair_id: int
    other_user_id: int
    created_at: datetime
    status: str
    other_profile: UserProfileRead

    class Config:
        from_attributes = True

from typing import List, Optional

from pydantic import BaseModel

from app.schemas.profile import UserProfileRead


class MatchCandidate(BaseModel):
    user_id: int
    nickname: Optional[str] = None
    city: Optional[str] = None
    bio: Optional[str] = None
    # 兼容性得分（先占位，将来可以接入真正的算法）
    compatibility_score: float = 0.0
    # 完整的 profile 信息（用于前端展示详细信息）
    profile: Optional[UserProfileRead] = None
    # 匹配理由列表
    reasons: Optional[List[str]] = None

    class Config:
        orm_mode = True


class MatchSuggestionsResponse(BaseModel):
    total_candidates: int        # 符合条件的总人数（粗略）
    returned_count: int          # 本次实际返回多少人
    items: List[MatchCandidate]


class MatchSummary(BaseModel):
    match_pair_id: int
    other_user_id: int
    other_nickname: Optional[str] = None
    # 添加完整的用户资料信息
    other_user_profile: Optional[UserProfileRead] = None

    class Config:
        from_attributes = True

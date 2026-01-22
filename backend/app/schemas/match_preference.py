from typing import Optional

from pydantic import BaseModel


class MatchPreferenceBase(BaseModel):
    preferred_gender: Optional[str] = None         # male / female / any
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    min_height_cm: Optional[int] = None
    max_height_cm: Optional[int] = None

    min_income_monthly_aed: Optional[int] = None
    education_level: Optional[str] = None

    marriage_timeline: Optional[str] = None        # within_1_year / 1_3_years / not_sure
    want_children: Optional[str] = None            # yes / no / maybe
    plan_settle_in_uae: Optional[bool] = None
    plan_return_china: Optional[str] = None        # yes / no / maybe

    religion: Optional[str] = None
    mbti: Optional[str] = None

    notes: Optional[str] = None


class MatchPreferenceUpdate(MatchPreferenceBase):
    pass


class MatchPreferenceRead(MatchPreferenceBase):
    id: int

    class Config:
        from_attributes = True

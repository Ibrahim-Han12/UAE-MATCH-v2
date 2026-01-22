from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.match_preference import MatchPreference
from app.schemas.match_preference import MatchPreferenceRead, MatchPreferenceUpdate

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("/me", response_model=MatchPreferenceRead)
def get_my_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    prefs: Optional[MatchPreference] = (
        db.query(MatchPreference)
        .filter(MatchPreference.user_id == current_user.id)
        .first()
    )

    if prefs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="尚未填写相亲偏好",
        )

    return prefs


@router.put("/me", response_model=MatchPreferenceRead)
def upsert_my_preferences(
    prefs_in: MatchPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    创建 / 更新当前用户的相亲偏好。
    """
    prefs: Optional[MatchPreference] = (
        db.query(MatchPreference)
        .filter(MatchPreference.user_id == current_user.id)
        .first()
    )

    if prefs is None:
        prefs = MatchPreference(user_id=current_user.id)
        db.add(prefs)

    update_data = prefs_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prefs, field, value)

    db.commit()
    db.refresh(prefs)

    return prefs

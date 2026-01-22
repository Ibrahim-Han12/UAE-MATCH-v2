from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.profile import UserProfile
from app.schemas.profile import UserProfileRead, UserProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me", response_model=UserProfileRead)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    profile: Optional[UserProfile] = (
        db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="尚未填写个人资料",
        )

    return profile


@router.put("/me", response_model=UserProfileRead)
def upsert_my_profile(
    profile_in: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    创建 / 更新当前用户的个人资料。
    - 如果不存在，则创建新的记录；
    - 如果已存在，则按传入字段进行更新。
    """
    profile: Optional[UserProfile] = (
        db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    )

    if profile is None:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    # 只更新传入的字段（值为 None 的不动）
    update_data = profile_in.dict(exclude_unset=True)
    
    # 处理 extended_info：如果传入新的 extended_info，需要合并到现有的
    if 'extended_info' in update_data and update_data['extended_info'] is not None:
        if profile.extended_info:
            # 合并扩展信息
            profile.extended_info.update(update_data['extended_info'])
        else:
            profile.extended_info = update_data['extended_info']
        # 从 update_data 中移除，避免直接 setattr
        del update_data['extended_info']
    
    # 更新其他字段
    for field, value in update_data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)

    return profile

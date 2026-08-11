"""
Schema 字段 → 数据库落点的唯一映射（事实层路由，BR-202）。

抽取器落库、完成度计算、变更确认三方共用本映射——改字段落点只改这里。
D 类 + E1/E2 路由在 extractor.PSYCH_ROUTING（心理测评区块）；G/F3 见 extractor。
"""
from typing import Any, Dict, Optional, Set

from sqlalchemy.orm import Session

from app.models.profile import UserProfile
from app.models.match_preference import MatchPreference
from app.models.user_psych_profile import UserPsychProfile

# field_id → (model, column)。value 直接 setattr；对象/数组型列为 JSON。
PROFILE_ROUTES = {
    "A4": "height_cm",
    "A7": "income_band_aed",
    "A9": "visa_type",
    "A10": "has_children",
    "B1": "relocation_plan",
    "B2": "marriage_timeline",
    "B3": "children_plan",
    "B4": "parents_care_plan",
    "B5": "cross_cultural_openness",
    "B6": "distance_tolerance",
}
# 对象型字段的子键展开（A5/A6/A8 → 多列）
PROFILE_OBJECT_ROUTES = {
    "A5": {"level": "education_level", "institution": "education_institution"},
    "A6": {"industry": "occupation_industry", "role_type": "occupation_role_type"},
    "A8": {"emirate": "residence_emirate", "district": "residence_district"},
}
PREFERENCE_ROUTES = {
    "C5": "dealbreakers",
}
PREFERENCE_OBJECT_ROUTES = {
    "C1": {"min": "min_age", "max": "max_age"},
    "C2": {"min_cm": "min_height_cm", "max_cm": "max_height_cm"},
    "C3": {"education_floor": "education_floor", "income_floor_band": "income_floor_band"},
    "C4": {"same_emirate_only": "same_emirate_only"},
}
# C1-C4 抽取结果里可带 elasticity_value 子键 → 汇入 preferences.elasticity JSON
ELASTIC_FIELDS = ("C1", "C2", "C3", "C4")

# D 类完成度检查：psych profile 列非空即视为已采
PSYCH_FILLED_COLUMNS = {
    "D1": "attachment_style",
    "D2": "conflict_style",
    "D3": "family_role_expectation",
    "D4": "money_view",
}


def _get_or_create(db: Session, model, user_id: int):
    row = db.query(model).filter_by(user_id=user_id).first()
    if row is None:
        row = model(user_id=user_id)
        db.add(row)
        db.flush()
    return row


def apply_field(db: Session, user_id: int, field_id: str, value: Any) -> bool:
    """把一个 A/B/C 字段值写入正确落点。返回是否已处理。不 commit。"""
    if field_id in PROFILE_ROUTES:
        row = _get_or_create(db, UserProfile, user_id)
        setattr(row, PROFILE_ROUTES[field_id], value)
        return True

    if field_id in PROFILE_OBJECT_ROUTES and isinstance(value, dict):
        row = _get_or_create(db, UserProfile, user_id)
        for sub, col in PROFILE_OBJECT_ROUTES[field_id].items():
            if value.get(sub) is not None:
                setattr(row, col, value[sub])
        if field_id == "B1" and value.get("return_horizon_years") is not None:
            row.return_horizon_years = value["return_horizon_years"]
        return True
    # B1 的 enum+extra 混合形态：值为纯枚举字符串时走 PROFILE_ROUTES（上面已覆盖）

    if field_id in PREFERENCE_ROUTES:
        row = _get_or_create(db, MatchPreference, user_id)
        setattr(row, PREFERENCE_ROUTES[field_id], value)
        return True

    if field_id in PREFERENCE_OBJECT_ROUTES and isinstance(value, dict):
        row = _get_or_create(db, MatchPreference, user_id)
        for sub, col in PREFERENCE_OBJECT_ROUTES[field_id].items():
            if value.get(sub) is not None:
                setattr(row, col, value[sub])
        if field_id in ELASTIC_FIELDS and value.get("elasticity_value"):
            elasticity = dict(row.elasticity or {})
            elasticity[field_id] = value["elasticity_value"]
            row.elasticity = elasticity
        return True

    return False


def get_filled_field_ids(db: Session, user_id: int) -> Set[str]:
    """扫描三张事实表，返回已采集的字段 ID 集合（完成度分子）。"""
    filled: Set[str] = set()

    profile: Optional[UserProfile] = db.query(UserProfile).filter_by(user_id=user_id).first()
    if profile is not None:
        for fid, col in PROFILE_ROUTES.items():
            if getattr(profile, col) is not None:
                filled.add(fid)
        for fid, subs in PROFILE_OBJECT_ROUTES.items():
            # 对象字段：主子键（第一个）非空即视为已采（institution/district 等为可选）
            main_col = next(iter(subs.values()))
            if getattr(profile, main_col) is not None:
                filled.add(fid)

    pref: Optional[MatchPreference] = db.query(MatchPreference).filter_by(user_id=user_id).first()
    if pref is not None:
        for fid, col in PREFERENCE_ROUTES.items():
            if getattr(pref, col) is not None:
                filled.add(fid)
        for fid, subs in PREFERENCE_OBJECT_ROUTES.items():
            main_col = next(iter(subs.values()))
            if getattr(pref, main_col) is not None:
                filled.add(fid)

    psych: Optional[UserPsychProfile] = db.query(UserPsychProfile).filter_by(user_id=user_id).first()
    if psych is not None:
        for fid, col in PSYCH_FILLED_COLUMNS.items():
            if getattr(psych, col) is not None:
                filled.add(fid)

    return filled

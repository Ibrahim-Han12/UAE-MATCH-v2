from datetime import datetime
from typing import Any, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api.deps import get_db, get_current_user, get_current_active_user
from app.models.user import User
from app.models.profile import UserProfile
from app.models.match_preference import MatchPreference
from app.models.match_action import MatchAction
from app.models.match_pair import MatchPair
from app.models.user_block import UserBlock
from app.schemas.match import MatchCandidate, MatchSuggestionsResponse, MatchSummary
from app.schemas.profile import UserProfileRead
from app.schemas.interaction import MatchActionRequest, MatchActionResponse





router = APIRouter(prefix="/matches", tags=["matches"])


def _calc_age(birth_year: Optional[int]) -> Optional[int]:
    if not birth_year:
        return None
    return datetime.utcnow().year - birth_year


def _score_candidate(
    me_profile: UserProfile,
    me_pref: MatchPreference,
    candidate_profile: UserProfile,
    candidate_pref: Optional[MatchPreference],
) -> Tuple[float, List[str]]:
    """
    一个基础的兼容性打分函数。
    后续接入 AI 时，可以保留这个接口，但内部改成调用 AI。
    """
    score = 0.0
    reasons: List[str] = []

    # 1. 性别：自己的偏好（硬过滤）
    if me_pref.preferred_gender and me_pref.preferred_gender not in ("any", ""):
        if candidate_profile.gender != me_pref.preferred_gender:
            # 完全不符合性别偏好，直接淘汰
            return 0.0, []
        score += 30
        reasons.append("对方性别符合你的偏好")

    # 2. 对方的性别偏好：互相匹配加分
    if candidate_pref and candidate_pref.preferred_gender and candidate_pref.preferred_gender not in ("any", ""):
        if me_profile.gender == candidate_pref.preferred_gender:
            score += 10
            reasons.append("你也符合对方的性别偏好")

    # 3. 年龄：按区间加分
    my_age = _calc_age(me_profile.birth_year)
    cand_age = _calc_age(candidate_profile.birth_year)

    if me_pref.min_age or me_pref.max_age:
        if cand_age is not None:
            in_range = True
            if me_pref.min_age and cand_age < me_pref.min_age:
                in_range = False
            if me_pref.max_age and cand_age > me_pref.max_age:
                in_range = False
            if in_range:
                score += 20
                reasons.append("对方年龄在你的期望范围内")

    # 对方对年龄的偏好（互相匹配再加一点）
    if candidate_pref and (candidate_pref.min_age or candidate_pref.max_age):
        if my_age is not None:
            in_range = True
            if candidate_pref.min_age and my_age < candidate_pref.min_age:
                in_range = False
            if candidate_pref.max_age and my_age > candidate_pref.max_age:
                in_range = False
            if in_range:
                score += 10
                reasons.append("你的年龄也在对方的期望范围内")

    # 4. 身高（可选过滤）
    if me_pref.min_height_cm or me_pref.max_height_cm:
        if candidate_profile.height_cm is not None:
            in_range = True
            if me_pref.min_height_cm and candidate_profile.height_cm < me_pref.min_height_cm:
                in_range = False
            if me_pref.max_height_cm and candidate_profile.height_cm > me_pref.max_height_cm:
                in_range = False
            if in_range:
                score += 10
                reasons.append("对方身高在你的期望范围内")

    # 5. 地理位置相关：同城 / 同国更优先
    if (
        me_profile.current_country
        and candidate_profile.current_country
        and me_profile.current_country == candidate_profile.current_country
    ):
        score += 10
        reasons.append("你们目前在同一个国家")

    if (
        me_profile.current_city
        and candidate_profile.current_city
        and me_profile.current_city == candidate_profile.current_city
    ):
        score += 10
        reasons.append("你们目前在同一个城市")

    # 6. 婚恋节奏 / 去留打算的一致性（价值观向）
    if me_pref.marriage_timeline and candidate_pref and candidate_pref.marriage_timeline:
        if me_pref.marriage_timeline == candidate_pref.marriage_timeline:
            score += 8
            reasons.append("对婚姻时间规划比较一致")

    if me_pref.plan_settle_in_uae is not None and candidate_pref and candidate_pref.plan_settle_in_uae is not None:
        if me_pref.plan_settle_in_uae == candidate_pref.plan_settle_in_uae:
            score += 8
            reasons.append("对是否长期在阿联酋发展的看法相近")

    if me_pref.plan_return_china and candidate_pref and candidate_pref.plan_return_china:
        if me_pref.plan_return_china == candidate_pref.plan_return_china:
            score += 5
            reasons.append("对回国/不回国的想法相似")

    # 7. 宗教、MBTI、教育、收入这些可以当成轻量加分项
    if me_pref.religion and candidate_profile and candidate_profile.nationality:
        # 这里先简单判断：如果宗教偏好有值，且对方也有宗教字段，直接加一点；
        # 未来可以把 religion 拆得更细。
        if candidate_pref and candidate_pref.religion and candidate_pref.religion == me_pref.religion:
            score += 5
            reasons.append("在宗教信仰上更容易达成共识")

    if me_pref.education_level and candidate_profile.education_level:
        if candidate_profile.education_level == me_pref.education_level:
            score += 4
            reasons.append("对方学历符合你的期望")

    if me_pref.min_income_monthly_aed and candidate_pref and candidate_pref.min_income_monthly_aed:
        # 这里先简单用「对方期望的最低收入」跟你的期望比一比，真实收入以后可以接
        score += 2
        reasons.append("你们对收入水平的预期相差不大")

    # 8. MBTI：先简单一致加分，未来可以用更复杂 MBTI 兼容矩阵
    if me_pref.mbti and candidate_pref and candidate_pref.mbti:
        if me_pref.mbti == candidate_pref.mbti:
            score += 3
            reasons.append("你们的 MBTI 类型相同（或许更懂彼此）")

    # 最后做一个下限：没分就过滤掉
    if score <= 0:
        return 0.0, []

    # 归一化分数到 0-1 范围
    # 理论最大分：30(性别) + 10(对方性别偏好) + 20(年龄) + 10(对方年龄) + 10(身高) 
    #            + 10(同国) + 10(同城) + 8(婚恋节奏) + 8(定居) + 5(回国) 
    #            + 5(宗教) + 4(教育) + 2(收入) + 3(MBTI) = 136
    # 为了更合理，我们设置最大分为 100，超过100的按100处理
    max_possible_score = 100.0
    normalized_score = min(score / max_possible_score, 1.0)
    
    return normalized_score, reasons
    # 未来接 AI 时，可以把上面的逻辑：
    # - 先算一个 rule_based_score
    # - 再把双方信息丢给 AI，让 AI 输出一个调过权重后的最终 score 和 reasons
    # 这里先简单实现一个基础规则版，后续再扩展 AI 版
def _normalize_pair(user_a_id: int, user_b_id: int) -> tuple[int, int]:
    """
    保证 (user1_id, user2_id) 有序：小的在前。
    """
    return (user_a_id, user_b_id) if user_a_id < user_b_id else (user_b_id, user_a_id)

@router.get("/suggestions", response_model=MatchSuggestionsResponse)
def get_match_suggestions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(20, ge=1, le=50),
    strategy: str = Query("rule", description="目前仅支持 rule，未来可扩展 ai"),
) -> Any:
    """
    获取当前用户的匹配推荐列表（基础规则版 + 拉黑过滤）。
    """

    # 1. 拿自己的资料 & 偏好
    me_profile: Optional[UserProfile] = (
        db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    )
    if me_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先完善个人资料（/profile/me）",
        )

    me_pref: Optional[MatchPreference] = (
        db.query(MatchPreference)
        .filter(MatchPreference.user_id == current_user.id)
        .first()
    )
    if me_pref is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先填写相亲偏好（/preferences/me）",
        )

    # 2. 计算与我存在拉黑关系的用户 ID 集合
    block_rows: list[UserBlock] = (
        db.query(UserBlock)
        .filter(
            (UserBlock.blocker_id == current_user.id)
            | (UserBlock.blocked_id == current_user.id)
        )
        .all()
    )

    blocked_user_ids: set[int] = set()
    for br in block_rows:
        if br.blocker_id == current_user.id:
            blocked_user_ids.add(br.blocked_id)
        if br.blocked_id == current_user.id:
            blocked_user_ids.add(br.blocker_id)

    # 3. 拉出候选人列表：其他活跃用户 + 资料公开的
    candidates = (
        db.query(User, UserProfile, MatchPreference)
        .join(UserProfile, UserProfile.user_id == User.id)
        .outerjoin(MatchPreference, MatchPreference.user_id == User.id)
        .filter(User.id != current_user.id)
        .filter(User.is_active == True)  # noqa: E712
        .filter(UserProfile.is_public == True)  # noqa: E712
        .all()
    )

    scored_candidates: List[MatchCandidate] = []

    for other_user, other_profile, other_pref in candidates:
        # 和我有拉黑关系的直接跳过（不出现在推荐里）
        if other_user.id in blocked_user_ids:
            continue

        score, reasons = _score_candidate(
            me_profile=me_profile,
            me_pref=me_pref,
            candidate_profile=other_profile,
            candidate_pref=other_pref,
        )
        if score <= 0:
            continue

        profile_read = UserProfileRead.model_validate(other_profile)

        scored_candidates.append(
            MatchCandidate(
                user_id=other_user.id,
                compatibility_score=round(score, 2),
                reasons=reasons,
                profile=profile_read,
            )
        )

    # 4. 排序 + 截断
    scored_candidates.sort(key=lambda c: c.compatibility_score, reverse=True)

    top_items = scored_candidates[:limit]

    return MatchSuggestionsResponse(
        total_candidates=len(scored_candidates),
        returned_count=len(top_items),
        items=top_items,
    )

@router.post("/action", response_model=MatchActionResponse)
def perform_match_action(
    action_in: MatchActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. 规范化 pair（把小 id 放前面，大 id 放后面）
    if current_user.id == action_in.target_user_id:
        raise HTTPException(status_code=400, detail="不能给自己点心动")

    uid1, uid2 = sorted([current_user.id, action_in.target_user_id])

    pair = (
        db.query(MatchPair)
        .filter(
            MatchPair.user1_id == uid1,
            MatchPair.user2_id == uid2,
        )
        .first()
    )
    if not pair:
        pair = MatchPair(
            user1_id=uid1,
            user2_id=uid2,
            status="pending",  # 初始状态
        )
        db.add(pair)
        db.flush()          # 拿到 pair.id

    # 2. 当前用户的 action（使用 actor_user_id 和 target_user_id）
    action = (
        db.query(MatchAction)
        .filter(
            MatchAction.actor_user_id == current_user.id,
            MatchAction.target_user_id == action_in.target_user_id,
        )
        .first()
    )
    if not action:
        action = MatchAction(
            actor_user_id=current_user.id,
            target_user_id=action_in.target_user_id,
            action_type=action_in.action_type,
        )
        db.add(action)
    else:
        action.action_type = action_in.action_type

    # 3. 判断是否形成 mutual like
    is_mutual_match = False
    if action_in.action_type == "like":
        # 查找对方是否也对当前用户点了 like
        other_action = (
            db.query(MatchAction)
            .filter(
                MatchAction.actor_user_id == action_in.target_user_id,
                MatchAction.target_user_id == current_user.id,
            )
            .first()
        )
        if other_action and other_action.action_type == "like":
            is_mutual_match = True
            pair.status = "active"  # ⭐ 关键：改成 active

    # 4. 真正落库
    db.commit()
    db.refresh(pair)
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[perform_match_action] 用户 {current_user.id} 对用户 {action_in.target_user_id} 执行 {action_in.action_type} 操作")
    logger.info(f"[perform_match_action] 是否互相匹配: {is_mutual_match}, MatchPair状态: {pair.status}, MatchPair ID: {pair.id}")

    return MatchActionResponse(
        target_user_id=action_in.target_user_id,
        action_type=action_in.action_type,
        is_mutual_match=is_mutual_match,
        match_pair_id=pair.id,
    )


@router.get("/my-matches", response_model=list[MatchSummary])
def get_my_matches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[get_my_matches] 用户ID: {current_user.id}")
    
    pairs = (
        db.query(MatchPair)
        .filter(
            MatchPair.status == "active",  # 只取互相 like 成功的
            or_(
                MatchPair.user1_id == current_user.id,
                MatchPair.user2_id == current_user.id,
            ),
        )
        .all()
    )
    
    logger.info(f"[get_my_matches] 找到 {len(pairs)} 个匹配对")

    result: list[MatchSummary] = []
    for p in pairs:
        # 找"对方"
        if p.user1_id == current_user.id:
            other = p.user2
        else:
            other = p.user1

        # 获取对方的显示名称（从 profile 或使用 email）
        other_nickname = other.email
        other_profile = db.query(UserProfile).filter(UserProfile.user_id == other.id).first()
        if other_profile and other_profile.display_name:
            other_nickname = other_profile.display_name

        # 将 profile 转换为 UserProfileRead 格式
        other_profile_read = None
        if other_profile:
            other_profile_read = UserProfileRead.model_validate(other_profile)

        result.append(
            MatchSummary(
                match_pair_id=p.id,
                other_user_id=other.id,
                other_nickname=other_nickname,
                other_user_profile=other_profile_read,
            )
        )

    return result


@router.get("/who-liked-me", response_model=list[MatchSummary])
def get_who_liked_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    查看对我点了 like 但还没形成 mutual match 的用户列表
    """
    # 1. 找到所有对我点了 like 的 actions
    received_likes = (
        db.query(MatchAction)
        .filter(
            MatchAction.target_user_id == current_user.id,
            MatchAction.action_type.in_(["like", "super_like"])
        )
        .all()
    )
    
    actor_ids = [a.actor_user_id for a in received_likes]
    
    # 2. 排除掉已经是 active match 的用户
    matched_pairs = (
        db.query(MatchPair)
        .filter(
            MatchPair.status == "active",
            or_(
                MatchPair.user1_id == current_user.id,
                MatchPair.user2_id == current_user.id,
            ),
        )
        .all()
    )
    
    matched_ids = set()
    for p in matched_pairs:
        matched_ids.add(p.user1_id if p.user1_id != current_user.id else p.user2_id)
        
    final_actor_ids = [aid for aid in actor_ids if aid not in matched_ids]
    
    # 3. 构造结果
    result = []
    if final_actor_ids:
        users = db.query(User).filter(User.id.in_(final_actor_ids)).all()
        for u in users:
            nickname = u.email
            profile = db.query(UserProfile).filter(UserProfile.user_id == u.id).first()
            if profile and profile.display_name:
                nickname = profile.display_name
                
            result.append(
                MatchSummary(
                    match_pair_id=0, # 还没有配对
                    other_user_id=u.id,
                    other_nickname=nickname,
                )
            )
            
    return result
@router.get("/recommendations", response_model=list[MatchCandidate])
def get_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    返回当前用户可以看到的“候选对象”列表：
    - 排除自己
    - 排除已经是 active 配对的用户
    （后面要的话可以再加：按偏好筛选、排除拉黑等）
    """

    # 1）先找出已经和我 active 配对过的对方 id
    pairs = (
        db.query(MatchPair)
        .filter(
            MatchPair.status == "active",
            or_(
                MatchPair.user1_id == current_user.id,
                MatchPair.user2_id == current_user.id,
            ),
        )
        .all()
    )

    matched_ids: set[int] = set()
    for p in pairs:
        if p.user1_id != current_user.id:
            matched_ids.add(p.user1_id)
        if p.user2_id != current_user.id:
            matched_ids.add(p.user2_id)

    # 2）从 User 里挑出“不是我 + 也没和我配对过”的人
    q = db.query(User).filter(User.id != current_user.id)
    if matched_ids:
        q = q.filter(~User.id.in_(matched_ids))

    users = q.all()

    # 3）组装成 MatchCandidate 列表
    result: list[MatchCandidate] = []
    for u in users:
        result.append(
            MatchCandidate(
                user_id=u.id,
                nickname=getattr(u, "nickname", None),
                city=getattr(u, "city", None),
                bio=getattr(u, "bio", None),
            )
        )

    return result

"""
匹配推荐API端点
实现：SQL硬过滤 + 向量搜索 + GPT-4o-mini生成推荐语
"""
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.profile import UserProfile
from app.models.match_preference import MatchPreference
from app.models.user_embedding import UserEmbedding
from app.models.user_block import UserBlock
from app.models.match_pair import MatchPair
from app.models.user_recommendation_quota import UserRecommendationQuota
from app.core.openai_client import get_openai_client
from app.core.embedding_service import get_embedding_service
from app.core.config import settings

router = APIRouter(prefix="/match", tags=["match"])


def _get_current_month() -> str:
    """获取当前年月字符串（格式：2025-01）"""
    now = datetime.utcnow()
    return now.strftime("%Y-%m")


def _is_user_vip(db: Session, user_id: int) -> bool:
    """检查用户是否是VIP"""
    from app.models.order import Subscription
    active_subscription = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            Subscription.expires_at > datetime.utcnow(),
        )
        .first()
    )
    return active_subscription is not None


def _check_recommendation_quota(db: Session, user_id: int) -> bool:
    """检查推荐额度"""
    is_vip = _is_user_vip(db, user_id)
    month = _get_current_month()
    
    quota = (
        db.query(UserRecommendationQuota)
        .filter(
            UserRecommendationQuota.user_id == user_id,
            UserRecommendationQuota.month == month,
        )
        .first()
    )
    
    if not quota:
        quota_limit = settings.VIP_USER_RECOMMENDATION_QUOTA if is_vip else settings.DEFAULT_USER_RECOMMENDATION_QUOTA
        quota = UserRecommendationQuota(
            user_id=user_id,
            month=month,
            quota_limit=quota_limit,
            quota_used=0,
        )
        db.add(quota)
        db.commit()
        db.refresh(quota)
    
    return quota.quota_used < quota.quota_limit


def _apply_hard_filters(
    db: Session,
    current_user_id: int,
    current_profile: UserProfile,
    preferences: Optional[MatchPreference],
) -> List[UserProfile]:
    """
    应用硬过滤（SQL WHERE语句）
    过滤条件：年龄、身高、城市、性别等硬指标
    """
    # 构建查询
    query = db.query(UserProfile).filter(
        UserProfile.user_id != current_user_id,  # 排除自己
        UserProfile.is_public == True,  # 只推荐公开资料
    )
    
    # 获取当前用户的择偶偏好
    if preferences:
        # 性别过滤
        if preferences.preferred_gender and preferences.preferred_gender != "any":
            query = query.filter(UserProfile.gender == preferences.preferred_gender)
        
        # 年龄过滤
        if preferences.min_age and current_profile.birth_year:
            max_birth_year = datetime.now().year - preferences.min_age
            query = query.filter(UserProfile.birth_year <= max_birth_year)
        
        if preferences.max_age and current_profile.birth_year:
            min_birth_year = datetime.now().year - preferences.max_age
            query = query.filter(UserProfile.birth_year >= min_birth_year)
        
        # 身高过滤
        if preferences.min_height_cm:
            query = query.filter(UserProfile.height_cm >= preferences.min_height_cm)
        
        if preferences.max_height_cm:
            query = query.filter(UserProfile.height_cm <= preferences.max_height_cm)
        
        # 城市过滤（如果用户指定了期望城市）
        if preferences.notes and "城市" in preferences.notes:
            # 简单解析，实际可以更复杂
            preferred_cities = [city.strip() for city in preferences.notes.split(",") if "城市" in city]
            if preferred_cities:
                query = query.filter(UserProfile.current_city.in_(preferred_cities))
    
    # 排除已屏蔽的用户
    blocked_user_ids = (
        db.query(UserBlock.blocked_user_id)
        .filter(UserBlock.user_id == current_user_id)
        .all()
    )
    blocked_ids = [row[0] for row in blocked_user_ids]
    if blocked_ids:
        query = query.filter(~UserProfile.user_id.in_(blocked_ids))
    
    # 排除已经推荐过的用户（可选，根据业务需求）
    # 这里暂时不排除，允许重复推荐
    
    return query.all()


def _format_profile_for_ai(profile: UserProfile) -> str:
    """格式化用户资料，用于AI生成推荐语"""
    parts = []
    
    if profile.display_name:
        parts.append(f"昵称：{profile.display_name}")
    
    if profile.gender:
        parts.append(f"性别：{profile.gender}")
    
    if profile.birth_year:
        age = datetime.now().year - profile.birth_year
        parts.append(f"年龄：{age}岁")
    
    if profile.current_city:
        parts.append(f"所在城市：{profile.current_city}")
    
    if profile.occupation:
        parts.append(f"职业：{profile.occupation}")
    
    if profile.education_level:
        parts.append(f"学历：{profile.education_level}")
    
    if profile.bio:
        parts.append(f"自我介绍：{profile.bio}")
    
    if profile.extended_info:
        ext = profile.extended_info
        if ext.get("interests"):
            parts.append(f"兴趣爱好：{ext.get('interests')}")
        if ext.get("values"):
            parts.append(f"价值观：{ext.get('values')}")
    
    return "\n".join(parts)


@router.post("/recommend", response_model=Dict[str, Any])
def get_ai_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    获取AI匹配推荐
    流程：SQL硬过滤 → 向量搜索 → GPT-4o-mini生成推荐语
    """
    # 检查推荐额度
    if not _check_recommendation_quota(db, current_user.id):
        is_vip = _is_user_vip(db, current_user.id)
        quota_limit = settings.VIP_USER_RECOMMENDATION_QUOTA if is_vip else settings.DEFAULT_USER_RECOMMENDATION_QUOTA
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"本月推荐额度已用完（{quota_limit}次/月）。升级VIP或等待下月重置。",
        )
    
    # 获取当前用户资料和偏好
    current_profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )
    
    if not current_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先完善个人资料",
        )
    
    preferences = (
        db.query(MatchPreference)
        .filter(MatchPreference.user_id == current_user.id)
        .first()
    )
    
    # 步骤1：SQL硬过滤（年龄、身高、城市、性别）
    filtered_profiles = _apply_hard_filters(db, current_user.id, current_profile, preferences)
    
    if not filtered_profiles:
        return {
            "candidates": [],
            "message": "暂时没有找到符合条件的候选人，请调整筛选条件或稍后再试。",
        }
    
    # 步骤2：向量搜索（找出Top 5）
    embedding_service = get_embedding_service()
    
    # 确保当前用户有向量嵌入
    try:
        embedding_service.create_or_update_embedding(
            db, current_user.id, current_profile, preferences
        )
    except Exception as e:
        print(f"[WARNING] 创建用户向量嵌入失败: {e}")
    
    # 获取相似用户（只从硬过滤后的结果中搜索）
    filtered_user_ids = [p.user_id for p in filtered_profiles]
    
    # 获取所有候选用户的向量
    candidate_embeddings = (
        db.query(UserEmbedding)
        .filter(UserEmbedding.user_id.in_(filtered_user_ids))
        .all()
    )
    
    # 如果没有向量，返回硬过滤的结果（前5个）
    top_candidates_with_similarity = []
    if not candidate_embeddings:
        top_candidates = filtered_profiles[:5]
        # 为没有向量的候选人生成默认相似度
        for profile in top_candidates:
            top_candidates_with_similarity.append({
                "profile": profile,
                "similarity": 0.75,  # 默认相似度
            })
    else:
        # 计算相似度
        current_embedding = (
            db.query(UserEmbedding)
            .filter(UserEmbedding.user_id == current_user.id)
            .first()
        )
        
        if not current_embedding:
            # 如果当前用户没有向量，返回硬过滤的结果
            top_candidates = filtered_profiles[:5]
            for profile in top_candidates:
                top_candidates_with_similarity.append({
                    "profile": profile,
                    "similarity": 0.75,  # 默认相似度
                })
        else:
            # 计算相似度并排序
            current_vec = json.loads(current_embedding.embedding_vector)
            similarities = []
            
            for emb in candidate_embeddings:
                other_vec = json.loads(emb.embedding_vector)
                similarity = embedding_service.cosine_similarity(current_vec, other_vec)
                
                # 找到对应的profile
                profile = next((p for p in filtered_profiles if p.user_id == emb.user_id), None)
                if profile:
                    similarities.append({
                        "profile": profile,
                        "similarity": similarity,
                    })
            
            # 按相似度排序
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            top_candidates_with_similarity = similarities[:5]
            top_candidates = [item["profile"] for item in top_candidates_with_similarity]
    
    if not top_candidates:
        return {
            "candidates": [],
            "message": "暂时没有找到合适的候选人，请稍后再试。",
        }
    
    # 步骤3：GPT-4o-mini生成推荐语
    openai_client = get_openai_client()
    
    # 格式化当前用户资料
    current_user_text = _format_profile_for_ai(current_profile)
    
    # 为每个候选人生成推荐语
    recommendations = []
    # 保存相似度映射（用于后续查找）
    similarity_map = {}
    for item in top_candidates_with_similarity:
        similarity_map[item["profile"].user_id] = item["similarity"]
    
    for candidate in top_candidates:
        candidate_text = _format_profile_for_ai(candidate)
        
        # 获取实际相似度
        actual_similarity = similarity_map.get(candidate.user_id, 0.85)
        
        # 找出共同点（简单实现，可以从extended_info中提取）
        common_points = []
        if current_profile.extended_info and candidate.extended_info:
            current_interests = current_profile.extended_info.get("interests", [])
            candidate_interests = candidate.extended_info.get("interests", [])
            if isinstance(current_interests, list) and isinstance(candidate_interests, list):
                common_points = list(set(current_interests) & set(candidate_interests))
        
        # 构建Prompt
        recommendation_prompt = f"""这是女用户B的资料：
{current_user_text}

这是男嘉宾A的资料：
{candidate_text}

他们匹配度很高（向量相似度：{actual_similarity:.2f}）。
{"共同爱好：" + ", ".join(common_points) if common_points else "他们在多个方面都很契合"}

请用红娘的口吻，告诉B为什么要见A？
要求：
1. 语气温暖、专业，像真正的红娘
2. 重点突出他们的共同爱好和契合点
3. 字数控制在100-150字
4. 不要说出"作为AI"、"根据算法"这种话
5. 用emoji要适度（1-2个即可）
6. **重要：不要提到"性别符合偏好"、"对方性别就是你偏好的类型"这种显而易见的内容**
7. 避免使用模板化的套话，要基于实际资料进行分析

推荐语："""
        
        try:
            response = openai_client.chat_completion(
                messages=[
                    {"role": "system", "content": "你是一个专业的红娘，擅长为单身人士推荐合适的对象。不要提到性别匹配这种显而易见的内容。"},
                    {"role": "user", "content": recommendation_prompt}
                ],
                model=openai_client.model_gpt4o_mini,
                temperature=0.7,
                fallback_model=openai_client.model_gpt35,
            )
            
            recommendation_text = response["content"].strip()
            
            # 过滤掉弱智的推荐理由
            bad_keywords = ["性别符合", "对方性别", "性别就是你偏好", "性别匹配", "对方性别符合"]
            if any(keyword in recommendation_text for keyword in bad_keywords):
                # 如果包含弱智关键词，使用更通用的推荐语
                if common_points:
                    recommendation_text = f"根据你们的资料，{candidate.display_name}与你在{', '.join(common_points[:2])}等方面有很多共同点，值得认识一下～"
                else:
                    recommendation_text = f"根据你们的资料，{candidate.display_name}与你在兴趣爱好、价值观等方面有很多共同点，值得认识一下～"
            
            recommendations.append({
                "user_id": candidate.user_id,
                "display_name": candidate.display_name,
                "age": datetime.now().year - candidate.birth_year if candidate.birth_year else None,
                "city": candidate.current_city,
                "occupation": candidate.occupation,
                "bio": candidate.bio,
                "recommendation_reason": recommendation_text,
                "similarity_score": actual_similarity,
            })
        except Exception as e:
            # 如果生成推荐语失败，使用默认推荐语
            recommendations.append({
                "user_id": candidate.user_id,
                "display_name": candidate.display_name,
                "age": datetime.now().year - candidate.birth_year if candidate.birth_year else None,
                "city": candidate.current_city,
                "occupation": candidate.occupation,
                "bio": candidate.bio,
                "recommendation_reason": f"根据您的资料，{candidate.display_name}与您在很多方面都很契合，值得认识一下～",
                "similarity_score": 0.85,
            })
    
    # 更新推荐额度
    month = _get_current_month()
    quota = (
        db.query(UserRecommendationQuota)
        .filter(
            UserRecommendationQuota.user_id == current_user.id,
            UserRecommendationQuota.month == month,
        )
        .first()
    )
    if quota:
        quota.quota_used += 1
        db.commit()
    
    return {
        "candidates": recommendations,
        "quota_used": quota.quota_used if quota else 1,
        "quota_limit": quota.quota_limit if quota else settings.DEFAULT_USER_RECOMMENDATION_QUOTA,
    }













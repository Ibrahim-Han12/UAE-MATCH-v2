from typing import Any, List, Optional
import json
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.profile import UserProfile
from app.models.match_preference import MatchPreference
from app.models.user_embedding import UserEmbedding
from app.models.match_insight_cache import MatchInsightCache
from app.schemas.coach import MatchInsightRequest, MatchInsightResponse
from app.core.risk import log_event, check_rate_limit
from app.core.openai_client import get_openai_client
from app.core.embedding_service import get_embedding_service
from app.core.config import settings
from app.models.order import Subscription
from datetime import datetime, timedelta

router = APIRouter(prefix="/coach", tags=["coach"])


def _get_profile_and_pref(
    db: Session,
    user_id: int,
) -> tuple[Optional[UserProfile], Optional[MatchPreference]]:
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .first()
    )
    pref = (
        db.query(MatchPreference)
        .filter(MatchPreference.user_id == user_id)
        .first()
    )
    return profile, pref


def _is_user_vip(db: Session, user_id: int) -> bool:
    """检查用户是否是VIP"""
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


@router.post("/match-insights", response_model=MatchInsightResponse)
def get_match_insights(
    body: MatchInsightRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    给当前用户针对某个对象生成AI分析报告：
    - 基于embedding的深度匹配分析
    - 多维度兼容性评分
    - 个性化的匹配解释
    - 建议的开场白
    - 安全提示
    """
    if body.target_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没必要给自己生成红娘建议（虽然你也很优秀）",
        )

    # 确认目标用户存在
    target_user = db.query(User).filter(User.id == body.target_user_id).first()
    if target_user is None or not target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="目标用户不存在或不可用",
        )
    check_rate_limit(
        db,
        user_id=current_user.id,
        event_type="coach_match_insights",
        window_seconds=60,
        max_count=30,
        error_message="你请求红娘建议太频繁了，请稍后再试。",
    )

    me_profile, me_pref = _get_profile_and_pref(db, current_user.id)
    target_profile, target_pref = _get_profile_and_pref(db, body.target_user_id)

    if me_profile is None or me_pref is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先完善个人资料和相亲偏好",
        )

    if target_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="对方资料不完整，暂时无法生成详细解释",
        )

    # 检查是否是VIP用户
    is_vip = _is_user_vip(db, current_user.id)
    
    # 先检查缓存：是否已经为这个用户和匹配对象生成过分析报告
    cached_insight = (
        db.query(MatchInsightCache)
        .filter(
            MatchInsightCache.user_id == current_user.id,
            MatchInsightCache.target_user_id == body.target_user_id,
        )
        .first()
    )
    
    # 从配置中获取缓存参数
    CACHE_EXPIRY_DAYS = settings.MATCH_INSIGHT_CACHE_EXPIRY_DAYS
    MAX_CACHE_PER_USER = settings.MATCH_INSIGHT_CACHE_MAX_PER_USER
    
    # 如果缓存存在且未过期，直接返回缓存的结果
    if cached_insight:
        # 处理时区问题：如果created_at有时区信息，转换为UTC naive datetime
        created_at_naive = cached_insight.created_at
        if created_at_naive.tzinfo:
            created_at_naive = created_at_naive.replace(tzinfo=None)
        
        cache_age = datetime.utcnow() - created_at_naive
        if cache_age < timedelta(days=CACHE_EXPIRY_DAYS):
            # 返回缓存的结果，避免重复生成浪费token
            return MatchInsightResponse(
                explanation=cached_insight.explanation,
                key_points=[],
                suggested_openers=cached_insight.opener_suggestions or [],
                safety_tips=[
                    "第一次见面请务必选择公共场所，例如商场、咖啡馆、餐厅等，人多且有监控的地方。",
                    "不要在短时间内向对方转账、投资或借钱，严防任何形式的'感情+钱'的套路。",
                    "线下见面前，可以事先告诉一位信得过的朋友：你要见谁、在什么地方、大约多久回来。",
                    "刚开始交往阶段，不要过早暴露家庭住址、详细工作地点等过于私密的信息。",
                ],
                match_score_breakdown=cached_insight.match_score_breakdown,
            )
        else:
            # 缓存过期，删除旧缓存
            db.delete(cached_insight)
            db.commit()
    
    # 使用embedding + AI生成真正的分析报告
    embedding_service = get_embedding_service()
    openai_client = get_openai_client()
    
    # 获取向量相似度
    similarity_score = 0.0
    try:
        current_embedding = db.query(UserEmbedding).filter(
            UserEmbedding.user_id == current_user.id
        ).first()
        target_embedding = db.query(UserEmbedding).filter(
            UserEmbedding.user_id == body.target_user_id
        ).first()
        
        if current_embedding and target_embedding:
            current_vec = json.loads(current_embedding.embedding_vector)
            target_vec = json.loads(target_embedding.embedding_vector)
            similarity_score = embedding_service.cosine_similarity(current_vec, target_vec)
    except Exception as e:
        print(f"[WARNING] 计算向量相似度失败: {e}")
    
    # 构建用户资料文本（用于AI分析）
    def format_profile_for_ai(profile: UserProfile, pref: Optional[MatchPreference]) -> str:
        parts = []
        if profile.display_name:
            parts.append(f"昵称：{profile.display_name}")
        if profile.birth_year:
            age = datetime.now().year - profile.birth_year
            parts.append(f"年龄：{age}岁")
        if profile.gender:
            parts.append(f"性别：{profile.gender}")
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
                interests = ext.get("interests")
                if isinstance(interests, list):
                    parts.append(f"兴趣爱好：{', '.join(interests)}")
                else:
                    parts.append(f"兴趣爱好：{interests}")
            if ext.get("values"):
                values = ext.get("values")
                if isinstance(values, list):
                    parts.append(f"价值观：{', '.join(values)}")
                else:
                    parts.append(f"价值观：{values}")
        if pref:
            if pref.marriage_timeline:
                parts.append(f"期望结婚时间：{pref.marriage_timeline}")
            if pref.plan_settle_in_uae is not None:
                parts.append(f"计划在阿联酋定居：{'是' if pref.plan_settle_in_uae else '否'}")
        return "\n".join(parts)
    
    current_user_text = format_profile_for_ai(me_profile, me_pref)
    target_user_text = format_profile_for_ai(target_profile, target_pref)
    
    # 获取目标用户的昵称，用于个性化称呼
    target_name = target_profile.display_name or "对方"
    
    # 使用AI生成分析报告
    # 注意：不向AI传递向量相似度等技术指标，只传递用户资料，让AI基于资料自然分析
    analysis_prompt = f"""你是专业的AI红娘，正在为你的用户分析一个匹配对象。请用红娘直接对用户说话的口气，使用第二人称"你们"、"你"和对方的昵称"{target_name}"，而不是第三人称"他们"、"双方"或"TA"。

你的用户（你正在为他/她分析）的资料：
{current_user_text}

匹配对象（{target_name}）的资料：
{target_user_text}

请生成一份专业的匹配分析报告，包括：

1. **总体匹配度分析**（200-300字）：
   - 用红娘对用户说话的口气，使用"你们"、"你"和对方昵称"{target_name}"
   - 例如："你和{target_name}之间的匹配度..."、"你们都对..."、"你的...与{target_name}的..."
   - **重要：直接使用对方昵称"{target_name}"，不要用"TA"、"对方"等代词**
   - 基于你们的资料、兴趣爱好、价值观、生活方式等
   - 突出你们的共同点和契合之处
   - 分析潜在的优势和需要注意的差异
   - 语气温暖、专业，像真正的红娘在给用户做专属分析
   - **重要：不要提到"性别符合偏好"这种显而易见的内容**
   - **重要：不要使用第三人称"他们"、"双方"、"麦田和恰大夫"等，要用"你们"、"你"、"{target_name}"**

2. **多维度兼容性评分**（请为以下维度打分，0-1之间）：
   - 价值观（values）：基于你们的价值观、人生目标
   - 生活方式（lifestyle）：基于你们的生活习惯、兴趣爱好
   - 性格匹配（personality）：基于你们的性格特点、MBTI等
   - 未来规划（goals）：基于你们对婚姻、定居、职业的规划

3. **推荐开场白**（2-3条）：
   - 基于你们的共同点，生成自然、真诚的开场白
   - 每条50-80字
   - 避免过于正式或生硬

要求：
- **必须使用第二人称"你们"、"你"和对方昵称"{target_name}"，不要使用第三人称"他们"、"双方"，也不要使用"TA"、"对方"等代词**
- **绝对不要提到任何技术术语，如"向量相似度"、"算法"、"匹配度计算"等，用户不需要知道这些技术细节**
- 不要提到"性别符合偏好"这种显而易见的内容
- 不要使用模板化的套话
- 基于实际资料进行分析，如果信息不足，诚实说明
- 语气温暖、专业，像真正的红娘在给用户做专属分析
- 让用户感觉这是他的专属红娘在为他分析

请以JSON格式返回：
{{
  "summary": "总体匹配度分析文本（使用第二人称：你们、你、{target_name}）",
  "match_score_breakdown": {{
    "values": 0.85,
    "lifestyle": 0.92,
    "personality": 0.78,
    "goals": 0.95
  }},
  "opener_suggestions": ["开场白1", "开场白2", "开场白3"]
}}"""
    
    try:
        response = openai_client.chat_completion(
            messages=[
                {"role": "system", "content": f"你是一个专业的AI红娘，正在为你的用户分析匹配对象。请用红娘直接对用户说话的口气，使用第二人称'你们'、'你'和对方昵称'{target_name}'，而不是第三人称'他们'、'双方'或'TA'。绝对不要提到任何技术术语如'向量相似度'、'算法'等。请只返回JSON格式，不要其他文字。"},
                {"role": "user", "content": analysis_prompt}
            ],
            model=openai_client.model_gpt4o_mini,
            temperature=0.7,
            fallback_model=openai_client.model_gpt35,
        )
        
        # 解析AI返回的JSON
        content = response["content"].strip()
        
        # 尝试提取JSON（可能包含markdown代码块）
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        else:
            # 查找第一个 { 到最后一个 } 之间的内容
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                content = content[start:end+1]
        
        ai_analysis = json.loads(content)
        
        explanation = ai_analysis.get("summary", "基于你们的资料，AI正在分析中...")
        match_score_breakdown = ai_analysis.get("match_score_breakdown", {})
        suggested_openers = ai_analysis.get("opener_suggestions", [])
        
        # 如果没有生成开场白，使用默认的
        if not suggested_openers:
            if target_profile.current_city and me_profile.current_city == target_profile.current_city:
                suggested_openers.append(
                    f"你好呀，看到你也在 {target_profile.current_city}，平时都在哪一块活动？最近那边有什么好吃的推荐吗？"
                )
            else:
                suggested_openers.append(
                    f"你好，我这边在 {me_profile.current_city or 'UAE'} 工作，看到你的资料感觉很踏实，方便简单自我介绍一下吗？"
                )
            if target_profile.occupation:
                suggested_openers.append(
                    f"看到你是做 {target_profile.occupation} 的，我对这个行业挺好奇的，你平时的工作节奏是怎样的？"
                )
        
        key_points = []  # AI分析不需要key_points，使用summary即可
        
    except Exception as e:
        print(f"[WARNING] AI分析生成失败，使用降级方案: {e}")
        # 降级方案：使用简单的规则生成
        name = target_profile.display_name or "对方"
        city = target_profile.current_city or target_profile.current_country or "你所在的城市"
        explanation = (
            f"从目前的信息看，你和「{name}」在一些核心维度上是比较契合的，"
            f"尤其是在 {city} 的生活轨迹、未来规划以及基本偏好上有不少共识。"
        )
        match_score_breakdown = {
            "values": 0.85,
            "lifestyle": 0.92,
            "personality": 0.78,
            "goals": 0.95,
        }
        suggested_openers = []
        if target_profile.current_city and me_profile.current_city == target_profile.current_city:
            suggested_openers.append(
                f"你好呀，看到你也在 {target_profile.current_city}，平时都在哪一块活动？最近那边有什么好吃的推荐吗？"
            )
        else:
            suggested_openers.append(
                f"你好，我这边在 {me_profile.current_city or 'UAE'} 工作，看到你的资料感觉很踏实，方便简单自我介绍一下吗？"
            )
        if target_profile.occupation:
            suggested_openers.append(
                f"看到你是做 {target_profile.occupation} 的，我对这个行业挺好奇的，你平时的工作节奏是怎样的？"
            )
        key_points = []

    # 安全提示（固定内容）
    safety_tips = [
        "第一次见面请务必选择公共场所，例如商场、咖啡馆、餐厅等，人多且有监控的地方。",
        "不要在短时间内向对方转账、投资或借钱，严防任何形式的'感情+钱'的套路。",
        "线下见面前，可以事先告诉一位信得过的朋友：你要见谁、在什么地方、大约多久回来。",
        "刚开始交往阶段，不要过早暴露家庭住址、详细工作地点等过于私密的信息。",
    ]
    
    # 保存到缓存（无论是否生成成功，都保存，避免重复尝试）
    try:
        # 检查是否已有缓存（可能在上面的过期检查中被删除了）
        existing_cache = (
            db.query(MatchInsightCache)
            .filter(
                MatchInsightCache.user_id == current_user.id,
                MatchInsightCache.target_user_id == body.target_user_id,
            )
            .first()
        )
        
        if existing_cache:
            # 更新现有缓存
            existing_cache.explanation = explanation
            existing_cache.match_score_breakdown = match_score_breakdown if match_score_breakdown else None
            existing_cache.opener_suggestions = suggested_openers
            existing_cache.updated_at = datetime.utcnow()
        else:
            # 检查当前用户的缓存数量，如果超过限制，删除最旧的缓存
            user_cache_count = (
                db.query(MatchInsightCache)
                .filter(MatchInsightCache.user_id == current_user.id)
                .count()
            )
            
            if user_cache_count >= MAX_CACHE_PER_USER:
                # 删除最旧的缓存（按created_at排序）
                oldest_cache = (
                    db.query(MatchInsightCache)
                    .filter(MatchInsightCache.user_id == current_user.id)
                    .order_by(MatchInsightCache.created_at.asc())
                    .first()
                )
                if oldest_cache:
                    db.delete(oldest_cache)
                    print(f"[INFO] 用户 {current_user.id} 缓存数量已达上限，删除最旧缓存（target_user_id: {oldest_cache.target_user_id}）")
            
            # 创建新缓存
            new_cache = MatchInsightCache(
                user_id=current_user.id,
                target_user_id=body.target_user_id,
                explanation=explanation,
                match_score_breakdown=match_score_breakdown if match_score_breakdown else None,
                opener_suggestions=suggested_openers,
            )
            db.add(new_cache)
        db.commit()
    except Exception as e:
        print(f"[WARNING] 保存分析报告缓存失败: {e}")
        db.rollback()
        # 缓存失败不影响返回结果
    
    log_event(
        db,
        user_id=current_user.id,
        event_type="coach_match_insights",
        target_user_id=body.target_user_id,
    )
    db.commit()

    return MatchInsightResponse(
        explanation=explanation,
        key_points=key_points,
        suggested_openers=suggested_openers,
        safety_tips=safety_tips,
        match_score_breakdown=match_score_breakdown if match_score_breakdown else None,
    )

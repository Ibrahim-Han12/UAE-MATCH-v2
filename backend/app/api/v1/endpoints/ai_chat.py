"""
AI红娘对话API端点
"""
import json
import re
from datetime import datetime, timedelta
from typing import Any, List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.profile import UserProfile
from app.models.match_preference import MatchPreference
from app.models.order import Subscription
from app.models.ai_conversation import AIConversation
from app.models.user_token_usage import UserTokenUsage
from app.models.user_recommendation_quota import UserRecommendationQuota
from app.models.global_ai_budget import GlobalAIBudget
from app.models.ai_memory_summary import AIMemorySummary
from app.schemas.ai_chat import (
    AIChatRequest,
    AIChatResponse,
    AIConversationHistory,
    StartRegistrationRequest,
    CompleteRegistrationRequest,
    TokenUsageResponse,
    RecommendationQuotaResponse,
    AIMemorySummaryResponse,
    AIRecommendationRequest,
    AIRecommendationResponse,
)
from app.core.openai_client import get_openai_client
from app.core.config import settings
from app.core.memory_service import get_memory_service
from app.core.embedding_service import get_embedding_service

router = APIRouter(prefix="/ai-chat", tags=["ai-chat"])


def _get_current_month() -> str:
    """获取当前年月字符串（格式：2025-01）"""
    now = datetime.utcnow()
    return now.strftime("%Y-%m")


def _get_or_create_token_usage(
    db: Session,
    user_id: int,
    is_vip: bool = False,
) -> UserTokenUsage:
    """获取或创建用户的Token使用记录"""
    month = _get_current_month()
    token_limit = settings.VIP_USER_TOKEN_LIMIT if is_vip else settings.DEFAULT_USER_TOKEN_LIMIT
    
    usage = (
        db.query(UserTokenUsage)
        .filter(
            UserTokenUsage.user_id == user_id,
            UserTokenUsage.month == month,
        )
        .first()
    )
    
    if not usage:
        usage = UserTokenUsage(
            user_id=user_id,
            month=month,
            tokens_used=0,
            tokens_limit=token_limit,
        )
        db.add(usage)
        db.commit()
        db.refresh(usage)
    else:
        # 如果已有记录但额度是旧的（10,000），自动升级到新额度（50,000）
        # 这样可以确保旧用户也能享受新的额度
        if not is_vip and usage.tokens_limit < settings.DEFAULT_USER_TOKEN_LIMIT:
            usage.tokens_limit = settings.DEFAULT_USER_TOKEN_LIMIT
            db.commit()
            db.refresh(usage)
    
    return usage


def _get_or_create_recommendation_quota(
    db: Session,
    user_id: int,
    is_vip: bool = False,
) -> UserRecommendationQuota:
    """获取或创建用户的推荐额度记录"""
    month = _get_current_month()
    quota_limit = settings.VIP_USER_RECOMMENDATION_QUOTA if is_vip else settings.DEFAULT_USER_RECOMMENDATION_QUOTA
    
    quota = (
        db.query(UserRecommendationQuota)
        .filter(
            UserRecommendationQuota.user_id == user_id,
            UserRecommendationQuota.month == month,
        )
        .first()
    )
    
    if not quota:
        quota = UserRecommendationQuota(
            user_id=user_id,
            month=month,
            quota_used=0,
            quota_limit=quota_limit,
        )
        db.add(quota)
        db.commit()
        db.refresh(quota)
    
    return quota


def _check_global_budget(db: Session) -> bool:
    """检查全局预算是否超限"""
    month = _get_current_month()
    budget = (
        db.query(GlobalAIBudget)
        .filter(GlobalAIBudget.month == month)
        .first()
    )
    
    if not budget:
        # 创建当月预算记录
        budget = GlobalAIBudget(
            month=month,
            budget_limit=Decimal(str(settings.GLOBAL_BUDGET_LIMIT)),
            budget_used=Decimal("0.00"),
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)
    
    # 检查是否超限（留10%缓冲）
    threshold = float(budget.budget_limit) * 0.9
    return float(budget.budget_used) < threshold


def _update_global_budget(db: Session, tokens_used: int, model: str):
    """更新全局预算（根据token使用量估算成本）"""
    # 简化的成本估算（实际应该根据OpenAI的定价计算）
    # GPT-3.5-turbo: $0.0015/1K input, $0.002/1K output
    # GPT-4: $0.03/1K input, $0.06/1K output
    cost_per_1k = 0.002 if "gpt-3.5" in model else 0.06
    estimated_cost = (tokens_used / 1000.0) * cost_per_1k
    
    month = _get_current_month()
    budget = (
        db.query(GlobalAIBudget)
        .filter(GlobalAIBudget.month == month)
        .first()
    )
    
    if budget:
        budget.budget_used += Decimal(str(estimated_cost))
        db.commit()


def _get_user_profile_dict(db: Session, user_id: int) -> Optional[dict]:
    """获取用户基本信息字典"""
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .first()
    )
    
    if not profile:
        return None
    
    return {
        "display_name": profile.display_name,
        "age": datetime.utcnow().year - profile.birth_year if profile.birth_year else None,
        "gender": profile.gender,
        "current_city": profile.current_city,
        "occupation": profile.occupation,
        "education_level": profile.education_level,
        "bio": profile.bio,
    }


def _get_recent_conversations(
    db: Session,
    user_id: int,
    conversation_type: str,
    limit: int = 10,
) -> List[dict]:
    """获取最近的对话历史"""
    conversations = (
        db.query(AIConversation)
        .filter(
            AIConversation.user_id == user_id,
            AIConversation.conversation_type == conversation_type,
        )
        .order_by(desc(AIConversation.created_at))
        .limit(limit)
        .all()
    )
    
    # 倒序，让最旧的在前
    conversations.reverse()
    
    return [
        {
            "role": conv.role,
            "content": conv.content,
        }
        for conv in conversations
    ]


def _get_memory_summary(db: Session, user_id: int) -> Optional[dict]:
    """获取用户的记忆摘要（VIP用户）"""
    summaries = (
        db.query(AIMemorySummary)
        .filter(AIMemorySummary.user_id == user_id)
        .all()
    )
    
    if not summaries:
        return None
    
    result = {}
    for summary in summaries:
        try:
            content = json.loads(summary.content) if isinstance(summary.content, str) else summary.content
            result[summary.summary_type] = content
        except:
            result[summary.summary_type] = {}
    
    return result


def _is_user_vip(db: Session, user_id: int) -> bool:
    """判断用户是否为VIP"""
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status == "active",
        )
        .first()
    )
    
    if not subscription:
        return False
    
    # 检查是否过期
    if subscription.expires_at and subscription.expires_at < datetime.utcnow():
        return False
    
    # 检查是否为premium
    return subscription.plan_type == "premium"


@router.post("/send-message", response_model=AIChatResponse)
def send_message(
    request: AIChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    发送消息给AI红娘
    """
    # 检查全局预算
    if not _check_global_budget(db):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI服务暂时不可用，预算已超限",
        )
    
    # 检查用户Token配额
    is_vip = _is_user_vip(db, current_user.id)
    token_usage = _get_or_create_token_usage(db, current_user.id, is_vip)
    
    # 检查是否超限
    if token_usage.tokens_used >= token_usage.tokens_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"本月对话额度已用完（{token_usage.tokens_used}/{token_usage.tokens_limit} tokens）。升级VIP或等待下月重置。",
        )
    
    # 获取用户信息和对话历史
    user_profile = _get_user_profile_dict(db, current_user.id)
    recent_conversations = _get_recent_conversations(
        db,
        current_user.id,
        request.conversation_type,
        limit=50 if is_vip else 10,
    )
    
    # 获取滚动摘要（长期记忆）- 所有用户都使用，不只是VIP
    memory_service = get_memory_service()
    memory_summary = memory_service.get_memory(db, current_user.id)
    
    # 获取用户风格偏好（从profile的extended_info中）
    user_style_preference = None
    if user_profile and user_profile.get("extended_info"):
        ext_info = user_profile.get("extended_info", {})
        if isinstance(ext_info, dict):
            user_style_preference = ext_info.get("chat_style_preference") or ext_info.get("personality_style")
    
    # 构建System Prompt
    openai_client = get_openai_client()
    system_prompt = openai_client.get_system_prompt_for_user(
        user_id=current_user.id,
        user_profile=user_profile,
        recent_conversations=recent_conversations,
        memory_summary=memory_summary,  # 现在是字符串格式
        conversation_type=request.conversation_type,
        user_style_preference=user_style_preference,
    )
    
    # 构建消息列表
    messages = openai_client.build_conversation_messages(
        system_prompt=system_prompt,
        conversation_history=recent_conversations,
        current_message=request.message,
    )
    
    # 选择模型：全部使用GPT-4o-mini（成本低、速度快、性能好）
    # 如果GPT-4o-mini不可用，会自动降级到GPT-3.5-turbo
    model = openai_client.model_gpt4o_mini
    fallback_model = openai_client.model_gpt35
    
    # 调用OpenAI API
    try:
        response = openai_client.chat_completion(
            messages=messages,
            model=model,
            temperature=0.7,
            max_retries=3,
            fallback_model=fallback_model,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI服务暂时不可用：{str(e)}",
        )
    
    # 保存对话记录
    user_message = AIConversation(
        user_id=current_user.id,
        role="user",
        content=request.message,
        conversation_type=request.conversation_type,
        tokens_used=0,  # 用户消息不单独计token
        model=response["model"],
    )
    db.add(user_message)
    
    ai_message = AIConversation(
        user_id=current_user.id,
        role="assistant",
        content=response["content"],
        conversation_type=request.conversation_type,
        tokens_used=response["tokens_used"],
        model=response["model"],
    )
    db.add(ai_message)
    
    # 更新Token使用
    token_usage.tokens_used += response["tokens_used"]
    
    # 更新全局预算
    _update_global_budget(db, response["tokens_used"], response["model"])
    
    db.commit()
    
    # 对话结束后，异步更新长期记忆（滚动摘要）
    # 注意：这里可以改为后台任务，避免阻塞响应
    try:
        memory_service.update_memory_after_conversation(db, current_user.id, limit=10)
        db.commit()
    except Exception as e:
        # 记忆更新失败不影响主流程
        print(f"[WARNING] 更新长期记忆失败: {e}")
    
    return AIChatResponse(
        content=response["content"],
        tokens_used=response["tokens_used"],
        model=response["model"],
        conversation_id=ai_message.id,
    )


@router.get("/history", response_model=List[AIConversationHistory])
def get_conversation_history(
    conversation_type: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    获取对话历史
    """
    import logging
    logger = logging.getLogger(__name__)
    
    query = (
        db.query(AIConversation)
        .filter(AIConversation.user_id == current_user.id)
    )
    
    logger.info(f"[get_conversation_history] 用户ID: {current_user.id}, conversation_type: {conversation_type}, limit: {limit}")
    
    if conversation_type:
        query = query.filter(AIConversation.conversation_type == conversation_type)
        logger.info(f"[get_conversation_history] 过滤条件: conversation_type == {conversation_type}")
    else:
        logger.info(f"[get_conversation_history] 无类型过滤，返回所有类型的对话")
    
    # 先查询总数（用于调试）
    total_count = query.count()
    logger.info(f"[get_conversation_history] 符合条件的记录总数: {total_count}")
    
    conversations = (
        query
        .order_by(desc(AIConversation.created_at))
        .limit(limit)
        .all()
    )
    
    logger.info(f"[get_conversation_history] 返回记录数: {len(conversations)}")
    if conversations:
        logger.info(f"[get_conversation_history] 第一条记录: id={conversations[0].id}, type={conversations[0].conversation_type}, role={conversations[0].role}")
    
    return conversations


@router.post("/start-registration")
def start_registration(
    request: StartRegistrationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    开始注册引导对话
    AI红娘主动打招呼并开始收集用户信息
    """
    # 检查是否已有完整profile（如果已有完整信息，不需要重新注册）
    existing_profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )
    
    # 检查profile是否完整（至少要有display_name或birth_year等关键信息）
    # 需要确保字段不是空字符串
    if existing_profile:
        has_display_name = existing_profile.display_name and existing_profile.display_name.strip()
        has_birth_year = existing_profile.birth_year
        has_city = existing_profile.current_city and existing_profile.current_city.strip()
        has_occupation = existing_profile.occupation and existing_profile.occupation.strip()
        
        if has_display_name or has_birth_year or has_city or has_occupation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="您已经完成过注册引导，如需修改资料请前往个人中心",
            )
    
    # 检查是否有未完成的注册对话
    existing_conversations = (
        db.query(AIConversation)
        .filter(
            AIConversation.user_id == current_user.id,
            AIConversation.conversation_type == "registration",
        )
        .order_by(AIConversation.created_at)
        .all()
    )
    
    # 如果已经有对话记录，返回第一条消息（不创建新消息）
    if existing_conversations:
        first_message = existing_conversations[0]
        return {
            "message": first_message.content,
            "conversation_id": first_message.id,
        }
    
    # 如果没有对话记录，创建新的开场消息
    greeting = (
        "你好！我是小缘，你的专属AI红娘。很高兴认识你！\n\n"
        "我想通过聊天来了解你，这样我才能为你找到最合适的人。"
        "我们可以像朋友一样聊天，不用紧张～\n\n"
        "能告诉我你今年多大吗？我想知道我们是在和哪个年龄段的朋友聊天呢～"
    )
    
    # 保存开场消息
    try:
        greeting_msg = AIConversation(
            user_id=current_user.id,
            role="assistant",
            content=greeting,
            conversation_type="registration",
            tokens_used=0,  # 开场白不计token
            model="system",
        )
        db.add(greeting_msg)
        db.commit()
        db.refresh(greeting_msg)
        
        return {
            "message": greeting,
            "conversation_id": greeting_msg.id,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存开场消息失败：{str(e)}",
        )


@router.post("/complete-registration")
def complete_registration(
    request: CompleteRegistrationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    完成注册引导对话
    AI红娘总结收集到的信息，并存储到数据库
    """
    if not request.confirm:
        return {"message": "好的，我们继续聊天～"}
    
    # 获取所有注册引导对话
    conversations = (
        db.query(AIConversation)
        .filter(
            AIConversation.user_id == current_user.id,
            AIConversation.conversation_type == "registration",
        )
        .order_by(AIConversation.created_at)
        .all()
    )
    
    if not conversations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有找到注册引导对话记录",
        )
    
    # 构建完整对话历史（用于AI总结）
    conversation_text = "\n".join([
        f"{conv.role}: {conv.content}"
        for conv in conversations
    ])
    
    # 定义JSON提取函数
    def extract_json_from_text(text: str) -> dict:
        """从文本中提取JSON（可能包含markdown代码块或其他文字）"""
        # 尝试1：直接解析
        try:
            return json.loads(text.strip())
        except:
            pass
        
        # 尝试2：提取markdown代码块中的JSON
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
        
        # 尝试3：查找第一个 { 到最后一个 } 之间的内容
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except:
                pass
        
        # 如果都失败了，返回空字典
        return {}
    
    # 调用AI进行信息提取和总结
    openai_client = get_openai_client()
    
    extraction_prompt = f"""
请从以下对话中提取用户的基本信息，并以JSON格式返回。
需要提取的字段：
- display_name (昵称)
- gender (性别：male/female)
- birth_year (出生年份)
- current_city (所在城市)
- occupation (职业)
- education_level (学历)
- bio (自我介绍)
- interests (兴趣爱好，数组)
- lifestyle (生活方式)
- values (价值观，数组)
- marriage_timeline (期望结婚时间)
- preferred_gender (期望对象性别)
- age_min, age_max (期望年龄范围)

对话内容：
{conversation_text}

请只返回JSON，不要其他文字。如果某个字段没有提到，设为null。
"""
    
    def extract_json_from_text(text: str) -> dict:
        """从文本中提取JSON（可能包含markdown代码块或其他文字）"""
        # 尝试1：直接解析
        try:
            return json.loads(text.strip())
        except:
            pass
        
        # 尝试2：提取markdown代码块中的JSON
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
        
        # 尝试3：查找第一个 { 到最后一个 } 之间的内容
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except:
                pass
        
        # 如果都失败了，返回空字典
        return {}
    
    try:
        response = openai_client.chat_completion(
            messages=[
                {"role": "system", "content": "你是一个专业的信息提取助手，从对话中提取结构化数据。请只返回JSON格式，不要其他文字。"},
                {"role": "user", "content": extraction_prompt}
            ],
            model=openai_client.model_gpt4o_mini,  # 使用GPT-4o-mini，成本低且性能好
            temperature=0.3,  # 降低温度，确保输出稳定
            fallback_model=openai_client.model_gpt35,  # 如果GPT-4o-mini不可用，降级到GPT-3.5
        )
        
        # 解析JSON（支持多种格式）
        content = response["content"].strip()
        extracted_data = extract_json_from_text(content)
        
        # 如果提取失败，记录错误并返回空字典
        if not extracted_data:
            print(f"[WARNING] 无法从AI回复中提取JSON，原始内容：{content[:200]}")
            # 返回空字典，后续代码会处理
            extracted_data = {}
            
    except Exception as e:
        print(f"[ERROR] 信息提取失败: {str(e)}")
        print(f"[ERROR] AI回复内容: {response.get('content', '')[:200] if 'response' in locals() else 'N/A'}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"信息提取失败：{str(e)}。请重试或联系客服。",
        )
    
    # 创建或更新UserProfile
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )
    
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
    
    # 更新字段（只更新非null的字段）
    # 如果extracted_data为空，至少保存一些基本信息
    extended_info = {}
    
    if extracted_data:
        for key, value in extracted_data.items():
            if value is not None:
                # 扩展字段存储在 extended_info JSON 中
                if key in ["interests", "values", "lifestyle", "personality_traits"]:
                    extended_info[key] = value
                elif hasattr(profile, key):
                    setattr(profile, key, value)
    else:
        # 如果AI提取失败，至少从对话中提取一些基本信息
        # 这是一个降级策略，确保用户资料至少能保存
        print("[WARNING] AI信息提取失败，尝试从对话中手动提取基本信息")
        # 这里可以添加简单的文本匹配逻辑，但暂时先保存空资料
    
    # 保存扩展信息
    if extended_info:
        if profile.extended_info:
            profile.extended_info.update(extended_info)
        else:
            profile.extended_info = extended_info
    
    # 创建默认的MatchPreference
    pref = (
        db.query(MatchPreference)
        .filter(MatchPreference.user_id == current_user.id)
        .first()
    )
    
    if not pref:
        pref = MatchPreference(user_id=current_user.id)
        if extracted_data:
            if extracted_data.get("preferred_gender"):
                pref.preferred_gender = extracted_data["preferred_gender"]
            if extracted_data.get("age_min"):
                pref.min_age = extracted_data["age_min"]
            if extracted_data.get("age_max"):
                pref.max_age = extracted_data["age_max"]
            if extracted_data.get("marriage_timeline"):
                pref.marriage_timeline = extracted_data["marriage_timeline"]
        db.add(pref)
    
    # 保存AI的总结消息
    summary_content = (
        "太好了！我已经了解了你的基本信息。"
        "让我为你总结一下：\n\n"
        f"• 昵称：{extracted_data.get('display_name', '未设置') if extracted_data else '未设置'}\n"
        f"• 年龄：{datetime.utcnow().year - extracted_data.get('birth_year', 0) if extracted_data and extracted_data.get('birth_year') else '未设置'}岁\n"
        f"• 城市：{extracted_data.get('current_city', '未设置') if extracted_data else '未设置'}\n"
        f"• 职业：{extracted_data.get('occupation', '未设置') if extracted_data else '未设置'}\n\n"
        "资料已保存！现在我可以为你推荐合适的对象了。"
        "有什么想补充的，随时可以告诉我～"
    )
    
    summary_msg = AIConversation(
        user_id=current_user.id,
        role="assistant",
        content=summary_content,
        conversation_type="registration",
        tokens_used=response.get("tokens_used", 0) if 'response' in locals() else 0,
        model=response.get("model", "gpt-4o-mini") if 'response' in locals() else "gpt-4o-mini",
    )
    db.add(summary_msg)
    
    try:
        db.commit()
        db.refresh(profile)
    except Exception as e:
        db.rollback()
        print(f"[ERROR] 保存资料失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存资料失败：{str(e)}",
        )
    
    # 创建用户向量嵌入（用于匹配推荐）
    try:
        embedding_service = get_embedding_service()
        embedding_service.create_or_update_embedding(
            db, current_user.id, profile, pref
        )
        print(f"[OK] 用户 {current_user.id} 的向量嵌入已创建")
    except Exception as e:
        # 向量嵌入创建失败不影响主流程
        print(f"[WARNING] 创建用户向量嵌入失败: {e}")
    
    return {
        "message": "注册引导完成！",
        "profile_created": True,
    }


@router.get("/token-usage", response_model=TokenUsageResponse)
def get_token_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """获取用户Token使用情况"""
    is_vip = _is_user_vip(db, current_user.id)
    usage = _get_or_create_token_usage(db, current_user.id, is_vip)
    
    return TokenUsageResponse(
        tokens_used=usage.tokens_used,
        tokens_limit=usage.tokens_limit,
        tokens_remaining=max(0, usage.tokens_limit - usage.tokens_used),
        month=usage.month,
    )


@router.get("/recommendation-quota", response_model=RecommendationQuotaResponse)
def get_recommendation_quota(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """获取用户推荐额度使用情况"""
    is_vip = _is_user_vip(db, current_user.id)
    quota = _get_or_create_recommendation_quota(db, current_user.id, is_vip)
    
    return RecommendationQuotaResponse(
        quota_used=quota.quota_used,
        quota_limit=quota.quota_limit,
        quota_remaining=max(0, quota.quota_limit - quota.quota_used),
        month=quota.month,
    )


@router.get("/memory-summary", response_model=AIMemorySummaryResponse)
def get_memory_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """获取AI记忆摘要（VIP用户专用）"""
    if not _is_user_vip(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此功能仅限VIP用户",
        )
    
    summary = _get_memory_summary(db, current_user.id)
    
    return AIMemorySummaryResponse(
        short_term=summary.get("short_term") if summary else None,
        mid_term=summary.get("mid_term") if summary else None,
        long_term=summary.get("long_term") if summary else None,
    )
















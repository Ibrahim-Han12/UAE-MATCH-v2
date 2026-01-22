from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class AIConversationMessage(BaseModel):
    """AI对话消息"""
    role: str  # user/assistant/system
    content: str
    created_at: Optional[datetime] = None


class AIChatRequest(BaseModel):
    """发送消息给AI红娘的请求"""
    message: str
    conversation_type: str = "consultation"  # registration/consultation/care/match_recommendation


class AIChatResponse(BaseModel):
    """AI红娘的回复"""
    content: str
    tokens_used: int
    model: str
    conversation_id: Optional[int] = None


class AIConversationHistory(BaseModel):
    """对话历史"""
    id: int
    role: str
    content: str
    conversation_type: str
    tokens_used: int
    model: str
    created_at: datetime

    class Config:
        from_attributes = True


class StartRegistrationRequest(BaseModel):
    """开始注册引导对话的请求"""
    pass


class CompleteRegistrationRequest(BaseModel):
    """完成注册引导对话的请求"""
    confirm: bool = True  # 用户确认是否完成


class TokenUsageResponse(BaseModel):
    """Token使用情况"""
    tokens_used: int
    tokens_limit: int
    tokens_remaining: int
    month: str  # 格式：2025-01


class RecommendationQuotaResponse(BaseModel):
    """推荐额度使用情况"""
    quota_used: int
    quota_limit: int
    quota_remaining: int
    month: str  # 格式：2025-01


class AIMemorySummaryResponse(BaseModel):
    """AI记忆摘要（VIP用户）"""
    short_term: Optional[Dict[str, Any]] = None
    mid_term: Optional[Dict[str, Any]] = None
    long_term: Optional[Dict[str, Any]] = None


class AIRecommendationRequest(BaseModel):
    """请求AI推荐候选人的请求"""
    preferences: Optional[Dict[str, Any]] = None  # 可选的额外偏好


class AIRecommendationResponse(BaseModel):
    """AI推荐响应"""
    candidates: List[Dict[str, Any]]  # 候选人列表
    recommendation_reason: str  # AI生成的推荐理由
    tokens_used: int
    quota_used: int  # 消耗的推荐额度
















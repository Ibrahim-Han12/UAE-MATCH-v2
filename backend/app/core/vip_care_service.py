"""
VIP主动询问与陪伴服务
实现事件驱动 + 兜底时间的主动关怀机制
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.openai_client import get_openai_client
from app.core.memory_service import get_memory_service
from app.models.user import User
from app.models.profile import UserProfile
from app.models.order import Subscription
from app.models.match_pair import MatchPair
from app.models.chat_message import ChatMessage
from app.models.ai_conversation import AIConversation


class VIPCareService:
    """VIP主动关怀服务"""
    
    def __init__(self):
        self.openai_client = get_openai_client()
        self.memory_service = get_memory_service()
    
    def get_vip_users(self, db: Session) -> List[User]:
        """获取所有活跃的VIP用户"""
        now = datetime.utcnow()
        active_vips = (
            db.query(User)
            .join(Subscription)
            .filter(
                Subscription.status == "active",
                Subscription.expires_at > now,
                User.is_active == True,
            )
            .all()
        )
        return active_vips
    
    def check_user_activity(self, db: Session, user_id: int) -> Dict[str, Any]:
        """
        检查用户活跃状态
        
        Returns:
            {
                "is_active": bool,  # 是否正在活跃（3天内有操作）
                "last_activity": datetime,  # 最后活跃时间
                "recent_matches": int,  # 最近匹配数
                "recent_chats": int,  # 最近聊天数
            }
        """
        three_days_ago = datetime.utcnow() - timedelta(days=3)
        
        # 检查最近对话
        recent_conversations = (
            db.query(AIConversation)
            .filter(
                AIConversation.user_id == user_id,
                AIConversation.created_at > three_days_ago,
            )
            .count()
        )
        
        # 检查最近匹配
        recent_matches = (
            db.query(MatchPair)
            .filter(
                or_(
                    MatchPair.user1_id == user_id,
                    MatchPair.user2_id == user_id,
                ),
                MatchPair.created_at > three_days_ago,
            )
            .count()
        )
        
        # 检查最近聊天
        recent_chats = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.sender_id == user_id,
                ChatMessage.created_at > three_days_ago,
            )
            .count()
        )
        
        total_activity = recent_conversations + recent_matches + recent_chats
        
        # 获取最后活跃时间
        last_activity = None
        if recent_conversations > 0:
            last_conv = (
                db.query(AIConversation)
                .filter(AIConversation.user_id == user_id)
                .order_by(AIConversation.created_at.desc())
                .first()
            )
            if last_conv:
                last_activity = last_conv.created_at
        
        return {
            "is_active": total_activity > 0,
            "last_activity": last_activity,
            "recent_matches": recent_matches,
            "recent_chats": recent_chats,
            "total_activity": total_activity,
        }
    
    def check_event_driven_triggers(self, db: Session, user_id: int) -> Optional[str]:
        """
        检查事件驱动的触发条件
        
        Returns:
            如果应该触发，返回触发原因；否则返回None
        """
        # 检查1：用户刚和一个推荐对象互换了联系方式（24小时内）
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        
        recent_match = (
            db.query(MatchPair)
            .filter(
                or_(
                    MatchPair.user1_id == user_id,
                    MatchPair.user2_id == user_id,
                ),
                MatchPair.created_at > one_day_ago,
                MatchPair.status == "matched",  # 已匹配
            )
            .order_by(MatchPair.created_at.desc())
            .first()
        )
        
        if recent_match:
            return "event:recent_match"  # 最近有匹配
        
        # 检查2：聊天热度突然下降（之前很活跃，最近3天没消息）
        activity = self.check_user_activity(db, user_id)
        
        if not activity["is_active"] and activity["last_activity"]:
            # 之前活跃，现在不活跃了
            days_since_activity = (datetime.utcnow() - activity["last_activity"]).days
            if 3 <= days_since_activity <= 7:
                return "event:activity_drop"  # 活跃度下降
        
        return None
    
    def generate_care_message(
        self,
        db: Session,
        user_id: int,
        trigger_reason: str,
    ) -> str:
        """
        生成关怀消息
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            trigger_reason: 触发原因
        
        Returns:
            生成的关怀消息
        """
        # 获取用户资料
        profile = (
            db.query(UserProfile)
            .filter(UserProfile.user_id == user_id)
            .first()
        )
        
        user_name = profile.display_name if profile else "朋友"
        
        # 获取长期记忆
        memory_summary = self.memory_service.get_memory(db, user_id)
        
        # 获取最近状态
        activity = self.check_user_activity(db, user_id)
        
        # 构建Prompt
        if trigger_reason == "event:recent_match":
            prompt = f"""用户{user_name}最近刚和一个推荐对象匹配成功（24小时内）。

用户档案：
{memory_summary if memory_summary else "用户刚开始使用服务"}

请生成一句温暖的开场白，主动询问匹配进展。
要求：
1. 语气温暖、自然，像真正的红娘朋友
2. 不要直接问"你们聊得怎么样"，要更巧妙
3. 字数控制在50字以内
4. 可以用1个emoji增加亲和力
5. 不要说出"作为AI"这种话

开场白："""
        
        elif trigger_reason == "event:activity_drop":
            prompt = f"""用户{user_name}之前很活跃，但最近3-7天没有操作了。

用户档案：
{memory_summary if memory_summary else "用户刚开始使用服务"}

请生成一句温暖的开场白，关心用户近况。
要求：
1. 语气温暖、自然，像真正的红娘朋友
2. 不要显得太刻意，要自然
3. 字数控制在50字以内
4. 可以用1个emoji增加亲和力
5. 不要说出"作为AI"这种话

开场白："""
        
        else:  # 兜底时间（周二/周五晚上）
            prompt = f"""用户{user_name}已经3天没有任何操作了，现在是关怀时间。

用户档案：
{memory_summary if memory_summary else "用户刚开始使用服务"}

请生成一句温暖的开场白，主动关心用户。
要求：
1. 语气温暖、自然，像真正的红娘朋友
2. 可以问最近的感情进展、是否遇到合适的人等
3. 字数控制在50字以内
4. 可以用1个emoji增加亲和力
5. 不要说出"作为AI"这种话

开场白："""
        
        try:
            response = self.openai_client.chat_completion(
                messages=[
                    {"role": "system", "content": "你是用户专属的AI红娘'小缘'，温暖、专业、不死板。"},
                    {"role": "user", "content": prompt}
                ],
                model=self.openai_client.model_gpt4o_mini,
                temperature=0.8,  # 稍微提高温度，让回答更自然
                fallback_model=self.openai_client.model_gpt35,
            )
            
            return response["content"].strip()
        except Exception as e:
            # 如果生成失败，使用默认消息
            if trigger_reason == "event:recent_match":
                return f"Hi {user_name}，最近怎么样？上次推荐的那个人有联系吗？"
            else:
                return f"Hi {user_name}，最近过得怎么样？有什么想聊的吗？"
    
    def should_send_care_message(self, db: Session, user_id: int) -> tuple[bool, Optional[str]]:
        """
        判断是否应该发送关怀消息
        
        Returns:
            (should_send, trigger_reason)
        """
        # 检查1：用户是否正在活跃聊天（防打扰）
        activity = self.check_user_activity(db, user_id)
        
        # 如果用户正在活跃聊天（最近1小时内有聊天），不打扰
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_chat = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.sender_id == user_id,
                ChatMessage.created_at > one_hour_ago,
            )
            .first()
        )
        
        if recent_chat:
            return (False, None)  # 用户正在聊天，不打扰
        
        # 检查2：事件驱动（高优先级）
        event_trigger = self.check_event_driven_triggers(db, user_id)
        if event_trigger:
            return (True, event_trigger)
        
        # 检查3：兜底时间（低优先级）- 3天没有操作
        if not activity["is_active"]:
            days_since_activity = None
            if activity["last_activity"]:
                days_since_activity = (datetime.utcnow() - activity["last_activity"]).days
            else:
                # 没有活跃记录，检查注册时间
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    days_since_activity = (datetime.utcnow() - user.created_at).days
            
            if days_since_activity and days_since_activity >= 3:
                # 检查是否是周二或周五晚上（18:00-22:00）
                now = datetime.utcnow()
                weekday = now.weekday()  # 0=Monday, 1=Tuesday, 4=Friday
                hour = now.hour
                
                if (weekday == 1 or weekday == 4) and 18 <= hour <= 22:
                    return (True, "fallback:schedule")
        
        return (False, None)
    
    def process_vip_care(self, db: Session) -> List[Dict[str, Any]]:
        """
        处理VIP主动关怀（批量）
        
        Returns:
            处理结果列表
        """
        vip_users = self.get_vip_users(db)
        results = []
        
        for user in vip_users:
            try:
                should_send, trigger_reason = self.should_send_care_message(db, user.id)
                
                if should_send:
                    # 生成关怀消息
                    care_message = self.generate_care_message(db, user.id, trigger_reason)
                    
                    # 保存为AI对话（类型为care）
                    from app.models.ai_conversation import AIConversation
                    ai_message = AIConversation(
                        user_id=user.id,
                        role="assistant",
                        content=care_message,
                        conversation_type="care",
                        tokens_used=0,  # 主动关怀不计入用户token配额
                        model="gpt-4o-mini",
                    )
                    db.add(ai_message)
                    db.commit()
                    
                    results.append({
                        "user_id": user.id,
                        "trigger": trigger_reason,
                        "message": care_message,
                        "status": "sent",
                    })
                else:
                    results.append({
                        "user_id": user.id,
                        "trigger": None,
                        "status": "skipped",
                    })
            except Exception as e:
                results.append({
                    "user_id": user.id,
                    "status": "error",
                    "error": str(e),
                })
        
        return results


# 全局单例
_vip_care_service: Optional[VIPCareService] = None


def get_vip_care_service() -> VIPCareService:
    """获取VIP关怀服务单例"""
    global _vip_care_service
    if _vip_care_service is None:
        _vip_care_service = VIPCareService()
    return _vip_care_service













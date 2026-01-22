"""
长期记忆服务
实现滚动摘要机制，避免存储全量聊天记录
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.core.openai_client import get_openai_client
from app.models.user_ai_memory import UserAIMemory
from app.models.ai_conversation import AIConversation


class MemoryService:
    """长期记忆服务类"""
    
    def __init__(self):
        self.openai_client = get_openai_client()
        self.max_tokens = 800  # 摘要最大token数（500-800 tokens）
    
    def compress_conversation(
        self,
        db: Session,
        user_id: int,
        new_conversations: list,
    ) -> UserAIMemory:
        """
        压缩对话，更新滚动摘要
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            new_conversations: 新的对话列表（最近几次对话）
        
        Returns:
            UserAIMemory对象
        """
        # 获取旧的记忆
        old_memory = db.query(UserAIMemory).filter(
            UserAIMemory.user_id == user_id
        ).first()
        
        old_summary = old_memory.summary_text if old_memory else "这是第一次对话，还没有历史记忆。"
        
        # 构建新对话文本
        new_conversation_text = "\n".join([
            f"{conv.get('role', 'user')}: {conv.get('content', '')}"
            for conv in new_conversations
        ])
        
        # 构建压缩Prompt
        compression_prompt = f"""这是旧的用户档案：
{old_summary}

这是刚才的新对话：
{new_conversation_text}

请把它们合并成一份新的用户档案，要求：
1. 保留关键事实（如：她提到不喜欢抽烟的人、她最近见了张三觉得太闷）
2. 去除寒暄废话（如："你好"、"谢谢"等）
3. 突出用户的情感状态、偏好变化、重要事件
4. 字数控制在500字以内
5. 用简洁的语言，像写人物小传一样

新的用户档案："""
        
        # 调用GPT-4o-mini进行压缩
        try:
            response = self.openai_client.chat_completion(
                messages=[
                    {"role": "system", "content": "你是一个专业的信息压缩助手，擅长从对话中提取关键信息。"},
                    {"role": "user", "content": compression_prompt}
                ],
                model=self.openai_client.model_gpt4o_mini,
                temperature=0.3,  # 降低温度，确保输出稳定
                fallback_model=self.openai_client.model_gpt35,
            )
            
            new_summary = response["content"].strip()
            
            # 估算token数（简单估算：1 token ≈ 4字符）
            token_count = len(new_summary) // 4
            
            # 更新或创建记忆
            if old_memory:
                old_memory.summary_text = new_summary
                old_memory.token_count = token_count
            else:
                old_memory = UserAIMemory(
                    user_id=user_id,
                    summary_text=new_summary,
                    token_count=token_count,
                )
                db.add(old_memory)
            
            db.commit()
            db.refresh(old_memory)
            return old_memory
            
        except Exception as e:
            # 如果压缩失败，保留旧记忆
            if old_memory:
                return old_memory
            else:
                # 创建默认记忆
                default_memory = UserAIMemory(
                    user_id=user_id,
                    summary_text="用户刚开始使用服务，还没有足够的信息。",
                    token_count=20,
                )
                db.add(default_memory)
                db.commit()
                db.refresh(default_memory)
                return default_memory
    
    def get_memory(self, db: Session, user_id: int) -> Optional[str]:
        """
        获取用户的滚动摘要
        
        Args:
            db: 数据库会话
            user_id: 用户ID
        
        Returns:
            摘要文本，如果没有则返回None
        """
        memory = db.query(UserAIMemory).filter(
            UserAIMemory.user_id == user_id
        ).first()
        
        return memory.summary_text if memory else None
    
    def update_memory_after_conversation(
        self,
        db: Session,
        user_id: int,
        limit: int = 10,  # 取最近10条对话进行压缩
    ) -> UserAIMemory:
        """
        对话结束后，自动更新记忆
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            limit: 取最近多少条对话
        
        Returns:
            UserAIMemory对象
        """
        # 获取最近的对话
        recent_conversations = db.query(AIConversation).filter(
            AIConversation.user_id == user_id
        ).order_by(AIConversation.created_at.desc()).limit(limit).all()
        
        # 转换为字典格式
        conversations_list = [
            {
                "role": conv.role,
                "content": conv.content,
            }
            for conv in reversed(recent_conversations)  # 反转，按时间正序
        ]
        
        # 压缩并更新
        return self.compress_conversation(db, user_id, conversations_list)


# 全局单例
_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """获取记忆服务单例"""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service













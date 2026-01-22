"""
Embedding服务
负责将用户资料向量化，用于相似度匹配
"""
import json
from typing import List, Optional, Dict, Any
from openai import OpenAI
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.user_embedding import UserEmbedding
from app.models.profile import UserProfile
from app.models.match_preference import MatchPreference

try:
    import numpy as np
except ImportError:
    np = None


class EmbeddingService:
    """Embedding服务类"""
    
    def __init__(self):
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY 未配置")
        self.client = OpenAI(api_key=api_key)
        self.model = settings.OPENAI_MODEL_EMBEDDING
        self.dimension = 1536  # text-embedding-3-small 的维度
    
    def build_profile_text(self, profile: UserProfile, preferences: Optional[MatchPreference] = None) -> str:
        """
        混合拼接策略：将用户资料拼接成富文本
        
        排除硬过滤字段：年龄、身高、城市（这些用SQL筛选）
        包含软匹配字段：自我介绍、兴趣爱好、价值观、生活方式等
        """
        parts = []
        
        # 基础信息（非硬过滤）
        if profile.display_name:
            parts.append(f"昵称：{profile.display_name}")
        
        if profile.gender:
            parts.append(f"性别：{profile.gender}")
        
        if profile.occupation:
            parts.append(f"职业：{profile.occupation}")
            if profile.company:
                parts.append(f"公司：{profile.company}")
        
        if profile.education_level:
            parts.append(f"学历：{profile.education_level}")
        
        if profile.nationality:
            parts.append(f"国籍：{profile.nationality}")
        
        if profile.current_country:
            parts.append(f"所在国家：{profile.current_country}")
        
        # 自我介绍（核心）
        if profile.bio:
            parts.append(f"自我介绍：{profile.bio}")
        
        # 扩展信息（JSON格式）
        if profile.extended_info:
            ext = profile.extended_info
            
            # 兴趣爱好
            if ext.get("interests"):
                interests = ext["interests"]
                if isinstance(interests, list):
                    parts.append(f"兴趣爱好：{', '.join(interests)}")
                elif isinstance(interests, str):
                    parts.append(f"兴趣爱好：{interests}")
            
            # 价值观
            if ext.get("values"):
                values = ext["values"]
                if isinstance(values, list):
                    parts.append(f"价值观：{', '.join(values)}")
                elif isinstance(values, str):
                    parts.append(f"价值观：{values}")
            
            # 生活方式
            if ext.get("lifestyle"):
                lifestyle = ext["lifestyle"]
                if isinstance(lifestyle, dict):
                    lifestyle_str = ", ".join([f"{k}: {v}" for k, v in lifestyle.items()])
                    parts.append(f"生活方式：{lifestyle_str}")
                elif isinstance(lifestyle, str):
                    parts.append(f"生活方式：{lifestyle}")
            
            # 性格特点
            if ext.get("personality"):
                personality = ext["personality"]
                if isinstance(personality, list):
                    parts.append(f"性格特点：{', '.join(personality)}")
                elif isinstance(personality, str):
                    parts.append(f"性格特点：{personality}")
            
            # 择偶标准（重要）
            if ext.get("partner_preferences"):
                prefs = ext["partner_preferences"]
                if isinstance(prefs, dict):
                    prefs_str = ", ".join([f"{k}: {v}" for k, v in prefs.items()])
                    parts.append(f"择偶标准：{prefs_str}")
                elif isinstance(prefs, str):
                    parts.append(f"择偶标准：{prefs}")
            
            # 其他信息
            for key in ["hobbies", "favorite_activities", "life_goals", "relationship_goals"]:
                if ext.get(key):
                    value = ext[key]
                    if isinstance(value, list):
                        parts.append(f"{key}：{', '.join(value)}")
                    elif isinstance(value, str):
                        parts.append(f"{key}：{value}")
        
        # 择偶偏好（从MatchPreference表）
        if preferences:
            if preferences.preferred_gender:
                parts.append(f"期望对象性别：{preferences.preferred_gender}")
            
            # 使用正确的字段名：min_age 和 max_age
            if preferences.min_age and preferences.max_age:
                parts.append(f"期望对象年龄：{preferences.min_age}-{preferences.max_age}岁")
            elif preferences.min_age:
                parts.append(f"期望对象最小年龄：{preferences.min_age}岁")
            elif preferences.max_age:
                parts.append(f"期望对象最大年龄：{preferences.max_age}岁")
            
            # 身高范围
            if preferences.min_height_cm and preferences.max_height_cm:
                parts.append(f"期望对象身高：{preferences.min_height_cm}-{preferences.max_height_cm}cm")
            
            # 学历
            if preferences.education_level:
                parts.append(f"期望对象学历：{preferences.education_level}")
            
            # 收入
            if preferences.min_income_monthly_aed:
                parts.append(f"期望对象最低收入：{preferences.min_income_monthly_aed} AED/月")
            
            # 婚姻时间线
            if preferences.marriage_timeline:
                parts.append(f"期望结婚时间：{preferences.marriage_timeline}")
            
            # 是否要孩子
            if preferences.want_children:
                parts.append(f"是否要孩子：{preferences.want_children}")
            
            # 是否计划在阿联酋定居
            if preferences.plan_settle_in_uae is not None:
                parts.append(f"计划在阿联酋定居：{'是' if preferences.plan_settle_in_uae else '否'}")
            
            # 宗教偏好
            if preferences.religion:
                parts.append(f"宗教偏好：{preferences.religion}")
            
            # MBTI
            if preferences.mbti:
                parts.append(f"MBTI类型：{preferences.mbti}")
            
            # 其他备注
            if preferences.notes:
                parts.append(f"其他偏好：{preferences.notes}")
        
        # 拼接成完整文本
        full_text = "\n".join(parts)
        return full_text
    
    def get_embedding(self, text: str) -> List[float]:
        """
        获取文本的向量嵌入
        
        Args:
            text: 要向量化的文本
        
        Returns:
            向量列表（1536维）
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"获取Embedding失败: {str(e)}")
    
    def create_or_update_embedding(
        self, 
        db: Session, 
        user_id: int, 
        profile: UserProfile, 
        preferences: Optional[MatchPreference] = None
    ) -> UserEmbedding:
        """
        创建或更新用户的向量嵌入
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            profile: 用户资料
            preferences: 择偶偏好
        
        Returns:
            UserEmbedding对象
        """
        # 构建文本
        source_text = self.build_profile_text(profile, preferences)
        
        # 获取向量
        embedding_vector = self.get_embedding(source_text)
        
        # 查找或创建
        user_embedding = db.query(UserEmbedding).filter(UserEmbedding.user_id == user_id).first()
        
        if user_embedding:
            # 更新
            user_embedding.embedding_vector = json.dumps(embedding_vector)
            user_embedding.source_text = source_text
            user_embedding.dimension = self.dimension
        else:
            # 创建
            user_embedding = UserEmbedding(
                user_id=user_id,
                embedding_vector=json.dumps(embedding_vector),
                source_text=source_text,
                dimension=self.dimension,
            )
            db.add(user_embedding)
        
        db.commit()
        db.refresh(user_embedding)
        return user_embedding
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算两个向量的余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
        
        Returns:
            相似度分数（0-1之间）
        """
        if np is None:
            # 如果没有numpy，使用纯Python实现
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            norm1 = sum(a * a for a in vec1) ** 0.5
            norm2 = sum(b * b for b in vec2) ** 0.5
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot_product / (norm1 * norm2))
        else:
            vec1_arr = np.array(vec1)
            vec2_arr = np.array(vec2)
            
            dot_product = np.dot(vec1_arr, vec2_arr)
            norm1 = np.linalg.norm(vec1_arr)
            norm2 = np.linalg.norm(vec2_arr)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot_product / (norm1 * norm2))
    
    def find_similar_users(
        self,
        db: Session,
        user_id: int,
        limit: int = 5,
        min_similarity: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        使用向量搜索找到相似用户
        
        注意：这是简化版本，实际应该使用PostgreSQL的pgvector和HNSW索引
        
        Args:
            db: 数据库会话
            user_id: 当前用户ID
            limit: 返回数量
            min_similarity: 最小相似度阈值
        
        Returns:
            相似用户列表，包含user_id和similarity_score
        """
        # 获取当前用户的向量
        current_embedding = db.query(UserEmbedding).filter(
            UserEmbedding.user_id == user_id
        ).first()
        
        if not current_embedding:
            return []
        
        current_vec = json.loads(current_embedding.embedding_vector)
        
        # 获取所有其他用户的向量
        all_embeddings = db.query(UserEmbedding).filter(
            UserEmbedding.user_id != user_id
        ).all()
        
        # 计算相似度
        similarities = []
        for embedding in all_embeddings:
            other_vec = json.loads(embedding.embedding_vector)
            similarity = self.cosine_similarity(current_vec, other_vec)
            
            if similarity >= min_similarity:
                similarities.append({
                    "user_id": embedding.user_id,
                    "similarity_score": similarity,
                })
        
        # 按相似度排序
        similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # 返回Top N
        return similarities[:limit]


# 全局单例
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """获取Embedding服务单例"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service













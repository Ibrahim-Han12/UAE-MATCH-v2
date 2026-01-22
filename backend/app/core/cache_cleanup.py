"""
缓存清理定时任务
定期清理过期的匹配分析报告缓存
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.match_insight_cache import MatchInsightCache
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 从配置中获取缓存参数
CACHE_EXPIRY_DAYS = settings.MATCH_INSIGHT_CACHE_EXPIRY_DAYS
MAX_CACHE_PER_USER = settings.MATCH_INSIGHT_CACHE_MAX_PER_USER


def cleanup_expired_cache():
    """
    清理过期的匹配分析报告缓存
    应该在定时任务中调用（例如每天凌晨执行）
    """
    db: Session = SessionLocal()
    try:
        # 计算过期时间点
        expiry_date = datetime.utcnow() - timedelta(days=CACHE_EXPIRY_DAYS)
        
        # 查找所有过期的缓存
        expired_caches = (
            db.query(MatchInsightCache)
            .filter(MatchInsightCache.created_at < expiry_date)
            .all()
        )
        
        if expired_caches:
            count = len(expired_caches)
            # 批量删除过期缓存
            for cache in expired_caches:
                db.delete(cache)
            db.commit()
            logger.info(f"[CACHE CLEANUP] 清理了 {count} 条过期缓存（超过 {CACHE_EXPIRY_DAYS} 天）")
        else:
            logger.info(f"[CACHE CLEANUP] 没有需要清理的过期缓存")
            
    except Exception as e:
        logger.error(f"[CACHE CLEANUP] 清理缓存失败: {e}")
        db.rollback()
    finally:
        db.close()


def cleanup_excess_cache_per_user(max_per_user: int = MAX_CACHE_PER_USER):
    """
    清理每个用户超出限制的缓存（保留最新的N个）
    应该在定时任务中调用（例如每天凌晨执行）
    """
    db: Session = SessionLocal()
    try:
        # 获取所有有缓存的用户ID
        user_ids = (
            db.query(MatchInsightCache.user_id)
            .distinct()
            .all()
        )
        
        total_deleted = 0
        for (user_id,) in user_ids:
            # 获取该用户的所有缓存，按创建时间倒序
            user_caches = (
                db.query(MatchInsightCache)
                .filter(MatchInsightCache.user_id == user_id)
                .order_by(MatchInsightCache.created_at.desc())
                .all()
            )
            
            # 如果超过限制，删除最旧的
            if len(user_caches) > max_per_user:
                caches_to_delete = user_caches[max_per_user:]
                for cache in caches_to_delete:
                    db.delete(cache)
                total_deleted += len(caches_to_delete)
                logger.info(f"[CACHE CLEANUP] 用户 {user_id} 缓存数量 {len(user_caches)}，删除 {len(caches_to_delete)} 条最旧缓存")
        
        if total_deleted > 0:
            db.commit()
            logger.info(f"[CACHE CLEANUP] 共清理了 {total_deleted} 条超出限制的缓存")
        else:
            logger.info(f"[CACHE CLEANUP] 没有需要清理的超出限制缓存")
            
    except Exception as e:
        logger.error(f"[CACHE CLEANUP] 清理超出限制缓存失败: {e}")
        db.rollback()
    finally:
        db.close()


def run_cache_cleanup():
    """
    执行完整的缓存清理任务
    包括：清理过期缓存 + 清理超出限制的缓存
    """
    logger.info("[CACHE CLEANUP] 开始执行缓存清理任务...")
    cleanup_expired_cache()
    cleanup_excess_cache_per_user(max_per_user=MAX_CACHE_PER_USER)
    logger.info("[CACHE CLEANUP] 缓存清理任务完成")













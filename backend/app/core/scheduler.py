"""
定时任务调度器
使用schedule库实现定时任务（后台线程运行）
"""
import logging
import threading
import time
import schedule
from app.core.cache_cleanup import run_cache_cleanup

logger = logging.getLogger(__name__)

_scheduler_thread = None
_scheduler_running = False


def _run_scheduler():
    """在后台线程中运行定时任务"""
    global _scheduler_running
    _scheduler_running = True
    while _scheduler_running:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次


def start_scheduler():
    """启动定时任务调度器"""
    global _scheduler_thread
    try:
        # 每天凌晨2点执行缓存清理任务
        schedule.every().day.at("02:00").do(run_cache_cleanup)
        
        # 在后台线程中运行调度器
        if _scheduler_thread is None or not _scheduler_thread.is_alive():
            _scheduler_thread = threading.Thread(target=_run_scheduler, daemon=True)
            _scheduler_thread.start()
            logger.info("[SCHEDULER] 定时任务调度器已启动")
            logger.info("[SCHEDULER] 缓存清理任务已安排：每天凌晨2点执行")
    except Exception as e:
        logger.error(f"[SCHEDULER] 启动定时任务调度器失败: {e}")


def stop_scheduler():
    """停止定时任务调度器"""
    global _scheduler_running
    try:
        _scheduler_running = False
        schedule.clear()
        logger.info("[SCHEDULER] 定时任务调度器已停止")
    except Exception as e:
        logger.error(f"[SCHEDULER] 停止定时任务调度器失败: {e}")













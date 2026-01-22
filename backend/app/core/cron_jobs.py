"""
定时任务（Cron Jobs）
实现VIP主动询问的定时触发
"""
import schedule
import time
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.core.vip_care_service import get_vip_care_service


def run_vip_care_job():
    """执行VIP主动关怀任务"""
    db: Session = SessionLocal()
    try:
        print(f"[{datetime.now()}] 开始执行VIP主动关怀任务...")
        care_service = get_vip_care_service()
        results = care_service.process_vip_care(db)
        
        sent_count = sum(1 for r in results if r.get("status") == "sent")
        skipped_count = sum(1 for r in results if r.get("status") == "skipped")
        error_count = sum(1 for r in results if r.get("status") == "error")
        
        print(f"[{datetime.now()}] VIP主动关怀任务完成:")
        print(f"  发送: {sent_count} 条")
        print(f"  跳过: {skipped_count} 条")
        print(f"  错误: {error_count} 条")
        
        return results
    except Exception as e:
        print(f"[{datetime.now()}] VIP主动关怀任务失败: {e}")
        return []
    finally:
        db.close()


def setup_cron_jobs():
    """设置定时任务"""
    # 每周二和周五晚上8点执行
    schedule.every().tuesday.at("20:00").do(run_vip_care_job)
    schedule.every().friday.at("20:00").do(run_vip_care_job)
    
    print("定时任务已设置:")
    print("  - 每周二晚上8点: VIP主动关怀")
    print("  - 每周五晚上8点: VIP主动关怀")


def run_scheduler():
    """运行调度器（阻塞）"""
    setup_cron_jobs()
    
    print("定时任务调度器已启动，等待执行...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次


if __name__ == "__main__":
    # 可以直接运行此文件来启动定时任务
    run_scheduler()













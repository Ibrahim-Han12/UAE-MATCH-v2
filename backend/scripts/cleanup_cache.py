"""
独立的缓存清理脚本
可以通过cron或Windows任务计划程序定期运行
用法：python scripts/cleanup_cache.py
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.cache_cleanup import run_cache_cleanup

if __name__ == "__main__":
    print("开始执行缓存清理任务...")
    run_cache_cleanup()
    print("缓存清理任务完成")













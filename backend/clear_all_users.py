"""
清理所有用户注册信息的脚本
警告：此操作不可逆，会删除所有用户数据！
"""
import sqlite3
from pathlib import Path

# 数据库文件路径
db_path = Path(__file__).parent / "app.db"

if not db_path.exists():
    print(f"❌ 数据库文件不存在: {db_path}")
    exit(1)

# 需要清空的表（按依赖关系排序，先删除子表，再删除主表）
tables_to_clear = [
    # AI相关
    "ai_conversations",
    "ai_memory_summaries",
    "user_token_usage",
    "user_recommendation_quota",
    
    # 匹配相关
    "match_pairs",
    "match_actions",
    "match_preferences",
    
    # 聊天相关
    "chat_messages",
    
    # 用户互动相关
    "user_blocks",
    "user_reports",
    
    # 照片和订单
    "user_photos",
    "orders",
    
    # 事件日志
    "event_logs",
    
    # 用户资料和用户
    "user_profiles",
    "users",
]

def clear_all_users():
    """清空所有用户数据"""
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("⚠️  警告：即将删除所有用户注册信息！")
        print(f"📁 数据库文件: {db_path}")
        print(f"📊 将清空 {len(tables_to_clear)} 个表")
        
        confirm = input("\n❓ 确认删除？输入 'YES' 继续: ")
        if confirm != "YES":
            print("❌ 操作已取消")
            conn.close()
            return
        
        print("\n🔄 开始清理...")
        
        # 禁用外键约束（SQLite默认是关闭的，但为了安全）
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        # 清空每个表
        for table in tables_to_clear:
            try:
                cursor.execute(f"DELETE FROM {table}")
                count = cursor.rowcount
                print(f"  ✅ {table}: 删除了 {count} 条记录")
            except sqlite3.OperationalError as e:
                # 表可能不存在，跳过
                print(f"  ⚠️  {table}: 表不存在或已为空 ({e})")
        
        # 提交更改
        conn.commit()
        
        # 重新启用外键约束
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # 清理数据库（释放空间）
        cursor.execute("VACUUM")
        
        print("\n✅ 清理完成！所有用户数据已删除")
        print("💡 提示：重启后端服务后，数据库表结构会自动重建")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ 清理失败: {e}")
        if conn:
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    clear_all_users()














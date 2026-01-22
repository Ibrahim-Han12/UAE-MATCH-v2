"""
数据库迁移脚本：为 user_profiles 表添加 extended_info 列
"""
import sqlite3
from pathlib import Path

# 数据库路径
db_path = Path(__file__).parent / "app.db"

if not db_path.exists():
    print(f"错误：数据库文件不存在：{db_path}")
    exit(1)

print(f"正在连接数据库：{db_path}")

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

try:
    # 检查列是否已存在
    cursor.execute("PRAGMA table_info(user_profiles)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "extended_info" in columns:
        print("[OK] extended_info column already exists, no migration needed")
    else:
        print("Adding extended_info column...")
        # 添加 extended_info 列（JSON 类型，SQLite 中存储为 TEXT）
        cursor.execute("""
            ALTER TABLE user_profiles 
            ADD COLUMN extended_info TEXT
        """)
        conn.commit()
        print("[OK] Successfully added extended_info column")
    
    # 验证
    cursor.execute("PRAGMA table_info(user_profiles)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"\n当前 user_profiles 表的列：{', '.join(columns)}")
    
except Exception as e:
    print(f"错误：{e}")
    conn.rollback()
    raise
finally:
    conn.close()

print("\n迁移完成！")















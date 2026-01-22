"""
数据库迁移脚本：添加AI相关表
- user_embeddings: 存储用户向量嵌入
- user_ai_memory: 存储滚动摘要
"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "app.db"

if not db_path.exists():
    print(f"[ERROR] 数据库文件不存在: {db_path}")
    exit(1)

print("=" * 60)
print("数据库迁移：添加AI相关表")
print("=" * 60)
print(f"数据库文件: {db_path}")

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

try:
    # 1. 创建 user_embeddings 表
    print("\n[1/2] 创建 user_embeddings 表...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            embedding_vector TEXT NOT NULL,
            source_text TEXT,
            dimension INTEGER DEFAULT 1536,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_embedding_user_id ON user_embeddings(user_id)")
    print("  [OK] user_embeddings 表创建成功")
    
    # 2. 创建 user_ai_memory 表
    print("\n[2/2] 创建 user_ai_memory 表...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_ai_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            summary_text TEXT NOT NULL,
            token_count INTEGER DEFAULT 0,
            last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_ai_memory_user_id ON user_ai_memory(user_id)")
    print("  [OK] user_ai_memory 表创建成功")
    
    conn.commit()
    print("\n[OK] 迁移完成！")
    
except sqlite3.Error as e:
    conn.rollback()
    print(f"\n[ERROR] 迁移失败: {e}")
    exit(1)
finally:
    conn.close()

print("=" * 60)
print("\n注意：")
print("1. SQLite不支持pgvector，如需使用HNSW索引，请切换到PostgreSQL")
print("2. 当前向量存储在TEXT字段（JSON格式）")
print("3. 生产环境建议使用PostgreSQL + pgvector扩展")













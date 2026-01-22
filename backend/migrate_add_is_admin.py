"""
数据库迁移脚本：添加 is_admin 列到 users 表
使用方法: python migrate_add_is_admin.py
"""
import sqlite3
from pathlib import Path

def migrate_database(db_path: str = "app.db"):
    """
    添加 is_admin 列到 users 表
    """
    # 检查数据库文件是否存在
    db_file = Path(db_path)
    if not db_file.exists():
        print(f"错误: 数据库文件 {db_path} 不存在")
        print(f"请确保在正确的目录下运行此脚本（应该在 backend 目录）")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查列是否已存在
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "is_admin" in columns:
            print("✓ is_admin 列已存在，无需迁移")
            conn.close()
            return True
        
        print("正在添加 is_admin 列...")
        
        # SQLite 的 ALTER TABLE ADD COLUMN 支持 DEFAULT 值
        # 使用 INTEGER 类型（SQLite 的布尔类型实际上是 INTEGER，0=False, 1=True）
        try:
            # 方法1: 尝试添加 NOT NULL 列（如果表为空或 SQLite 版本支持）
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0
            """)
            conn.commit()
            print("✓ 成功添加 is_admin 列（NOT NULL）")
        except sqlite3.OperationalError as e:
            # 方法2: 如果失败，添加可空列，然后更新所有记录
            error_msg = str(e).lower()
            if "not null" in error_msg or "cannot add" in error_msg:
                print("  使用可空列方式...")
                cursor.execute("""
                    ALTER TABLE users 
                    ADD COLUMN is_admin INTEGER DEFAULT 0
                """)
                conn.commit()
                
                # 更新所有现有记录为 0
                cursor.execute("UPDATE users SET is_admin = 0 WHERE is_admin IS NULL")
                conn.commit()
                print("✓ 成功添加 is_admin 列（已更新现有记录）")
            else:
                # 其他错误，重新抛出
                raise
        
        # 验证
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        if "is_admin" in columns:
            print("✓ 验证成功: is_admin 列已存在")
            
            # 显示当前所有用户的管理员状态
            cursor.execute("SELECT id, email, is_admin FROM users")
            users = cursor.fetchall()
            if users:
                print("\n当前用户列表:")
                print("-" * 60)
                print(f"{'ID':<5} {'Email':<30} {'is_admin':<10}")
                print("-" * 60)
                for user_id, email, is_admin in users:
                    email = email or "无"
                    admin_status = "是" if is_admin else "否"
                    print(f"{user_id:<5} {email:<30} {admin_status:<10}")
                print("-" * 60)
            
            conn.close()
            return True
        else:
            print("✗ 验证失败: is_admin 列未找到")
            conn.close()
            return False
            
    except sqlite3.Error as e:
        print(f"✗ 数据库错误: {e}")
        conn.rollback()
        conn.close()
        return False
    except Exception as e:
        print(f"✗ 错误: {e}")
        conn.rollback()
        conn.close()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("数据库迁移: 添加 is_admin 列")
    print("=" * 60)
    
    # 尝试多个可能的数据库路径
    possible_paths = [
        "app.db",
        "./app.db",
        "../app.db",
        "H:/uae-match/backend/app.db",
    ]
    
    db_path = None
    for path in possible_paths:
        if Path(path).exists():
            db_path = path
            break
    
    if not db_path:
        print("\n未找到数据库文件，请手动指定路径:")
        db_path = input("请输入数据库文件路径 (例如: app.db): ").strip()
        if not db_path:
            print("未提供路径，退出")
            exit(1)
    
    print(f"\n使用数据库: {db_path}\n")
    
    if migrate_database(db_path):
        print("\n✓ 迁移完成！")
        print("\n提示: 现在可以使用 test_admin_setup.py 来设置管理员用户")
    else:
        print("\n✗ 迁移失败，请检查错误信息")

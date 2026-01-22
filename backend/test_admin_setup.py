"""
快速设置管理员用户的脚本
使用方法: python test_admin_setup.py
"""
from app.db.session import SessionLocal
from app.models.user import User

def set_admin_user(user_id: int = None, email: str = None):
    """
    设置管理员用户
    
    Args:
        user_id: 用户ID（如果提供，直接使用）
        email: 用户邮箱（如果提供，通过邮箱查找用户）
    """
    db = SessionLocal()
    
    try:
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
        elif email:
            user = db.query(User).filter(User.email == email).first()
        else:
            print("请提供 user_id 或 email")
            return
        
        if not user:
            print(f"用户不存在 (ID: {user_id}, Email: {email})")
            return
        
        # 显示当前状态
        print(f"找到用户: ID={user.id}, Email={user.email}, is_admin={user.is_admin}")
        
        # 设置为管理员
        user.is_admin = True
        db.commit()
        
        print(f"✓ 用户 {user.id} ({user.email}) 已设置为管理员")
        
        # 验证
        db.refresh(user)
        if user.is_admin:
            print("✓ 验证成功：is_admin = True")
        else:
            print("✗ 验证失败：is_admin 仍为 False")
            
    except Exception as e:
        print(f"错误: {e}")
        db.rollback()
    finally:
        db.close()


def list_all_users():
    """列出所有用户"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print("\n所有用户列表:")
        print("-" * 60)
        print(f"{'ID':<5} {'Email':<30} {'is_admin':<10}")
        print("-" * 60)
        for user in users:
            admin_status = "是" if user.is_admin else "否"
            email = user.email or "无"
            print(f"{user.id:<5} {email:<30} {admin_status:<10}")
        print("-" * 60)
    except Exception as e:
        print(f"错误: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("管理员用户设置工具")
    print("=" * 60)
    
    # 列出所有用户
    list_all_users()
    
    # 交互式设置
    print("\n请选择要设置为管理员的用户:")
    print("1. 通过用户ID设置")
    print("2. 通过邮箱设置")
    print("3. 退出")
    
    choice = input("\n请输入选项 (1/2/3): ").strip()
    
    if choice == "1":
        user_id = input("请输入用户ID: ").strip()
        try:
            set_admin_user(user_id=int(user_id))
        except ValueError:
            print("无效的用户ID")
    elif choice == "2":
        email = input("请输入邮箱: ").strip()
        set_admin_user(email=email)
    elif choice == "3":
        print("退出")
    else:
        print("无效的选项")

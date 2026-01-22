import sqlite3

conn = sqlite3.connect('app.db')
cursor = conn.cursor()

# 检查表结构
cursor.execute("PRAGMA table_info(user_profiles)")
columns = cursor.fetchall()

print("user_profiles 表的列：")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

# 检查 extended_info 是否存在
col_names = [col[1] for col in columns]
if "extended_info" in col_names:
    print("\n[OK] extended_info 列存在")
else:
    print("\n[ERROR] extended_info 列不存在，需要添加")

conn.close()















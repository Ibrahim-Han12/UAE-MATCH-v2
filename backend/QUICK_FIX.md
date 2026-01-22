# 快速修复指南

## 问题：数据库缺少 is_admin 列

### 错误信息
```
sqlalchemy.exc.OperationalError: no such column: users.is_admin
```

### 解决方法

#### 方法1：使用迁移脚本（推荐）

1. 打开终端，进入后端目录：
```bash
cd H:\uae-match\backend
```

2. 运行迁移脚本：
```bash
python migrate_add_is_admin.py
```

3. 脚本会自动：
   - 检测数据库文件位置
   - 添加 `is_admin` 列
   - 设置默认值为 0 (False)
   - 显示所有用户的当前状态

4. 重启后端服务：
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 方法2：手动使用 SQLite

如果方法1不工作，可以手动执行：

1. 打开 SQLite 命令行：
```bash
cd H:\uae-match\backend
sqlite3 app.db
```

2. 执行 SQL：
```sql
ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0;
```

3. 验证：
```sql
PRAGMA table_info(users);
```

4. 退出：
```sql
.quit
```

#### 方法3：重新创建数据库（⚠️ 会丢失数据）

**警告：这会删除所有现有数据！**

1. 备份现有数据库（如果需要）：
```bash
cd H:\uae-match\backend
copy app.db app.db.backup
```

2. 删除数据库文件：
```bash
del app.db
```

3. 重启后端服务，数据库会自动重新创建（包含 is_admin 列）

### 设置管理员用户

迁移完成后，设置管理员：

```bash
python test_admin_setup.py
```

或者使用 SQL：
```sql
UPDATE users SET is_admin = 1 WHERE id = 1;  -- 替换1为你的用户ID
```

### 验证修复

1. 重启后端服务
2. 尝试登录
3. 应该不再出现 "no such column" 错误

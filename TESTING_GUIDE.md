# 功能测试指南

本文档详细说明如何测试新添加的三个功能：WebSocket实时聊天、AI文本审核和管理员后台。

## 快速测试工具

我们提供了几个Python脚本来帮助快速测试功能：

### 1. 设置管理员用户
```bash
cd H:\uae-match\backend
python test_admin_setup.py
```
这个脚本会：
- 列出所有用户
- 允许你选择用户并设置为管理员
- 验证设置是否成功

### 2. 测试WebSocket连接
```bash
cd H:\uae-match\backend
pip install websockets  # 如果还没安装
python test_websocket.py <token> <match_pair_id>
```
或者交互式运行：
```bash
python test_websocket.py
# 然后输入token和配对ID
```

### 3. 测试AI文本审核
```bash
cd H:\uae-match\backend
python test_moderation.py
```
这个脚本会测试各种文本内容，显示审核结果。

---

## 前置准备

### 1. 确保后端服务运行

```bash
# 进入后端目录
cd H:\uae-match\backend

# 安装依赖（如果需要）
pip install fastapi uvicorn websockets python-jose[cryptography] sqlalchemy

# 启动后端服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 确保前端服务运行

```bash
# 进入前端目录
cd H:\uae-match\uae-match-web

# 安装依赖（如果需要）
npm install

# 启动前端服务
npm run dev
```

### 3. 数据库准备

确保数据库中有至少两个测试用户，并且他们之间有匹配关系（MatchPair）。

## 功能一：WebSocket实时聊天测试

### 测试步骤

#### 步骤1：准备测试环境
1. 确保有两个用户账号（User A 和 User B）
2. 确保两个用户之间有 `active` 状态的 `MatchPair` 记录
3. 两个用户都需要登录获取 access_token

#### 步骤2：打开两个浏览器窗口
- **窗口1**：使用 User A 登录，访问 `http://localhost:3000/chats`
- **窗口2**：使用 User B 登录，访问 `http://localhost:3000/chats`

#### 步骤3：建立WebSocket连接
1. 在窗口1中，选择与 User B 的配对对话
2. 观察页面顶部是否显示 "✓ 实时聊天已连接" 的绿色提示
3. 打开浏览器开发者工具（F12），查看 Console 标签
4. 应该能看到 "WebSocket连接已建立" 的日志

#### 步骤4：测试实时消息发送
1. **在窗口1（User A）中**：
   - 在输入框输入消息："你好，这是测试消息"
   - 点击"发送"按钮
   - 消息应该立即出现在聊天窗口中，并且显示为"我发送的"（右侧，粉色背景）

2. **在窗口2（User B）中**：
   - 消息应该**立即**出现在聊天窗口中，无需刷新页面
   - 消息显示为"对方发送的"（左侧，白色背景）

3. **在窗口2（User B）中回复**：
   - 输入回复："收到，测试成功！"
   - 点击"发送"
   - 窗口1应该立即收到消息

#### 步骤5：验证消息持久化
1. 刷新窗口1的页面
2. 之前发送的消息应该仍然存在（从数据库加载）
3. 重新建立WebSocket连接后，应该能继续实时接收消息

#### 步骤6：测试连接断开和重连
1. 在窗口1中，打开开发者工具的 Network 标签
2. 找到 WebSocket 连接，右键选择 "Close connection"
3. 等待几秒，观察是否自动重连
4. 在 Console 中应该能看到重连日志

### 预期结果
- ✅ WebSocket连接成功建立
- ✅ 消息实时双向传输
- ✅ 消息正确保存到数据库
- ✅ 连接断开后自动重连
- ✅ 页面显示连接状态

### 故障排查

**问题1：WebSocket连接失败**
- 检查后端服务是否运行在 8000 端口
- 检查浏览器控制台是否有 CORS 错误
- 检查 token 是否有效（未过期）
- 检查后端日志是否有错误信息

**问题2：消息不实时**
- 检查两个窗口是否都建立了WebSocket连接
- 检查浏览器控制台是否有错误
- 尝试刷新页面重新连接

**问题3：消息发送失败**
- 检查是否被拉黑（isBlockedByMe 或 isBlockedByOther）
- 检查配对状态是否为 "active"
- 检查消息长度是否超过1000字符

---

## 功能二：AI文本审核测试

### 测试步骤

#### 步骤1：测试安全内容（应该通过）
1. 在聊天窗口中输入正常消息："你好，很高兴认识你"
2. 点击发送
3. **预期**：消息正常发送，无错误提示

#### 步骤2：测试诈骗关键词（应该被阻止）
1. 输入包含诈骗关键词的消息：
   - "加我微信，一起投资赚钱"
   - "刷单兼职，日赚500"
   - "免费领取中奖红包"
2. 点击发送
3. **预期**：显示错误提示 "消息包含违规内容：内容包含高风险内容，已被阻止"

#### 步骤3：测试色情关键词（应该被阻止）
1. 输入包含色情关键词的消息：
   - "约炮吗"
   - "特殊服务"
2. 点击发送
3. **预期**：显示错误提示，消息被阻止

#### 步骤4：测试赌博关键词（应该被阻止）
1. 输入包含赌博关键词的消息：
   - "一起赌博吧"
   - "下注赚钱"
2. 点击发送
3. **预期**：显示错误提示，消息被阻止

#### 步骤5：测试毒品关键词（应该被阻止）
1. 输入包含毒品关键词的消息：
   - "要不要试试毒品"
2. 点击发送
3. **预期**：显示错误提示，消息被阻止

#### 步骤6：测试边界情况
1. 输入包含部分关键词但上下文正常：
   - "我不喜欢赌博，觉得不好"
   - "投资理财需要谨慎"
2. 点击发送
3. **预期**：可能被标记为低风险或中等风险，但不会阻止（取决于关键词数量）

#### 步骤7：验证事件日志
1. 访问后端日志或数据库
2. 检查 `event_logs` 表
3. 应该能看到 `event_type = "content_blocked"` 的记录
4. 记录的 `metadata` 字段应该包含审核详情

### 预期结果
- ✅ 正常消息可以发送
- ✅ 包含违规关键词的消息被阻止
- ✅ 显示明确的错误提示
- ✅ 违规事件被记录到日志

### 故障排查

**问题1：违规消息没有被阻止**
- 检查后端 `app/core/safety.py` 是否正确导入
- 检查 `chat.py` 和 `chat_ws.py` 中是否调用了 `get_moderation_result`
- 查看后端日志是否有错误

**问题2：正常消息被误阻止**
- 检查关键词列表是否过于严格
- 可以调整 `safety.py` 中的风险等级判断逻辑

---

## 功能三：管理员后台测试

### 测试步骤

#### 步骤1：设置管理员用户

**方法1：使用Python脚本**
```python
# 在 Python shell 中执行
from app.db.session import SessionLocal
from app.models.user import User

db = SessionLocal()
# 将用户ID为1的用户设置为管理员（替换为实际用户ID）
user = db.query(User).filter(User.id == 1).first()
if user:
    user.is_admin = True
    db.commit()
    print(f"用户 {user.id} 已设置为管理员")
else:
    print("用户不存在")
db.close()
```

**方法2：使用SQLite命令行**
```bash
# 进入后端目录
cd H:\uae-match\backend

# 打开数据库（如果使用SQLite）
sqlite3 app.db

# 执行SQL
UPDATE users SET is_admin = 1 WHERE id = 1;  -- 替换1为实际用户ID

# 验证
SELECT id, email, is_admin FROM users WHERE id = 1;

# 退出
.quit
```

#### 步骤2：登录管理员账号
1. 使用设置为管理员的账号登录前端
2. 访问 `http://localhost:3000/admin`
3. **预期**：能够正常访问，看到管理员后台界面

#### 步骤3：测试非管理员访问
1. 使用普通用户账号登录
2. 尝试访问 `http://localhost:3000/admin`
3. **预期**：应该显示 "您没有管理员权限" 错误

#### 步骤4：查看举报列表
1. 在管理员后台，点击"举报管理"标签
2. **预期**：显示所有举报记录的列表
3. 测试筛选功能：
   - 选择"待处理"状态，应该只显示状态为 "open" 的举报
   - 选择"已解决"状态，应该只显示状态为 "resolved" 的举报

#### 步骤5：查看举报详情
1. 点击某个举报记录
2. **预期**：显示举报的详细信息，包括：
   - 举报人和被举报人的信息
   - 举报类别和描述
   - 相关消息内容（如果有）
   - 创建时间

#### 步骤6：更新举报状态
1. 选择一个状态为 "open" 的举报
2. 点击"操作"按钮
3. 选择"标记为审核中"
4. **预期**：
   - 状态更新成功
   - 列表刷新，该举报的状态变为 "reviewing"
   - 可以继续更新为 "resolved" 或 "closed"

#### 步骤7：查看风控事件
1. 点击"风控事件"标签
2. **预期**：显示所有事件日志
3. 应该能看到各种类型的事件：
   - `message_send` - 消息发送
   - `user_block` - 用户拉黑
   - `user_report` - 用户举报
   - `content_blocked` - 内容被阻止

#### 步骤8：查看统计信息
1. 点击"统计概览"标签
2. **预期**：显示统计卡片，包括：
   - 举报统计：总数、待处理数、近24小时、近7天、按类别统计
   - 事件统计：总数、近24小时、近7天、按类型统计

#### 步骤9：测试关联事件功能
1. 选择一个举报记录
2. 查看该举报的详情
3. 在详情中应该能看到相关的风控事件
4. 使用 API 测试关联功能：
```bash
# 使用 curl 或 Postman
curl -X POST "http://localhost:8000/api/v1/admin/reports/1/link-events" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"event_log_ids": [1, 2, 3]}'
```

### 预期结果
- ✅ 管理员可以访问后台
- ✅ 非管理员无法访问
- ✅ 举报列表正确显示
- ✅ 可以筛选和更新状态
- ✅ 事件列表正确显示
- ✅ 统计信息准确

### 故障排查

**问题1：无法访问管理员后台**
- 检查用户是否设置了 `is_admin = True`
- 检查数据库中的值是否正确
- 检查后端日志是否有权限错误

**问题2：API返回403错误**
- 确认使用的是管理员账号的token
- 检查 `get_current_admin_user` 函数是否正确工作
- 查看后端日志

**问题3：列表为空**
- 确认数据库中有举报记录（`user_reports` 表）
- 确认数据库中有事件记录（`event_logs` 表）
- 可以先创建一些测试数据

---

## 综合测试场景

### 场景1：完整聊天流程测试
1. User A 和 User B 建立配对
2. User A 发送正常消息 → 应该成功
3. User A 发送包含违规关键词的消息 → 应该被阻止
4. User B 实时收到正常消息
5. 管理员查看事件日志，应该能看到 `content_blocked` 事件
6. 管理员查看举报列表（如果有用户举报）

### 场景2：举报处理流程测试
1. User A 举报 User B
2. 管理员登录后台
3. 管理员查看举报列表，看到新的举报
4. 管理员查看举报详情
5. 管理员将状态更新为 "reviewing"
6. 管理员查看相关事件
7. 管理员将状态更新为 "resolved"

---

## 使用工具进行API测试

### 使用 curl 测试

```bash
# 1. 获取token（登录）
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "password"}'

# 2. 测试管理员API（替换TOKEN）
curl -X GET "http://localhost:8000/api/v1/admin/reports" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 3. 测试WebSocket（使用wscat工具）
# 安装: npm install -g wscat
wscat -c "ws://localhost:8000/api/v1/ws/chat/1?token=YOUR_TOKEN"
```

### 使用 Postman 测试
1. 创建新的 WebSocket 请求
2. URL: `ws://localhost:8000/api/v1/ws/chat/{match_pair_id}?token={token}`
3. 连接后发送 JSON 消息：
```json
{
  "type": "message",
  "content": "测试消息"
}
```

---

## 数据库检查

### 检查WebSocket连接
```sql
-- 无法直接查询，但可以检查消息是否保存
SELECT * FROM chat_messages ORDER BY created_at DESC LIMIT 10;
```

### 检查AI审核事件
```sql
SELECT * FROM event_logs 
WHERE event_type = 'content_blocked' 
ORDER BY created_at DESC;
```

### 检查管理员设置
```sql
SELECT id, email, is_admin FROM users WHERE is_admin = 1;
```

### 检查举报记录
```sql
SELECT * FROM user_reports ORDER BY created_at DESC;
```

---

## 常见问题解决

### 问题：WebSocket连接被拒绝
**解决方案**：
1. 检查后端是否支持WebSocket（FastAPI默认支持）
2. 检查防火墙设置
3. 检查CORS配置是否允许WebSocket

### 问题：AI审核不工作
**解决方案**：
1. 检查 `app/core/safety.py` 文件是否存在
2. 检查导入是否正确
3. 查看后端日志

### 问题：管理员权限不生效
**解决方案**：
1. 确认数据库中的 `is_admin` 字段为 `1` 或 `True`
2. 重新登录获取新的token
3. 检查 `get_current_admin_user` 函数

---

## 测试检查清单

- [ ] WebSocket连接成功建立
- [ ] 消息实时双向传输
- [ ] 正常消息可以发送
- [ ] 违规消息被阻止
- [ ] 违规事件被记录
- [ ] 管理员可以访问后台
- [ ] 非管理员无法访问
- [ ] 举报列表正确显示
- [ ] 可以更新举报状态
- [ ] 事件列表正确显示
- [ ] 统计信息准确

完成以上所有测试后，三个功能应该都能正常工作！

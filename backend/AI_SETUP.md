# AI 红娘功能配置指南

## 1. 环境变量配置

在 `backend` 目录下创建 `.env` 文件（如果不存在），添加以下配置：

```env
# OpenAI API 配置（必需）
OPENAI_API_KEY=sk-your-openai-api-key-here

# AI 预算配置（可选，有默认值）
GLOBAL_BUDGET_LIMIT=500.00
DEFAULT_USER_TOKEN_LIMIT=10000
VIP_USER_TOKEN_LIMIT=100000
DEFAULT_USER_RECOMMENDATION_QUOTA=2
VIP_USER_RECOMMENDATION_QUOTA=10
```

## 2. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

新增的依赖：
- `openai>=1.0.0` - OpenAI Python SDK

## 3. 数据库迁移

新的数据库表会在应用启动时自动创建：
- `ai_conversations` - AI对话历史
- `user_token_usage` - 用户Token使用追踪
- `user_recommendation_quota` - 推荐额度使用追踪
- `global_ai_budget` - 全局预算管理
- `ai_memory_summary` - AI记忆摘要（VIP用户）

## 4. 启动服务

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

## 5. API 端点

### 注册引导对话
- `POST /api/v1/ai-chat/start-registration` - 开始注册引导
- `POST /api/v1/ai-chat/send-message` - 发送消息（conversation_type: "registration"）
- `POST /api/v1/ai-chat/complete-registration` - 完成注册引导

### 日常咨询对话
- `POST /api/v1/ai-chat/send-message` - 发送消息（conversation_type: "consultation"）
- `GET /api/v1/ai-chat/history` - 获取对话历史

### Token和额度查询
- `GET /api/v1/ai-chat/token-usage` - 获取Token使用情况
- `GET /api/v1/ai-chat/recommendation-quota` - 获取推荐额度使用情况

## 6. 注意事项

1. **OpenAI API Key 是必需的**：如果没有配置，应用启动时会报错
2. **成本控制**：建议设置全局预算上限，防止意外超支
3. **Token 限制**：普通用户和VIP用户有不同的Token配额
4. **推荐额度**：每月自动重置，普通用户2次，VIP用户10次

## 7. 测试

1. 注册新账号
2. 自动跳转到 `/onboarding` 页面
3. AI红娘"小缘"会主动打招呼并开始收集信息
4. 与AI对话，回答相关问题
5. AI会主动判断是否收集充分，并总结
6. 确认后，资料保存完成，跳转到dashboard
















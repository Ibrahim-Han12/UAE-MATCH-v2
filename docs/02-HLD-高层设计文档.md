# 02 · HLD 高层设计文档

> UAE Match ｜ 版本 v1.0.0 ｜ 更新 2026-07-04

---

## 1. 系统架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                          浏览器 (Web 客户端)                        │
│   React 18 + TypeScript + Vite + Tailwind + Radix(shadcn/ui)     │
│   状态机导航 · localStorage 存 JWT · WebSocket 实时聊天             │
└───────────────┬─────────────────────────────┬───────────────────┘
                │ HTTPS REST (/api/v1/*)        │ WS (/ws/chat/{id})
                ▼                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      后端 API 服务 (FastAPI)                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ API 层  app/api/v1/endpoints/  (~58 接口, 17 功能域)         │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 核心服务 app/core/                                          │  │
│  │  security(JWT) · safety(审核) · risk(限流/日志)             │  │
│  │  openai_client · embedding_service · memory_service        │  │
│  │  vip_care_service · scheduler · cron_jobs · cache_cleanup  │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 数据层 models(SQLAlchemy ORM) + schemas(Pydantic)          │  │
│  └───────────────────────────────────────────────────────────┘  │
└───────┬─────────────────────────────┬───────────────┬───────────┘
        │                             │               │
        ▼                             ▼               ▼
   ┌─────────┐               ┌────────────────┐  ┌──────────┐
   │ SQLite  │               │  OpenAI API    │  │ 本地磁盘  │
   │ app.db  │               │ gpt-4o-mini /  │  │ uploads/ │
   │(生产→PG) │               │ embedding-3-sm │  │ (照片)   │
   └─────────┘               └────────────────┘  └──────────┘
```

---

## 2. 技术栈

### 2.1 后端
| 类别 | 选型 | 说明 |
|---|---|---|
| 语言/框架 | Python + **FastAPI** 0.104 | 异步高性能 Web 框架 |
| 服务器 | **Uvicorn** 0.24 (standard) | ASGI 服务器 |
| ORM | **SQLAlchemy** 2.0 | 数据库映射 |
| 数据校验 | **Pydantic** v2 + pydantic-settings | 请求/响应模型、配置 |
| 数据库 | **SQLite**（开发）→ PostgreSQL（生产推荐） | 见"部署" |
| 认证 | **python-jose**（JWT）+ **passlib**（PBKDF2-SHA256） | HS256 令牌 |
| AI | **openai** SDK ≥1.0 | GPT-4o-mini / text-embedding-3-small |
| 实时 | FastAPI **WebSocket** | 聊天 |
| 定时任务 | **schedule** + 守护线程 | 缓存清理、VIP 关怀 |
| 图像 | **Pillow** | 照片处理 |
| 数值 | **numpy** | 余弦相似度（带纯 Python 兜底）|

### 2.2 前端
| 类别 | 选型 |
|---|---|
| 框架 | React 18 + TypeScript |
| 构建 | Vite |
| UI | Tailwind CSS + Radix UI（shadcn/ui 组件） |
| 图标 | lucide-react |
| 表单 | React Hook Form |
| 导航 | **状态机切换**（无 react-router） |
| 状态 | React 本地 state（无 Redux/Context 全局库） |

---

## 3. 模块划分（后端）

| 目录 | 职责 |
|---|---|
| `app/main.py` | 应用入口：注册路由、CORS、启动/关闭钩子（启动调度器） |
| `app/api/v1/endpoints/` | 各功能域 API（auth/profile/photos/preferences/matches/match_recommendation/chat/chat_ws/ai_chat/coach/payment/notifications/safety/admin/analytics/events/health） |
| `app/core/` | 核心服务（AI、匹配、记忆、安全、认证、调度） |
| `app/models/` | 20 张 ORM 表定义 |
| `app/schemas/` | Pydantic 请求/响应模型 |
| `app/db/` | 数据库引擎、会话、Base |

> 各接口与算法细节见 [LLD](04-LLD-详细设计文档.md)。

---

## 4. 关键数据流

### 4.1 AI 引导注册 → 生成匹配向量
```
用户对话(小缘) → ai_chat 保存对话 → complete-registration
   → GPT 抽取结构化资料 → 写入 UserProfile + MatchPreference
   → embedding_service.build_profile_text() → OpenAI embedding
   → 写入 UserEmbedding(1536维, JSON存储)
```

### 4.2 智能匹配推荐（两套并存）
```
A) 规则匹配  GET /matches/suggestions?strategy=rule
   SQL 硬过滤(性别/年龄/身高/城市/时间线/居留) + 规则打分 → 候选列表

B) AI 向量匹配  POST /match/recommend
   SQL 硬过滤 → 加载全部 UserEmbedding → 余弦相似度(阈值0.7, Top5)
   → GPT-4o-mini 生成个性化推荐理由 → 返回(受配额/预算约束)
```

### 4.3 匹配互动 → 配对 → 聊天
```
POST /matches/action(like)
   → 写 MatchAction → 若双方互相 like → 建/激活 MatchPair(status=active)
   → 前端提示"互相喜欢" → 进入聊天(REST + WebSocket)
```

### 4.4 聊天消息安全链路
```
发消息 → safety.detect_content_risk()(关键词/正则) 
   → risk.check_rate_limit()(10秒内≤20条)
   → 通过则落库 ChatMessage + WebSocket 推送双方 + 记 EventLog
   → 违规则拦截并记 content_blocked 事件
```

### 4.5 AI 红娘对话 + 长期记忆
```
POST /ai-chat/send-message
   → 取 UserAIMemory 摘要 + 最近历史 → 组装个性化 system prompt
   → openai_client.chat_completion()(gpt-4o-mini, 失败回退gpt-3.5)
   → 落库 AIConversation + 更新 token 用量
   → memory_service 滚动摘要压缩(≤800 token)更新记忆
```

---

## 5. 定时/后台任务

| 任务 | 时间 (UTC) | 作用 |
|---|---|---|
| 缓存清理 `cache_cleanup` | 每天 02:00 | 删 30 天过期匹配分析缓存 + 每人保留最多 20 条 |
| VIP 主动关怀 `vip_care` | 每周二、周五 20:00 | 事件触发(新匹配/活跃度下降) + 兜底问候，含防打扰 |

由 `scheduler.py` 启动守护线程，随主进程存亡；任务定义在 `cron_jobs.py`。

---

## 6. 成本控制机制

- **模型策略**：主力 gpt-4o-mini；embedding 用 text-embedding-3-small；失败回退 gpt-3.5-turbo。
- **用户配额**：普通 50K token/月 + 2 次推荐/月；VIP 100K token/月 + 10 次推荐/月（`user_token_usage` / `user_recommendation_quota` 按月计）。
- **全局预算**：`global_ai_budget` 月度上限（默认 $500），超出报 403。
- **缓存**：匹配分析报告 `match_insight_cache` 缓存 30 天，避免重复计算。
- **记忆压缩**：滚动摘要将历史压到 ≤800 token，避免上下文膨胀。

---

## 7. 部署拓扑

### 7.1 开发环境（当前）
```
后端  cd backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
前端  cd uae-match-web-fronted-version2 && npm run dev   (Vite)
API 基址  前端读 VITE_API_BASE_URL，默认 http://127.0.0.1:8000/api/v1
CORS  main.py 中 origins 白名单
```

### 7.2 生产环境（目标）
| 组件 | 建议 |
|---|---|
| 前端 | 构建静态资源（`vite build`）托管到 Vercel/Netlify/对象存储 + CDN |
| 后端 | Uvicorn + Gunicorn（多 worker）/ 容器化，置于 Nginx 反向代理后 |
| 数据库 | **PostgreSQL**（+ pgvector 做向量检索）替换 SQLite |
| 存储 | 照片迁移到对象存储（S3/OSS）+ CDN，替换本地 `uploads/` |
| HTTPS | 生产强制 SSL |
| 密钥 | 全部走环境变量（JWT 密钥、OpenAI Key、支付密钥），禁止硬编码 |
| 缓存 | 引入 Redis（会话/热点/限流） |

---

## 8. 非功能性需求（NFR）

| 维度 | 现状 | 目标 |
|---|---|---|
| 安全 | JWT + 密码哈希 + 内容审核 + 限流 | JWT 密钥更换、HTTPS、API 限流、审计日志 |
| 性能 | 向量匹配 O(n) 线性扫描（SQLite 适用） | pgvector + HNSW 索引，支撑规模增长 |
| 可扩展 | 单实例 + 内置线程调度 | 无状态多实例 + 独立任务队列 |
| 可观测 | 日志打印 | APM、错误追踪、指标看板 |
| 可维护 | 模块清晰、无 Alembic | 引入数据库迁移工具（Alembic） |

---

## 9. 现状与缺口

- 🗄️ **SQLite 单文件**：并发/规模有限，向量以 JSON 文本存储、线性检索——生产需迁 PostgreSQL + pgvector。
- 🔑 **JWT 密钥为默认值**（`config.py` 中 `change-this-in-production`），上线前**必须**改并走环境变量。
- 🔐 **OpenAI Key 现存于 `backend/.env`**（已 gitignore 未上传），但曾明文存在，建议**轮换新 Key**。
- ⚙️ **无数据库迁移框架**：目前靠 `migrate_add_*.py` 手写脚本 + `create_all`，建议引入 Alembic。
- 🧵 **调度器为进程内守护线程**：多实例部署会重复执行，需改为独立调度/分布式锁。
- 🖼️ **照片存本地磁盘**：不利于横向扩展与 CDN 加速。
- 🔔 **通知系统桩实现**：需补存储与推送。

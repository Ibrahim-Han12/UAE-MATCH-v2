# 04 · LLD 详细设计文档

> UAE Match ｜ 版本 v1.0.0 ｜ 更新 2026-07-04
> 后端：`backend/app/`（FastAPI + SQLAlchemy）｜ 数据库前缀：`/api/v1`

本文分三部分：**A. 数据库表结构** · **B. API 接口清单** · **C. 核心算法实现**。

---

# A. 数据库表结构

共 **20 张表**（`backend/app/models/`）。除特别说明外，各表均含 `id`(PK)、`created_at`、`updated_at`；`user_id` 均为外键指向 `users.id`。时间字段为带时区 DateTime，默认 `func.now()`。

### A.1 账户与资料

**users** — 用户账户
| 字段 | 类型 | 约束 |
|---|---|---|
| email | String(255) | 唯一, 可空(与 phone 二选一) |
| phone | String(50) | 唯一, 可空 |
| hashed_password | String(255) | 非空 |
| is_active | Boolean | 默认 true |
| is_admin | Boolean | 默认 false |
| status | String(50) | 默认 "active" |

**user_profiles** — 个人资料（与 user 一对一，`user_id` 唯一）
| 关键字段 | 类型 | 说明 |
|---|---|---|
| display_name | String(100) | 昵称 |
| gender | String(20) | male/female |
| birth_year | Integer | 出生年（用于算年龄） |
| height_cm | Integer | 身高 |
| nationality / current_country / current_city | String | 国籍/所在国/所在城市 |
| occupation / company / education_level | String | 职业/公司/学历 |
| bio | String(500) | 自我介绍（向量化重点） |
| is_public | Boolean | 默认 true |
| extended_info | JSON | 兴趣/价值观/生活方式等扩展 |

**user_photos** — 照片
| 关键字段 | 类型 | 说明 |
|---|---|---|
| file_path / file_url / file_name | String | 路径/URL/文件名 |
| file_size / mime_type / width / height | - | 元数据 |
| display_order | Integer | 排序，0=主图 |
| is_primary / is_verified | Boolean | 是否主图/已验证 |
| status | String(20) | pending/approved/rejected |
| rejection_reason | String(500) | 驳回原因 |

**match_preferences** — 择偶偏好（一对一，`user_id` 唯一）
| 关键字段 | 说明 |
|---|---|
| preferred_gender / min_age / max_age / min_height_cm / max_height_cm | 基础偏好 |
| min_income_monthly_aed | 月收入门槛(AED) |
| education_level / religion / mbti | 学历/宗教/MBTI |
| marriage_timeline / want_children | 结婚时间线/子女意愿 |
| plan_settle_in_uae (Bool) / plan_return_china | UAE 本地化关键维度 |
| notes | 备注 |

### A.2 匹配与聊天

**match_actions** — 喜欢/跳过动作
- `actor_user_id`, `target_user_id`, `action_type`(like/pass/super_like)
- 唯一约束 `uq_actor_target_once (actor, target)`——每对仅一条，新覆盖旧。

**match_pairs** — 配对关系
- `user1_id`, `user2_id`, `status`(active/blocked/archived)
- 唯一约束 `uq_match_pair_unique (user1, user2)`；双方互相 like 时建立。

**chat_messages** — 聊天消息
- `match_pair_id`(FK), `sender_user_id`(FK), `content`(Text), `is_read`(Bool)

### A.3 安全与审计

**user_blocks** — 拉黑：`blocker_id`, `blocked_id`, `reason`；唯一 `uq_blocker_blocked`。
**user_reports** — 举报：`reporter_id`, `reported_user_id`, `reported_message_id`(可空), `category`(harassment/scam/fake_profile/spam/other), `description`, `status`(open/reviewing/closed)。
**event_logs** — 事件日志：`user_id`, `event_type`, 可选 `target_user_id/match_pair_id/message_id/report_id`, `meta`(DB 列名 `metadata`, 存 JSON 串)。用于风控与审计。

### A.4 支付与订阅（`order.py`）

**orders** — 订单
| 关键字段 | 说明 |
|---|---|
| order_no | String(64) 唯一 |
| product_type / product_id / product_name | subscription/premium_feature |
| amount | Numeric(10,2) |
| currency | 默认 "CNY" |
| payment_method | alipay/wechat/credit_card |
| payment_status | pending/paid/failed/refunded |
| payment_transaction_id / paid_at / callback_data | 支付回执 |
| status | pending/completed/cancelled/refunded |

**subscriptions** — 订阅（一对一，`user_id` 唯一）
- `plan_type`(free/basic/premium), `status`(active/expired/cancelled)
- `started_at / expires_at / cancelled_at`, `order_id`(FK), `auto_renew`(Bool), `next_billing_date`

### A.5 AI 相关

**user_token_usage** — 月度 token 用量：`month`("YYYY-MM"), `tokens_used`, `tokens_limit`(默认10000)；唯一 `uq_user_month_token`。
**user_recommendation_quota** — 月度推荐额度：`month`, `quota_used`, `quota_limit`(默认2)；唯一 `uq_user_month_quota`。
**global_ai_budget** — 全局预算：`month`(唯一), `budget_limit`(默认500.00 USD), `budget_used`, `modified_by`, `modification_history`(JSON)。
**ai_conversations** — AI 对话历史：`role`(user/assistant/system), `content`(Text), `conversation_type`(registration/consultation/care/match_recommendation), `tokens_used`, `model`, `meta`(JSON, 列名 metadata)。
**ai_memory_summary** — 分层记忆(VIP)：`summary_type`(short_term/mid_term/long_term), `content`；唯一 `uq_user_memory_type`。
**user_ai_memory** — 滚动摘要：`summary_text`(Text), `token_count`, `last_updated_at`；`user_id` 唯一（每人一条）。
**user_embeddings** — 用户向量：`embedding_vector`(Text, JSON 存), `source_text`, `dimension`(默认1536)；`user_id` 唯一，索引 `idx_user_embedding_user_id`。
**match_insight_cache** — 匹配分析缓存：`user_id`, `target_user_id`, `explanation`(Text), `match_score_breakdown`(JSON), `opener_suggestions`(JSON)；唯一索引 `idx_user_target_unique`。

### A.6 关系图（简）
```
users 1─1 user_profiles / match_preferences / subscriptions / user_ai_memory / user_embeddings
users 1─N user_photos / match_actions / ai_conversations / event_logs / orders
match_pairs (user1,user2) 1─N chat_messages
user_reports ─? chat_messages ；event_logs ─? (match_pair/message/report/target_user)
```

---

# B. API 接口清单

**统一前缀 `/api/v1`**。除标注外均需 `Authorization: Bearer <access_token>`。共约 **58 个接口**。

### B.1 健康 / 认证
| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | /health | 否 | 健康检查 `{"status":"ok"}` |
| POST | /auth/register | 否 | 注册（邮箱或手机 + 密码） |
| POST | /auth/login | 否 | 登录，返回 access+refresh token |
| POST | /auth/refresh | 否 | 用 refresh token 换新 access |
| GET | /auth/me | 是 | 当前用户信息 |

### B.2 资料 / 偏好
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /profile/me | 取我的资料（未建返回404） |
| PUT | /profile/me | 创建或更新资料（merge extended_info） |
| GET | /preferences/me | 取我的择偶偏好 |
| PUT | /preferences/me | 创建或更新偏好 |

### B.3 照片
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /photos/upload | 上传（JPEG/PNG/WebP，≤10MB，≤9张） |
| GET | /photos/me | 我的照片（按序，排除已驳回） |
| GET | /photos/{photo_id} | 单张元数据 |
| GET | /photos/file/{filename} | 下载文件（无需鉴权） |
| PUT | /photos/{photo_id} | 设主图/改顺序 |
| POST | /photos/reorder | 批量重排（首张自动设主图） |
| DELETE | /photos/{photo_id} | 删除（含磁盘文件） |

### B.4 匹配
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /matches/suggestions | 规则匹配推荐（limit, strategy=rule/ai） |
| POST | /matches/action | 喜欢/跳过/超级喜欢，返回 is_mutual_match |
| GET | /matches/my-matches | 我的互相匹配列表 |
| GET | /matches/who-liked-me | 喜欢我但未互相的人 |
| GET | /matches/recommendations | (旧)候选用户列表 |
| POST | /match/recommend | **AI 向量推荐**（配额+预算约束，返回推荐理由） |

### B.5 聊天（REST）+ WebSocket
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /chats/my-conversations | 会话列表（仅 active） |
| GET | /chats/{id}/messages | 消息历史（skip/limit, 自动标已读） |
| POST | /chats/{id}/messages | 发消息（≤1000字, 审核, 10秒≤20条） |
| POST | /chats/{id}/block · /unblock · /report | 会话内拉黑/取消/举报 |
| WS | /ws/chat/{id}?token=JWT | 实时聊天（message/ping；new_message/pong/error） |

### B.6 AI 红娘 / 匹配分析
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /ai-chat/send-message | 与小缘对话（消耗 token，记忆更新） |
| GET | /ai-chat/history | 对话历史 |
| POST | /ai-chat/start-registration | 开始引导注册 |
| POST | /ai-chat/complete-registration | 完成注册（AI 抽取资料落库 + 建向量） |
| GET | /ai-chat/token-usage | 月度 token 额度 |
| GET | /ai-chat/recommendation-quota | 月度推荐额度 |
| GET | /ai-chat/memory-summary | 分层长期记忆（VIP，非 VIP 返回403） |
| POST | /coach/match-insights | 对指定对象生成 AI 分析（缓存30天, 30次/分） |

### B.7 支付 / 订阅
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /payment/create-order | 下单，返回 payment_url |
| POST | /payment/callback | 支付平台回调（无需鉴权），更新订单/订阅 |
| GET | /payment/orders/me · /orders/{order_no} | 订单列表/详情 |
| GET | /payment/subscription/status | 订阅状态（是否 premium、剩余天数） |
| GET | /payment/products | 商品目录（无需鉴权） |

### B.8 安全 / 管理 / 分析 / 事件 / 通知
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /safety/block · DELETE /safety/block/{id} · GET /safety/blocked | 拉黑管理 |
| POST | /safety/report | 举报用户/消息 |
| GET | /admin/reports · /reports/{id} · PATCH /reports/{id}/status | 举报处理（管理员） |
| POST | /admin/reports/{id}/link-events | 关联风险事件（管理员） |
| GET | /admin/events · /events/{id} · /admin/stats | 事件与统计（管理员） |
| GET | /analytics/me/snapshot | 用户快照统计 |
| GET | /analytics/me/match-context | 为 LLM 提供匹配上下文 |
| GET | /events/my | 我的行为事件日志 |
| GET/POST/DELETE | /notifications/* | 通知（🔴 当前为桩，返回空/0） |

---

# C. 核心算法实现（`backend/app/core/`）

### C.1 认证与密码（security.py）
- 密码哈希：**PBKDF2-SHA256**（`passlib` CryptContext，无 bcrypt 72 字节限制）。
- `create_access_token`：payload `{sub: user_id, exp}`，HS256，密钥 `JWT_SECRET_KEY`，有效期 30 分钟。
- `create_refresh_token`：HS256，密钥 `JWT_REFRESH_SECRET_KEY`，有效期 7 天。
- 令牌流：登录发 access(30m)+refresh(7d)；access 过期用 refresh 换新；refresh 过期需重登。

### C.2 匹配算法（embedding_service.py）
```
1. build_profile_text(user)  组装用于向量化的文本
   - 排除年龄/身高/城市(这些走 SQL 硬过滤)
   - 纳入 bio(重点)、职业/学历/公司、extended_info(兴趣/价值观/生活方式/性格/择偶/人生目标)、
     以及 match_preferences(偏好性别/年龄段/身高/学历/收入/结婚时间线/子女/定居/宗教/MBTI)
2. get_embedding(text) → OpenAI text-embedding-3-small → 1536 维向量
3. create_or_update_embedding() 写入 user_embeddings(JSON 存向量)
4. find_similar_users():
   - 载入本人向量 + 全部其他用户向量
   - cosine_similarity = dot(v1,v2)/(‖v1‖·‖v2‖)  (numpy, 纯 Python 兜底)
   - 过滤 similarity ≥ 0.7(min_similarity)，按降序取 Top5(limit)
   复杂度 O(n) 线性扫描（SQLite 适用；生产建议 pgvector + HNSW）
```

### C.3 AI 对话与长期记忆
**openai_client.py**
- `chat_completion()`：30s 超时、最多重试；错误分类处理——模型错误(404)立即回退 `fallback_model` 重试；配额错误(429)立即抛；连接错误指数退避；返回 `{content, tokens_used, model}`。
- `get_system_prompt_for_user()`：按资料 + 记忆摘要 + 会话类型(registration/consultation) + 用户风格(活泼/温柔/直接)生成个性化 system prompt；含边界约束（不提供医疗/法律建议）。

**memory_service.py（滚动摘要）**
```
update_memory_after_conversation():
  取最近 10 条 AIConversation + 旧摘要(user_ai_memory.summary_text)
  → GPT-4o-mini 压缩(temperature=0.3): 保留事实/去寒暄/突出情感与偏好变化, ≤500字
  → 估算 token(≈4字/token) → 更新 user_ai_memory
好处: 上下文有界(≤800 token)，跨会话保持连续性
```

### C.4 智能推荐链路（match_recommendation.py）
```
POST /match/recommend:
  校验配额(user_recommendation_quota) + 全局预算(global_ai_budget)
  → SQL 硬过滤(性别/年龄/身高/城市/居留等) 得候选
  → embedding 余弦相似度排序
  → GPT-4o-mini 为每位候选生成个性化"推荐理由"
  → 配额+1、预算累加；超限抛 403
```

### C.5 匹配分析报告（coach.py）
- `POST /coach/match-insights`：基于双方向量 + GPT-4o-mini 生成兼容性分析。
- 输出：`explanation`、`match_score_breakdown{values, lifestyle, personality, goals}`（各 0–1）、`suggested_openers`（2–3 条 50–80 字破冰语）、`safety_tips`（固定 4 条）。
- **缓存**：写入 `match_insight_cache`，有效期 30 天，每人最多 20 条（超出淘汰最旧）；限流 30 次/分钟。

### C.6 内容安全（safety.py）
```
detect_content_risk(text):
  分类关键词匹配(诈骗/色情/赌博/毒品/暴力/垃圾, 共 ~150 词) + 正则高危模式(联系方式+诈骗组合)
  风险等级:
    BLOCKED: 色情/暴力/毒品 命中, 或 诈骗+高危模式
    HIGH:    赌博 ≥2 词
    MEDIUM:  垃圾 ≥2 词 / 多类命中
    LOW:     垃圾 =1 词
    SAFE:    无命中
  should_block_content() = (BLOCKED 或 HIGH)
```
> 说明：当前为**关键词/正则**方案（非 LLM 审核），成本低但覆盖有限，后续可升级为 AI 审核。

### C.7 限流与事件（risk.py）
- `log_event()`：写 `event_logs`（支持 target/match_pair/message/report + metadata JSON）。
- `check_rate_limit(user, event_type, window_seconds, max_count)`：滑动窗口计数，超限抛 HTTP 429。

### C.8 VIP 主动关怀（vip_care_service.py + cron_jobs.py）
```
调度: 每周二/五 20:00 UTC (cron_jobs.setup_cron_jobs)
should_send_care_message(user):
  若 1 小时内在活跃聊天 → 不打扰(False)
  事件触发: 24h 内新匹配 / 活跃度下降(3–7天沉默) → True
  兜底: ≥3天不活跃 且 周二/五 18:00–22:00 → True("fallback:schedule")
generate_care_message(): GPT-4o-mini(temp=0.8) 按触发类型生成 ≤50字、≤1 emoji、朋友口吻
process_vip_care(): 批量遍历 VIP → 生成 → 存为 ai_conversations(type=care)
```

### C.9 定时清理（scheduler.py + cache_cleanup.py）
- 守护线程每 60s 检查 `schedule.run_pending()`；随主进程存亡。
- `run_cache_cleanup()`（每天 02:00 UTC）：删 30 天过期 `match_insight_cache` + 每人保留最多 20 条。

---

# D. 现状与缺口（技术）

| 缺口 | 影响 | 建议 |
|---|---|---|
| SQLite + JSON 向量 + O(n) 检索 | 规模/并发受限 | 迁 PostgreSQL + pgvector + HNSW |
| JWT 密钥为默认值 | 安全风险 | 上线前改，走环境变量 |
| OpenAI Key 曾明文于 .env | 泄露风险 | 轮换新 Key |
| 无 Alembic 迁移 | 表结构演进靠手写脚本 | 引入 Alembic |
| 调度器进程内线程 | 多实例重复执行 | 独立调度/分布式锁 |
| 支付未接真实网关 | 无法真实收款 | 对接支付宝/微信/信用卡 + 验签 |
| 通知系统桩实现 | 无法触达用户 | 实现存储 + 站内/Web Push |
| 内容审核仅关键词 | 漏判/误判 | 升级 AI 审核 + 人工复核 |
| 照片存本地磁盘 | 扩展/加速受限 | 迁对象存储 + CDN |

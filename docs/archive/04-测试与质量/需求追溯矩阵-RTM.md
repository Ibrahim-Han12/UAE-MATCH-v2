# 04 · 需求追溯矩阵（RTM）

> UAE Match ｜ 版本 v1.0.0 ｜ 更新 2026-07-04

本矩阵建立 **需求 → 接口/模块 → 测试用例** 的双向追溯，用于确认每条需求均有测试覆盖、每个用例均可回溯到需求，并跟踪覆盖率。需求来源为 BRD 功能范围（第 3.1 节）与 LLD 接口/算法；用例 ID 引用《测试用例集.md》。

**覆盖状态**：✅ 已覆盖 / ⚠️ 部分覆盖（受演示态或桩实现限制） / 🔴 未覆盖（框架/桩，仅结构验证）。

---

## 1. 需求追溯主表

| 需求ID | 需求描述 | 对应模块（BRD 3.1） | 关键接口/算法（LLD） | 对应测试用例 | 覆盖状态 |
|---|---|---|---|---|---|
| REQ-01 | 邮箱/手机 + 密码注册登录 | 账户与认证 | `POST /auth/register`、`/auth/login` | TC-AUTH-01~03, 06~08 | ✅ |
| REQ-02 | JWT 令牌 + 刷新令牌机制 | 账户与认证 | `/auth/me`、`/auth/refresh`；HS256 access(30m)/refresh(7d) | TC-AUTH-04, 05, 09, 10 | ✅ |
| REQ-03 | JWT 密钥安全（非默认值） | 账户与认证（安全缺口） | `JWT_SECRET_KEY` 环境变量 | TC-AUTH-11 | ⚠️ 已知缺口，专项跟踪 |
| REQ-04 | 密码安全存储 | 账户与认证 | PBKDF2-SHA256 哈希 | TC-AUTH-01（校验非明文） | ✅ |
| REQ-05 | 个人资料增改查 | 个人资料 | `GET/PUT /profile/me`（merge extended_info） | TC-PROF-01~04, 07 | ✅ |
| REQ-06 | 择偶偏好设置（含 UAE 本地化维度） | 个人资料 | `GET/PUT /preferences/me`（定居/回国/结婚时间线/子女） | TC-PROF-05, 06, 08 | ✅ |
| REQ-07 | 前后端字段转换 | 前端 | 男女↔male/female、age↔birth_year | TC-PROF-10 | ✅ |
| REQ-08 | 照片上传（≤9张/≤10MB/类型限制） | 照片系统 | `POST /photos/upload`（JPEG/PNG/WebP） | TC-PHOTO-01, 02, 08, 09, 10 | ✅ |
| REQ-09 | 照片排序/设主图/删除 | 照片系统 | `/photos/reorder`、`PUT/DELETE /photos/{id}` | TC-PHOTO-03~06 | ✅ |
| REQ-10 | 照片审核状态字段 | 照片系统 | `status` pending/approved/rejected | TC-PHOTO-03（排除 rejected） | ⚠️ 状态字段有，审核流程为演示态 |
| REQ-11 | AI 对话式引导注册 | AI 引导注册 | `/ai-chat/start-registration`、`/send-message` | TC-AIREG-01, 02, 04 | ✅ |
| REQ-12 | AI 抽取资料落库 + 生成向量 | AI 引导注册 | `/ai-chat/complete-registration`；embedding_service | TC-AIREG-03, 05 | ✅ |
| REQ-13 | 规则匹配（SQL 硬过滤） | 智能匹配 | `GET /matches/suggestions?strategy=rule` | TC-MATCH-01 | ✅ |
| REQ-14 | AI 向量语义匹配（余弦≥0.7 Top5） | 智能匹配（核心差异化） | `strategy=ai`、`POST /match/recommend`；cosine_similarity | TC-MATCH-02, 08, 09 | ✅ |
| REQ-15 | 喜欢/跳过/超级喜欢 | 匹配互动 | `POST /matches/action`（返回 is_mutual_match） | TC-MATCH-03, 05, 10 | ✅ |
| REQ-16 | 互相喜欢自动配对 | 匹配互动 | `match_pairs` 建立 | TC-MATCH-04, 06 | ✅ |
| REQ-17 | 谁喜欢我 | 匹配互动 | `GET /matches/who-liked-me` | TC-MATCH-07 | ✅ |
| REQ-18 | AI 匹配分析报告 + 破冰开场白 | AI 匹配分析 | `POST /coach/match-insights`（4维 breakdown/openers/safety_tips） | TC-INSIGHT-01, 04, 06 | ✅ |
| REQ-19 | 匹配分析缓存（30天/20条/人） | AI 匹配分析 | `match_insight_cache` | TC-INSIGHT-02, 03 | ✅ |
| REQ-20 | 匹配分析限流（30次/分） | AI 匹配分析 | risk.py check_rate_limit | TC-INSIGHT-05 | ✅ |
| REQ-21 | WebSocket 实时聊天 | 实时聊天（核心差异化） | `WS /ws/chat/{id}?token=JWT`（message/ping/new_message/pong） | TC-CHAT-04, 12, 13 | ✅ |
| REQ-22 | REST 历史消息 + 已读状态 | 实时聊天 | `GET /chats/{id}/messages`（自动标已读）、`/my-conversations` | TC-CHAT-01, 02 | ✅ |
| REQ-23 | 发消息（≤1000字，10秒≤20条） | 实时聊天 | `POST /chats/{id}/messages` | TC-CHAT-03, 07, 08 | ✅ |
| REQ-24 | 聊天内容审核拦截 | 安全与风控 | detect_content_risk（关键词/正则） | TC-CHAT-09, 10, 11 | ⚠️ 仅关键词/正则，覆盖有限 |
| REQ-25 | AI 红娘日常咨询 | AI 红娘咨询（核心差异化） | `POST /ai-chat/send-message`(consultation) | TC-AICHAT-01, 02, 08 | ✅ |
| REQ-26 | AI 长期记忆（滚动摘要） | AI 红娘咨询 | memory_service；`user_ai_memory` | TC-AICHAT-01, 09 | ✅ |
| REQ-27 | 分层长期记忆（VIP 专属） | AI 红娘咨询 | `GET /ai-chat/memory-summary`（非VIP 403） | TC-AICHAT-05, 06 | ✅ |
| REQ-28 | Token 配额（默认10000/月） | AI 成本控制 | `user_token_usage`；`/token-usage` | TC-AICHAT-03, 07；TC-QUOTA-01, 02 | ✅ |
| REQ-29 | 推荐额度（默认2/月） | AI 成本控制 | `user_recommendation_quota`；`/recommendation-quota` | TC-AICHAT-04；TC-MATCH-12；TC-QUOTA-03 | ✅ |
| REQ-30 | 全局预算控制（默认500 USD） | AI 成本控制 | `global_ai_budget` | TC-MATCH-13；TC-QUOTA-04 | ✅ |
| REQ-31 | 跨月配额重置 | AI 成本控制 | 唯一 `uq_user_month_*` | TC-QUOTA-05 | ✅ |
| REQ-32 | VIP 主动关怀（定时+事件） | VIP 主动关怀 | vip_care_service + cron_jobs | （见备注）后端定时任务 | ⚠️ 需定时/触发环境专测 |
| REQ-33 | 拉黑管理 | 安全与风控 | `POST/DELETE /safety/block`、`GET /safety/blocked` | TC-SAFE-01~03, 05, 06, 08 | ✅ |
| REQ-34 | 举报用户/消息 | 安全与风控 | `POST /safety/report`、`/chats/{id}/report` | TC-SAFE-04, 07；TC-CHAT-05 | ✅ |
| REQ-35 | 限流防刷（滑动窗口） | 安全与风控 | check_rate_limit | TC-CHAT-08；TC-INSIGHT-05 | ✅ |
| REQ-36 | 事件日志审计 | 安全与风控 | `event_logs`、`GET /events/my` | TC-SAFE-04；TC-ADMIN-07 | ✅ |
| REQ-37 | 支付下单 + payment_url | 支付与订阅 | `POST /payment/create-order` | TC-PAY-02, 08 | ⚠️ 未接真实网关 |
| REQ-38 | 支付回调 + 订阅开通 | 支付与订阅 | `POST /payment/callback` | TC-PAY-03, 06, 07 | ⚠️ 模拟回调，缺验签 |
| REQ-39 | 订单/订阅状态查询 | 支付与订阅 | `/orders/me`、`/subscription/status`、`/products` | TC-PAY-01, 04, 05, 09 | ✅ |
| REQ-40 | 管理后台举报处理 | 管理后台 | `/admin/reports*`、`link-events` | TC-ADMIN-01~03, 06 | ✅ |
| REQ-41 | 风险事件与统计看板 | 管理后台 | `/admin/events`、`/admin/stats` | TC-ADMIN-04, 05 | ✅ |
| REQ-42 | 用户数据分析快照 | 数据分析 | `/analytics/me/snapshot`、`/match-context` | TC-ADMIN-07 | ✅ |
| REQ-43 | 通知系统 | 通知系统 | `/notifications/*` | TC-NOTIF-01 | 🔴 桩实现，仅结构验证 |

---

## 2. 覆盖率追踪

### 2.1 按覆盖状态统计

| 状态 | 需求数 | 说明 |
|---|---|---|
| ✅ 完全覆盖 | 33 | 有对应用例且可正常验证 |
| ⚠️ 部分覆盖 | 9 | 受演示态/桩/未接网关/审核方案限制（REQ-03、10、24、32、37、38 等） |
| 🔴 结构验证 | 1 | REQ-43 通知桩实现 |
| **合计** | **43** | **需求用例映射率 100%（均有对应用例或验证策略）** |

覆盖率计算：`需求覆盖率 = 有对应用例的需求数 / 需求总数 = 43/43 = 100%`。其中 ✅ 状态的"可真实验证覆盖率" = 33/43 ≈ 77%，差额由 v1.0 已知缺口（支付网关/通知桩/演示态/审核方案）构成，均已在《测试计划.md》范围外说明并跟踪。

### 2.2 差异化能力覆盖（重点保障）

| 差异化能力 | 需求 | 用例 | 状态 |
|---|---|---|---|
| AI 向量语义匹配 | REQ-14 | TC-MATCH-02/08/09 | ✅ |
| AI 红娘小缘 | REQ-11/12/25/26/27 | TC-AIREG-*、TC-AICHAT-* | ✅ |
| 实时聊天（WebSocket） | REQ-21/22/23 | TC-CHAT-* | ✅ |
| AI 成本可控（配额+预算） | REQ-28/29/30/31 | TC-QUOTA-*、TC-MATCH-12/13 | ✅ |

### 2.3 追溯维护规则

- 新增/变更需求时，同步在本表登记，并补充或修订对应用例 ID，保持双向可追溯。
- 需求删除时，标注废弃并保留历史行（可加删除线），关联用例同步归档。
- 每轮测试结束更新覆盖状态；⚠️/🔴 项须在发布评审中逐条给出结论与上线前处置计划。

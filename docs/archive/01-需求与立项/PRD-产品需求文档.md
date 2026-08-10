# 02 · PRD 产品需求文档

> UAE Match ｜ 版本 v1.0.0 ｜ 更新 2026-07-04

---

## 1. 文档说明与范围

### 1.1 目的

本文档是**开发对照的核心清单**，将 UAE Match 的业务需求（见 [BRD](./BRD-业务需求文档.md)）拆解为可执行、可验收的用户故事与验收标准，并逐条标注**真实实现状态**，供产品、研发、测试三方对齐。

### 1.2 范围

- **覆盖**：v1.0 已成形的全部功能模块（约 58 个 API、20 张数据表），以及为商业化上线必须补齐的缺口。
- **不覆盖**：具体 UI 视觉稿（见 [UIUX](../02-设计与规划/UIUX-界面与交互文档.md)）、数据库/接口/算法细节（见 [LLD](../02-设计与规划/LLD-详细设计文档.md)）、技术架构（见 [HLD](../02-设计与规划/HLD-高层设计文档.md)）。

### 1.3 状态图例

| 图例 | 含义 |
|---|---|
| ✅ 已实现 | 后端逻辑完整、可端到端运行 |
| ⚠️ 部分 | 后端具备但未接真实依赖，或前端未完整串联 |
| 🔴 未实现 | 桩实现 / 仅接口定义 / 尚未开发 |

### 1.4 平台策略

**先 Web 后 App**。当前形态为 React + Vite Web 应用；移动 App（iOS/Android）为远期目标，本 PRD 以 Web 现状为基线。

---

## 2. 角色定义

| 角色 | 标识 | 说明 | 关键权限 |
|---|---|---|---|
| 游客 | Guest | 未注册/未登录 | 浏览落地页、注册、登录、查看商品目录（`/payment/products`） |
| 免费用户 | Free | 已注册且完成资料，`subscription.plan_type=free` | 核心功能，每日推荐/匹配额度受限（默认月推荐配额 2），AI 分析仅前 2 维 |
| 普通会员 | Basic | `plan_type=basic`（¥29/月） | 解除额度限制、查看谁喜欢我、优先推荐 |
| VIP（高级会员） | Premium | `plan_type=premium`（¥59/月） | 全部特权 + 超级喜欢 + 已读状态 + 高级筛选 + AI 长期分层记忆 + AI 主动关怀 |
| 管理员 | Admin | `users.is_admin=true` | 举报处理、风险事件、关联事件、统计看板 |

> 说明：前端当前 `isVIP` 为演示开关（非真实订阅态），商业化阶段需以 `/payment/subscription/status` 为准。

---

## 3. 功能模块与用户故事

> 每条故事标注状态并给出验收标准（Given/When/Then 或要点式）。接口以 LLD 清单为准，统一前缀 `/api/v1`。

### 3.1 账号认证 ✅

**US-AUTH-01｜邮箱或手机注册** ✅
- 作为游客，我希望用邮箱或手机号 + 密码注册，以便创建账户。
- 验收：
  - Given 提供合法邮箱或手机号与密码，When 调 `POST /auth/register`，Then 创建 `users` 记录（`hashed_password` 为 PBKDF2-SHA256），并自动登录返回 access+refresh token。
  - Given 邮箱/手机已存在，When 注册，Then 返回冲突错误，不重复建号。
  - 邮箱与手机二选一即可（数据库均为可空、唯一）。

**US-AUTH-02｜登录与令牌** ✅
- 作为已注册用户，我希望登录获取访问令牌。
- 验收：
  - `POST /auth/login` 成功返回 access(30 分钟)+refresh(7 天)。
  - 所有受保护请求需 `Authorization: Bearer <token>`；令牌无效/过期返回 401。

**US-AUTH-03｜刷新令牌** ✅
- 验收：`POST /auth/refresh` 用 refresh token 换新 access；refresh 过期需重新登录。
- 现状：前端已存 `access_token`，`refresh_token` 预留但**未启用**（⚠️ 前端），401 直接登出回落地页。

**US-AUTH-04｜获取当前用户** ✅
- 验收：`GET /auth/me` 返回当前用户账户信息。

**US-AUTH-05｜Google/第三方登录** 🔴
- 现状：登录页有占位入口，未实现 OAuth。

### 3.2 AI 引导注册 ✅

**US-ONB-01｜"小缘"对话式收集资料** ✅
- 作为新用户，我希望通过与 AI 红娘"小缘"对话完成资料填写，而非填表。
- 验收：
  - Given 新用户进入引导，When 调 `POST /ai-chat/start-registration`，Then 小缘发起首个问题，前端展示进度条与气泡。
  - When 用户逐条回答，`POST /ai-chat/send-message` 追问收集：姓名、年龄、性别、UAE 城市、职业、在 UAE 时长、结婚时间线、长期规划、子女计划、期望年龄段等 12+ 项。
  - `GET /ai-chat/history` 可回放引导对话。

**US-ONB-02｜AI 抽取结构化资料并生成向量** ✅
- 验收：
  - When 调 `POST /ai-chat/complete-registration`，Then AI 从自然语言对话抽取结构化字段写入 `user_profiles`，并调用 embedding 服务生成 1536 维向量写入 `user_embeddings`。
  - 完成后进入待审核态。

**US-ONB-03｜注册审核** ⚠️
- 现状：后端有照片/资料审核状态字段；**前端为演示态**——待审核页 10 秒自动过审，非真实人工/AI 审核流程。

### 3.3 个人资料与偏好 ✅ / 前端 ⚠️

**US-PROF-01｜创建/更新资料** ✅（后端）/ ⚠️（前端）
- 验收：
  - `GET /profile/me` 未建资料返回 404（前端据此判定进引导）。
  - `PUT /profile/me` 创建或更新资料，`extended_info`（兴趣/价值观/生活方式）以 **merge** 方式合并。
  - 前后端字段转换：性别 `男/女 ↔ male/female`，年龄 `age ↔ birth_year`。
- 现状：前端 ProfilePage 编辑入口存在但**未完整对接** `PUT /profile/me`（⚠️）。

**US-PROF-02｜择偶偏好设置** ✅
- 验收：
  - `GET /preferences/me`、`PUT /preferences/me` 管理 `match_preferences`。
  - 支持基础偏好（性别/年龄/身高/收入门槛 AED/学历/宗教/MBTI）与**本地化维度**（结婚时间线、子女意愿、`plan_settle_in_uae`、`plan_return_china`）。
- 说明：本地化维度是差异化匹配的关键输入。

### 3.4 照片 ✅（后端）/ 前端 ⚠️

**US-PHOTO-01｜上传照片** ✅（后端）/ ⚠️（前端）
- 验收：
  - `POST /photos/upload` 接受 JPEG/PNG/WebP，单张 ≤10MB，最多 9 张，写入 `user_photos`，初始 `status=pending`。
- 现状：后端完整；前端上传/管理/展示尚未完整串联（⚠️）。

**US-PHOTO-02｜排序与设主图** ✅
- 验收：
  - `PUT /photos/{id}` 设主图/改顺序；`POST /photos/reorder` 批量重排，首张自动设为主图（`display_order=0, is_primary=true`）。

**US-PHOTO-03｜查看与删除** ✅
- 验收：
  - `GET /photos/me` 按序返回（排除已驳回）；`GET /photos/{id}` 单张元数据；`GET /photos/file/{filename}` 下载（无需鉴权）。
  - `DELETE /photos/{id}` 删除记录并清理磁盘文件。

**US-PHOTO-04｜照片审核** ⚠️
- 现状：`status`（pending/approved/rejected）与 `rejection_reason` 字段就绪，缺自动/人工审核落地流程与前端展示。

### 3.5 智能匹配与推荐 ✅

**US-MATCH-01｜规则匹配推荐** ✅
- 验收：`GET /matches/suggestions?limit=&strategy=rule` 基于 SQL 硬过滤（性别/年龄/身高/城市/居留）返回候选。

**US-MATCH-02｜AI 向量语义推荐** ✅（核心差异化）
- 作为用户，我希望获得基于价值观/职业/人生规划语义相似的推荐，而非仅标签匹配。
- 验收：
  - Given 已生成本人向量，When 调 `POST /match/recommend`，Then 先校验**月度推荐配额**（`user_recommendation_quota`，默认 2）与**全局 AI 预算**（`global_ai_budget`，默认 500 USD/月）。
  - SQL 硬过滤得候选 → 计算余弦相似度（`min_similarity≥0.7`，Top5）→ GPT-4o-mini 为每位候选生成**个性化推荐理由**。
  - 成功后配额 +1、预算累加；超限返回 403。
  - 亦支持 `GET /matches/suggestions?strategy=ai`。

**US-MATCH-03｜谁喜欢我** ✅（权限受控）
- 验收：`GET /matches/who-liked-me` 返回喜欢我但未互相的人；免费用户前端为 VIP 引导卡，会员/增值（¥9 单次）解锁。

### 3.6 匹配互动 ✅

**US-INT-01｜喜欢 / 跳过 / 超级喜欢** ✅
- 验收：
  - `POST /matches/action`（action_type=like/pass/super_like）写入 `match_actions`，唯一约束 `(actor,target)` 保证每对仅一条、新覆盖旧。
  - 超级喜欢为增值/VIP 权益（¥5 单次）。

**US-INT-02｜互相喜欢自动配对** ✅
- 验收：
  - Given 双方均 like，When 后者提交动作，Then 返回 `is_mutual_match=true`，在 `match_pairs` 建立配对（唯一 `(user1,user2)`，`status=active`）。
  - 前端提示"恭喜互相喜欢"，对象出现在匹配页/消息页。

**US-INT-03｜我的匹配列表** ✅
- 验收：`GET /matches/my-matches` 返回 active 配对，含匹配分与匹配理由。

### 3.7 AI 匹配分析报告 ✅

**US-INSIGHT-01｜生成兼容性分析与破冰语** ✅
- 作为用户，我希望针对某个对象获得 AI 兼容性分析和开场白建议。
- 验收：
  - `POST /coach/match-insights` 基于双方向量 + GPT-4o-mini 生成：`explanation`、`match_score_breakdown{values, lifestyle, personality, goals}`（各 0–1）、`suggested_openers`（2–3 条 50–80 字）、`safety_tips`（4 条）。
  - **缓存** `match_insight_cache` 有效 30 天，每人≤20 条（超出淘汰最旧）；限流 30 次/分钟。

**US-INSIGHT-02｜分层权益** ✅
- 验收：免费用户展示匹配分 + 匹配理由 + 前 2 个兼容维度；VIP 展示完整 4 维 + 亮点 + 注意事项。

### 3.8 实时聊天 ✅

**US-CHAT-01｜会话列表与历史** ✅
- 验收：
  - `GET /chats/my-conversations` 返回 active 会话（含最后一条预览、未读数、New Match 标记）。
  - `GET /chats/{id}/messages?skip=&limit=` 返回历史并**自动标已读**（`is_read`）。

**US-CHAT-02｜发送消息（含审核与限流）** ✅
- 验收：
  - `POST /chats/{id}/messages` 单条 ≤1000 字，经内容审核，限流 10 秒 ≤20 条，写入 `chat_messages`。
  - 命中 BLOCKED/HIGH 风险内容被拦截。

**US-CHAT-03｜WebSocket 实时通道** ✅
- 验收：`WS /ws/chat/{id}?token=JWT` 支持 message/ping 上行，new_message/pong/error 下行，实时推送新消息。

**US-CHAT-04｜已读状态** ⚠️
- 现状：后端有 `is_read`；作为 VIP 展示权益的前端呈现待完善。

### 3.9 AI 红娘咨询 ✅

**US-COACH-01｜日常对话咨询** ✅
- 作为用户，我希望随时向"小缘"咨询匹配分析/约会/资料建议。
- 验收：
  - 全局悬浮气泡展开咨询窗；`GET /ai-chat/history?conversation_type=consultation` 载入历史，`POST /ai-chat/send-message`（type=consultation）对话。
  - system prompt 按资料 + 记忆摘要 + 用户风格（活泼/温柔/直接）个性化，含边界约束（不提供医疗/法律建议）。
  - 消耗 token 记入 `user_token_usage`（默认月限 10000）。

**US-COACH-02｜滚动长期记忆** ✅
- 验收：
  - 对话后触发 `memory_service` 将最近 10 条 + 旧摘要经 GPT-4o-mini 压缩为 ≤500 字摘要写入 `user_ai_memory`（每人一条），保持跨会话连续性、上下文有界。

**US-COACH-03｜分层记忆（VIP）** ✅
- 验收：`GET /ai-chat/memory-summary` 返回 short/mid/long_term 分层记忆；非 VIP 返回 403。

**US-COACH-04｜额度查询** ✅
- 验收：`GET /ai-chat/token-usage`、`GET /ai-chat/recommendation-quota` 返回本月用量与上限。

### 3.10 VIP 主动关怀 ✅

**US-CARE-01｜定时 + 事件触发关怀** ✅（差异化）
- 作为 VIP，我希望小缘在合适时机主动发来关心消息。
- 验收：
  - 调度：每周二/五 20:00 UTC 遍历 VIP。
  - 触发条件：24h 内新匹配 / 活跃度下降（3–7 天沉默）；兜底：≥3 天不活跃且周二/五 18:00–22:00。
  - **防打扰**：若 1 小时内在活跃聊天则不发送。
  - 内容：GPT-4o-mini（temp=0.8）生成 ≤50 字、≤1 emoji、朋友口吻消息，存为 `ai_conversations`（type=care）。

### 3.11 安全（拉黑 / 举报 / 内容审核） ✅

**US-SAFE-01｜拉黑管理** ✅
- 验收：`POST /safety/block`、`DELETE /safety/block/{id}`、`GET /safety/blocked` 管理 `user_blocks`（唯一 blocker+blocked）；会话内亦可 `POST /chats/{id}/block · /unblock`。

**US-SAFE-02｜举报** ✅
- 验收：`POST /safety/report` 或 `POST /chats/{id}/report` 提交举报（category=harassment/scam/fake_profile/spam/other，可关联消息），写入 `user_reports`（status=open）。

**US-SAFE-03｜内容审核** ✅
- 验收：`detect_content_risk` 对聊天/资料文本做关键词（~150 词）+ 正则检测，分级 BLOCKED/HIGH/MEDIUM/LOW/SAFE；`should_block_content`=(BLOCKED 或 HIGH) 时拦截。
- 说明：当前为关键词/正则方案，后续升级 AI 审核。

**US-SAFE-04｜限流与事件日志** ✅
- 验收：`check_rate_limit` 滑动窗口计数超限抛 429；`log_event` 写 `event_logs` 供风控审计；`GET /events/my` 查我的行为事件。

### 3.12 支付与订阅 ⚠️

**US-PAY-01｜商品目录** ✅
- 验收：`GET /payment/products`（无需鉴权）返回 basic_monthly/yearly、premium_monthly/yearly、super_like、boost、who_liked_me。

**US-PAY-02｜下单与支付** ⚠️
- 验收：
  - `POST /payment/create-order` 生成 `orders`（order_no 唯一，payment_status=pending）并返回 payment_url。
  - `POST /payment/callback`（无需鉴权）更新订单支付状态并激活/续订 `subscriptions`。
- 现状：下单/回调/订阅逻辑框架完整，但**未接真实支付网关**（支付宝/微信/信用卡）与验签（⚠️）。

**US-PAY-03｜订单与订阅查询** ✅（逻辑）
- 验收：`GET /payment/orders/me`、`GET /payment/orders/{order_no}` 查订单；`GET /payment/subscription/status` 返回是否 premium 与剩余天数。

**US-PAY-04｜自动续费** 🔴
- 现状：`auto_renew`、`next_billing_date` 字段就绪，自动扣费未实现（依赖网关对接）。

**US-PAY-05｜会员权益前端落地** ⚠️
- 现状：会员中心、升级引导、额度展示等前端呈现待完整落地；前端 `isVIP` 为演示开关。

### 3.13 通知 🔴

**US-NOTIF-01｜通知列表与已读** 🔴
- 目标：新匹配/新消息/关怀/系统通知的站内 + Web Push 触达。
- 现状：`GET/POST/DELETE /notifications/*` 为**桩实现**（返回空/0），无存储与推送；前端无通知中心/未读提醒。
- 验收（目标态）：产生业务事件时写通知记录；`GET /notifications` 返回列表与未读数；标记已读/删除生效；支持 Web Push 推送。

### 3.14 管理后台 ✅

**US-ADMIN-01｜举报处理** ✅
- 验收：`GET /admin/reports`、`GET /admin/reports/{id}`、`PATCH /admin/reports/{id}/status`（open/reviewing/closed）管理举报；`POST /admin/reports/{id}/link-events` 关联风险事件。仅管理员可访问。

**US-ADMIN-02｜风险事件与统计** ✅
- 验收：`GET /admin/events`、`GET /admin/events/{id}` 查事件；`GET /admin/stats` 返回统计看板数据。

### 3.15 数据分析 ✅

**US-ANALYTICS-01｜用户快照统计** ✅
- 验收：`GET /analytics/me/snapshot` 返回获得喜欢/匹配成功/资料完整度等个人统计。

**US-ANALYTICS-02｜匹配上下文** ✅
- 验收：`GET /analytics/me/match-context` 为 LLM 提供匹配上下文数据（服务于推荐理由/分析生成）。

---

## 4. 需求状态汇总

| 模块 | 状态 | 关键缺口 |
|---|---|---|
| 账号认证 | ✅ | 第三方登录未做；前端 refresh 未启用 |
| AI 引导注册 | ✅ | 前端审核为 10 秒自动过审（演示态） |
| 个人资料与偏好 | ✅ 后端 / ⚠️ 前端 | 前端编辑资料未对接 `PUT /profile/me` |
| 照片 | ✅ 后端 / ⚠️ 前端 | 前端上传/管理未串联；审核流程未落地 |
| 智能匹配与推荐 | ✅ | 生产建议迁 pgvector |
| 匹配互动 | ✅ | — |
| AI 匹配分析报告 | ✅ | — |
| 实时聊天 | ✅ | 已读状态前端呈现待完善 |
| AI 红娘咨询 | ✅ | — |
| VIP 主动关怀 | ✅ | 多实例调度需分布式锁 |
| 安全 | ✅ | 审核仅关键词，建议升级 AI |
| 支付与订阅 | ⚠️ | 未接真实网关/验签；自动续费未实现 |
| 通知 | 🔴 | 桩实现，需存储 + 站内/Web Push |
| 管理后台 | ✅ | — |
| 数据分析 | ✅ | 增长/收入看板待完善 |

---

## 5. 非功能需求摘要

### 5.1 性能
- AI 推荐/分析走缓存（`match_insight_cache` 30 天）与小模型（gpt-4o-mini + embedding-3-small）控制延迟与成本。
- 向量检索当前 O(n) 线性扫描（SQLite 适用）；规模化迁 PostgreSQL + pgvector + HNSW。
- 聊天限流 10 秒 ≤20 条；`coach/match-insights` 30 次/分。

### 5.2 安全
- 密码 PBKDF2-SHA256；JWT HS256（access 30m / refresh 7d）。
- 内容审核（关键词/正则）+ 拉黑/举报 + 滑动窗口限流 + 事件审计日志。
- 上线前：更换默认 JWT 密钥、轮换 OpenAI Key（走环境变量）。

### 5.3 合规
- 目标市场涉及 UAE 与跨境数据：需 HTTPS、传输/存储加密、数据导出与账户注销、隐私政策与合规审查。

### 5.4 可用性
- 移动优先（max-w 容器居中）、珊瑚橘主色；错误态兜底（部分接口失败回落 mock，商业化前需去除演示态）。
- AI 服务具备容错：模型错误回退 fallback_model、连接错误指数退避、配额错误快速失败。

### 5.5 成本可控
- token 配额（`user_token_usage` 默认月 10000）+ 推荐配额（默认月 2）+ 全局预算（默认 500 USD/月）三重约束；预计 1000 普通 + 100 VIP 月度 AI 成本约 $212–257。

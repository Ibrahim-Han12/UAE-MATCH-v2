# HLD · 现状架构评估（Current State Assessment）

> UAE Match ｜ 评估基线：v1.0 代码 ｜ 对照标准：PRD v1.1 / BRD v2.1 / CLAUDE.md ｜ 日期：2026-08-10
> 本文只做现状盘点与差距分析，不含 M2 设计方案（见 [hld-m2-design.md](hld-m2-design.md)），不含未决产品问题（见 [open-questions.md](open-questions.md)）。

---

## 0. 一句话结论

v1.0 是一个"**通用滑动式相亲 App**"的完整骨架；而 PRD v1.1 要的是"**AI 红娘 + 稀缺推荐信 + 三道信任闸**"的严肃婚恋服务。两者**底层基础设施可大量复用**（账户/聊天/照片/风控/事件/向量/订阅表结构），但**产品核心机制（匹配交互、记忆、变现、信任闸、深访）需改造或废弃重建**。M2 不是"加功能"，而是"换内核"。

---

## 1. 现有技术栈盘点

| 层 | 选型 | 评价（对照 v2.1 方向） |
|---|---|---|
| 后端框架 | FastAPI + Uvicorn | ✅ 保留 |
| ORM / DB | SQLAlchemy 2.0 + **SQLite** | ✅ 框架保留；⚠️ SQLite 仅开发级，生产迁 PostgreSQL |
| 认证 | python-jose(JWT HS256) + passlib(**PBKDF2-SHA256**) | ✅ 密码哈希保留；⚠️ 仅密码登录，**无手机 OTP**（违背 BR-001） |
| AI | openai SDK；`gpt-4o-mini` / `text-embedding-3-small`(1536维) | ⚠️ 有 config 层但未形成"任务→档位"抽象层（CLAUDE.md §4） |
| 向量存储 | SQLite Text 列存 JSON，**O(n) 线性扫描** | 🔶 v1 量级（<2000）可接受；非瓶颈，暂不动 |
| 记忆 | `memory_service` 滚动摘要（≤800 token） | 🔴 **必须废弃重建**（BR-202） |
| 定时任务 | `schedule` 库 + 进程内守护线程 | ⚠️ 多实例会重复执行；推荐信流水线需重新设计调度 |
| 实时通信 | FastAPI WebSocket | ✅ 保留（配对聊天） |
| 前端 | React18 + TS + Vite + Tailwind + shadcn/ui | ✅ 技术栈保留；🔴 交互模型（滑动）需重建 |
| 前端导航 | 状态机切换（无 react-router） | 🔶 可保留；信息架构需按 PRD 2.1 五入口重排 |
| 前端鉴权 | JWT 存 localStorage | ✅ 保留 |

---

## 2. 模块清单

### 2.1 后端 API（17 域 · ~58 接口）
| 域 | 现有能力 | 对 v2.1 的定位 |
|---|---|---|
| auth | 注册/登录(密码)/refresh/me | 🔧 改造：加手机 OTP、单设备踢出、注销四道闸 |
| profile / preferences | 资料与偏好增改查 | 🔧 改造：扩展为深访 24 项 Schema + 弹性系数 |
| photos | 上传/排序/主图/删除/审核状态 | 🔧 改造：接入活体×EID 交叉比对、水印 |
| matches / match_recommendation | 规则匹配 + AI 向量推荐 + like/pass/superlike | 🔴 废弃重建：改推荐信制，下线滑动 |
| chat / chat_ws | REST + WebSocket 聊天、已读 | ✅ 复用；➕ 加破冰卡片、10 轮埋点 |
| ai_chat / coach | 对话、历史、引导注册、匹配分析、配额 | 🔧 改造：接三层记忆 + 深访三层架构 |
| payment | 订单/回调/订阅/商品目录 | 🔧 改造：CNY 道具制 → Stripe AED 订阅；冻结道具 |
| notifications | 4 个接口 | 🔴 **桩实现**（全部返回空），需真实实现 |
| safety | 拉黑/举报/内容审核(关键词) | ✅ 复用；➕ 加拉黑排除表进匹配引擎、防诈话术库 |
| admin | 举报处置/事件/统计 | ✅ 复用；➕ 加照片审核队列、推荐质检队列、成本看板 |
| analytics / events | 快照统计 / 事件日志 | ✅ 复用为埋点底座（BR-209/北极星漏斗） |
| health | 健康检查 | ✅ 保留 |

### 2.2 前端页面（9 个应用级组件）
| 页面 | 定位 |
|---|---|
| LandingPage / LoginPage | 🔧 改造（登录改 OTP、去掉 Google 按钮） |
| AIOnboardingChat / OnboardingFlow | 🔴 废弃重建（深访三层架构） |
| DailyRecommendationsPage / DiscoverPage | 🔴 废弃重建（推荐信制，下线滑动/发现） |
| MatchesPage / MessagesPage | ✅ 复用改造（配对与聊天保留） |
| ProfilePage | 🔧 改造（资料/画像报告/认证中心/会员中心） |
| AICupidChatBubble | ✅ 复用（小缘对话入口） |

---

## 3. 数据模型盘点（20 表）

| 表 | 现状用途 | 定位 | 说明 |
|---|---|---|---|
| users | 账户 | ✅ 复用+扩展 | 加 `status`(状态机 S0–S7)、手机验证、锁定字段 |
| user_profiles | 资料 | 🔧 改造 | 扩展深访 A/B 类字段、置信度、EID 带入锁定 |
| match_preferences | 择偶偏好 | 🔧 改造 | 加弹性系数、免谈项、C 类字段 |
| user_photos | 照片 | ✅ 复用+扩展 | 加活体比对结论、水印元数据 |
| user_embeddings | 向量 | ✅ 复用 | 向量记忆双轨的"画像向量"一支；v1 量级保留 JSON 存 |
| match_actions | like/pass/superlike | 🔶 语义重建 | 改为推荐信三动作（愿意认识/想再了解/不合适）；super_like 冻结 |
| match_pairs | 配对 | ✅ 复用 | 保留；配对中暂停新推荐（PRD 5.4-⑫） |
| chat_messages | 聊天 | ✅ 复用 | 保留 |
| user_blocks | 拉黑 | ✅ 复用+扩展 | 拉黑进匹配引擎永久排除表（PRD 4.6） |
| user_reports | 举报 | ✅ 复用 | 保留 |
| event_logs | 事件 | ✅ 复用为埋点底座 | 扩展 PRD 第 15 章埋点事件 |
| orders | 订单 | 🔧 改造 | 货币 CNY→AED；product 目录重构 |
| subscriptions | 订阅 | 🔧 改造 | plan_type 改 标准/高级/尊享/候补 |
| user_token_usage | token 计量 | ✅ 复用+扩展 | 加 scene / cache_hit 维度（BR-209） |
| global_ai_budget | 全局预算 | ✅ 复用 | 80% 告警/100% 熔断 |
| ai_conversations | AI 对话历史 | ✅ 复用 | 保留 |
| user_ai_memory | **滚动摘要** | 🔴 **废弃** | 被三层记忆取代（BR-202） |
| ai_memory_summary | short/mid/long 摘要(VIP) | 🔴 **废弃/重构** | 时间维摘要 ≠ 事实/事件/情感三层，重建 |
| user_recommendation_quota | 推荐配额 | 🔶 复用改造 | 配额语义随推荐信制调整 |
| match_insight_cache | 匹配分析缓存 | ✅ 复用 | 推荐语/兼容性缓存（"用户对"维度） |

**汇总**：20 表中 ✅ 直接复用/小扩展 11 张、🔧 改造 6 张、🔴 废弃或重构 3 张（`user_ai_memory` / `ai_memory_summary` / `match_actions` 语义）。

---

## 4. 对照 PRD v1.1 的差距分析（按能力域）

> 图例：♻️ 可复用 ｜ 🔧 要改造 ｜ 🔴 废弃重建

### 4.1 账户与访问（PRD 3 / BR-001~005）
- 🔴 **登录方式**：现为邮箱/手机+密码；PRD 要求 **UAE 手机 OTP 为主（验证即登录）**、邮箱为辅、**禁第三方登录**（`LoginPage.tsx:364` 有 Google 按钮，违背 BR-001）。
- 🔧 **会话策略**：现无单设备互踢；PRD 要求单设备在线 + 踢旧会话 + 通知（BR-002）。
- 🔴 **注销**：现无注销流程；PRD 要求**四道防线 + 级联删除（含向量库）**（PRD 3.4 / BR-004）。
- ♻️ users 表、JWT、密码哈希可复用。

### 4.2 信任与身份（PRD 4 / BR-101~110）—— 现状几乎为空白
- 🔴 **EID 核验**：现完全没有；PRD 要求持牌 KYC SDK、平台不存证件图像、年龄/性别锁定（BR-107，M2 硬前置）。
- 🔴 **照片真实性**：现有 `is_verified` 字段但无活体×EID 交叉比对逻辑（BR-101）。
- 🔴 **婚姻状况申报**（BR-109）、**熟人回避**（BR-105）、**资料水印**（BR-106）、**拉黑三层缓冲**（PRD 4.6）：均未实现。
- ♻️ user_photos / user_reports / user_blocks 表结构可复用。

### 4.3 AI 红娘（PRD 5 / BR-201~209）
- 🔴 **记忆体系**：现为滚动摘要（单会话连续性）；PRD 要求**事实/事件/情感三层 + 结构化画像库 + 向量记忆库双轨**（BR-202，最高优先技术项）。
- 🔴 **深访架构**：现为 `AIOnboardingChat` 约 12 个问题**硬编码进 prompt**；PRD 要求**三层分离（Schema YAML / 问法库 / 系统 prompt）**、24 必采字段、疲劳检测、去审问感（PRD 5.1–5.3.5）。
- 🔴 **深访双产物**：现无内部画像/用户报告分离；PRD 要求**先抽取落库再生成报告**、五板块、报告即漏斗（BR-201）。
- 🔴 **L3 主动性引擎**：现有 `vip_care_service`（周二/五定时）为雏形；PRD 要求**全用户分级事件引擎 + 日历事件 + 伦理护栏同步**（BR-204, BR-206，v1.0 范围）。
- 🔧 **模型路由与计量**：现有 config + fallback，但未形成抽象层；PRD/CLAUDE.md §4 要求"任务→档位"路由 + Prompt Caching + BR-209 计量。
- ♻️ ai_conversations / user_token_usage / global_ai_budget / user_embeddings 可复用。

### 4.4 匹配与推荐（PRD 6 / BR-301~307）
- 🔴 **交互模型**：现为滑动/每日推荐/发现页 + like/pass；PRD 要求**每周 1–3 封推荐信、周五 20:00 送达、先理由后照片、三动作、72h 时限**（BR-301, BR-302, BR-307）。
- 🔴 **推荐流水线**：现为实时查询；PRD 要求 **T-3 计算 → T-2 生成 → T-1 质检 → T0 送达**的周流水线（PRD 6.1）。
- 🔧 **匹配算法**：现为向量余弦 + 规则；PRD 要求本地化硬约束 + 心理维度规则 + 语义向量三段式（BR-306，算法细节待专门文档）。
- ♻️ user_embeddings / match_pairs / match_insight_cache 可复用。

### 4.5 沟通与关系（PRD 7 / BR-401~406）
- ♻️ **配对聊天**：REST + WebSocket + 已读，基本满足 BR-401，直接复用。
- 🔧 破冰开场白（BR-402）、10 轮埋点（BR-403）：需补。
- 🔴 微信交换（BR-406）、见面引导（BR-404）：未实现（M3）。

### 4.6 商业化（PRD 8 / BR-501~504）
- 🔴 **商品目录**：现为人民币道具制（`payment.py:30` 起：¥29/¥59 + super_like/boost/who_liked_me）；PRD 要求 **Stripe AED 订阅四层 + 冻结道具（下线入口、接口返 410）**（BR-501, BR-503）。
- 🔧 订阅生命周期（升降级/宽限期/退款/席位管控）：需按 PRD 8.2 重建。
- ♻️ orders / subscriptions 表结构可复用改造。

---

## 5. CLAUDE.md 第 6 节「已知问题」逐项确认

| 第 6 节条目 | 代码实证 | 确认 |
|---|---|---|
| 支付：商品目录人民币道具制 | `payment.py:30-64`（¥29/59/299/599 + super_like/boost/who_liked_me） | ✅ 属实 |
| 通知系统是桩实现（返回空） | `notifications.py:22` 返回 `{"unread_count":0}`，4 处 `TODO` | ✅ 属实 |
| 前端演示态：注册 10 秒自动过审 | `App.tsx:94` `setTimeout(()=>setAppState('main'),10000)`（注释"为了演示"） | ✅ 属实 |
| 前端演示态：VIP 前端开关 | `MainApp.tsx:21` `useState(false) // VIP状态，可以通过UI切换` | ✅ 属实 |
| 前端演示态：mock 兜底 | `DailyRecommendationsPage.tsx:13,143` `DAILY_RECOMMENDATIONS` catch 兜底 | ✅ 属实 |
| 记忆是滚动摘要 | `memory_service.py` + `user_ai_memory` 表 | ✅ 属实 |
| 滑动式匹配交互 | `DiscoverPage.tsx` + `match_actions`(like/pass) | ✅ 属实 |

### 5.1 第 6 节之外、评估中新发现的遗漏
1. 🔴 **登录无手机 OTP**（`LoginPage.tsx` 无 OTP/验证码逻辑）——违背 BR-001，第 6 节未列。
2. 🔴 **Google 第三方登录按钮**（`LoginPage.tsx:364`）——违背 BR-001"不做第三方登录"。
3. 🔴 **完全没有 EID 核验 / 信任闸**——第 6 节未强调，但这是 M2 最大新建工作量。
4. 🔴 **无注销流程**——BR-004 要求级联删除，现无。
5. 🟠 **`ai_memory_summary`（short/mid/long）** 是另一套时间维摘要，与滚动摘要并存，同样不符合三层记忆，需一并处理。
6. 🟠 **支付回调无验签**（现 `payment/callback` 无第三方签名校验）——迁 Stripe 时须补 Webhook 验签。
7. 🟠 **JWT 密钥为默认值**、**OpenAI Key 曾明文于 `.env`**——上线前必处理（见 HLD 现有文档）。
8. 🟠 **文档债**：早前自动生成的 `docs/01/BRD`、`PRD`、`docs/02/HLD/LLD/UIUX` 描述的是 **v1.0 代码**（滑动/CNY），与权威 BRD v2.1/PRD v1.1 **方向冲突**，需标注"代码现状文档"或重写对齐（见 open-questions）。

---

## 6. 演示态代码完整清单（M2 必须拆除/替换）

| # | 演示态 | 位置（文件:行） | 处置 |
|---|---|---|---|
| 1 | 注册后 10 秒自动过审 | `App.tsx:93-96` | 拆除，替换为真实"深访→核验→审核 SLA"状态流转 |
| 2 | VIP 前端开关（`isVIP` useState） | `MainApp.tsx:21`（传入各页 `isVIP={isVIP}`） | 拆除，改读真实订阅状态（`/payment/subscription/status`） |
| 3 | 推荐 mock 兜底数据 | `DailyRecommendationsPage.tsx:13`（`DAILY_RECOMMENDATIONS`）、`:143`（catch 内 `setRecommendations(DAILY_RECOMMENDATIONS)`） | 随推荐信页重建一并移除 |
| 4 | Google 登录按钮 | `LoginPage.tsx:364`「使用 Google 账号登录」 | 移除（BR-001） |
| 5 | 通知系统桩 | `notifications.py:22/37/58/71/85`（5 处 `TODO`+空返回） | 实现真实通知（站内 + Web Push） |
| 6 | 滑动/发现页 | `DiscoverPage.tsx`（未接入主流程但存在） | 下线/删除（BR-503 精神：滑动交互废弃） |
| 7 | 前端编辑资料未打通 | `ProfilePage.tsx`（编辑入口占位） | 随资料/画像模块重建 |
| 8 | 人民币道具商品 | `payment.py:30-64` | 冻结道具、重构为 AED 订阅 |

> 说明：#3/#6/#7 会在"推荐信制 + 资料模块"重建时自然消解；#1/#2/#4/#5/#8 是可独立拆除的明确演示态/错向实现。

---

## 7. M2 改造工作量分级（现状 → 目标）

| 等级 | 含义 | 涉及模块 |
|---|---|---|
| 🟢 复用（改动小） | 直接用或小扩展 | 聊天/WebSocket、事件日志、照片存储结构、admin 框架、analytics |
| 🟡 改造（中） | 表/接口在，逻辑重写 | 账户(加 OTP/单设备/注销)、支付(→Stripe AED)、配额计量(BR-209)、资料/偏好(深访 Schema) |
| 🔴 重建（大） | 新建核心机制 | **三层记忆(BR-202)**、**深访三层架构**、**推荐信流水线**、**EID 信任闸 + 状态机**、L3 主动性引擎 + 护栏 |

**建议动手顺序**（与 BRD 13 章 M2 包一致，且尊重"记忆是地基"）：
① 模型抽象层 + 计量（BR-209，其他 AI 工作的前提）→ ② 三层记忆（BR-202，地基）→ ③ 账户/状态机/EID 闸（BR-001, BR-107）→ ④ 深访三层架构（BR-201）→ ⑤ 推荐信流水线（BR-301）→ ⑥ Stripe AED 订阅（BR-501, BR-503）。

> 详细设计见 [hld-m2-design.md](hld-m2-design.md)；工作量/排期数字属项目管理范畴，不在本文断言。

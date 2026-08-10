# 03 · UI-UX 界面与交互文档

> UAE Match ｜ 版本 v1.0.0 ｜ 更新 2026-07-04
> 前端：`uae-match-web-fronted-version2/`（React 18 + Vite + Tailwind + shadcn/ui）

---

## 1. 导航结构

前端**不使用 react-router**，而是用 `App.tsx` 中的**状态机**切换主界面：

```
appState: landing → login → onboarding → pending-review → main
```

进入主应用 `MainApp` 后，采用**底部 Tab 导航**（4 个）切换子页面：

```
┌───────────────────────── MainApp ─────────────────────────┐
│  顶部：标题 + 今日喜欢计数(如 1/3)                            │
│  内容区：按当前 Tab 渲染                                     │
│  悬浮：AI 红娘"小缘"聊天气泡（任意页面可用，可拖拽）           │
│  底部 Tab：  推荐 │ 匹配 │ 消息 │ 我的                       │
└────────────────────────────────────────────────────────────┘
```

设计基调：珊瑚橘主色 `#E07A5F`，玫瑰→橙渐变，柔和暖色背景；移动优先（max-w 容器居中）。

---

## 2. 认证与会话

- **令牌存储**：`localStorage` 存 `access_token`（`refresh_token` 预留未启用）。
- **请求鉴权**：所有 API 请求头带 `Authorization: Bearer {token}`。
- **401 处理**：清除令牌并登出回落地页。
- **登录后判定资料**：调 `GET /profile/me`——404 视为未建资料 → 进引导；成功且有 name → 进主应用。
- **前后端字段转换**：性别 `男/女 ↔ male/female`；年龄 `age ↔ birth_year`（换算）。

---

## 3. 页面清单与职责

| 页面组件 | 阶段/Tab | 职责 |
|---|---|---|
| `LandingPage` | landing | 落地营销页，介绍价值主张，CTA 进入登录 |
| `LoginPage` | login | 登录/注册切换（邮箱/手机 + 密码） |
| `AIOnboardingChat` | onboarding | "小缘"对话式收集资料（12+ 问） |
| `MainApp` | main（容器） | 底部 Tab 容器 + 顶栏 + 悬浮 AI 气泡 |
| `DailyRecommendationsPage` | 推荐 | 每日 AI 精选推荐 + 详情 + AI 分析报告 |
| `MatchesPage` | 匹配 | 互相喜欢的匹配列表 |
| `MessagesPage` | 消息 | 会话列表 + 聊天界面 |
| `ProfilePage` | 我的 | 个人资料、统计、设置、VIP 升级、登出 |
| `AICupidChatBubble` | 全局 | 悬浮 AI 红娘咨询窗 |
| `DiscoverPage` | （未接入主流程） | 卡片式探索，代码存在但未在主流程使用 |

---

## 4. 各页面交互与接口

### 4.1 LandingPage（落地页）
- **展示**：品牌价值（真实认证、AI 匹配、严肃意图）、4 项特性、3 步流程、与传统软件的差异。
- **动作**：点"开始认真相亲" → 进入登录。
- **接口**：无。

### 4.2 LoginPage（登录/注册）
- **展示**：登录/注册模式切换、邮箱/手机、密码及确认、记住我、密码可见切换、Google 登录（占位）。
- **动作**：
  - 登录 → `POST /auth/login`
  - 注册 → `POST /auth/register` → 自动登录
- **接口**：`/auth/register`、`/auth/login`。

### 4.3 AIOnboardingChat（AI 引导注册）
- **展示**：流式对话界面、进度条、气泡消息、输入框；"小缘"逐条提问。
- **收集**：姓名、年龄、性别、UAE 城市、职业、在 UAE 时长、结婚时间线、长期规划、子女计划、期望年龄段、其他偏好。
- **动作**：自然语言回答 → AI 追问 → 完成后生成资料并进入待审核。
- **接口**：`/ai-chat/start-registration`、`/ai-chat/send-message`、`/ai-chat/history`、`/ai-chat/complete-registration`。

### 4.4 DailyRecommendationsPage（每日推荐）
- **列表态**：3–5 张推荐卡（头像+认证徽章、姓名/年龄/城市/职业、简介、匹配分、"查看 AI 分析报告"）。
- **详情态**：大图资料卡 + 兴趣标签 + 资料网格（职业/行业/学历/在 UAE 时长/结婚时间/长期规划）。
- **AI 分析报告**：
  - 免费：匹配分 + 匹配理由 + 前 2 个兼容维度
  - VIP：完整 4 维兼容度 + 亮点 + 注意事项
- **动作**：查看分析、"表达好感"(like)、"不太合适"(pass)；VIP 升级引导。
- **接口**：`GET /matches/suggestions`、`POST /matches/action`、`POST /coach/match-insights`。
- **兜底**：接口失败时回落到本地 mock 数据。

### 4.5 MatchesPage（匹配）
- **展示**：空态（无匹配）；匹配卡（头像、姓名/年龄/职业/城市、匹配分进度条、匹配理由、"开始聊天"）。
- **动作**：查看匹配对象、跳转到消息 Tab 聊天。
- **接口**：`GET /matches/my-matches`；"谁喜欢我"为 VIP 引导卡。

### 4.6 MessagesPage（消息）
- **会话列表态**：空态；会话卡（头像、姓名/职业、最后一条预览、New Match 标记、未读数）。
- **聊天态**：聊天头、匹配成功横幅、首聊提示、消息气泡（我方右侧珊瑚渐变/对方左侧白底）、时间戳、安全提示条、输入框。
- **动作**：进入会话、发消息（回车/按钮）、返回列表。
- **接口**：`GET /chats/my-conversations`、`GET /chats/{id}/messages`、`POST /chats/{id}/messages`（另有 WebSocket 实时通道）。

### 4.7 ProfilePage（我的）
- **展示**：用户卡（头像/姓名/年龄/简介、编辑资料、设置）、VIP 升级卡、统计三宫格（获得喜欢/匹配成功/资料完整度）、菜单（我的认证、谁喜欢我(VIP)、隐私/通知设置、安全中心、帮助、关于）、登出、版本号。
- **动作**：编辑资料（未完全实现）、登出。
- **接口**：当前多为占位 UI，编辑资料应对接 `PUT /profile/me`。

### 4.8 AICupidChatBubble（悬浮 AI 红娘）
- **展示**：悬浮气泡（可拖拽）→ 展开 380×550 聊天窗（标题"AI 红娘小缘 · 在线"、历史消息、输入框）。
- **动作**：拖动、展开、提问（如"我和 XX 合适吗"）、获取建议。
- **接口**：`GET /ai-chat/history?conversation_type=consultation`、`POST /ai-chat/send-message`（type=consultation）。

---

## 5. 核心用户旅程

**注册引导**
```
落地页 →(开始) 登录页(注册) → 自动登录 →(无资料) AI 引导对话
   → 完成注册 → 待审核(演示:10秒自动过审) → 主应用/推荐页
```

**每日推荐 → 匹配**
```
推荐页加载 suggestions → 点卡片看 AI 分析 → 表达好感(like)
   → 若互相喜欢 → 提示"恭喜互相喜欢" → 出现在匹配页/消息页
```

**聊天**
```
匹配页 →(开始聊天) 消息 Tab → 选会话 → 发消息(REST/WS) → 消息入线程
```

**AI 咨询（任意页面）**
```
点悬浮气泡 → 载入咨询历史 → 提问 → 小缘回复(匹配分析/约会建议/资料建议)
```

---

## 6. 状态管理

- **方案**：纯 React 本地 state（无 Redux/Context/Zustand）。
- **App 级**：`appState`、`currentUser`、`loading`。
- **MainApp 级**：`activeTab`、`matches`、`conversations`、`dailyLikesUsed`、`isVIP`。
- **页面级**：各页自管（如推荐页的 `recommendations/selectedIndex/liked/passed`）。
- **数据流**：组件挂载/依赖变化时 `useEffect` 调用 `lib/api.ts` → 更新本地 state → 重渲染；除 JWT 外无持久化。

---

## 7. 现状与缺口（前端）

- 🧪 **演示态**：待审核 10 秒自动通过；`isVIP` 是前端开关（非真实订阅态）；多处接口失败回落 mock 数据。
- ✏️ **编辑资料未打通**：ProfilePage 编辑入口存在，未完整对接 `PUT /profile/me`。
- 🧭 **DiscoverPage 未接入**：组件已写但主流程未使用。
- 🔔 **通知 UI 缺失**：后端通知为桩，前端无通知中心/未读提醒。
- 📸 **照片前端流程弱**：后端照片接口完整，但前端上传/管理/展示尚未完整串联。
- 🌐 **无路由**：状态机导航导致无法通过 URL 直达/分享具体页面，SEO 与深链能力弱。
- 🌍 **仅中文**：面向 UAE 市场需补英/阿语。

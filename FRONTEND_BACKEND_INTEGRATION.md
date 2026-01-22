# 前后端对接方案

## 📋 概述

本文档详细说明如何将 `uae-match-web-fronted-version2`（React + Vite）与现有后端对接。

## 🔍 前后端参数差异分析

### 1. 性别字段
- **前端**: `"男"` / `"女"` (中文)
- **后端**: `"male"` / `"female"` (英文)
- **解决方案**: 在前端 API 层做转换

### 2. 年龄字段
- **前端**: `age` (数字或字符串，如 `"28"`)
- **后端**: `birth_year` (年份，如 `1996`)
- **解决方案**: 前端发送 `birth_year`，后端计算年龄返回

### 3. 城市字段
- **前端**: `city` (如 `"Dubai"`, `"Abu Dhabi"`)
- **后端**: `current_city` (相同格式)
- **解决方案**: 前端发送时使用 `current_city`

### 4. 婚恋时间线
- **前端**: `marriageTimeline` (如 `"1-2年内"`, `"6个月内"`)
- **后端**: `marriage_timeline` (可能格式不同)
- **解决方案**: 统一格式，后端接受前端格式

### 5. 长期规划
- **前端**: `longTermPlan` (如 `"stay_uae"`, `"back_china"`)
- **后端**: 可能在 `extended_info` 中
- **解决方案**: 后端支持在 `extended_info` 中存储

### 6. 宗教信仰
- **前端**: `religiousView` (如 `"not_religious"`, `"buddhist"`)
- **后端**: 可能在 `extended_info` 中
- **解决方案**: 后端支持在 `extended_info` 中存储

### 7. 孩子计划
- **前端**: `childrenPlan` (如 `"want_children"`, `"no_children"`)
- **后端**: 可能在 `extended_info` 中
- **解决方案**: 后端支持在 `extended_info` 中存储

### 8. 择偶条件
- **前端**: `preferredAgeMin`, `preferredAgeMax`, `preferredEducation`, `preferredCity`
- **后端**: `MatchPreference` 模型 (`min_age`, `max_age`, `preferred_gender`)
- **解决方案**: 前端发送时映射到后端字段

## 📝 需要实现的功能清单

### ✅ 已确认保留
- [x] LandingPage（首页）- 完全保留，不修改

### 🔧 需要对接的功能

1. **用户认证**
   - 登录 (`/api/v1/auth/login`)
   - 注册 (`/api/v1/auth/register`)

2. **AI 引导注册**
   - 开始注册对话 (`/api/v1/ai-chat/start-registration`)
   - 发送消息 (`/api/v1/ai-chat/send-message`)
   - 完成注册 (`/api/v1/ai-chat/complete-registration`)

3. **每日推荐**
   - 获取推荐 (`/api/v1/matches/suggestions`)
   - 表达好感 (`/api/v1/matches/action`)
   - 获取匹配分析 (`/api/v1/coach/match-insights`)

4. **匹配列表**
   - 我的匹配 (`/api/v1/matches/my-matches`)
   - 谁喜欢我 (`/api/v1/matches/who-liked-me`)

5. **消息功能**
   - 获取对话列表 (`/api/v1/chat/conversations`)
   - 发送消息 (`/api/v1/chat/send`)
   - WebSocket 实时消息

6. **个人资料**
   - 获取资料 (`/api/v1/profile/me`)
   - 更新资料 (`/api/v1/profile/me`)

7. **AI 聊天球**
   - 发送消息 (`/api/v1/ai-chat/send-message`)
   - 获取历史 (`/api/v1/ai-chat/history`)

## 🔄 参数映射表

### 注册/登录
| 前端字段 | 后端字段 | 转换规则 |
|---------|---------|---------|
| `email` | `email` | 直接映射 |
| `phone` | `phone` | 直接映射 |
| `password` | `password` | 直接映射 |

### 个人资料
| 前端字段 | 后端字段 | 转换规则 |
|---------|---------|---------|
| `name` | `display_name` | 直接映射 |
| `age` | `birth_year` | `birth_year = 当前年份 - age` |
| `gender` | `gender` | `"男" -> "male"`, `"女" -> "female"` |
| `city` | `current_city` | 直接映射 |
| `occupation` | `occupation` | 直接映射 |
| `industry` | `extended_info.industry` | 存储到扩展信息 |
| `residencyStatus` | `extended_info.residency_status` | 存储到扩展信息 |
| `yearsInUAE` | `extended_info.years_in_uae` | 存储到扩展信息 |
| `marriageTimeline` | `extended_info.marriage_timeline` | 存储到扩展信息 |
| `longTermPlan` | `extended_info.long_term_plan` | 存储到扩展信息 |
| `religiousView` | `extended_info.religious_view` | 存储到扩展信息 |
| `childrenPlan` | `extended_info.children_plan` | 存储到扩展信息 |
| `preferredAgeMin` | `min_age` (MatchPreference) | 映射到匹配偏好 |
| `preferredAgeMax` | `max_age` (MatchPreference) | 映射到匹配偏好 |
| `preferredEducation` | `extended_info.preferred_education` | 存储到扩展信息 |
| `preferredCity` | `extended_info.preferred_city` | 存储到扩展信息 |
| `dealbreakers` | `extended_info.dealbreakers` | 存储到扩展信息（数组）|

### 匹配推荐
| 前端字段 | 后端字段 | 转换规则 |
|---------|---------|---------|
| `matchScore` | `compatibility_score` | 直接映射 |
| `matchReason` | `reasons` (数组第一个) | 从 reasons 数组取第一个 |
| `aiAnalysis` | 从 `/coach/match-insights` 获取 | 调用分析接口 |

## 🚀 实施步骤

### 第一步：创建前端 API 服务层
创建 `src/lib/api.ts` 文件，包含：
- API 基础 URL 配置
- Token 管理
- 请求封装函数
- 参数转换函数

### 第二步：调整后端 API
1. 修改注册接口，支持前端字段格式
2. 修改个人资料接口，支持扩展信息
3. 确保所有接口返回格式与前端期望一致

### 第三步：实现各功能对接
1. 登录/注册
2. AI 引导注册
3. 每日推荐
4. 匹配列表
5. 消息功能
6. 个人资料
7. AI 聊天球

### 第四步：配置和测试
1. 配置 CORS
2. 配置环境变量
3. 端到端测试

## 📌 注意事项

1. **保留首页**: LandingPage 组件完全保留，不修改
2. **参数转换**: 所有参数转换在前端 API 层完成
3. **错误处理**: 统一的错误处理机制
4. **Token 管理**: 使用 localStorage 存储 token
5. **类型安全**: 使用 TypeScript 确保类型安全

## 🔐 安全考虑

1. Token 存储在 localStorage
2. 所有 API 请求携带 Authorization header
3. 敏感信息加密传输
4. CORS 配置只允许前端域名

---

**下一步**: 开始实施对接方案








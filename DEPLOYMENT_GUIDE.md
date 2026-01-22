# 前后端对接部署指南

## 📋 概述

本指南将帮助您将前端代码（已上传到 GitHub）与本地后端对接，确保应用正常运行。

## 🔍 当前配置检查

### 后端配置
- **后端地址**: `http://127.0.0.1:8000`
- **API 前缀**: `/api/v1`
- **CORS 允许的源**: `localhost:3000`, `localhost:3001`

### 前端配置
- **前端地址**: `http://localhost:3000` (Next.js 默认)
- **API 基础 URL**: `http://127.0.0.1:8000/api/v1` (在 `src/lib/api.ts` 中配置)

## ✅ 部署步骤

### 1. 克隆前端代码（如果还没有）

```bash
# 如果前端代码在 GitHub 上，克隆到本地
cd H:\uae-match
git clone <your-frontend-repo-url> uae-match-web
# 或者如果已经存在，确保代码是最新的
cd uae-match-web
git pull origin main
```

### 2. 安装前端依赖

```bash
cd H:\uae-match\uae-match-web
npm install
```

### 3. 配置前端环境变量

创建或更新 `.env.local` 文件：

```bash
# 前端环境变量配置
# H:\uae-match\uae-match-web\.env.local

# 后端 API 地址（开发环境）
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1

# 如果部署到生产环境，修改为：
# NEXT_PUBLIC_API_BASE_URL=https://your-backend-domain.com/api/v1
```

### 4. 更新后端 CORS 配置（如果需要）

如果前端部署在不同的域名或端口，需要更新后端的 CORS 配置：

**文件**: `H:\uae-match\backend\app\main.py`

```python
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    # 添加生产环境域名（如果需要）
    # "https://your-frontend-domain.com",
]
```

### 5. 启动后端服务

```bash
cd H:\uae-match\backend
# 激活虚拟环境（如果使用）
.venv\Scripts\activate  # Windows
# 或
source .venv/bin/activate  # Linux/Mac

# 启动后端
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 6. 启动前端服务

```bash
cd H:\uae-match\uae-match-web
npm run dev
```

前端将在 `http://localhost:3000` 启动。

## 🔧 配置检查清单

### 后端检查项

- [ ] 后端服务运行在 `http://127.0.0.1:8000`
- [ ] CORS 配置包含前端地址
- [ ] 数据库已初始化（`app.db` 存在）
- [ ] 环境变量已配置（`.env` 文件）
- [ ] OpenAI API Key 已配置（如果使用 AI 功能）

### 前端检查项

- [ ] `.env.local` 文件存在并配置了 `NEXT_PUBLIC_API_BASE_URL`
- [ ] 前端依赖已安装（`node_modules` 存在）
- [ ] 前端可以访问 `http://localhost:3000`

### API 连接测试

打开浏览器控制台，检查：

1. **网络请求**: 打开开发者工具 → Network，查看 API 请求是否成功
2. **CORS 错误**: 如果看到 CORS 错误，检查后端 CORS 配置
3. **401 错误**: 如果看到 401，检查登录状态和 token

## 🚨 常见问题排查

### 问题 1: CORS 错误

**错误信息**: `Access to fetch at 'http://127.0.0.1:8000/api/v1/...' from origin 'http://localhost:3000' has been blocked by CORS policy`

**解决方案**:
1. 检查后端 `main.py` 中的 CORS 配置
2. 确保前端地址在 `origins` 列表中
3. 重启后端服务

### 问题 2: 无法连接到后端

**错误信息**: `Failed to fetch` 或 `NetworkError`

**解决方案**:
1. 确认后端服务正在运行
2. 检查后端地址是否正确（`http://127.0.0.1:8000`）
3. 检查防火墙设置

### 问题 3: API 路径不匹配

**错误信息**: `404 Not Found`

**解决方案**:
1. 检查前端 `api.ts` 中的 `API_BASE_URL`
2. 检查后端路由前缀（应该是 `/api/v1`）
3. 确保 API 路径完整（例如：`/api/v1/auth/login`）

### 问题 4: 环境变量未生效

**解决方案**:
1. Next.js 环境变量必须以 `NEXT_PUBLIC_` 开头才能在客户端使用
2. 修改 `.env.local` 后需要重启前端服务
3. 检查 `.env.local` 文件位置（应该在项目根目录）

## 📦 生产环境部署

### 前端部署（Vercel/Netlify 等）

1. **设置环境变量**:
   ```
   NEXT_PUBLIC_API_BASE_URL=https://your-backend-domain.com/api/v1
   ```

2. **更新后端 CORS**:
   ```python
   origins = [
       "https://your-frontend-domain.com",
       "https://www.your-frontend-domain.com",
   ]
   ```

### 后端部署

1. **更新 CORS 配置**（包含生产前端域名）
2. **配置环境变量**（数据库、API Keys 等）
3. **使用 HTTPS**（生产环境必须）

## 🔐 安全检查

- [ ] 后端 JWT Secret Key 已更改（不是默认值）
- [ ] 生产环境使用 HTTPS
- [ ] API Keys 存储在环境变量中，不在代码中
- [ ] CORS 只允许必要的域名

## 📝 测试清单

部署后，测试以下功能：

- [ ] 用户注册/登录
- [ ] 个人资料编辑
- [ ] AI 聊天功能
- [ ] 匹配推荐
- [ ] 照片上传
- [ ] 支付功能（如果已实现）

## 🆘 需要帮助？

如果遇到问题：
1. 检查浏览器控制台的错误信息
2. 检查后端终端的日志
3. 确认所有服务都在运行
4. 验证环境变量配置

---

**最后更新**: 2025-01-XX










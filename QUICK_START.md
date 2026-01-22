# 🚀 快速启动指南

## 前提条件

- Python 3.10+ 已安装
- Node.js 18+ 已安装
- npm 或 yarn 已安装

## 快速启动步骤

### 1. 检查配置

```bash
# 在项目根目录运行
python check_deployment.py
```

这会检查前后端配置是否正确。

### 2. 配置前端环境变量

创建 `uae-match-web/.env.local` 文件：

```bash
cd uae-match-web
# Windows (PowerShell)
echo "NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1" > .env.local

# Linux/Mac
echo "NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1" > .env.local
```

或者手动创建 `.env.local` 文件，内容：
```
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

### 3. 安装前端依赖（如果还没有）

```bash
cd uae-match-web
npm install
```

### 4. 启动后端

```bash
cd backend
# 激活虚拟环境（如果使用）
.venv\Scripts\activate  # Windows
# 或
source .venv/bin/activate  # Linux/Mac

# 启动后端服务
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

后端将在 `http://127.0.0.1:8000` 启动。

### 5. 启动前端（新终端窗口）

```bash
cd uae-match-web
npm run dev
```

前端将在 `http://localhost:3000` 启动。

### 6. 访问应用

打开浏览器访问：`http://localhost:3000`

## ✅ 验证连接

1. 打开浏览器开发者工具（F12）
2. 查看 Network 标签
3. 尝试登录或注册
4. 检查 API 请求是否成功（状态码 200）

## 🔧 常见问题

### 端口被占用

如果端口 8000 或 3000 被占用：

**后端端口**：修改 `uvicorn` 命令中的 `--port` 参数
```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

**前端端口**：修改 `package.json` 中的 dev 脚本
```json
"dev": "next dev -p 3001"
```

然后更新 `.env.local` 和 CORS 配置。

### CORS 错误

如果看到 CORS 错误，检查 `backend/app/main.py` 中的 `origins` 列表是否包含前端地址。

## 📚 更多信息

详细部署指南请查看：`DEPLOYMENT_GUIDE.md`










# 05 · 部署运维手册 Runbook

> UAE Match ｜ 版本 v1.0.0 ｜ 更新 2026-07-04

本手册面向负责 UAE Match（面向 UAE 华人的 AI 相亲平台）部署与日常运维的工程师。所有命令均基于本项目真实目录结构：后端 `backend/`（FastAPI + Uvicorn + SQLAlchemy），前端 `uae-match-web-fronted-version2/`（React 18 + TS + Vite），后端 `.env` 位于 `backend/.env`，Python 虚拟环境位于项目根 `.venv`。

---

## 1. 环境矩阵

| 维度 | 本地（Local） | 预发（Staging） | 生产（Production） |
|---|---|---|---|
| 用途 | 开发自测 | 上线前验证/压测/回归 | 对外服务 |
| 后端进程 | `uvicorn --reload` 单进程 | Gunicorn+Uvicorn worker（2 worker） | Gunicorn+Uvicorn worker（按 CPU 核心）+ Nginx |
| 监听 | 127.0.0.1:8000 | 内网 IP:8000（Nginx 前置） | 仅 Nginx 对外 443，后端绑 127.0.0.1:8000 |
| 数据库 | SQLite `backend/app.db` | PostgreSQL + pgvector | PostgreSQL + pgvector（主从/托管实例） |
| 缓存/限流 | 无（进程内） | Redis | Redis（持久化+高可用） |
| 照片存储 | 本地 `backend/uploads/` | 对象存储（测试桶） | 对象存储 + CDN |
| OpenAI | 真实 Key（低预算） | 真实 Key（独立预算） | 真实 Key（独立预算+成本告警） |
| 定时任务 | 进程内线程 | 单实例运行 | 单实例专用调度节点 / 分布式锁 |
| HTTPS | 否 | 是（可自签或测试证书） | 是（强制，正式证书） |
| DEBUG | 开 | 关 | 关 |

> 关键原则：本地与生产**唯一差异应集中在环境变量**，代码保持一致。

---

## 2. 依赖与前置

### 2.1 运行时版本

| 组件 | 版本要求 | 说明 |
|---|---|---|
| Python | 3.11+ | FastAPI 0.104 / SQLAlchemy 2.0 / openai ≥1.0 |
| Node.js | 18 LTS+ | Vite 构建前端 |
| PostgreSQL | 15+ | 生产数据库，需装 pgvector |
| pgvector | 0.5+ | 向量检索扩展 |
| Redis | 7+ | 缓存 / 限流 / 会话 |
| Nginx | 1.24+ | 反向代理 + TLS 终止 + 静态托管 |

### 2.2 安装 PostgreSQL + pgvector（Ubuntu 示例）

```bash
sudo apt-get update
sudo apt-get install -y postgresql-15 postgresql-server-dev-15
# 安装 pgvector
sudo apt-get install -y postgresql-15-pgvector    # 或从源码编译
# 建库建用户
sudo -u postgres psql <<'SQL'
CREATE DATABASE uae_match;
CREATE USER uae_app WITH PASSWORD '<强口令>';
GRANT ALL PRIVILEGES ON DATABASE uae_match TO uae_app;
\c uae_match
CREATE EXTENSION IF NOT EXISTS vector;
SQL
```

### 2.3 安装 Redis

```bash
sudo apt-get install -y redis-server
sudo systemctl enable --now redis-server
redis-cli ping     # 期望返回 PONG
```

---

## 3. 后端部署

### 3.1 本地开发（现状）

```bash
# 项目根创建/激活虚拟环境（.venv 在项目根）
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

# 启动（开发热重载）
cd backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3.2 预发/生产（Gunicorn + Uvicorn Worker）

Uvicorn 的 `--reload` 仅用于开发。生产用 Gunicorn 管理多个 Uvicorn worker（ASGI）。

```bash
source /opt/uae-match/.venv/bin/activate
cd /opt/uae-match/backend
pip install gunicorn

# worker 数建议 = (2 × CPU核数) + 1；先从 4 起，压测后调整
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000 \
  --timeout 60 \
  --graceful-timeout 30 \
  --access-logfile /var/log/uae-match/access.log \
  --error-logfile  /var/log/uae-match/error.log
```

> **重要（多 worker 与定时任务）**：`app/main.py` 的启动钩子会拉起 `scheduler.py` 的守护线程。多 worker 情况下每个 worker 都会启动线程 → 定时任务重复执行。见 [第 8 节](#8-定时任务在多实例多-worker-下的处理)。

#### systemd 托管（推荐）

`/etc/systemd/system/uae-match-api.service`：

```ini
[Unit]
Description=UAE Match API
After=network.target postgresql.service redis-server.service

[Service]
User=uae
WorkingDirectory=/opt/uae-match/backend
EnvironmentFile=/opt/uae-match/backend/.env
ExecStart=/opt/uae-match/.venv/bin/gunicorn app.main:app \
  --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000 --timeout 60
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now uae-match-api
```

### 3.3 容器化建议

`backend/Dockerfile`：

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn
COPY . .
EXPOSE 8000
CMD ["gunicorn", "app.main:app", "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

建议拆分容器：`api`（无状态，可横向扩展）、`scheduler`（**单副本**，专跑定时任务）、`postgres`、`redis`。密钥通过环境变量/Secret 注入，**不打进镜像**。照片目录改用对象存储后，容器可完全无状态。

### 3.4 Nginx 反向代理（含 WebSocket）

```nginx
server {
    listen 443 ssl http2;
    server_name api.uae-match.com;

    ssl_certificate     /etc/letsencrypt/live/api.uae-match.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.uae-match.com/privkey.pem;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket 聊天 /ws/chat/{id}
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;      # 长连接
    }
}
```

---

## 4. 前端构建与托管

前端连接后端地址由环境变量 `VITE_API_BASE_URL` 决定（默认 `http://127.0.0.1:8000/api/v1`）。

```bash
cd uae-match-web-fronted-version2

# 生产环境变量（构建期注入，Vite 变量必须 VITE_ 前缀）
cat > .env.production <<'ENV'
VITE_API_BASE_URL=https://api.uae-match.com/api/v1
ENV

npm ci
npm run build           # 产物输出到 dist/
```

托管方式（任选其一）：
- **Vercel / Netlify**：连接 GitHub 仓库（https://github.com/Ibrahim-Han12/UAE-MATCH-v2），构建目录设 `uae-match-web-fronted-version2`，构建命令 `npm run build`，输出 `dist`。
- **对象存储 + CDN**：`dist/` 上传到 S3/OSS 桶，前置 CDN，配置 SPA 回退（所有路径回 `index.html`，因前端为状态机导航、无 react-router，但仍需保证根路径正确返回）。

> 注意：`VITE_API_BASE_URL` 在**构建时**固化进静态文件，切换后端地址需重新 `build`。

---

## 5. 环境变量清单

后端 `.env` 位于 `backend/.env`（已 gitignore）。上线前逐项落实：

| 变量 | 说明 | 上线要求 |
|---|---|---|
| `JWT_SECRET_KEY` | Access Token 签名密钥（HS256） | **必须**改掉默认值 `change-this-in-production`，用高强度随机串 |
| `JWT_REFRESH_SECRET_KEY` | Refresh Token 签名密钥 | 必须独立于上者，高强度随机 |
| `OPENAI_API_KEY` | OpenAI 密钥 | **必须轮换新 Key**（曾明文存在），仅走环境变量 |
| `DATABASE_URL` | 数据库连接串 | 生产为 `postgresql+psycopg://uae_app:<pwd>@host:5432/uae_match` |
| `REDIS_URL` | Redis 连接串 | `redis://:<pwd>@host:6379/0` |
| `CORS_ORIGINS` | 允许的前端来源 | 收紧为正式域名，禁止 `*` |
| `DEBUG` | 调试模式 | 生产设 `false` |
| `PAYMENT_*` | 支付平台密钥/回调验签密钥（支付宝/微信） | 走环境变量，禁止硬编码 |
| `OSS_*` / `S3_*` | 对象存储访问密钥/桶名/区域 | 照片迁移后配置 |
| `AI_GLOBAL_BUDGET_USD` | 全局月度预算（默认 500） | 按运营预算设定 |

生成强密钥：

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

> CORS 白名单当前在 `backend/app/main.py` 中定义。上线前应改为从环境变量读取，避免改代码重发布。

---

## 6. 数据库迁移：SQLite → PostgreSQL

现状：SQLite 单文件 `backend/app.db`，20 张表，向量以 JSON 文本存于 `user_embeddings.embedding_vector`，检索为 O(n) 线性扫描；无 Alembic，靠 `migrate_add_*.py` 手写脚本 + `create_all`。

### 6.1 引入 Alembic（迁移框架）

```bash
cd backend
pip install alembic
alembic init alembic
# 编辑 alembic/env.py：
#   from app.db.base import Base           # 指向项目 Base
#   target_metadata = Base.metadata
#   sqlalchemy.url 从 DATABASE_URL 环境变量读取
alembic revision --autogenerate -m "init schema"
alembic upgrade head
```

此后表结构演进一律通过 `alembic revision --autogenerate` + `alembic upgrade head`，废弃手写 `migrate_add_*.py`。

### 6.2 数据迁移步骤

1. 在 PostgreSQL 建库并 `CREATE EXTENSION vector;`（见 2.2）。
2. 用 Alembic 在 PG 上建全部 20 张表（`alembic upgrade head`）。
3. 从 SQLite 导出数据，按表导入 PG。因存在 JSON 字段与自增主键，建议用脚本逐表迁移（读 SQLite ORM 对象 → 写 PG），或用 `pgloader`：
   ```bash
   pgloader sqlite:///opt/uae-match/backend/app.db \
     postgresql://uae_app:<pwd>@localhost/uae_match
   ```
4. 校验行数一致：对每张表比对 `SELECT count(*)`。

### 6.3 向量迁 pgvector

- 将 `user_embeddings` 的向量列由 JSON 文本改为 `vector(1536)` 类型（Alembic 迁移中执行 `ALTER TABLE`）。
- 迁移脚本读取旧 JSON 数组 → 写入 `vector` 列。
- 建 HNSW 索引加速：
  ```sql
  ALTER TABLE user_embeddings ADD COLUMN embedding vector(1536);
  -- 回填后：
  CREATE INDEX idx_user_embeddings_hnsw
    ON user_embeddings USING hnsw (embedding vector_cosine_ops);
  ```
- `embedding_service.find_similar_users()` 的 O(n) 余弦扫描改为 SQL：
  ```sql
  SELECT user_id, 1 - (embedding <=> :query_vec) AS similarity
  FROM user_embeddings
  WHERE user_id <> :me
  ORDER BY embedding <=> :query_vec
  LIMIT 5;
  ```
  相似度阈值 0.7、Top5 逻辑与现有一致。

---

## 7. 照片迁对象存储

现状：照片存本地 `backend/uploads/`，`user_photos` 表记 `file_path/file_url/file_name`，下载走 `GET /api/v1/photos/file/{filename}`（无需鉴权）。

迁移方案：
1. 接入 S3/OSS SDK，上传接口（`POST /api/v1/photos/upload`）改为写对象存储，保存返回的对象 URL 到 `file_url`。
2. 前置 CDN，`file_url` 存 CDN 域名地址；`GET /photos/file/{filename}` 可改为 302 重定向到 CDN 或前端直接用 `file_url`。
3. 历史照片批量迁移：遍历 `backend/uploads/`，上传到桶并回填 `user_photos.file_url`。
4. 桶权限：图片可公开读或走签名 URL；上传保持后端鉴权。
5. 迁移完成、验证无误后再删除本地 `uploads/`。

---

## 8. 定时任务在多实例/多 worker 下的处理

**风险**：`scheduler.py` 用 `schedule` + 守护线程随主进程启动。缓存清理（每天 02:00 UTC）与 VIP 关怀（每周二/五 20:00 UTC）在 Gunicorn 多 worker 或多实例下**会被重复执行**（每个 worker/实例各跑一次），导致重复发送关怀消息、重复清理。

处理方案（择一）：

1. **单独调度节点（推荐，改动最小）**：API 多副本关闭内置调度，仅一个专用副本/容器运行调度。用环境变量开关，如 `ENABLE_SCHEDULER=true` 仅在调度节点设为 true，`main.py` 启动钩子据此决定是否启动线程。
2. **迁移到系统级调度**：改用 `cron` 或 systemd timer 触发独立脚本执行 `cache_cleanup` / `vip_care`，与 API 进程解耦。
3. **分布式锁**：任务执行前用 Redis `SET key NX EX` 抢锁，仅抢到锁的实例执行（适合无法拆节点时的兜底）。

> 上线 v1.0 若为单实例部署，可暂维持现状，但 Gunicorn 请**只让一个 worker 跑调度**（方案 1）或临时用单 worker。

---

## 9. 常用运维操作

```bash
# —— 启动 / 停止 / 重启（systemd）——
sudo systemctl start   uae-match-api
sudo systemctl stop    uae-match-api
sudo systemctl restart uae-match-api
sudo systemctl status  uae-match-api

# —— 查看日志 ——
sudo journalctl -u uae-match-api -f              # 实时
tail -f /var/log/uae-match/error.log             # Gunicorn 错误日志
tail -f /var/log/uae-match/access.log            # 访问日志

# —— 健康检查 ——
curl -s http://127.0.0.1:8000/api/v1/health      # 期望 {"status":"ok"}

# —— 数据库备份（PostgreSQL）——
pg_dump -Fc -U uae_app -h localhost uae_match \
  > /backup/uae_match_$(date +%F_%H%M).dump
# 恢复
pg_restore -c -U uae_app -h localhost -d uae_match /backup/xxx.dump

# —— SQLite 备份（迁移前的本地/现状）——
cp backend/app.db /backup/app_$(date +%F).db

# —— Redis 检查 ——
redis-cli ping
redis-cli info memory

# —— 前端重新发布 ——
cd uae-match-web-fronted-version2 && npm ci && npm run build   # 再同步 dist/ 到 CDN
```

> 建议数据库每日全量备份 + 保留 7~30 天；对象存储开启版本控制。备份需定期做**恢复演练**。

---

## 10. 故障排查

| 现象 | 可能原因 | 排查 / 处理 |
|---|---|---|
| 前端请求报 **CORS** 错误 | `main.py` 白名单未含前端正式域名 / 用了 `http` 而后端要 `https` | 检查 `CORS_ORIGINS`/`main.py` origins，加入正式域名并重启；确认协议一致 |
| 接口返回 **401 Unauthorized** | Token 过期（access 30 分钟）/ JWT 密钥不一致 / 未带 `Authorization: Bearer` | 前端用 refresh token 换新（`POST /api/v1/auth/refresh`）；确认服务端 `JWT_SECRET_KEY` 与签发时一致（改密钥会使所有旧 token 失效） |
| 数据库**连接失败** | `DATABASE_URL` 错 / PG 未启动 / 防火墙 / 连接数满 | `psql "$DATABASE_URL"` 验证；`systemctl status postgresql`；检查 `max_connections` 与连接池 |
| **端口 8000 被占用** | 旧进程未退出 / 端口冲突 | `lsof -i:8000`（Win: `netstat -ano \| findstr :8000`）找 PID 后 kill；或换端口并同步 Nginx |
| **WebSocket 聊天连不上** | Nginx 未配 Upgrade 头 / token 无效 / 超时断连 | 检查 Nginx `/ws/` 的 `Upgrade`/`Connection` 头；确认 `?token=` 有效；调大 `proxy_read_timeout` |
| **OpenAI 报错 / AI 功能不可用** | Key 失效 / 429 配额 / 全局预算超限（403） | 查 `OPENAI_API_KEY`；查 `global_ai_budget` 是否超月度上限；429 为用户/账户配额，需退避或提额 |
| AI 匹配**很慢** | SQLite 下 O(n) 线性向量扫描 | 迁 pgvector + HNSW（见第 6 节） |
| 定时任务**重复执行** | 多 worker/实例都起了调度线程 | 见第 8 节，仅单节点跑调度 |
| 照片打不开 | 本地 `uploads/` 权限 / 迁移后 URL 未回填 | 检查文件权限或 `user_photos.file_url`；确认 CDN 可达 |

---

## 附：关键路径速查

- 后端入口：`backend/app/main.py`（路由注册、CORS、启动钩子/调度器）
- 核心服务：`backend/app/core/`（security / safety / risk / openai_client / embedding_service / memory_service / vip_care_service / scheduler / cron_jobs / cache_cleanup）
- 数据模型：`backend/app/models/`（20 张表）
- 后端配置：`backend/.env`、`backend/app/core/config.py`
- 前端：`uae-match-web-fronted-version2/`（构建产物 `dist/`）
- 仓库：https://github.com/Ibrahim-Han12/UAE-MATCH-v2

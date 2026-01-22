# 启动后端服务器

## 问题：端口被多个进程占用

如果遇到"浏览器一直在加载"的问题，可能是因为有多个进程同时占用8000端口。

## 解决方法

### 1. 停止所有占用8000端口的进程

在 PowerShell 中运行：

```powershell
cd H:\uae-match\backend
.\kill_port_8000.ps1
```

或者手动查找并停止：

```powershell
# 查找占用8000端口的进程
netstat -ano | findstr :8000

# 停止特定进程（替换PID为实际进程ID）
taskkill /F /PID <进程ID>
```

### 2. 启动服务器

**方法1：使用 uvicorn（推荐）**

```powershell
cd H:\uae-match\backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**方法2：使用启动脚本**

```powershell
cd H:\uae-match\backend
python start_server.py
```

### 3. 验证服务器运行

打开浏览器访问：
- API文档: http://127.0.0.1:8000/docs
- Health检查: http://127.0.0.1:8000/api/v1/health

如果看到 API 文档页面或 health 返回 `{"status":"ok"}`，说明服务器正常运行。

## 注意事项

1. **只启动一个服务器实例**：确保只有一个进程在监听8000端口
2. **检查端口占用**：如果启动失败，先运行 `kill_port_8000.ps1` 清理端口
3. **查看错误日志**：如果启动失败，查看 PowerShell 中的错误信息

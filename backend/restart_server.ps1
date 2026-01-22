# 停止所有占用8000端口的进程并重新启动服务器

Write-Host "=== 停止现有服务器进程 ===" -ForegroundColor Yellow

# 查找所有占用8000端口的LISTENING进程
$listeningPids = netstat -ano | Select-String ":8000.*LISTENING" | ForEach-Object {
    if ($_ -match 'LISTENING\s+(\d+)') {
        $matches[1]
    }
} | Select-Object -Unique

if ($listeningPids) {
    foreach ($processId in $listeningPids) {
        Write-Host "正在停止进程 PID: $processId" -ForegroundColor Yellow
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
            Write-Host "  成功停止进程 $processId" -ForegroundColor Green
        } catch {
            Write-Host "  无法停止进程 $processId : $($_.Exception.Message)" -ForegroundColor Red
        }
    }
} else {
    Write-Host "没有找到占用8000端口的进程" -ForegroundColor Green
}

Write-Host "`n等待3秒让端口释放..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# 验证端口是否已释放
$remaining = netstat -ano | Select-String ":8000.*LISTENING"
if ($remaining) {
    Write-Host "警告: 仍有进程占用8000端口" -ForegroundColor Red
    Write-Host $remaining
} else {
    Write-Host "端口8000已释放" -ForegroundColor Green
}

Write-Host "`n=== 启动服务器 ===" -ForegroundColor Yellow
Write-Host "使用命令: python start_server.py" -ForegroundColor Cyan
Write-Host "或: uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`n" -ForegroundColor Cyan

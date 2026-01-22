# 停止占用8000端口的进程
Write-Host "正在查找占用8000端口的进程..."

$processes = netstat -ano | findstr :8000 | ForEach-Object {
    if ($_ -match 'LISTENING\s+(\d+)') {
        $matches[1]
    }
} | Select-Object -Unique

if ($processes) {
    foreach ($processId in $processes) {
        Write-Host "正在停止进程 PID: $processId"
        taskkill /F /PID $processId 2>$null
    }
    Write-Host "所有占用8000端口的进程已停止"
} else {
    Write-Host "没有找到占用8000端口的进程"
}

Start-Sleep -Seconds 2

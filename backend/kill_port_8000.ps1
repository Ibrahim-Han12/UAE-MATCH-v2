# 强制停止所有占用8000端口的进程
$pids = netstat -ano | Select-String ":8000.*LISTENING" | ForEach-Object {
    if ($_ -match 'LISTENING\s+(\d+)') {
        [int]$matches[1]
    }
} | Select-Object -Unique

if ($pids) {
    Write-Host "找到 $($pids.Count) 个进程占用8000端口: $pids"
    foreach ($processId in $pids) {
        Write-Host "停止进程 $processId..."
        taskkill /F /PID $processId
    }
    Start-Sleep -Seconds 2
    Write-Host "完成"
} else {
    Write-Host "没有找到占用8000端口的进程"
}

# frpc 被控端卸载脚本（需管理员权限）
$dst = "C:\frp"
$taskName = "FrpClientWin"
Write-Host "停止并删除计划任务 $taskName ..."
schtasks /End /TN $taskName 2>$null | Out-Null
schtasks /Delete /TN $taskName /F 2>$null | Out-Null
Get-Process -Name frpc -ErrorAction SilentlyContinue | Stop-Process -Force
if (Test-Path $dst) {
    Remove-Item -Recurse -Force $dst
    Write-Host "已删除 $dst"
}
Write-Host "frpc 已卸载。OpenSSH Server 保持原状，如需关闭："
Write-Host "  Stop-Service sshd; Set-Service sshd -StartupType Disabled"

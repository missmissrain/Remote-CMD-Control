# frpc 被控端一键安装脚本（需管理员权限，由 Install.bat 提权调用）
# 参数：-RemotePort  本机要占用的 VPS 隧道端口（默认取 frpc.toml 里的 remotePort）
# 流程：复制 frpc -> 启用 OpenSSH Server（系统组件失败则用随包离线版）
#       -> 默认 shell 设为 cmd.exe -> 注册开机自启计划任务 -> 自检并打印连接命令
param([int]$RemotePort = 0)

$ErrorActionPreference = "Continue"
$src = $PSScriptRoot
$dst = "C:\frp"
$taskName = "FrpClientWin"

Write-Host "==== 1/5 复制 frpc 到 $dst ====" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Copy-Item -Force (Join-Path $src "frpc.exe") (Join-Path $dst "frpc.exe")
Copy-Item -Force (Join-Path $src "frpc.toml") (Join-Path $dst "frpc.toml")
if ($RemotePort -gt 0) {
    $toml = Get-Content (Join-Path $dst "frpc.toml") -Raw
    $toml = [regex]::Replace($toml, '(?m)^remotePort\s*=\s*\d+', ("remotePort = " + $RemotePort))
    Set-Content -Path (Join-Path $dst "frpc.toml") -Value $toml -Encoding UTF8
    Write-Host ("remotePort 已设置为 " + $RemotePort)
}
Write-Host "完成"

Write-Host "==== 2/5 启用 OpenSSH Server ====" -ForegroundColor Cyan
$sshReady = $false
$cap = Get-WindowsCapability -Online -Name "OpenSSH.Server*" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($cap -and $cap.State -ne "Installed") {
    Write-Host "正在通过系统组件安装 OpenSSH Server（可能需要几分钟，请勿关闭窗口）..."
    try {
        Add-WindowsCapability -Online -Name $cap.Name | Out-Null
    } catch {
        Write-Host ("系统组件安装失败：" + $_.Exception.Message) -ForegroundColor Yellow
    }
}
if (Get-Service sshd -ErrorAction SilentlyContinue) {
    $sshReady = $true
    Write-Host "OpenSSH Server 就绪（系统组件）"
}

if (-not $sshReady) {
    $bundle = Join-Path $src "OpenSSH-Win64"
    if (Test-Path $bundle) {
        Write-Host "改用随包离线版 OpenSSH-Win64 ..."
        $dest = "C:\Program Files\OpenSSH"
        if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Force -Path $dest | Out-Null }
        Copy-Item -Path (Join-Path $bundle "*") -Destination $dest -Recurse -Force
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $dest "install-sshd.ps1")
        Start-Sleep -Seconds 2
        if (Get-Service sshd -ErrorAction SilentlyContinue) { $sshReady = $true }
        Write-Host ("离线版安装结果：" + $sshReady)
    }
}

if ($sshReady) {
    Set-Service -Name sshd -StartupType Automatic
    Start-Service -Name sshd
    $sshKey = "HKLM:\SOFTWARE\OpenSSH"
    if (-not (Test-Path $sshKey)) { New-Item -Path $sshKey -Force | Out-Null }
    New-ItemProperty -Path $sshKey -Name "DefaultShell" -Value "C:\Windows\System32\cmd.exe" -PropertyType String -Force | Out-Null
    Write-Host ("sshd 状态：" + (Get-Service sshd).Status)
} else {
    Write-Host "OpenSSH Server 未能启用，隧道会建立但无法登录。请手动开启：
设置 -> 系统 -> 可选功能 -> 添加功能 -> OpenSSH 服务器" -ForegroundColor Red
}

Write-Host "==== 3/5 注册开机自启任务 ====" -ForegroundColor Cyan
schtasks /Delete /TN $taskName /F 2>$null | Out-Null
$tr = '"' + (Join-Path $dst "frpc.exe") + '" -c "' + (Join-Path $dst "frpc.toml") + '"'
schtasks /Create /TN $taskName /TR $tr /SC ONSTART /RU SYSTEM /RL HIGHEST /F | Out-Null
schtasks /Run /TN $taskName | Out-Null
Write-Host "任务已创建并启动"

Write-Host "==== 4/5 验证 frpc ====" -ForegroundColor Cyan
Start-Sleep -Seconds 5
$proc = Get-Process -Name frpc -ErrorAction SilentlyContinue
if ($proc) {
    Write-Host ("frpc 正在运行，PID=" + ($proc | Select-Object -First 1).Id) -ForegroundColor Green
} else {
    Write-Host "frpc 未运行，请查看 C:\frp\frpc.log" -ForegroundColor Red
}
if (Test-Path (Join-Path $dst "frpc.log")) {
    Write-Host "---- frpc.log 末尾 ----"
    Get-Content (Join-Path $dst "frpc.log") -Tail 15
}

Write-Host "==== 5/5 连接方式 ====" -ForegroundColor Cyan
$cfg = Get-Content (Join-Path $dst "frpc.toml") -Raw
$server = [regex]::Match($cfg, 'serverAddr\s*=\s*"([^"]+)"').Groups[1].Value
$remote = [regex]::Match($cfg, 'remotePort\s*=\s*(\d+)').Groups[1].Value
Write-Host ""
Write-Host ("别人控制本机： ssh -p " + $remote + " 本机用户名@" + $server) -ForegroundColor Green
Write-Host ("本机控制对方： ssh -p <对方端口> 对方用户名@" + $server)
Write-Host "登录后即为 cmd.exe；需要 PowerShell 时输入 powershell 回车。"
Write-Host "提示：若杀毒软件拦截 frpc.exe，请把 C:\frp 加入白名单。"

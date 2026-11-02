# -*- coding: utf-8 -*-
"""入口脚本：生成「整包拷走即用」的 Windows frpc 客户端分发包

功能：在 分发包/FrpWindowsClient 下生成
      frpc.exe、frpc.toml（全双工 TCP 隧道）、
      Install.bat / InstallFrpc.ps1（提权安装：启用 OpenSSH Server + 注册开机任务）、
      Uninstall.bat / UninstallFrpc.ps1（一键卸载）、
      OpenSSH-Win64 离线兜底目录、使用说明.md。
实现：从 软件/frp-win 复制可执行文件；OpenSSH-Win64.zip 解压成离线组件；
      .bat 用纯 ASCII 避免 cmd 编码问题，.ps1 用 UTF-8 BOM 保证中文不乱码。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\BuildFrpcPackage.py
"""

import os
import shutil
import sys
import zipfile

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ConfigLayer.ConfigLoader import ConfigLoader  # noqa: E402

PACKAGE_DIR = os.path.join(ROOT_DIR, "分发包", "FrpWindowsClient")

INSTALL_BAT = r"""@echo off
setlocal
cd /d "%~dp0"
set "PORT=%~1"
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    if "%PORT%"=="" (
        powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    ) else (
        powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -ArgumentList '%PORT%' -Verb RunAs"
    )
    exit /b
)
if "%PORT%"=="" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0InstallFrpc.ps1"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0InstallFrpc.ps1" -RemotePort %PORT%
)
pause
"""

LOCAL_BAT = r"""@echo off
rem Install THIS machine as the 21118 endpoint (bidirectional control)
call "%~dp0Install.bat" 21118
"""

UNINSTALL_BAT = r"""@echo off
setlocal
cd /d "%~dp0"
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0UninstallFrpc.ps1"
pause
"""

INSTALL_PS1 = r"""# frpc 被控端一键安装脚本（需管理员权限，由 Install.bat 提权调用）
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
"""

UNINSTALL_PS1 = r"""# frpc 被控端卸载脚本（需管理员权限）
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
"""


def build_config(cfg, remote_port=None):
    """cfg：配置对象。remote_port：本机要占用的 VPS 端口（默认取 frp.peerRemotePort）。
    返回 frpc.toml 文本（含 SSH 隧道与远端端口说明）。"""
    host = cfg.require("server.host")
    port = remote_port or cfg.get("frp.peerRemotePort", 21119)
    local_port = cfg.get("frp.localSideRemotePort", 21118)
    return """# frpc 配置（由部署脚本生成）
# 作用：本机主动连接 VPS 上的 frps，把本机 22 端口（OpenSSH Server）暴露到 VPS 的 {port} 端口。
# 隧道是 TCP 全双工的：两端可同时双向收发，既能被别人控制，也能从本机控制对方。
#
#   别人控制本机：  ssh -p {port} 本机用户名@{host}
#   本机控制对方：  ssh -p {local_port} 对方用户名@{host}
#
# 注意：多台电脑必须使用不同的 remotePort，否则端口冲突。
serverAddr = "{host}"
serverPort = {bind_port}

auth.method = "token"
auth.token = "{token}"

log.to = "C:/frp/frpc.log"
log.level = "info"
log.maxDays = 7

[[proxies]]
name = "win-cmd-ssh"
type = "tcp"
localIP = "127.0.0.1"
localPort = 22
remotePort = {port}
""".format(
        host=host,
        bind_port=cfg.get("frp.bindPort", 21117),
        token=cfg.get("frp.token", ""),
        port=port,
        local_port=local_port,
    )


def build_readme(cfg):
    """cfg：配置对象。返回使用说明.md 文本。
    服务器地址统一写成占位符，避免把真实 IP 带进仓库；实际地址见同目录 frpc.toml。"""
    host = "你的服务器公网IP"
    peer_port = cfg.get("frp.peerRemotePort", 21119)
    local_port = cfg.get("frp.localSideRemotePort", 21118)
    return """# Windows 端 frpc 分发包（整包拷走即用 · 双向互控）

## 一句话说明

在被控电脑上装好这套东西后，它的 CMD 会变成 VPS 上的一个 SSH 端口；
反过来，你本机的 CMD 也会变成 VPS 上的另一个端口 —— **双方可以互相控制**。

```
你本机  ──frpc(21118)──┐
                      ├── VPS frps(21117) ── ssh -p 端口 ──▶ 对方 CMD
对方PC  ──frpc(21119)──┘
```

隧道是 **TCP 全双工**：命令下行与回显上行同时双向传输，不是单向的转发。

## 端口分配（本项目默认）

| 机器 | remotePort | 谁连它 |
| --- | --- | --- |
| 本机（控制端 A） | %d | 对方：`ssh -p %d 用户名@%s` |
| 对方电脑（B） | %d | 本机：`ssh -p %d 用户名@%s` |

第 3 台开始，把 `remotePort` 改成 21115/21116/21120 等未占用且已放行的端口即可。

## 在另一台电脑上安装

1. 把整个 `FrpWindowsClient` 文件夹拷过去；
2. **确认包内有 `frpc.toml`**：仓库里的包只有 `frpc.toml.example`，
   复制一份改名 `frpc.toml` 并填好 `serverAddr` / `token`（或直接在仓库里跑
   `scripts\BuildFrpcPackage.py` 自动生成）；
3. 按角色选择安装方式：
   - 装成「对方电脑」（端口 21119）：双击 `Install.bat`
   - 装成「本机」（端口 21118，让别人能连进来）：双击 `InstallLocal-21118.bat`
   - 自定义端口：`Install.bat 21120`
4. UAC 点「是」，脚本自动完成：复制 frpc → 启用 OpenSSH Server（系统组件失败则用随包离线版）
   → 默认 shell 设为 cmd → 注册开机自启任务 `FrpClientWin` → 自检；
5. 结束时会打印本机对外端口与连接命令。

需要换端口时（例如本机要装成 21118）：

```powershell
powershell -ExecutionPolicy Bypass -File .\InstallFrpc.ps1 -RemotePort 21118
```

## 连接方式

```bat
:: 从本机控制对方（端口 21119）
ssh -p %d 对方用户名@%s

:: 从对方控制本机（端口 21118）
ssh -p %d 本机用户名@%s
```

- 首次连接输入 `yes` 接受指纹；
- 密码是该电脑的 Windows 登录密码；
- 登录后就是 `cmd.exe`，输入 `powershell` 可切到 PowerShell；
- 传文件：`scp -P 21119 本地文件 用户名@%s:C:/Users/用户名/Desktop/`

## 系统改动清单

| 项目 | 内容 |
| --- | --- |
| 安装目录 | `C:\\frp`（frpc.exe、frpc.toml、frpc.log） |
| 开机自启 | 计划任务 `FrpClientWin`（SYSTEM 身份） |
| SSH 服务 | 优先系统自带 OpenSSH Server；不可用时用随包 `OpenSSH-Win64` 离线装到 `C:\\Program Files\\OpenSSH` |
| 默认 shell | `HKLM\\SOFTWARE\\OpenSSH\\DefaultShell` = `C:\\Windows\\System32\\cmd.exe` |

## 排查

```powershell
Get-Process frpc                       # 进程
schtasks /Query /TN FrpClientWin /V     # 任务
Get-Content C:\\frp\\frpc.log -Tail 20  # 隧道日志
Get-Service sshd                        # SSH 服务
```

## 卸载

双击 `Uninstall.bat`：结束进程、删除计划任务与 `C:\\frp`，OpenSSH Server 保留。

## 安全提醒

1. `frpc.toml` 里的 token 等同隧道口令，别外传、别提交到公开仓库；
2. 双向互控意味着对方也能进你的机器 —— 两边都要设强密码，建议改用密钥登录；
3. frp 常被杀软误判为黑客工具，被拦就把 `C:\\frp` 加白名单。
""" % (local_port, local_port, host, peer_port, peer_port, host,
       peer_port, host, local_port, host, host)


def write_text(path, text, encoding):
    """path：目标路径。text：内容。encoding：编码。内容统一使用 CRLF 换行。"""
    with open(path, "w", encoding=encoding, newline="\r\n") as handle:
        handle.write(text)


def extract_openssh(target_dir):
    """target_dir：分发包目录。把 OpenSSH-Win64.zip 解压为离线兜底组件。"""
    zip_path = os.path.join(ROOT_DIR, "软件", "OpenSSH-Win64.zip")
    if not os.path.isfile(zip_path):
        print("跳过离线 OpenSSH：缺少 %s" % zip_path)
        return 0
    out_dir = os.path.join(target_dir, "OpenSSH-Win64")
    os.makedirs(out_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(out_dir)
    inner = os.path.join(out_dir, "OpenSSH-Win64")
    if os.path.isdir(inner):
        for name in os.listdir(inner):
            target = os.path.join(out_dir, name)
            if not os.path.exists(target):
                os.rename(os.path.join(inner, name), target)
        os.rmdir(inner)
    return len(os.listdir(out_dir))


def main():
    """无参数。生成完整分发包。"""
    cfg = ConfigLoader()
    if os.path.isdir(PACKAGE_DIR):
        shutil.rmtree(PACKAGE_DIR)
    os.makedirs(PACKAGE_DIR, exist_ok=True)
    shutil.copy(os.path.join(ROOT_DIR, "软件", "frp-win", "frpc.exe"), PACKAGE_DIR)
    write_text(os.path.join(PACKAGE_DIR, "frpc.toml"), build_config(cfg), "utf-8")
    # 示例配置用模板生成，避免把真实 token 写进仓库
    example_cfg = ConfigLoader("config/ServerConfig.example.json")
    write_text(os.path.join(PACKAGE_DIR, "frpc.toml.example"), build_config(example_cfg), "utf-8")
    write_text(os.path.join(PACKAGE_DIR, "Install.bat"), INSTALL_BAT, "ascii")
    write_text(os.path.join(PACKAGE_DIR, "InstallLocal-21118.bat"), LOCAL_BAT, "ascii")
    write_text(os.path.join(PACKAGE_DIR, "Uninstall.bat"), UNINSTALL_BAT, "ascii")
    write_text(os.path.join(PACKAGE_DIR, "InstallFrpc.ps1"), INSTALL_PS1, "utf-8-sig")
    write_text(os.path.join(PACKAGE_DIR, "UninstallFrpc.ps1"), UNINSTALL_PS1, "utf-8-sig")
    write_text(os.path.join(PACKAGE_DIR, "使用说明.md"), build_readme(cfg), "utf-8")
    count = extract_openssh(PACKAGE_DIR)
    print("分发包已生成:", PACKAGE_DIR)
    for name in sorted(os.listdir(PACKAGE_DIR)):
        path = os.path.join(PACKAGE_DIR, name)
        size = os.path.getsize(path) if os.path.isfile(path) else "<目录>"
        print("  %-20s %s" % (name, size))
    print("离线 OpenSSH 文件数:", count)


if __name__ == "__main__":
    main()

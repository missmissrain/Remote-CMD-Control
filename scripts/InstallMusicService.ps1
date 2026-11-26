# 功能：为当前登录用户安装独立音乐接收器，生成仅本机保存的令牌，注册登录自启。
# 参数：Python 默认D:\py39\pythonw.exe；Ffplay默认PATH；Port默认17863，用户可显式指定。
param(
    [string]$Python = 'D:\py39\pythonw.exe',
    [string]$Ffplay = '',
    [int]$Port = 17863
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$configFile = Join-Path $root 'config\MusicConfig.json'
if (!(Test-Path -LiteralPath $Python)) { throw 'pythonw不存在，请指定已有Python路径' }
if (!$Ffplay) { $Ffplay = (Get-Command ffplay.exe -ErrorAction Stop).Source }
if (!(Test-Path -LiteralPath $Ffplay)) { throw 'ffplay不存在' }
if (!(Test-Path -LiteralPath $configFile)) {
    $config = Get-Content -LiteralPath (Join-Path $root 'config\MusicConfig.example.json') -Raw | ConvertFrom-Json
    $bytes = New-Object byte[] 32
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    $config.token = [Convert]::ToBase64String($bytes)
    $config.ffplay = $Ffplay
    $config.port = $Port
    $config | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $configFile -Encoding UTF8
}
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
& icacls.exe $configFile /inheritance:r /grant:r "*${sid}:(F)" '*S-1-5-18:(F)' | Out-Null
if ($LASTEXITCODE -ne 0) { throw '配置文件ACL设置失败' }
$script = Join-Path $root 'scripts\RunMusicService.py'
$action = New-ScheduledTaskAction -Execute $Python -Argument ('-X utf8 "'+$script+'" --config "'+$configFile+'"') -WorkingDirectory $root
$principal = New-ScheduledTaskPrincipal -UserId $sid -LogonType Interactive -RunLevel Limited
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $sid
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName 'SynLoveMusicReceiver' -Action $action -Principal $principal -Trigger $trigger -Settings $settings -Description '远控音乐接收器：当前用户会话播放，不依赖SynLove GUI' -Force | Out-Null
Start-ScheduledTask -TaskName 'SynLoveMusicReceiver'
Write-Output '音乐接收器计划任务已安装并请求启动；请使用MusicControl查询协议状态。'

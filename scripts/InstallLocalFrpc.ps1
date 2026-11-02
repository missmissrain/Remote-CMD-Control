# Install frpc on THIS machine (remotePort 21118) as administrator; log redirected to file
# Enables bidirectional control: other machines can ssh into this PC too
$root = Split-Path -Parent $PSScriptRoot
$installer = Get-ChildItem -Path $root -Recurse -Filter "InstallFrpc.ps1" -ErrorAction SilentlyContinue |
    Select-Object -First 1
if (-not $installer) { Write-Error "installer not found"; exit 1 }

$log = Join-Path $root "output\local_frpc_install.log"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $log) | Out-Null

$argList = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-Command",
    "& '" + $installer.FullName + "' -RemotePort 21118 *> '" + $log + "'"
)
Write-Output "Requesting administrator privileges, please click YES on the UAC prompt..."
Start-Process -FilePath "powershell.exe" -ArgumentList $argList -Verb RunAs
Write-Output ("Installer: " + $installer.FullName)
Write-Output ("Log file : " + $log)

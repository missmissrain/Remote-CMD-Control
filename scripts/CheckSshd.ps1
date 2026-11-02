# Check OpenSSH Server capability state (ASCII only to avoid encoding issues)
$cap = Get-WindowsCapability -Online -Name "OpenSSH.Server*" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($cap) { Write-Output ("OpenSSH.Server state: " + $cap.State + " name=" + $cap.Name) } else { Write-Output "OpenSSH.Server: capability not found" }
$svc = Get-Service sshd -ErrorAction SilentlyContinue
if ($svc) { Write-Output ("sshd service: " + $svc.Status + " starttype=" + $svc.StartType) } else { Write-Output "sshd service: not installed" }
Write-Output ("OS: " + (Get-CimInstance Win32_OperatingSystem).Caption + " build " + [System.Environment]::OSVersion.Version.Build)

# Check local frpc process, scheduled task and sshd status (ASCII output only)
$p = Get-Process -Name frpc -ErrorAction SilentlyContinue
if ($p) { Write-Output ("frpc: RUNNING pid=" + (($p | Select-Object -First 1).Id)) } else { Write-Output "frpc: not running" }
$t = schtasks /Query /TN FrpClientWin /FO LIST 2>$null
if ($t) { Write-Output "--- task ---"; $t | Select-String -Pattern "Status|TaskName|Next Run|Last Run" }
$s = Get-Service sshd -ErrorAction SilentlyContinue
if ($s) { Write-Output ("sshd: " + $s.Status + " / " + $s.StartType) }

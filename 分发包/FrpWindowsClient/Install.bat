@echo off
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

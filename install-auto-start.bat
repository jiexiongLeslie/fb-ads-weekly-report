@echo off
chcp 65001 >nul
cd /d "%~dp0"

set TASK_NAME=FB Ads Weekly Report

schtasks /Create /TN "%TASK_NAME%" /SC ONLOGON /TR "%~dp0start-background.bat" /RL LIMITED /F
if errorlevel 1 (
    echo [ERROR] Failed to create scheduled task.
    pause
    exit /b 1
)

schtasks /Run /TN "%TASK_NAME%"
echo Auto start is enabled. Service URL: http://localhost:5003
pause

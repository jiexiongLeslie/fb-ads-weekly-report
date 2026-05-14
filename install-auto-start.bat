@echo off
chcp 65001 >nul
cd /d "%~dp0"

set TASK_NAME=FB Ads Weekly Report

powershell -NoProfile -ExecutionPolicy Bypass -Command "$action=New-ScheduledTaskAction -Execute 'wscript.exe' -Argument '//B //Nologo \"%~dp0start-background.vbs\"'; $trigger=New-ScheduledTaskTrigger -AtLogOn; $principal=New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited; Register-ScheduledTask -TaskName '%TASK_NAME%' -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null"
if errorlevel 1 (
    echo [ERROR] Failed to create scheduled task.
    pause
    exit /b 1
)

schtasks /Run /TN "%TASK_NAME%"
echo Auto start is enabled. Service URL: http://localhost:5003
pause

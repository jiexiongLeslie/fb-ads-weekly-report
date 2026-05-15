@echo off
chcp 65001 >nul
cd /d "%~dp0"

set TASK_NAME=FB Ads Weekly Report
set WATCHDOG_NAME=FB Ads Weekly Report Watchdog

powershell -NoProfile -ExecutionPolicy Bypass -Command "$action=New-ScheduledTaskAction -Execute 'wscript.exe' -Argument '//B //Nologo \"%~dp0start-background.vbs\"'; $principal=New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited; $settings=New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew; $logon=New-ScheduledTaskTrigger -AtLogOn; Register-ScheduledTask -TaskName '%TASK_NAME%' -Action $action -Trigger $logon -Principal $principal -Settings $settings -Force | Out-Null; $once=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5); Register-ScheduledTask -TaskName '%WATCHDOG_NAME%' -Action $action -Trigger $once -Principal $principal -Settings $settings -Force | Out-Null"
if errorlevel 1 (
    echo [ERROR] Failed to create scheduled task.
    pause
    exit /b 1
)

schtasks /Run /TN "%TASK_NAME%"
echo Auto start is enabled. Service URL: http://localhost:5003
pause

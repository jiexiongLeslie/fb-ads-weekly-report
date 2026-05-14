@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist logs mkdir logs

where py >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python launcher "py" was not found. Please install Python or add it to PATH.
    exit /b 1
)

py -c "import flask, flask_cors, requests" >nul 2>nul
if errorlevel 1 (
    py -m pip install flask flask-cors requests -q
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-NetTCPConnection -LocalPort 5003 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }" >nul 2>nul
if not errorlevel 1 (
    echo Service is already running at http://localhost:5003
    exit /b 0
)

set FB_REPORT_PORT=5003
start "FB Ads Weekly Report" /min cmd /c call "%~dp0run-server.bat"

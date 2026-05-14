@echo off
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python launcher "py" was not found. Please install Python or add it to PATH.
    pause
    exit /b 1
)

py -c "import flask, flask_cors, requests" >nul 2>nul
if errorlevel 1 (
    py -m pip install flask flask-cors requests -q
)

set FB_REPORT_PORT=5003
cd /d "%~dp0backend"
echo Service URL: http://localhost:5003
py server.py
pause

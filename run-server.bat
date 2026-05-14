@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist logs mkdir logs
set FB_REPORT_PORT=5003

cd /d "%~dp0backend"
py server.py >> "%~dp0logs\server.log" 2>&1

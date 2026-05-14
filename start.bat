@echo off
chcp 65001 >nul
cd /d "%~dp0"

call "%~dp0start-background.bat"

timeout /t 3 /nobreak >nul
start http://localhost:5003

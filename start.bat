@echo off
chcp 65001 >nul

:: ==========================================
:: 自动上传代码到Git（静默执行）
:: ==========================================
cd /d "%~dp0"
if exist "auto-git-push.bat" (
    echo [自动上传] 正在同步代码到GitHub...
    start /min "" "auto-git-push.bat"
)

:: ==========================================
:: 启动FB广告周报系统服务
:: ==========================================
cd /d "%~dp0backend"
echo.
echo ==========================================
echo   Facebook Ads Weekly Report System
echo ==========================================
echo.
echo   Frontend: http://localhost:5003
echo   Backend:  http://localhost:5000
echo.
echo   Press Ctrl+C to stop
echo ==========================================
echo.
python server.py

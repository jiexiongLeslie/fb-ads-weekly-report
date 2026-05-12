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
:: 后台启动FB广告周报系统服务
:: ==========================================
cd /d "%~dp0backend"
echo 正在后台启动服务...
start /min "" python server.py

:: 等待服务启动
timeout /t 3 /nobreak >nul

:: 打开前端页面
start http://localhost:5003

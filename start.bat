@echo off
chcp 65001 >nul

:: ==========================================
:: 自动上传代码到Git（静默执行）
:: ==========================================
cd /d "%~dp0"
if exist "auto-git-push.bat" (
    echo [自动上传] 正在同步代码到GitHub...
    start "GitUpload" /min cmd /c "cd /d %~dp0 && auto-git-push.bat"
)

:: ==========================================
:: 后台启动FB广告周报系统服务
:: ==========================================
echo 正在后台启动服务...
start "FBService" /min cmd /c "cd /d %~dp0backend && py server.py"

:: 等待服务启动
timeout /t 5 /nobreak >nul

:: 打开前端页面
start http://localhost:5003

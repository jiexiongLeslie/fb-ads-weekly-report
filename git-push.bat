@echo off
chcp 65001 >nul
echo ==========================================
echo    Datenanalyse-Dashboard - Git自动上传工具
echo ==========================================
echo.

:: 检查Git是否可用
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到Git，请确保Git已安装
    pause
    exit /b 1
)

:: 获取当前日期时间作为提交信息
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=: " %%a in ('time /t') do (set mytime=%%a:%%b)
set commit_msg=更新于 %mydate% %mytime%

echo [1/4] 正在添加文件到暂存区...
git add .
if %errorlevel% neq 0 (
    echo [错误] git add 失败
    pause
    exit /b 1
)

echo [2/4] 正在检查是否有变更...
git diff --cached --quiet
if %errorlevel% equ 0 (
    echo [信息] 没有需要提交的变更
    echo.
    pause
    exit /b 0
)

echo [3/4] 正在提交变更: %commit_msg%
git commit -m "%commit_msg%"
if %errorlevel% neq 0 (
    echo [错误] git commit 失败
    pause
    exit /b 1
)

echo [4/4] 正在推送到GitHub...
git push origin main
if %errorlevel% neq 0 (
    echo [错误] git push 失败
    pause
    exit /b 1
)

echo.
echo ==========================================
echo    ✅ 上传成功！
echo    仓库: https://github.com/jiexiongLeslie/fb-ads-weekly-report
echo ==========================================
echo.
pause

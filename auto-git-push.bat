@echo off
chcp 65001 >nul

:: 自动Git上传脚本（静默模式，无窗口等待）
:: 获取当前日期时间作为提交信息
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=: " %%a in ('time /t') do (set mytime=%%a:%%b)
set commit_msg=Auto update %mydate% %mytime%

:: 检查Git是否可用
where git >nul 2>nul
if %errorlevel% neq 0 exit /b 1

:: 添加文件
git add . >nul 2>&1

:: 检查是否有变更
git diff --cached --quiet
if %errorlevel% equ 0 exit /b 0

:: 提交并推送
git commit -m "%commit_msg%" >nul 2>&1
git push origin main >nul 2>&1

exit /b 0

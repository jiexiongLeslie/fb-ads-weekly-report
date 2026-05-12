@echo off
chcp 65001 >nul
echo ==========================================
echo   Facebook Ads Weekly Report System
echo ==========================================
echo.
echo   请选择操作:
echo.
echo   [1] 启动服务 (前端+后端)
echo   [2] 启动服务 + 自动上传Git
echo   [3] 仅上传代码到Git
echo   [4] 退出
echo.
echo ==========================================
set /p choice="请输入选项 (1-4): "

if "%choice%"=="1" goto start_service
if "%choice%"=="2" goto start_and_push
if "%choice%"=="3" goto push_only
if "%choice%"=="4" exit

goto end

:start_service
cd /d "%~dp0backend"
echo.
echo   正在启动服务...
echo   Frontend: http://localhost:5003
echo   Backend:  http://localhost:5000
echo.
python server.py
pause
goto end

:start_and_push
cd /d "%~dp0"
echo.
echo [1/2] 正在上传代码到Git...
call git-push.bat
echo.
echo [2/2] 正在启动服务...
cd backend
python server.py
pause
goto end

:push_only
cd /d "%~dp0"
call git-push.bat
goto end

:end

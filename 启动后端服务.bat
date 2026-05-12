@echo off
chcp 65001 >nul
echo ==========================================
echo   Facebook Ads 数据同步服务启动器
echo ==========================================
echo.

cd /d "%~dp0backend"

echo 正在检查依赖...
python -c "import flask, flask_cors, requests" 2>nul
if errorlevel 1 (
    echo 正在安装依赖...
    pip install flask flask-cors requests -q
)

echo.
echo 启动后端服务...
echo 访问地址: http://localhost:5000
echo.
echo API 端点:
echo   POST /api/sync       - 同步数据
echo   GET  /api/data       - 获取数据
echo   GET  /api/accounts   - 获取账户列表
echo   GET  /api/token-status - 检查 Token
echo.
echo 按 Ctrl+C 停止服务
echo ==========================================
python server.py

pause

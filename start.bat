@echo off
cd /d "%~dp0backend"
echo ==========================================
echo   Facebook Ads Weekly Report System
echo ==========================================
echo.
echo   Frontend: http://localhost:5003
echo   Backend:  http://localhost:5000
echo.
echo   Press Ctrl+C to stop
echo ==========================================
python server.py
pause

@echo off
cd /d "%~dp0"

echo ==========================================
echo PrivCon local startup
echo ==========================================

echo.
echo Starting backend...
start "PrivCon Backend" /D "%~dp0backend" cmd /k "venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

timeout /t 3 >nul

echo Starting frontend...
start "PrivCon Frontend" /D "%~dp0frontend" cmd /k "npm run dev"

timeout /t 5 >nul
start "" http://localhost:3000

echo.
echo Both services are starting in separate terminals.
echo Backend: http://localhost:8000/api/health
echo Frontend: http://localhost:3000
echo.
echo Press any key to close this launcher window...
pause >nul

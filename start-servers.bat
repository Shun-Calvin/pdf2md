@echo off
chcp 65001 >nul
echo ========================================
echo   PDF2MD Converter - Server Starter
echo ========================================
echo.

:: Start Backend Server
echo [1/2] Starting Backend Server (FastAPI)...
echo         URL: http://localhost:8000
echo         API Docs: http://localhost:8000/docs
echo.
start "Backend Server" cmd /k "cd /d C:\Users\USER\Documents\pdf2md\backend && venv\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: Wait a bit for backend to start
timeout /t 3 /nobreak >nul

:: Start Frontend Server
echo [2/2] Starting Frontend Server (React)...
echo         URL: http://localhost:3000
echo.
start "Frontend Server" cmd /k "cd /d C:\Users\USER\Documents\pdf2md\frontend && npm start"

echo.
echo ========================================
echo   Servers are starting up!
echo ========================================
echo.
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo.
echo   API Documentation: http://localhost:8000/docs
echo.
echo   Press any key to close this window...
echo   (Servers will continue running)
echo ========================================
pause >nul
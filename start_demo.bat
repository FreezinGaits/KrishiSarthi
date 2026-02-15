@echo off
title Krishi-Sarthi Demo
echo.
echo ========================================
echo   Krishi-Sarthi Demo Launcher
echo ========================================
echo.

:: Start backend
echo [1/2] Starting Backend (port 8000)...
cd /d "%~dp0backend"
start "Krishi-Backend" cmd /c "set DEMO_MODE=true && python run.py"

:: Wait for backend
timeout /t 3 /nobreak >nul

:: Start frontend
echo [2/2] Starting Frontend (port 3000)...
cd /d "%~dp0frontend"
if not exist node_modules (
    echo Installing dependencies...
    call npm install
)
start "Krishi-Frontend" cmd /c "npm run dev"

:: Print URLs
timeout /t 3 /nobreak >nul
echo.
echo ========================================
echo   Demo Ready!
echo.
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo ========================================
echo.
echo Press any key to stop...
pause >nul

:: Cleanup
taskkill /FI "WINDOWTITLE eq Krishi-Backend" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Krishi-Frontend" /F >nul 2>&1

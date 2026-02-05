@echo off
REM Fansy Analytics MVP - Windows Startup Script

echo ========================================
echo   Fansy Analytics MVP
echo   Starting web server...
echo ========================================
echo.

REM Проверка Python
python --version > nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

REM Проверка зависимостей
echo Checking dependencies...
pip show flask > nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies!
        pause
        exit /b 1
    )
)

echo.
echo Dependencies OK
echo.
echo ========================================
echo   Server starting...
echo   Dashboard: http://localhost:5000
echo   API: http://localhost:5000/api/
echo ========================================
echo.
echo Press Ctrl+C to stop
echo.

REM Запуск сервера
cd backend
python web_server.py

pause

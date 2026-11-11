@echo off
title RACER-X Sign Language Backend Server
echo ========================================================
echo   RACER-X WebSocket Inference Server (Port 8000)
echo ========================================================

:: Check and install fastapi if missing
python -c "import fastapi" 2>nul
if %errorlevel% neq 0 (
    echo [+] 'fastapi' not detected. Installing dependencies automatically...
    python -m pip install fastapi uvicorn websockets
)

echo.
echo [+] Starting server...
echo.
python server.py
pause

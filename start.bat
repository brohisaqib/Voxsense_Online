@echo off
title VoxSense - AI Voice Assistant
color 0A
cls

echo.
echo  ============================================================
echo         VoxSense - AI Voice Assistant for Blind Users
echo  ============================================================
echo.

:: CHECK PYTHON
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found!
    echo  Download: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo  Python found.

:: CHECK .env FILE
echo [2/5] Checking .env file...
if not exist "backend\.env" (
    echo  WARNING: backend\.env not found! Creating template...
    echo ANTHROPIC_API_KEY=your_api_key_here > backend\.env
    echo CLAUDE_MODEL=claude-haiku-4-5-20251001 >> backend\.env
    echo.
    echo  Open backend\.env and add your Anthropic API key!
    echo  Get key: https://console.anthropic.com
    echo.
    pause
)
echo  .env file ready.

:: CREATE LOGS FOLDER
if not exist "logs" mkdir logs

:: CHECK PLAYWRIGHT
echo [3/5] Setting up Playwright browser...
python -m playwright install chromium >nul 2>&1
echo  Chromium ready.

:: START BACKEND
echo [4/5] Starting backend server...
cd backend
start /B python -m uvicorn main:app --host 127.0.0.1 --port 8000 > ..\logs\backend.log 2>&1
cd ..

echo  Waiting for backend to start...
timeout /t 5 /nobreak >nul
echo  Backend running at http://127.0.0.1:8000

:: OPEN BROWSER — localhost se kholo, file:// se NAHI
echo [5/5] Opening browser...
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:8000"
echo  Browser opened at http://localhost:8000

:: SPEAK READY — Fixed PowerShell syntax
powershell -Command "Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Rate = 0; $s.Speak('VoxSense is ready. Say Hey Vox to start.')" >nul 2>&1

echo.
echo  ============================================================
echo   VoxSense is RUNNING!
echo  ============================================================
echo   Backend  : http://127.0.0.1:8000
echo   Frontend : http://localhost:8000
echo   Logs     : logs\backend.log
echo  ============================================================
echo   Say "Hey Vox" ya "Computer" to activate
echo   Press Ctrl+C to stop server
echo  ============================================================
echo.

:: Microphone allow reminder
echo  IMPORTANT: Browser mein Microphone ALLOW karo (ek baar)
echo  Address bar mein lock icon > Site Settings > Microphone > Allow
echo.
pause
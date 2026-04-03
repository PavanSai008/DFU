@echo off
title DFU Wound Intelligence
echo.
echo  DFU Wound Intelligence — Starting...
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    pause & exit /b 1
)

cd backend

pip show tensorflow >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
)

echo.
echo  Backend : http://localhost:5000
echo  Frontend: Open frontend\index.html in your browser
echo.
echo  Press Ctrl+C to stop.
echo.
python app.py
pause

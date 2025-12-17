@echo off
REM SweetSeek Startup Script for Windows

echo ================================
echo    SweetSeek Starting...
echo ================================
echo.

REM Check if .env exists
if not exist .env (
    echo Warning: .env file not found
    echo Please copy .env.example to .env and configure your API key
    echo.
    pause
)

REM Check if virtual environment exists
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install dependencies if needed
if not exist .venv\installed (
    echo Installing dependencies...
    pip install -r requirements.txt
    echo. > .venv\installed
)

REM Start the application
echo.
echo ================================
echo Starting SweetSeek...
echo ================================
echo.
python app.py

pause

@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Start script for Windows: ensure .venv exists, install deps, run bot
echo 🚀 Starting ai-conditioner-discord bot locally...
echo 📍 Working directory: %cd%

REM Check if .env exists
if not exist .env (
    echo ❌ Error: .env file not found!
    echo Please create .env with your bot token:
    echo DISCORD_TOKEN=your_bot_token_here
    pause
    exit /b 1
)

set "VENV_DIR=.venv"
set "PYEXE=%VENV_DIR%\Scripts\python.exe"

REM Create venv if missing
if not exist "%PYEXE%" (
    echo 🧪 Creating virtual environment in %VENV_DIR% ...
    where py >nul 2>&1
    if %ERRORLEVEL%==0 (
        py -3 -m venv "%VENV_DIR%"
    ) else (
        python -m venv "%VENV_DIR%"
    )
)

if not exist "%PYEXE%" (
    echo ❌ Failed to create virtual environment (missing %PYEXE%).
    pause
    exit /b 1
)

echo 📦 Upgrading pip and wheel...
"%PYEXE%" -m pip install --upgrade pip wheel >nul

if exist requirements.txt (
    echo 📦 Installing dependencies from requirements.txt ...
    "%PYEXE%" -m pip install -r requirements.txt
)

echo 🤖 Starting bot...
"%PYEXE%" bot.py

echo 🛑 Bot stopped
pause
endlocal
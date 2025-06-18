@echo off

REM Simple start script for Windows local development/testing
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

REM Check if dependencies are installed
python -c "import discord" 2>nul
if errorlevel 1 (
    echo 📦 Installing dependencies...
    pip install -r requirements.txt
)

REM Run the bot
echo 🤖 Starting bot...
python bot.py

echo 🛑 Bot stopped
pause
#!/bin/bash

# Simple start script for local development/testing
echo "🚀 Starting ai-conditioner-discord bot locally..."
echo "📍 Working directory: $(pwd)"

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env with your bot token:"
    echo "DISCORD_TOKEN=your_bot_token_here"
    exit 1
fi

# Check if dependencies are installed
if ! python3 -c "import discord" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Run the bot
echo "🤖 Starting bot..."
python3 bot.py

echo "🛑 Bot stopped"
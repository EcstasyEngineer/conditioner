#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Starting ai-conditioner-discord bot locally..."
echo "📍 Working directory: $(pwd)"

if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env with your bot token:"
    echo "DISCORD_TOKEN=your_bot_token_here"
    exit 1
fi

VENV_DIR=".venv"
PYEXE="$VENV_DIR/bin/python3"

if [ ! -x "$PYEXE" ]; then
    echo "🧪 Creating virtual environment in $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
fi

if [ ! -x "$PYEXE" ]; then
    echo "❌ Failed to create virtual environment (missing $PYEXE)."
    exit 1
fi

echo "📦 Upgrading pip and wheel..."
"$PYEXE" -m pip install --upgrade pip wheel >/dev/null

if [ -f requirements.txt ]; then
    echo "📦 Installing dependencies from requirements.txt ..."
    "$PYEXE" -m pip install -r requirements.txt
fi

echo "🤖 Starting bot..."
"$PYEXE" bot.py

echo "🛑 Bot stopped"
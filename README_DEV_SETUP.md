# Development Setup Guide

## Running Two Bot Instances

This setup allows you to run both production and development bots simultaneously.

### 1. Create your dev bot on Discord
1. Go to https://discord.com/developers/applications
2. Create a new application for your dev bot
3. Get the bot token from the Bot section

### 2. Set up your .env.dev file
```bash
cp .env.dev.example .env.dev
# Edit .env.dev and add your dev bot token
```

### 3. Running the bots

**Development Bot (local testing):**
```bash
./start_dev.sh
# OR
python3 bot.py --dev
# OR  
DEV_MODE=1 python3 bot.py
```

**Production Bot (on server with systemctl):**
- Already running via systemctl
- Can be restarted with `!restart` command

### Visual Differences
- Dev bot will show `[DEV]` prefix in its status messages
- Dev bot loads from `.env.dev` file
- Production bot loads from `.env` file

### Tips
- Both bots can be in the same server
- Use different channels for testing to avoid confusion
- Dev bot status: `[DEV] Obey`, `[DEV] Submit`, etc.
- Prod bot status: `Obey`, `Submit`, etc.
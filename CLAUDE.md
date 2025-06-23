# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Discord bot designed for hypnosis audio session automation and server moderation, with a focus on gamification and engagement through various interactive systems.

## Key Commands

### Getting Started (First Time)
```bash
# 1. Set up environment variable
echo "DISCORD_TOKEN=your_bot_token_here" > .env

# 2. Run the bot (auto-installs dependencies)
./start.sh        # Linux/Mac
# OR
start.bat         # Windows
```

### Development/Testing
```bash
# Manual approach
pip install -r requirements.txt
python bot.py

# Script approach  
./start.sh        # Auto-checks dependencies
```

### Development Commands
- **No linting or test commands are currently configured**
- The bot relies on logging for debugging: check `logs/bot.log`
- Logs rotate at 5MB with 5 backups kept

## Architecture Overview

### Core Systems

1. **Bot Entry Point (`bot.py`)**
   - Initializes Discord bot with command prefix `!`
   - Loads cogs dynamically from `cogs/static/` and `cogs/dynamic/`
   - Implements rotating status messages and daily avatar changes
   - Handles centralized logging

2. **Configuration System (`core/config.py`)**
   - Thread-safe configuration management with auto-save (5-second delay)
   - Monitors external config changes every 2 seconds
   - Supports three config scopes:
     - Guild configs: `configs/guild_{guild_id}.json`
     - User configs: `configs/user_{user_id}.json`
     - Global config: `configs/global.json`
   - Atomic file writes prevent corruption

3. **Cog System Architecture**
   - **Static Cogs** (`cogs/static/`): Core functionality that doesn't change
     - `admin.py`: Superadmin/admin management system
     - `dev.py`: Developer utilities
   - **Dynamic Cogs** (`cogs/dynamic/`): Feature modules with per-guild configuration
     - `mantras.py`: Complex hypnotic mantra delivery system (most sophisticated feature)
     - `points.py`: User point tracking
     - `gacha.py`: Gambling/reward mechanics
     - `player.py`: Voice channel music playback
     - `logging.py`: Message logging
     - `setrole.py`: Role assignment
     - `counter.py`: Counting functionality

### Mantra System Deep Dive

The mantra system (`cogs/dynamic/mantras.py`) is the most complex feature:

- **User Enrollment**: Users specify pet name, dominant title, themes, and difficulty
- **Adaptive Delivery**: Adjusts frequency based on user engagement (30min-24hr intervals)
- **Point System**: 
  - Base points vary by difficulty
  - Speed bonuses for quick responses
  - Streak bonuses (up to 100 points for 20+ streak)
  - Public channel multiplier (2.5x)
  - Rapid fire mode for exceptional performance
- **Content Loading**: Mantras loaded from JSON files in `mantras/themes/`
- **Persistence**: User progress tracked in guild configs

### File Structure Conventions

```
configs/          # JSON configuration files (gitignored)
logs/            # Bot logs (gitignored)
mantras/themes/  # Mantra content JSON files
media/           # Bot avatars and gacha rewards
  spirals/       # Daily rotating bot avatars
  common/        # Gacha rarity tiers
  uncommon/
  rare/
  epic/
```

### Key Implementation Patterns

1. **Async/Await**: All Discord operations use proper async patterns
2. **Error Handling**: Try-except blocks with logging throughout
3. **Config Access**: Always use `self.bot.get_cog('ConfigManager')` for config operations
4. **Slash Commands**: Modern Discord interactions via `app_commands`
5. **Auto-save**: Config changes auto-save after 5 seconds to prevent data loss

### Common Development Tasks

When adding new features:
1. Create new cog in appropriate directory (`static` or `dynamic`)
2. Use the config system for persistence
3. Implement proper logging
4. Follow existing patterns for slash commands
5. Handle errors gracefully with user feedback

When modifying the mantra system:
1. Mantra content is in `mantras/themes/*.json`
2. Test enrollment, delivery, and point calculation
3. Consider the adaptive frequency system
4. Maintain backward compatibility with existing user configs

When creating GitHub issues:
1. Review `.github/LABELS.md` for the comprehensive label system
2. Apply appropriate labels for priority, effort, complexity, and components
3. Use multiple labels to help with triage and contributor matching
4. Follow the examples in the labels guide for consistent categorization

## Important Notes

- The bot uses a single global superadmin system
- Guild-specific admins have elevated permissions within their guild
- The mantra system is the primary engagement feature
- All user data is stored in JSON configs, not a database
- Media files follow a specific naming convention for the gacha system

## Development Workflow on Host Machine

When developing on the host machine (WSL/local), follow this process:

### Repository Structure

- **Production**: `~/ai-conditioner-discord/` (systemctl: `conditioner`)
- **Development**: `~/ai-conditioner-discord-dev/` (manual run only)

### Setting Up Dev Environment

1. **Development repository is already cloned** at `~/ai-conditioner-discord-dev/`
2. **Development token is configured** in `.env`

### Development Process

1. **Make code changes** in the development repository:
   ```bash
   cd ~/ai-conditioner-discord-dev/
   # Edit files as needed
   ```

2. **Test new features**:
   ```bash
   cd ~/ai-conditioner-discord-dev/
   ./start.sh
   # OR
   python3 bot.py
   ```
   
   The dev bot will:
   - Load from `.env` (separate token)
   - Show `[DEV]` prefix in status messages
   - Run alongside production bot without conflicts
   - Use separate configs/, logs/, and media/ directories

3. **Deploy to production** (choose based on changes):
   
   **For code-only changes:**
   - Commit and push changes from dev repo
   - Use `!update` and `!restart` in Discord (safe, no pip install)
   
   **For dependency changes or major updates:**
   - Commit and push changes from dev repo  
   - Run `./scripts/deploy.sh` (handles git pull + pip install + systemctl restart)

### AI Coder Instructions

When you (Claude Code) are working on the host machine:

1. **For Discord-Interactive Features** (commands, events, cogs):
   - Work in the development repository at `~/ai-conditioner-discord-dev/`
   - After implementing, start dev bot: `cd ~/ai-conditioner-discord-dev && ./start.sh`
   - Tell user: "Dev bot is starting. Test your feature in Discord now!"
   - After successful test, commit and push changes
   - Instruct user: "Use `!update` then `!restart` in Discord for code-only changes, or `./scripts/deploy.sh` if dependencies changed"

2. **For Non-Interactive Changes** (config updates, refactoring):
   - Test with standard Python syntax checks
   - No need to run the full bot

3. **Repository Management**:
   - Development work: `~/ai-conditioner-discord-dev/`
   - Production updates: Discord commands `!update` and `!restart`
   - Complete isolation prevents production conflicts

### Quick Reference
- **Getting Started**: `./start.sh` or `start.bat`
- **Dev Bot**: `cd ~/ai-conditioner-discord-dev && ./start.sh`
- **Stop Dev**: `Ctrl+C`
- **Deploy (Code Only)**: `!update` → `!restart` (in Discord)
- **Deploy (Full)**: `./scripts/deploy.sh` (for dependency changes)
- **Check Prod Logs**: `tail -f ~/ai-conditioner-discord/logs/bot.log`
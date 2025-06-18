# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Discord bot designed for hypnosis audio session automation and server moderation, with a focus on gamification and engagement through various interactive systems.

## Key Commands

### Running the Bot
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variable
echo "DISCORD_TOKEN=your_bot_token_here" > .env

# Run the bot
python bot.py
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

## Important Notes

- The bot uses a single global superadmin system
- Guild-specific admins have elevated permissions within their guild
- The mantra system is the primary engagement feature
- All user data is stored in JSON configs, not a database
- Media files follow a specific naming convention for the gacha system

## Development Workflow on Host Machine

When developing on the host machine (WSL/local), follow this process:

### Setting Up Dev Environment

1. **First Time Setup**:
   ```bash
   # Copy the dev environment template
   cp .env.dev.example .env.dev
   # Edit .env.dev and add your development bot token
   ```

2. **Testing New Features**:
   When implementing features that require user interaction testing:
   ```bash
   # Start the dev bot
   ./start_dev.sh
   # OR
   python bot.py --dev
   ```
   
   The dev bot will:
   - Load from `.env.dev` instead of `.env`
   - Show `[DEV]` prefix in status messages
   - Run alongside the production bot without conflicts

3. **Development Process**:
   - Make code changes
   - Run dev bot with `./start_dev.sh`
   - Test in Discord (dev bot can be in same server as prod)
   - Stop dev bot with Ctrl+C
   - Commit and push changes
   - Use `!update` and `!restart` in Discord to update production

### AI Coder Instructions

When you (Claude Code) are working on the host machine:

1. **For Discord-Interactive Features** (commands, events, cogs):
   ```bash
   # After implementing the feature, automatically start the dev bot
   ./start_dev.sh
   ```
   - Tell the user: "Dev bot is starting. Test your feature in Discord now!"
   - The dev bot will show `[DEV]` prefix in status
   - After user confirms testing is complete, remind them to stop with Ctrl+C

2. **For Non-Interactive Changes** (config updates, refactoring):
   - Test with standard Python syntax checks
   - No need to run the full bot

3. **Automated Testing Workflow**:
   When implementing a new Discord command or feature:
   - Complete the implementation
   - Start dev bot with `./start_dev.sh`
   - Provide clear testing instructions (e.g., "Try the new !command in Discord")
   - Wait for user feedback
   - After successful test, commit and push
   - Instruct user: "Run `!update` then `!restart` in Discord to deploy"

4. **Future Self-Modification Goals**:
   - The bot architecture supports dynamic cog loading/unloading
   - Commands like `!reload` already exist for hot-reloading cogs
   - Consider implementing:
     - `!edit <file> <content>` - Edit bot files from Discord
     - `!commit <message>` - Commit changes from Discord
     - `!deploy` - Combined update + restart
   - Security consideration: Limit self-modification to superadmin only

### Quick Reference
- **Dev Bot**: `./start_dev.sh` (uses `.env.dev`)
- **Stop Dev**: `Ctrl+C`
- **Deploy**: `!update` → `!restart` (in Discord)
- **Check Prod Logs**: `tail -f logs/bot.log`
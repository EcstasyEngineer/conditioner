# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

**AI Conditioner Discord Bot** - A sophisticated Discord bot for hypnotic conditioning through gamified mantra delivery and community engagement mechanics. Implements a V2 architecture with prediction error learning algorithms for adaptive user engagement.

- **Language**: Python 3.12+
- **Framework**: discord.py
- **Architecture**: Modular cog system with service layer separation
- **Data Storage**: File-based JSON configuration with intelligent buffering

## Common Development Commands

### Running the Bot
```bash
# The bot runs as a systemd service - restart with:
sudo systemctl restart conditioner

# View service status
sudo systemctl status conditioner

# View logs
sudo journalctl -u conditioner -f

# For development testing (not production)
./start.sh  # Creates venv, installs deps, runs bot locally
```

### Development Workflow
```bash
# Hot-reload a cog without restarting bot (run in Discord)
!reload mantras    # Reload specific cog
!reload            # Reload all dynamic cogs

# Update from git (run in Discord)
!update            # Pulls latest changes

# Sync Discord commands (run in Discord)
!sync              # Sync globally
!sync guild        # Sync to current guild only

# Restart bot (run in Discord - triggers systemd restart)
!restart           # Graceful shutdown, systemd auto-restarts
!kys               # Alias for restart
```

### Testing & Debugging
```bash
# Test error logging system (run in Discord)
!errorlog setchannel #channel  # Configure error channel
!testerror                      # Trigger test error

# View logs
tail -f logs/bot.log
tail -f logs/encounters/user_*.jsonl
```

## High-Level Architecture

### Core Design Pattern: Config-Centric Architecture

The bot uses a sophisticated file-based configuration system (`core/config.py`) that serves as the central state manager:

```python
# Access patterns available everywhere via bot.config:
value = bot.config.get(ctx, "key")           # Per-guild setting
bot.config.set(ctx, "key", value)            # Set guild config

user_val = bot.config.get_user(ctx, "key")   # Per-user setting
bot.config.set_user(ctx, "key", value)       # Set user config

global_val = bot.config.get_global("key")    # Global setting
bot.config.set_global("key", value)          # Set global
```

**Key Features**:
- Three-tier scoping: global → guild → user
- 5-second write buffering to batch rapid changes
- External change detection with auto-reload
- Thread-safe with conflict resolution

### Service Layer Architecture

The codebase follows a clean separation of concerns:

```
Discord Layer (cogs/)           → Handles Discord interactions
    ↓ calls
Service Layer (utils/*_service) → Business logic, state management
    ↓ uses
Utility Layer (utils/)          → Algorithms, data structures
```

**Example**: Mantra System
- `cogs/dynamic/mantras.py` - Discord UI, modals, views
- `utils/mantra_service.py` - Enrollment, delivery, response handling
- `utils/mantra_scheduler.py` - Scheduling algorithm, learning
- `utils/mantras.py` - Mantra selection, matching logic

### Cog System (Hot-Reloadable Modules)

**Static Cogs** (always loaded, in `cogs/static/`):
- `admin.py` - Superadmin/admin management
- `dev.py` - Developer tools (!reload, !update, etc.)
- `error_handler.py` - Error logging configuration

**Dynamic Cogs** (hot-reloadable, in `cogs/dynamic/`):
- `mantras.py` - Core mantra system (1,041 lines)
- `gacha.py` - Reward mechanics
- `points.py` - Points management
- `counter.py` - Counting game
- `player.py` - Music player
- `setrole.py` - Role management

**Standard Cog Template**:
```python
from discord.ext import commands

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger  # Always use central logger

    @commands.command()
    async def my_command(self, ctx, *, args):
        # Access config
        setting = self.bot.config.get(ctx, "key", "default")

        # Check permissions
        if not is_admin(ctx):
            return await ctx.send("Not authorized")

        # Implementation
        await ctx.send("Response")

async def setup(bot):
    await bot.add_cog(MyCog(bot))
```

### Mantra V2 System Architecture

The mantra system uses a **two-timestamp state machine** with **prediction error learning**:

**State Machine** (no explicit state variable):
```python
config = {
    "next_delivery": "2025-11-11T14:00:00",  # When to send/timeout
    "sent": None,  # When current was sent (None = waiting)
    "consecutive_failures": 0
}
```

**Learning Algorithm** (Elo-style prediction error):
```python
# 24-hour probability distribution
distribution = [0.5] * 24  # One bucket per hour
learning_rate = 0.20

# Update on each encounter
actual = 1.0 if success else 0.0
expected = distribution[hour]
error = actual - expected
distribution[hour] += learning_rate * error
```

**Scheduling** (probability mass integration):
- Walks forward through time accumulating probability
- Schedules when accumulated mass reaches target
- Target mass = 1.0 / frequency_per_day

### Permission System

Hierarchical admin system with helper utilities:

```python
from core.utils import is_superadmin, is_admin, get_superadmins

# Check permissions
if is_superadmin(ctx):
    # Global bot admin

if is_admin(ctx):
    # Guild admin OR superadmin
```

**Levels**:
1. **Superadmin** (global): Bot-wide control
2. **Guild Admin** (per-server): Server-specific control
3. **Discord Admin**: Auto-qualifies as guild admin

## Critical Implementation Details

### Config Write Buffering
The config system buffers writes for 5 seconds. If you need immediate persistence:
```python
bot.config.flush()  # Force immediate write
```

### Encounter Logging Format
User encounters are logged to `logs/encounters/user_{user_id}.jsonl` as JSONL:
```json
{"timestamp": "2025-11-11T14:30:00", "mantra": "...", "completed": true, "response_time": 45, "points_earned": 25}
```

### Media File Organization
Gacha rewards organized by tier:
- `media/common/` - 40% chance
- `media/uncommon/` - 30% chance
- `media/rare/` - 20% chance
- `media/epic/` - 10% chance

### Error Handling
Errors are automatically logged to Discord if configured:
```python
from core.error_handler import log_error_to_discord
await log_error_to_discord(bot, error, context)
```
Rate limited to one error per 5 minutes to prevent spam.

### Mantra Theme Structure
Themes in `mantras/*.json`:
```json
{
  "theme": "obedience",
  "mantras": [
    {
      "text": "I {verb} {controller}",
      "difficulty": "basic",
      "base_points": 10
    }
  ]
}
```
Placeholders: `{subject}`, `{controller}` are replaced per user config.

## Testing Considerations

### Running Tests
```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_utils_superadmin.py -v

# Run with coverage
python -m pytest --cov
```

### Mantra System Testing
- Test scripts in `scripts/test_*.py` for algorithm validation
- Use `scripts/analyze_*.py` for data analysis
- Historical encounter data can be analyzed from JSONL logs

### Config System Testing
- External changes (manual JSON edits) are auto-detected
- Test with rapid config changes to verify buffering
- Verify thread safety with concurrent operations

### Cog Hot-Reload Testing
```python
# In your cog's setup function
async def setup(bot):
    # Clean up any previous instance
    await bot.add_cog(YourCog(bot))
```

## Common Development Patterns

### Background Tasks
```python
from discord.ext import tasks

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.my_task.start()

    @tasks.loop(seconds=10)
    async def my_task(self):
        # Runs every 10 seconds
        pass

    @my_task.before_loop
    async def before_my_task(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.my_task.cancel()
```

### Command Decorators
```python
from core.utils import is_superadmin, is_admin

@commands.command()
@commands.check(is_admin)  # Permission check via decorator
async def admin_command(self, ctx):
    pass
```

### Config Lists Management
```python
# Lists require get → modify → set pattern
admins = self.bot.config.get(ctx, "admins", [])
admins.append(user_id)
self.bot.config.set(ctx, "admins", admins)
```

### Event Listeners
```python
@commands.Cog.listener()
async def on_message(self, message):
    if message.author.bot:
        return
    # Handle non-command messages
```

## Active Development Areas

Based on git status and recent commits:

1. **Mantra V2 Implementation** (`utils/mantra_scheduler.py`, `utils/mantra_service.py`)
   - Prediction error learning algorithm
   - Two-timestamp state machine
   - Probability distribution scheduling

2. **Response Messages System** (`utils/response_messages.py`)
   - Dynamic, contextual responses
   - Template-based message generation

3. **Error Logging Upgrade** (Issue #40)
   - Per-guild error channels
   - Full coverage error tracking

## Performance Considerations

- **Config writes** are buffered (5s) - batch operations when possible
- **Encounter logs** append-only JSONL - efficient for writes
- **Cog reloads** preserve bot instance - use for rapid iteration
- **Learning algorithm** uses only 24 floats per user - minimal memory
- **Status loop** runs every 5 minutes - adjust `change_status()` interval if needed

## Git Workflow

This repository belongs to **EcstasyEngineer**. The GitHub CLI is configured for this account. When creating PRs or working with issues:

```bash
# Verify correct account
gh auth status  # Should show EcstasyEngineer as active

# Create pull requests
gh pr create --title "Title" --body "Description"

# List issues
gh issue list --state open
```

## Permission System

Use `@commands.check(is_superadmin)` for bot-wide operations (reload, restart, global config) and `@commands.check(is_admin)` for guild-specific features (error channels, voice player, points) - superadmins automatically inherit all admin privileges.
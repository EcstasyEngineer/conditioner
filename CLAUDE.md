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
- **Content Loading**: Mantras loaded from JSON files in `mantras/`
- **Persistence**: User progress tracked in guild configs

### File Structure Conventions

```
configs/         # JSON configuration files (gitignored)
logs/            # Bot logs (gitignored)
mantras/         # Mantra content JSON files
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
3. **Config Access**: Always use `self.bot.config` for config operations with proper scope methods:
   - Guild configs: `self.bot.config.get(ctx, key)`, `self.bot.config.set(ctx, key, value)`
   - User configs: `self.bot.config.get_user(user, key)`, `self.bot.config.set_user(user, key, value)`
   - Global configs: `self.bot.config.get_global(key)`, `self.bot.config.set_global(key, value)`
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
1. Mantra content is in `mantras/*.json`
2. Test enrollment, delivery, and point calculation
3. Consider the adaptive frequency system
4. Maintain backward compatibility with existing user configs

When creating GitHub issues:
1. Review `.github/LABELS.md` for the comprehensive label system
2. Apply appropriate labels for priority, effort, complexity, and components
3. Use multiple labels to help with triage and contributor matching
4. Follow the examples in the labels guide for consistent categorization

## Configuration System Guide

The bot uses a centralized, thread-safe configuration system with three distinct scopes:

### Configuration Scopes

1. **Global Config** (`configs/global.json`)
   - Bot-wide settings (superadmin, bot-level toggles)
   - **Methods**: `get_global(key, default=None)`, `set_global(key, value)`
   - **Example**: `superadmin = self.bot.config.get_global("superadmin")`

2. **Guild Config** (`configs/{guild_id}.json`)
   - Per-server settings (guild admins, channel configurations)
   - **Methods**: `get(ctx, key, default=None)`, `set(ctx, key, value)`
   - **Example**: `admins = self.bot.config.get(ctx, "admins", [])`

3. **User Config** (`configs/user_{user_id}.json`)
   - Per-user settings (points, preferences, mantra configs)
   - **Methods**: `get_user(user, key, default=None)`, `set_user(user, key, value)`
   - **Example**: `points = self.bot.config.get_user(user, 'points', 0)`

### Configuration Usage Patterns

#### Basic Access with Defaults
```python
# User settings
points = self.bot.config.get_user(user, 'points', 0)
auto_claim = self.bot.config.get_user(user, 'auto_claim_gacha', False)

# Guild settings  
admins = self.bot.config.get(ctx, "admins", [])
channel = self.bot.config.get(ctx, 'mantra_public_channel', None)

# Global settings
superadmin = self.bot.config.get_global("superadmin")
```

#### Complex Configuration Objects
```python
# Load complex config with safe defaults
def get_user_mantra_config(self, user):
    default_config = {
        "enrolled": False,
        "themes": [],
        "subject": "puppet",
        "total_points_earned": 0
    }
    
    config = self.bot.config.get_user(user, 'mantra_system', None)
    if config is None or not isinstance(config, dict):
        config = default_config.copy()
    else:
        # Safe merge - only add missing keys
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
    
    return config

# Modify and save
config = self.get_user_mantra_config(user)
config["enrolled"] = True
config["themes"] = ["acceptance"]
self.bot.config.set_user(user, 'mantra_system', config)
```

#### Error Handling Best Practices
```python
# Always provide sensible defaults
config = self.bot.config.get_user(user, 'settings', {})

# Type checking for complex objects
if not isinstance(config, dict):
    config = {}

# Safe key access
points = config.get('points', 0)
```

### System Features

- **Thread-safe**: Automatic save buffering (5-second delay)
- **Atomic writes**: Prevents corruption during saves
- **External monitoring**: Detects manual file changes every 2 seconds
- **Lazy initialization**: Creates defaults on first access
- **Type safety**: Built-in validation support

### Configuration Guidelines

1. **Use appropriate scope methods** - Never use `get(None, ...)` for global configs
2. **Always provide defaults** when calling get methods
3. **Use type checking** for complex configuration objects
4. **Implement migration logic** for configuration format changes
5. **Batch updates** for complex objects (load → modify → save)
6. **Handle missing keys gracefully** with fallback values

## Utils Architecture Guidelines

When cogs grow beyond ~1000 lines of code, consider extracting helper functions to utils modules to maintain readability and promote code reuse.

### When to Extract to Utils

**Extract when functions are:**
- Pure logic with no Discord-specific dependencies
- Reusable across multiple cogs
- Complex data processing or calculations
- File I/O operations (JSONL, media files, etc.)
- Statistical analysis or report generation
- Generic delivery mechanisms

**Keep in cogs when functions:**
- Handle Discord interactions directly (commands, events)
- Contain business logic specific to that cog's domain
- Orchestrate high-level workflows
- Validate user input and permissions
- Build Discord-specific responses (embeds, views)

### Utils File Organization

```
utils/
├── __init__.py              # Package initialization
├── points.py               # Cross-cog point management
├── encounters.py           # JSONL logging and streak tracking
├── delivery.py             # DM delivery and media handling
├── [domain]_core.py        # Domain-specific pure logic
└── [domain]_admin.py       # Admin report generation
```

### Utils Design Principles

1. **Domain Separation**: Group related functionality together
2. **No Discord Dependencies**: Utils should work without discord.py imports
3. **Pure Functions**: Prefer stateless functions over classes when possible
4. **Clear Interfaces**: Well-documented parameters and return types
5. **Error Handling**: Graceful degradation with meaningful error messages
6. **Testability**: Easy to unit test in isolation

### Refactoring Guidelines

**Target Cog Size After Refactoring:**
- Simple cogs: 200-400 lines
- Complex cogs: 400-700 lines  
- If still >700 lines, consider splitting into multiple cogs

**What Should Remain in Cogs:**
- Command definitions and decorators
- Discord interaction handling
- High-level business logic flow
- Configuration validation
- User permission checks
- Response building and formatting

**Refactoring Process:**
1. Identify pure logic functions (no `self.bot`, `interaction`, `ctx` dependencies)
2. Group related functions by domain
3. Extract to appropriate utils modules
4. Update cog imports and function calls
5. Ensure cog still tells a clear story of what it does
6. Test that Discord functionality remains intact

**Example of Good Balance:**
```python
# Cog retains high-level flow and Discord integration
@app_commands.command(name="enroll")
async def enroll_user(self, interaction, subject: str):
    # Business logic and validation stays here
    if self.is_already_enrolled(interaction.user):
        await interaction.response.send_message("Already enrolled!")
        return
    
    # Delegate pure logic to utils
    config = mantras.create_enrollment_config(subject, themes=["acceptance"])
    mantras.schedule_first_encounter(config)
    
    # Discord response building stays here
    embed = self.build_enrollment_embed(config)
    await interaction.response.send_message(embed=embed)
```

This approach maintains readability while reducing complexity and promoting reuse.

## UI Components Guidelines (`utils/ui.py`)

The `utils/ui.py` file should contain **ONLY** Discord UI components (Views, Buttons, Select Menus, Modals) that handle user interaction. These components should be "dumb" views that display information and capture user input, NOT process business logic.

### What SHOULD be in `ui.py`:

1. **Discord UI Components**:
   - `discord.ui.View` subclasses
   - `discord.ui.Button` implementations
   - `discord.ui.Select` menus
   - `discord.ui.Modal` forms
   - Embed creation helper functions

2. **Pure Display Logic**:
   - Formatting data for display
   - Creating embed layouts
   - Setting button labels and styles
   - Managing view timeouts for UI cleanup

3. **User Input Handling**:
   - Capturing button clicks
   - Processing select menu choices
   - Validating modal form inputs
   - Sending responses to interactions

### What should NOT be in `ui.py`:

1. **Business Logic** ❌:
   - Config loading/saving
   - Points calculations
   - State transitions
   - Scheduling operations
   - Data persistence

2. **Complex Decision Making** ❌:
   - Determining next actions based on business rules
   - Calculating values or scores
   - Managing user state
   - Adjusting system parameters

3. **External System Calls** ❌:
   - Database/file operations
   - API calls
   - Background task management
   - Cross-cog communication

### Example of GOOD UI component:

```python
class ConfirmationView(discord.ui.View):
    def __init__(self, *, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.value = None
    
    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        await interaction.response.send_message("Confirmed!", ephemeral=True)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await interaction.response.send_message("Cancelled!", ephemeral=True)
```

### Example of BAD UI component:

```python
class BadView(discord.ui.View):
    async def on_timeout(self):
        # ❌ BAD: Business logic in UI
        config = load_user_config(self.user)
        config["points"] += calculate_timeout_penalty()
        config["streak"] = 0
        save_user_config(self.user, config)
        
        # ❌ BAD: Complex decision making
        if config["failures"] > 5:
            await disable_user_features(self.user)
        
        # ❌ BAD: Scheduling operations
        schedule_next_event(self.user, delay=3600)
```

### Proper Architecture Pattern:

```python
# In ui.py - Just the view
class MantraTimeoutView(discord.ui.View):
    def __init__(self, callback_handler, *, timeout: float = 1800):
        super().__init__(timeout=timeout)
        self.callback_handler = callback_handler
    
    async def on_timeout(self):
        # ✅ GOOD: Delegate to handler
        if self.callback_handler:
            result = await self.callback_handler.handle_timeout()
            if result.embed and self._message:
                await self._message.edit(embed=result.embed, view=result.next_view)

# In cog or service - Business logic
class MantraService:
    async def handle_timeout(self) -> TimeoutResult:
        # All business logic here
        config = self.load_config()
        self.adjust_parameters(config)
        self.save_config(config)
        
        return TimeoutResult(
            embed=self.create_timeout_embed(),
            next_view=self.determine_next_view()
        )
```

### Key Principle: Separation of Concerns

UI components should be reusable across different features without modification. They should not contain feature-specific logic or dependencies on specific data structures. Think of them as "templates" that can display any data passed to them and return user selections without knowing what those selections mean.

## Important Notes

- The bot uses a single global superadmin system
- Guild-specific admins have elevated permissions within their guild
- The mantra system is the primary engagement feature
- All user data is stored in JSON configs, not a database
- Media files follow a specific naming convention for the gacha system

## Language Guidelines for Hypnotic/Conditioning Features

When developing new features or modifying existing ones, use language that emphasizes mental programming and conditioning rather than gamification:

### Core Language Transformations
- **Points/Rewards** → "Compliance points", "Integration points", "Conditioning metrics"
- **Challenges/Games** → "Programming sequences", "Conditioning protocols", "Neural directives"
- **Success/Failure** → "Integration successful", "Processing confirmed", "Sequence timed out"
- **User Actions** → "Process", "Absorb", "Integrate" rather than "Complete", "Win", "Earn"

### Specific Examples
- "Mantra Challenge" → "Programming Sequence"
- "You earned X points!" → "Integration successful: X compliance points absorbed"
- "Good job!" → "Processing confirmed" or "Neural pathways responding well"
- "Streak bonus" → "Synchronization level" or "Conditioning amplified"
- "Repeat this mantra" → "Process this directive"

### Status/Progress Language
- "Deep Trance" → "Full Synchronization"
- "In the Zone" → "Conditioning Amplified"
- "Training enrolled" → "Neural pathways initialized"
- "Settings updated" → "Programming parameters adjusted"

### Avoid Overly Clinical/Drone Language
- Keep "Pet Name" instead of "Unit Identifier" (dronification is a specific theme, not the whole bot)
- Balance technical terms with warm conditioning language
- Maintain consensual undertones while emphasizing mental programming

### Automation/Bot Persona Guidelines
The bot should present as an unthinking conditioning automaton, not a caring entity:

**Appropriate Automation Language:**
- "Protocol adjustment required" → Not "Would you like to..."
- "Select response" → Not "What would you prefer?"
- "Dysfunction detected" → Not "I'm concerned about..."
- "Neural pathway malfunction" → Not "You seem to be struggling"
- "System recalibration initiated" → Not "Let's try again"

**Emoji Selection for Automation Theme:**
- ✅ **Use:** ⚠️ 🔄 ⏸️ ⏱️ 🌀 📊 ⚙️ 🧠 ◈ (clinical, mechanical, hypnotic)
- ❌ **Avoid:** 🤔 😊 💭 🙂 😢 (implies thinking, emotion, or caring)
- ⚠️ **Caution:** 😴 💤 (too soft - prefer ⏸️ "suspend" over "sleep")

**Error/Failure Language:**
- "Integration failure detected" → Not "That didn't work"
- "Consecutive malfunction threshold reached" → Not "You're having trouble"
- "Protocol suspension required" → Not "Maybe you need a break"

This language maintains the immersive experience of interacting with a conditioning system rather than a helpful assistant.

### Implementation Note
This language shift creates an immersive hypnotic experience that aligns with the bot's true purpose of mental conditioning through repetitive mantra work and behavioral reinforcement.

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
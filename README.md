# AI Conditioner Discord Bot

A sophisticated Discord bot designed for hypnotic conditioning through gamified mantra delivery and community engagement mechanics.

## 🚀 Quick Start

**Copy-paste these commands** (replace `your_bot_token_here` with your actual Discord bot token):

```bash
git clone https://github.com/EcstasyEngineer/ai-conditioner-discord.git
cd ai-conditioner-discord
echo "DISCORD_TOKEN=your_bot_token_here" > .env
./start.sh
```

The start script will:
- Create a virtual environment automatically
- Install all dependencies
- Start the bot

**First-time setup:**
1. Invite bot to your Discord server
2. Run `!claimsuper` in any channel to become a superadmin

That's it! Your bot is now running.

## ✨ Key Features

- **🌀 Hypnotic Mantra System** - Personalized mantras with adaptive frequency and 6 active themes
- **🎮 Points & Rewards** - Point system with gacha spins and streak bonuses
- **🎲 Counter Game** - Community counting game with hidden conditioning triggers
- **⚙️ Smart Configuration** - Per-server, per-user, and global settings with automatic persistence
- **🛡️ Admin System** - Hierarchical permissions (superadmin + guild admins)
- **🎵 Music Player** - Voice channel music playback
- **🛠️ Developer Friendly** - Hot-reload cogs, built-in REPL, comprehensive logging

## 📋 Available Commands

**Mantra System:**
- `/mantra enroll` - Start receiving personalized mantras
- `/mantra status` - Check your progress and statistics
- `/mantra settings` - Update your preferences
- `/mantra themes` - Manage your active themes

**Points & Rewards:**
- `/points balance` - Check your point balance
- `/gacha spin` - Spend points on random rewards

**Server Management:**
- `!help` - Show all commands
- `!setadmin @user` - Grant admin privileges (superadmin only)
- `!setchannel mantra_public #channel` - Set public mantra channel

**Music Player:**
- `!play <song>` - Play from YouTube/Spotify
- `!queue` - Show music queue
- `!skip` / `!pause` / `!resume`

## 🏗️ Development & Extension

### Creating Custom Cogs
Add new features by creating cogs in `cogs/dynamic/`:

```python
# cogs/dynamic/my_feature.py
from discord.ext import commands

class MyFeature(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def my_command(self, ctx):
        # Access config system
        setting = self.bot.config.get(ctx, "my_setting", "default")
        await ctx.send(f"Setting: {setting}")

async def setup(bot):
    await bot.add_cog(MyFeature(bot))
```

Load with `!load my_feature` - no restart needed!

### Config Quick Reference
AI Conditioner's config helper is available as `self.bot.config` in every cog:

```python
# Per-guild (default scope)
prefix = self.bot.config.get(ctx, "prefix", "!")
self.bot.config.set(ctx, "prefix", "?")

# Per-user
timezone = self.bot.config.get_user(ctx, "timezone", "UTC")
self.bot.config.set_user(ctx, "timezone", "UTC")

# Global (bot-wide)
superadmins = self.bot.config.get_global("superadmins", [])
self.bot.config.set_global("maintenance_mode", True)
```

Lists are just Python lists—get, mutate, then `set` the updated list. Call `self.bot.config.flush()` before shutdown if you need to force writes immediately.

For detailed documentation, see `configs/README.md` for config usage patterns.

### Administrative Commands
- `!claimsuper` - Become a bot superadmin (first time only)
- `!addsuperadmin @user` - Promote an additional bot superadmin
- `!load <cog>` / `!unload <cog>` - Manage features
- `!reload <cog>` - Hot-reload code changes
- `!update` - Pull latest changes from git
- `!kys` - Graceful shutdown (useful with systemd)

### Error Logging (optional)
- `!seterrorlog #channel` — Set the global error log channel for exceptions
- `!testerror` — Trigger a test exception to verify logging

Notes:
- Errors are rate-limited to avoid spam. Per-guild logging and broader coverage are planned in the upgrade issue.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any changes or improvements.

## License

This project is licensed under a CC0-compatible [License](LICENSE.md).

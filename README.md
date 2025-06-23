# AI Conditioner Discord Bot

A sophisticated Discord bot designed for hypnotic conditioning through gamified mantra delivery and community engagement mechanics.

## Features

### 🌀 Hypnotic Mantra System
- Personalized mantra delivery based on themes and difficulty levels
- Adaptive frequency adjustment (responds to user engagement)
- Point-based reward system with speed and streak bonuses
- Public channel multipliers to encourage community participation
- 6 active themes: acceptance, addiction, bimbo, brainwashing, obedience, suggestibility

### 🎮 Gamification Systems
- **Points System**: Earn points through mantra completion and activities
- **Gacha Rewards**: Spin for random media rewards using points
- **Counter Game**: Simple counting game with hidden triggers
- **Streak Tracking**: Consecutive completion bonuses

### 🛡️ Server Management
- Hierarchical admin system (superadmin + guild admins)
- Per-guild configuration
- Message logging capabilities
- Custom role assignment

### 🎵 Additional Features
- Music player for voice channels
- Daily rotating bot avatars
- Auto-save configuration system

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/EcstasyEngineer/ai-conditioner-discord.git
   cd ai-conditioner-discord
   ```

2. **Set up bot token**
   ```bash
   echo "DISCORD_TOKEN=your_bot_token_here" > .env
   ```

3. **Run the bot**
   ```bash
   ./start.sh        # Linux/Mac (auto-installs dependencies)
   # OR
   start.bat         # Windows
   # OR manually:
   pip install -r requirements.txt
   python bot.py
   ```

## Usage

### For Users
- `/mantra enroll` - Start receiving personalized mantras
- `/mantra status` - Check your progress and statistics
- `/mantra settings` - Update your preferences
- `/mantra themes` - Manage your active themes
- `/points balance` - Check your point balance
- `/gacha spin` - Spend points on random rewards

### For Admins
- `!setadmin @user` - Grant admin privileges (superadmin only)
- `!setchannel mantra_public #channel` - Set public mantra channel
- Check `!help` for all admin commands

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Reporting Issues
When creating issues, please:
1. Review our label system in `.github/LABELS.md`
2. Apply appropriate labels for priority, effort, complexity, and affected components
3. Provide clear reproduction steps for bugs
4. Include relevant logs or error messages

### Submitting Pull Requests
1. Link your PR to the relevant issue
2. Copy labels from the linked issue to your PR
3. Update labels if the scope changes during development
4. Follow existing code patterns and conventions

## License

This project is licensed under a CC0-compatible [License](LICENSE.md).
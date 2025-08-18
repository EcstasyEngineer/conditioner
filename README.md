# AI Conditioner Discord Bot

A modular Discord bot for programmable prompts, community mini‑games, and rich logging—designed to be fun, configurable, and safe for communities.

## What it does

- 🧠 Prompt delivery system ("mantras")
   - Theme‑based content with difficulty and points values
   - Adaptive frequency tuned by engagement (faster when active; slows when missed)
   - Online‑only gating with consecutive presence checks to avoid pinging offline folks
   - Private DM delivery by default; optional public posts with bonus multipliers
   - Per‑user stats, recent history, and configurable subjects/controllers

- 🎮 Games and rewards
   - Counting game across multiple channels per guild with registration controls
   - Points currency plus a second “token” currency for consumables/unlocks
   - Optional gacha/reward hooks for media drops

- 📋 Logging and safety
   - Per‑guild log channel setting: `!setlogchannel #log`, `!showlogchannel`
   - Central error routing with rate limiting, per‑guild routing when context is known, and global fallback
   - Admin gating: superadmins (global) + guild admins + configurable admin lists

- 🔊 Audio pipeline (roadmap)
   - Text‑to‑speech generation and caching for prompt playback in voice
   - Lightweight voice session management; opt‑in, per‑guild controls

## Architecture at a glance

- core/ (infrastructure)
   - config.py: JSON config (guild/user/global) with debounced writes and external reload
   - error_handler.py: error embeds → channel with rate limiting; per‑guild/global routing
   - permissions.py: shared admin checks for prefix and slash commands
   - media_migration.py: migration helpers at startup

- features/ (domain helpers)
   - points.py: points + tokens currency APIs
   - encounters.py: append‑only JSONL logs and stats for prompt interactions
   - mantras.py: façade to existing mantra utilities while we migrate incrementally

- cogs/
   - dynamic/: user‑facing features (mantras, counter, logging, points, gacha, etc.)
   - static/: admin utilities and global config helpers

## Setup

1) Create and configure the bot
- Create a Discord application and bot, then invite it with the necessary scopes and permissions.
- Put your token in a `.env` file as `DISCORD_TOKEN=...`.

2) Install and run
- Windows: run `start.bat`
- Linux/Mac: run `./start.sh`
- Or manually install with `pip install -r requirements.txt` and run `python bot.py`.

3) First‑time configuration
- Set a global error channel (optional but recommended): `!seterrorlog #errors`
- In each guild, set a log channel: `!setlogchannel #log` (admins only)
- Use slash commands or prefix commands to configure features (see below).

## Commands (high level)

- Prompt delivery (mantras)
   - Manage enrollment, themes, frequency, and see status via slash commands in the Mantra cog (varies per deployment).
   - Admins can set a public posting channel for extra rewards or keep delivery in DMs.

- Counting game
   - Register/unregister channels (admins): `/counting_register #channel`, `/counting_unregister #channel`, `/counting_list`
   - Game runs per‑channel with last‑value tracking and simple validation.

- Points and tokens
   - Check and award with bot‑specific commands (e.g., `/points`, admin grant commands where applicable).
   - Use tokens for consumables/unlocks once configured in your server’s flow.

- Logging
   - `!setlogchannel #log`, `!showlogchannel`
   - Global error channel (superadmins): `!seterrorlog #errors`

## Logging behavior

- Error routing tries, in order: explicit channel_id (if provided by the caller) → the guild’s configured log channel (or a channel named `#log`) → global error channel.
- Duplicate errors are rate‑limited (default 5 minutes per unique error signature).
- A test command exists (`!throw`, superadmin) to generate an intentional error for validation.

## Development notes

- Keep infrastructure in `core/`; feature logic in `features/`; user‑facing commands live in `cogs/`.
- The config service batches writes and hot‑reloads when files are edited externally.
- We maintain a gradual migration path—`features/mantras.py` re‑exports existing utilities to avoid large refactors in one step.

## Roadmap

- Prompt delivery modes
   - online_only | scheduled windows | always, with quiet hours and no‑timeout modes
   - per‑user windows and per‑guild defaults

- Content management
   - Unified prompt catalog with tags, difficulty, points, import/migration helpers
   - User submissions with approval flow and points gating

- Progression and roles
   - Points‑gated unlocks and optional role grants
   - “Dominant/Controller” assignment with audit log

- Audio delivery
   - Cache‑on‑demand TTS, small voice controller, per‑guild rate limiting

- Ops & reliability
   - Per‑guild error routing (complete for command errors), smarter guessing for events/tasks
   - Challenge registry for in‑flight prompts to survive restarts

## License

This project is released under a CC0‑compatible [License](LICENSE.md).
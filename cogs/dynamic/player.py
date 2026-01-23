"""
Ambient audio player - plays shuffled playlist in a voice channel with listening rewards.

State Machine:
    IDLE → user joins → WELCOME (if configured) or PLAYING
    WELCOME → track ends → PLAYING (random track)
    PLAYING → track ends → PLAYING (next random track)
    Any state → channel empty → IDLE

Zombie Recovery:
    Discord drops idle connections after 3-5 hours (1006 close code).
    Health check loop detects zombies and recovers with 45s cooldown.
    Keepalive packets prevent Discord from considering connection idle.
"""

import asyncio
import random
from enum import Enum, auto
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands, tasks

from core.utils import is_admin
from utils.points import add_points

# === Configuration ===
POINTS_PER_MINUTE = 5
VOICE_RECONNECT_COOLDOWN = 45.0
HEALTH_CHECK_INTERVAL = 30
KEEPALIVE_INTERVAL = 60
KEEPALIVE_ENABLED = True

OPUS_SILENCE = b'\xf8\xff\xfe'



class PlayerState(Enum):
    """State machine states for the playlist player."""
    IDLE = auto()
    WELCOME = auto()
    PLAYING = auto()


class GuildPlayer:
    """Per-guild playlist state."""

    def __init__(self):
        self.state: PlayerState = PlayerState.IDLE
        self.playlist: list[str] = []
        self.current_track: Optional[str] = None

    def reset(self):
        """Reset to idle state."""
        self.state = PlayerState.IDLE
        self.playlist = []
        self.current_track = None

    def pick_random(self) -> Optional[str]:
        """Pick a random track from playlist."""
        if not self.playlist:
            return None
        self.current_track = random.choice(self.playlist)
        return self.current_track


class AmbientPlayer(commands.Cog):
    """Ambient audio player with playlist support."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.media_dir = Path("media")
        self._recovering: set[int] = set()
        self._players: dict[int, GuildPlayer] = {}  # guild_id -> GuildPlayer

    def _get_player(self, guild_id: int) -> GuildPlayer:
        """Get or create player state for a guild."""
        if guild_id not in self._players:
            self._players[guild_id] = GuildPlayer()
        return self._players[guild_id]

    # === Lifecycle ===

    async def cog_load(self):
        self.listening_reward_loop.start()
        self.voice_health_check_loop.start()
        if KEEPALIVE_ENABLED:
            self.keepalive_loop.start()
        if self.bot.is_ready():
            for guild in self.bot.guilds:
                await self._connect(guild)

    async def cog_unload(self):
        self.listening_reward_loop.cancel()
        self.voice_health_check_loop.cancel()
        if KEEPALIVE_ENABLED:
            self.keepalive_loop.cancel()
        for guild in self.bot.guilds:
            await self._disconnect(guild)


    # === Voice Connection Management ===

    async def _connect(self, guild: discord.Guild) -> bool:
        """Connect to the ambient channel."""
        if not self.bot.config.get(guild.id, "ambient_enabled", False):
            return False

        channel_id = self.bot.config.get(guild.id, "ambient_channel_id")
        if not channel_id:
            return False

        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.VoiceChannel):
            return False

        # Check if playlist is configured
        playlist = self.bot.config.get(guild.id, "ambient_playlist", [])
        if not playlist:
            return False

        # Clean up zombie if present
        if guild.voice_client and not guild.voice_client.is_connected():
            self.logger.warning(f"[PLAYER] Cleaning up zombie on connect in {guild.name}")
            await self._force_cleanup(guild)

        try:
            if guild.voice_client and guild.voice_client.is_connected():
                await guild.voice_client.move_to(channel)
            else:
                await channel.connect(timeout=30.0, reconnect=False)

            if self._is_occupied(channel):
                await self._start_playlist(guild)

            self.logger.info(f"[PLAYER] Connected to {channel.name} in {guild.name}")
            return True

        except Exception as e:
            self.logger.error(f"[PLAYER] Failed to connect in {guild.name}: {e}")
            return False

    async def _disconnect(self, guild: discord.Guild):
        """Disconnect from voice."""
        player = self._get_player(guild.id)
        player.reset()

        if guild.voice_client:
            try:
                await guild.voice_client.disconnect(force=True)
            except Exception as e:
                self.logger.warning(f"[PLAYER] Disconnect error in {guild.name}: {e}")

    async def _force_cleanup(self, guild: discord.Guild):
        """Force remove a zombie voice client."""
        if guild.voice_client:
            try:
                await guild.voice_client.disconnect(force=True)
            except Exception:
                pass
            try:
                self.bot._connection._remove_voice_client(guild.id)
            except Exception:
                pass

    async def _recover(self, guild: discord.Guild):
        """Recover from zombie state."""
        if guild.id in self._recovering:
            return
        self._recovering.add(guild.id)

        try:
            self.logger.warning(f"[PLAYER] Starting zombie recovery for {guild.name}")
            await self._force_cleanup(guild)
            await asyncio.sleep(VOICE_RECONNECT_COOLDOWN)

            if self.bot.config.get(guild.id, "ambient_enabled", False):
                if await self._connect(guild):
                    self.logger.info(f"[PLAYER] Recovery successful for {guild.name}")
                else:
                    self.logger.error(f"[PLAYER] Recovery failed for {guild.name}")
        finally:
            self._recovering.discard(guild.id)

    # === Playlist Management ===

    def _get_available_files(self) -> list[str]:
        """Get list of available audio files."""
        audio_extensions = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".opus"}
        files = []
        for f in self.media_dir.iterdir():
            if f.is_file() and f.suffix.lower() in audio_extensions:
                files.append(f.name)
        return files

    def _match_file(self, name: str) -> Optional[str]:
        """Match a filename with or without extension. Returns matched filename or None."""
        for available in self._get_available_files():
            if available.lower() == name.lower() or available.lower().startswith(name.lower() + "."):
                return available
        return None

    def _validate_file_list(self, files: tuple[str, ...]) -> tuple[list[str], list[str]]:
        """Validate a list of filenames. Returns (valid_files, missing_files)."""
        valid = []
        missing = []
        for f in files:
            matched = self._match_file(f)
            if matched:
                valid.append(matched)
            else:
                missing.append(f)
        return valid, missing

    def _create_audio_source(self, filepath: Path) -> discord.AudioSource:
        """Create appropriate audio source for file type."""
        if filepath.suffix.lower() in {".opus", ".ogg"}:
            return discord.FFmpegOpusAudio(str(filepath), codec="copy")
        return discord.FFmpegPCMAudio(str(filepath))

    def _get_validated_playlist(self, guild_id: int) -> list[str]:
        """Get playlist with validated file paths."""
        configured = self.bot.config.get(guild_id, "ambient_playlist", [])
        if not configured:
            return []

        valid = []
        for f in configured:
            if (self.media_dir / f).exists():
                valid.append(f)
            else:
                self.logger.warning(f"[PLAYER] Configured file not found: {f}")
        return valid

    async def _start_playlist(self, guild: discord.Guild):
        """Start playing - welcome track first if configured, then random shuffle."""
        player = self._get_player(guild.id)

        playlist = self._get_validated_playlist(guild.id)
        if not playlist:
            player.reset()
            return

        # Set IDLE before stopping so after_callback does nothing
        vc = guild.voice_client
        if vc and vc.is_playing():
            player.state = PlayerState.IDLE
            vc.stop()

        player.playlist = playlist

        # Check for welcome track
        welcome = self.bot.config.get(guild.id, "ambient_welcome")
        if welcome and (self.media_dir / welcome).exists():
            player.state = PlayerState.WELCOME
            player.current_track = welcome
            self.logger.info(f"[PLAYER] Playing welcome in {guild.name}: {welcome}")
        else:
            player.state = PlayerState.PLAYING
            player.pick_random()
            self.logger.info(f"[PLAYER] Starting shuffle in {guild.name}: {playlist}")

        self._play_current(guild)

    def _play_current(self, guild: discord.Guild):
        """Play the current track."""
        vc = guild.voice_client
        if not vc or not vc.is_connected():
            return

        player = self._get_player(guild.id)
        track = player.current_track

        if not track:
            self.logger.warning(f"[PLAYER] No current track in {guild.name}")
            return

        filepath = self.media_dir / track
        if not filepath.exists():
            self.logger.error(f"[PLAYER] Track not found: {track}")
            # Pick another random track
            if player.pick_random():
                self._play_current(guild)
            return

        def after_callback(error):
            if error:
                self.logger.error(f"[PLAYER] Playback error in {guild.name}: {error}")
            asyncio.run_coroutine_threadsafe(self._on_track_complete(guild), self.bot.loop)

        source = self._create_audio_source(filepath)
        vc.play(source, after=after_callback)
        self.logger.info(f"[PLAYER] Now playing in {guild.name}: {track}")

    async def _on_track_complete(self, guild: discord.Guild):
        """Handle track completion - pick next random track."""
        vc = guild.voice_client
        if not vc or not vc.is_connected():
            return

        if not self._is_occupied(vc.channel):
            player = self._get_player(guild.id)
            player.reset()
            self.logger.info(f"[PLAYER] Channel empty, stopping in {guild.name}")
            return

        player = self._get_player(guild.id)

        if player.state == PlayerState.IDLE:
            return

        # After welcome or any track, continue with random shuffle
        player.state = PlayerState.PLAYING
        player.pick_random()
        self._play_current(guild)

    def _is_occupied(self, channel: discord.VoiceChannel) -> bool:
        """Check if channel has non-bot members."""
        return any(not m.bot for m in channel.members)

    # === Background Tasks ===

    @tasks.loop(minutes=1)
    async def listening_reward_loop(self):
        """Award points to listeners."""
        for guild in self.bot.guilds:
            vc = guild.voice_client
            if not vc or not vc.is_connected() or not vc.is_playing():
                continue

            for member in vc.channel.members:
                if member.bot:
                    continue
                if member.voice and (member.voice.deaf or member.voice.self_deaf):
                    continue
                add_points(self.bot, member, POINTS_PER_MINUTE)

    @listening_reward_loop.before_loop
    async def before_listening_reward_loop(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=HEALTH_CHECK_INTERVAL)
    async def voice_health_check_loop(self):
        """Check for zombie connections and reconnect if needed."""
        for guild in self.bot.guilds:
            if not self.bot.config.get(guild.id, "ambient_enabled", False):
                continue
            if guild.id in self._recovering:
                continue

            vc = guild.voice_client

            if vc is not None and not vc.is_connected():
                state = "unknown"
                try:
                    state = vc._connection.state.name
                except Exception:
                    pass
                self.logger.warning(f"[PLAYER] Zombie detected in {guild.name} (state={state})")
                asyncio.create_task(self._recover(guild))

            elif vc is None:
                channel_id = self.bot.config.get(guild.id, "ambient_channel_id")
                playlist = self.bot.config.get(guild.id, "ambient_playlist", [])
                if channel_id and guild.get_channel(channel_id) and playlist:
                    self.logger.info(f"[PLAYER] Reconnecting missing voice in {guild.name}")
                    await asyncio.sleep(2.0 + random.random() * 3.0)
                    await self._connect(guild)

    @voice_health_check_loop.before_loop
    async def before_voice_health_check_loop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)

    @tasks.loop(seconds=KEEPALIVE_INTERVAL)
    async def keepalive_loop(self):
        """Send silence packets to idle connections."""
        for guild in self.bot.guilds:
            vc = guild.voice_client
            if vc and vc.is_connected() and not vc.is_playing():
                try:
                    self.logger.debug(f"[PLAYER] Sending keepalive to {guild.name}")
                    vc.send_audio_packet(OPUS_SILENCE, encode=False)
                except Exception as e:
                    self.logger.debug(f"[PLAYER] Keepalive failed for {guild.name}: {e}")

    @keepalive_loop.before_loop
    async def before_keepalive_loop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)

    # === Event Handlers ===

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        guild = member.guild
        if not self.bot.config.get(guild.id, "ambient_enabled", False):
            return

        vc = guild.voice_client
        if not vc or not vc.is_connected():
            return

        ambient_id = self.bot.config.get(guild.id, "ambient_channel_id")
        if vc.channel.id != ambient_id:
            return

        player = self._get_player(guild.id)

        # Someone joined ambient channel
        if after.channel and after.channel.id == ambient_id:
            if not member.bot:
                if player.state == PlayerState.IDLE:
                    await self._start_playlist(guild)
                elif not vc.is_playing():
                    # Resume if paused/stopped
                    self._play_current(guild)

        # Someone left ambient channel
        if before.channel and before.channel.id == ambient_id:
            if not self._is_occupied(vc.channel):
                # Channel empty, stop and reset
                if vc.is_playing():
                    vc.stop()
                player.reset()
                self.logger.info(f"[PLAYER] Channel empty, reset in {guild.name}")

    # === Commands ===

    @commands.group(name="loop", invoke_without_command=True)
    @commands.check(is_admin)
    async def loop(self, ctx):
        """Ambient audio player commands."""
        await ctx.send_help(ctx.command)

    @loop.command(name="setup")
    @commands.check(is_admin)
    async def loop_setup(self, ctx, channel: discord.VoiceChannel, *files: str):
        """Set up the ambient player with a channel and playlist.

        Usage: !loop setup #voice-channel file1.opus file2.mp3 ...
        """
        if not files:
            available = self._get_available_files()
            if available:
                file_list = "\n".join(f"  {f}" for f in sorted(available))
                await ctx.send(f"**Available audio files:**\n{file_list}\n\nUsage: `!loop setup #channel file1 file2 ...`")
            else:
                await ctx.send("No audio files in `media/` directory.")
            return

        valid_files, missing = self._validate_file_list(files)
        if missing:
            await ctx.send(f"Files not found: {', '.join(missing)}\n\nUse `!loop setup` to see available files.")
            return

        # Save configuration
        self.bot.config.set(ctx, "ambient_channel_id", channel.id)
        self.bot.config.set(ctx, "ambient_playlist", valid_files)
        self.bot.config.set(ctx, "ambient_enabled", True)

        # Connect and start
        if await self._connect(ctx.guild):
            playlist_str = " → ".join(valid_files)
            await ctx.send(f"**Ambient player configured!**\nChannel: {channel.mention}\nPlaylist: {playlist_str}")
        else:
            await ctx.send("Configured but failed to connect. Check logs.")

    @loop.command(name="playlist")
    @commands.check(is_admin)
    async def loop_playlist(self, ctx, *files: str):
        """View or set the playlist.

        Usage:
          !loop playlist           - Show current playlist
          !loop playlist f1 f2 ... - Set new playlist
        """
        if not files:
            # Show current playlist
            playlist = self.bot.config.get(ctx, "ambient_playlist", [])
            if playlist:
                player = self._get_player(ctx.guild.id)
                lines = []
                for i, f in enumerate(playlist):
                    marker = "▶" if i == player.current_index and player.state == PlayerState.PLAYING else " "
                    lines.append(f"{marker} {i+1}. {f}")
                await ctx.send(f"**Current playlist:**\n" + "\n".join(lines))
            else:
                await ctx.send("No playlist configured. Use `!loop setup` or `!loop playlist file1 file2 ...`")
            return

        # Set new playlist
        valid_files, missing = self._validate_file_list(files)
        if missing:
            await ctx.send(f"Files not found: {', '.join(missing)}")
            return

        self.bot.config.set(ctx, "ambient_playlist", valid_files)

        # Restart if currently playing
        player = self._get_player(ctx.guild.id)
        if player.state != PlayerState.IDLE:
            await self._start_playlist(ctx.guild)

        await ctx.send(f"Playlist updated: {' → '.join(valid_files)}")

    @loop.command(name="welcome")
    @commands.check(is_admin)
    async def loop_welcome(self, ctx, filename: str = None):
        """View, set, or clear the welcome track (plays once when someone joins).

        Usage:
          !loop welcome              - Show current
          !loop welcome filename.opus - Set welcome track
          !loop welcome none         - Disable welcome track
        """
        if not filename:
            current = self.bot.config.get(ctx, "ambient_welcome")
            if current:
                await ctx.send(f"Welcome track: `{current}`")
            else:
                await ctx.send("No welcome track configured.")
            return

        if filename.lower() == "none":
            self.bot.config.set(ctx, "ambient_welcome", None)
            await ctx.send("Welcome track disabled.")
            return

        matched = self._match_file(filename)
        if not matched:
            await ctx.send(f"File not found: `{filename}`")
            return

        self.bot.config.set(ctx, "ambient_welcome", matched)
        await ctx.send(f"Welcome track set to `{matched}`")

    @loop.command(name="skip")
    @commands.check(is_admin)
    async def loop_skip(self, ctx):
        """Skip to the next track in the playlist."""
        player = self._get_player(ctx.guild.id)

        if player.state == PlayerState.IDLE:
            await ctx.send("Not currently playing.")
            return

        vc = ctx.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()  # This triggers the after callback which advances
            await ctx.send("Skipping...")
        else:
            await ctx.send("Nothing playing to skip.")

    @loop.command(name="restart")
    @commands.check(is_admin)
    async def loop_restart(self, ctx):
        """Restart the playlist from the beginning."""
        player = self._get_player(ctx.guild.id)

        vc = ctx.guild.voice_client
        if not vc or not vc.is_connected():
            await ctx.send("Not connected to voice.")
            return

        if vc.is_playing():
            vc.stop()

        await self._start_playlist(ctx.guild)
        await ctx.send("Playlist restarted.")

    @loop.command(name="channel")
    @commands.check(is_admin)
    async def loop_channel(self, ctx, channel: discord.VoiceChannel):
        """Set the voice channel for ambient audio."""
        self.bot.config.set(ctx, "ambient_channel_id", channel.id)
        await ctx.send(f"Channel set to **{channel.name}**")

    @loop.command(name="enable")
    @commands.check(is_admin)
    async def loop_enable(self, ctx):
        """Enable the ambient player."""
        channel_id = self.bot.config.get(ctx, "ambient_channel_id")
        playlist = self.bot.config.get(ctx, "ambient_playlist", [])

        if not channel_id:
            await ctx.send("No channel configured. Use `!loop setup` first.")
            return
        if not playlist:
            await ctx.send("No playlist configured. Use `!loop setup` first.")
            return

        self.bot.config.set(ctx, "ambient_enabled", True)

        if await self._connect(ctx.guild):
            await ctx.send("Ambient player **enabled**.")
        else:
            await ctx.send("Enabled but failed to connect.")

    @loop.command(name="disable")
    @commands.check(is_admin)
    async def loop_disable(self, ctx):
        """Disable the ambient player."""
        self.bot.config.set(ctx, "ambient_enabled", False)
        await self._disconnect(ctx.guild)
        await ctx.send("Ambient player **disabled**.")

    @loop.command(name="status")
    @commands.check(is_admin)
    async def loop_status(self, ctx):
        """Show current player status."""
        enabled = self.bot.config.get(ctx, "ambient_enabled", False)
        channel_id = self.bot.config.get(ctx, "ambient_channel_id")
        playlist = self.bot.config.get(ctx, "ambient_playlist", [])
        welcome = self.bot.config.get(ctx, "ambient_welcome")

        channel_name = "Not set"
        if channel_id:
            channel = ctx.guild.get_channel(channel_id)
            channel_name = channel.name if channel else f"Unknown ({channel_id})"

        vc = ctx.guild.voice_client
        player = self._get_player(ctx.guild.id)

        if vc is None:
            voice_status = "Not connected"
        else:
            connected = vc.is_connected()
            playing = vc.is_playing() if connected else False
            if connected:
                voice_status = f"Playing in {vc.channel.name}" if playing else f"Idle in {vc.channel.name}"
            else:
                voice_status = "ZOMBIE"

        track_info = player.current_track or "None"

        embed = discord.Embed(title="Ambient Player Status", color=discord.Color.blue())
        embed.add_field(name="Enabled", value="Yes" if enabled else "No", inline=True)
        embed.add_field(name="State", value=player.state.name, inline=True)
        embed.add_field(name="Channel", value=channel_name, inline=True)
        embed.add_field(name="Voice", value=voice_status, inline=True)
        embed.add_field(name="Current Track", value=track_info, inline=True)
        embed.add_field(name="Welcome", value=welcome or "None", inline=True)
        embed.add_field(name="Playlist", value=", ".join(playlist) if playlist else "Not configured", inline=False)

        await ctx.send(embed=embed)

    @loop.command(name="nuke")
    @commands.check(is_admin)
    async def loop_nuke(self, ctx):
        """Force cleanup voice client (debug command)."""
        if not ctx.guild.voice_client:
            await ctx.send("No voice client to nuke.")
            return

        player = self._get_player(ctx.guild.id)
        player.reset()
        await self._force_cleanup(ctx.guild)
        await ctx.send("Nuked. Run `!loop status` to verify, then `!loop enable` to reconnect.")

    @loop.command(name="files")
    @commands.check(is_admin)
    async def loop_files(self, ctx):
        """List available audio files."""
        available = self._get_available_files()
        if available:
            file_list = "\n".join(f"  {f}" for f in sorted(available))
            await ctx.send(f"**Available audio files:**\n{file_list}")
        else:
            await ctx.send("No audio files in `media/` directory.")


async def setup(bot):
    await bot.add_cog(AmbientPlayer(bot))

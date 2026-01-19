"""
Ambient audio player - loops audio in a voice channel with listening rewards.

Zombie Recovery Strategy:
-------------------------
Discord can drop idle voice connections after 3-5 hours (1006 close code), leaving
discord.py in a "zombie" state where voice_client exists but isn't connected.

We handle this with:
1. On any connect attempt: check for zombie first, clean it up immediately
2. Health check loop: detects zombies and triggers recovery with 45s cooldown
   (Discord needs ~30-60s to fully clean up old sessions)
3. Keepalive packets: when enabled, sends silence to prevent Discord from
   considering the connection idle

The 45s cooldown only applies to mid-operation zombie recovery, not startup.
"""

import asyncio
import random
from datetime import datetime, timedelta
from pathlib import Path

import discord
from discord.ext import commands, tasks

from core.utils import is_admin
from utils.points import add_points

# === Configuration ===
POINTS_PER_MINUTE = 5
VOICE_RECONNECT_COOLDOWN = 45.0  # Discord needs ~30-60s to clean up old sessions
HEALTH_CHECK_INTERVAL = 30  # Seconds between zombie checks
KEEPALIVE_INTERVAL = 60  # Seconds between silence packets
KEEPALIVE_ENABLED = True

# Voice boost configuration
VOICE_BOOST_MIN_DELAY = 30       # Minimum seconds before boosted mantra fires
VOICE_BOOST_MAX_DELAY = 240      # Maximum seconds (4 min) - also the guard threshold
VOICE_BOOST_THRESHOLD = 300      # Seconds in channel before boosting starts (5 min)

# Opus-encoded silence frame - prevents Discord from considering connection idle
OPUS_SILENCE = b'\xf8\xff\xfe'


class AmbientPlayer(commands.Cog):
    """Ambient audio player - loops a single audio file in a voice channel."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.media_dir = Path("media")
        self._recovering: set[int] = set()  # Guild IDs currently in recovery
        self._voice_join_times: dict[int, datetime] = {}  # user_id -> join time

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
        """Connect to the ambient channel. Handles zombie cleanup automatically."""
        if not self.bot.config.get(guild.id, "ambient_enabled", False):
            return False

        channel_id = self.bot.config.get(guild.id, "ambient_channel_id")
        if not channel_id:
            return False

        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.VoiceChannel):
            return False

        if not self._get_audio_file(guild.id):
            return False

        # Clean up zombie if present (no cooldown - this is immediate cleanup)
        if guild.voice_client and not guild.voice_client.is_connected():
            self.logger.warning(f"[AMBIENT] Cleaning up zombie on connect in {guild.name}")
            await self._force_cleanup(guild)

        # Now connect
        try:
            if guild.voice_client and guild.voice_client.is_connected():
                await guild.voice_client.move_to(channel)
            else:
                await channel.connect(timeout=30.0, reconnect=False)

            if self._is_occupied(channel):
                self._play(guild)

            self.logger.info(f"[AMBIENT] Connected to {channel.name} in {guild.name}")
            return True

        except Exception as e:
            self.logger.error(f"[AMBIENT] Failed to connect in {guild.name}: {e}")
            return False

    async def _disconnect(self, guild: discord.Guild):
        """Disconnect from voice, cleaning up properly."""
        if guild.voice_client:
            try:
                await guild.voice_client.disconnect(force=True)
            except Exception as e:
                self.logger.warning(f"[AMBIENT] Disconnect error in {guild.name}: {e}")

    async def _force_cleanup(self, guild: discord.Guild):
        """Force remove a zombie voice client from discord.py internals."""
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
        """Recover from zombie state with cooldown for Discord cleanup."""
        if guild.id in self._recovering:
            return
        self._recovering.add(guild.id)

        try:
            self.logger.warning(f"[AMBIENT] Starting zombie recovery for {guild.name}")
            await self._force_cleanup(guild)

            self.logger.info(f"[AMBIENT] Waiting {VOICE_RECONNECT_COOLDOWN}s for Discord cleanup")
            await asyncio.sleep(VOICE_RECONNECT_COOLDOWN)

            if self.bot.config.get(guild.id, "ambient_enabled", False):
                if await self._connect(guild):
                    self.logger.info(f"[AMBIENT] Recovery successful for {guild.name}")
                else:
                    self.logger.error(f"[AMBIENT] Recovery failed for {guild.name}")
        finally:
            self._recovering.discard(guild.id)

    # === Audio Playback ===

    def _get_audio_file(self, guild_id: int) -> Path | None:
        filename = self.bot.config.get(guild_id, "ambient_filename")
        if not filename:
            return None
        filepath = self.media_dir / filename
        return filepath if filepath.exists() else None

    def _is_occupied(self, channel: discord.VoiceChannel) -> bool:
        return any(not m.bot for m in channel.members)

    def _play(self, guild: discord.Guild):
        """Start or restart the audio loop."""
        vc = guild.voice_client
        if not vc or not vc.is_connected() or vc.is_playing():
            return

        filepath = self._get_audio_file(guild.id)
        if not filepath:
            return

        def after(error):
            if error:
                self.logger.error(f"[AMBIENT] Playback error in {guild.name}: {error}")
            if vc.is_connected() and self._is_occupied(vc.channel):
                self._play(guild)

        if filepath.suffix.lower() in {".opus", ".ogg"}:
            source = discord.FFmpegOpusAudio(str(filepath), codec="copy")
        else:
            source = discord.FFmpegPCMAudio(str(filepath))

        vc.play(source, after=after)

    # === Voice Boost ===

    def _try_voice_boost(self, member: discord.Member) -> None:
        """
        Try to boost mantra delivery for a user in the ambient channel.
        Sets next_delivery to soon if conditions are met.
        """
        # Get mantra config
        config = self.bot.config.get_user(member, 'mantra_system', {})

        # Skip if not enrolled
        if not config.get("enrolled"):
            return

        # Skip if mantra already pending (sent is not None)
        if config.get("sent") is not None:
            return

        # Skip if next_delivery already within max delay window
        next_delivery_str = config.get("next_delivery")
        if next_delivery_str:
            try:
                next_delivery = datetime.fromisoformat(next_delivery_str)
                if next_delivery <= datetime.now() + timedelta(seconds=VOICE_BOOST_MAX_DELAY):
                    return
            except (ValueError, TypeError):
                pass

        # Check join duration (need threshold time in channel)
        join_time = self._voice_join_times.get(member.id)
        if join_time is None:
            return
        if (datetime.now() - join_time).total_seconds() < VOICE_BOOST_THRESHOLD:
            return

        # All checks passed - boost the delivery
        delay_seconds = random.randint(VOICE_BOOST_MIN_DELAY, VOICE_BOOST_MAX_DELAY)
        config["next_delivery"] = (datetime.now() + timedelta(seconds=delay_seconds)).isoformat()
        config["voice_boost_requested"] = True
        self.bot.config.set_user(member, 'mantra_system', config)

        self.logger.info(f"[VOICE BOOST] Triggered for {member.name}, delivery in {delay_seconds}s")

    # === Background Tasks ===

    @tasks.loop(minutes=1)
    async def listening_reward_loop(self):
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

                # Voice boost: accelerate mantra delivery for users in trance
                self._try_voice_boost(member)

    @listening_reward_loop.before_loop
    async def before_listening_reward_loop(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=HEALTH_CHECK_INTERVAL)
    async def voice_health_check_loop(self):
        for guild in self.bot.guilds:
            if not self.bot.config.get(guild.id, "ambient_enabled", False):
                continue
            if guild.id in self._recovering:
                continue

            vc = guild.voice_client

            # Zombie: voice client exists but not connected
            if vc is not None and not vc.is_connected():
                state = "unknown"
                try:
                    state = vc._connection.state.name
                except Exception:
                    pass
                self.logger.warning(f"[AMBIENT] Zombie detected in {guild.name} (state={state})")
                asyncio.create_task(self._recover(guild))

            # Missing: should be connected but isn't
            elif vc is None:
                channel_id = self.bot.config.get(guild.id, "ambient_channel_id")
                if channel_id and guild.get_channel(channel_id):
                    self.logger.info(f"[AMBIENT] Reconnecting missing voice in {guild.name}")
                    await asyncio.sleep(2.0 + random.random() * 3.0)  # 2-5s jittered delay
                    await self._connect(guild)

    @voice_health_check_loop.before_loop
    async def before_voice_health_check_loop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)  # Let initial connections settle

    @tasks.loop(seconds=KEEPALIVE_INTERVAL)
    async def keepalive_loop(self):
        """Send silence packets to idle connections to prevent Discord timeout."""
        for guild in self.bot.guilds:
            vc = guild.voice_client
            # Only send keepalive when connected but not playing
            if vc and vc.is_connected() and not vc.is_playing():
                try:
                    self.logger.debug(f"[AMBIENT] Sending keepalive to {guild.name}")
                    vc.send_audio_packet(OPUS_SILENCE, encode=False)
                except Exception as e:
                    self.logger.debug(f"[AMBIENT] Keepalive failed for {guild.name}: {e}")

    @keepalive_loop.before_loop
    async def before_keepalive_loop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)  # Let initial connections settle

    # === Event Handlers ===

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            await self._connect(guild)

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

        # Someone joined ambient channel
        if after.channel and after.channel.id == ambient_id:
            if not member.bot:
                # Track join time for voice boost
                if not before.channel or before.channel.id != ambient_id:
                    self._voice_join_times[member.id] = datetime.now()
                # Start playing if not already
                if not vc.is_playing():
                    self._play(guild)

        # Someone left ambient channel
        if before.channel and before.channel.id == ambient_id:
            if not member.bot:
                # Clear join time tracking
                if not after.channel or after.channel.id != ambient_id:
                    self._voice_join_times.pop(member.id, None)
            # Stop if empty
            if not self._is_occupied(vc.channel) and vc.is_playing():
                vc.stop()

    # === Commands ===

    @commands.group(name="loop", invoke_without_command=True)
    @commands.check(is_admin)
    async def loop(self, ctx):
        """Ambient audio player commands."""
        await ctx.send_help(ctx.command)

    @loop.command(name="channel")
    @commands.check(is_admin)
    async def loop_channel(self, ctx, channel: discord.VoiceChannel):
        """Set the voice channel for ambient audio."""
        self.bot.config.set(ctx, "ambient_channel_id", channel.id)
        await ctx.send(f"Channel set to **{channel.name}**")

    @loop.command(name="file")
    @commands.check(is_admin)
    async def loop_file(self, ctx, *, filename: str):
        """Set the audio file to loop (from media/ directory, or download from URL)."""
        import aiohttp
        from urllib.parse import urlparse, unquote

        audio_extensions = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".opus"}

        # Handle URL downloads
        if filename.startswith(("http://", "https://")):
            parsed = urlparse(filename)
            url_filename = unquote(Path(parsed.path).name)

            if not url_filename or Path(url_filename).suffix.lower() not in audio_extensions:
                await ctx.send(f"URL must point to an audio file ({', '.join(audio_extensions)})")
                return

            filepath = self.media_dir / url_filename
            await ctx.send(f"Downloading `{url_filename}`...")

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(filename) as resp:
                        if resp.status != 200:
                            await ctx.send(f"Download failed: HTTP {resp.status}")
                            return
                        with open(filepath, 'wb') as f:
                            async for chunk in resp.content.iter_chunked(8192):
                                f.write(chunk)

                self.bot.config.set(ctx, "ambient_filename", url_filename)
                self._restart_playback(ctx.guild)

                hint = ""
                if Path(url_filename).suffix.lower() not in {".opus", ".ogg"}:
                    hint = "\nRun `!loop optimize` to reduce CPU usage."
                await ctx.send(f"Downloaded and set to **{url_filename}**{hint}")

            except Exception as e:
                await ctx.send(f"Download failed: {e}")
            return

        # Local file lookup (case-insensitive)
        available = {f.name.lower(): f.name for f in self.media_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in audio_extensions}

        matched = available.get(filename.lower())
        if not matched:
            for ext in audio_extensions:
                matched = available.get(f"{filename.lower()}{ext}")
                if matched:
                    break

        if not matched:
            if available:
                file_list = "\n".join(f"• {f}" for f in available.values())
                await ctx.send(f"File not found: `{filename}`\n\nAvailable:\n{file_list}")
            else:
                await ctx.send(f"File not found: `{filename}`\n\nNo audio files in media/")
            return

        self.bot.config.set(ctx, "ambient_filename", matched)
        self._restart_playback(ctx.guild)
        await ctx.send(f"File set to **{matched}**")

    def _restart_playback(self, guild: discord.Guild):
        vc = guild.voice_client
        if not vc or not vc.is_connected():
            return
        if vc.is_playing():
            vc.stop()
        if self._is_occupied(vc.channel):
            self._play(guild)

    @loop.command(name="enable")
    @commands.check(is_admin)
    async def loop_enable(self, ctx):
        """Enable ambient audio and join the configured channel."""
        channel_id = self.bot.config.get(ctx, "ambient_channel_id")
        filename = self.bot.config.get(ctx, "ambient_filename")

        if not channel_id:
            await ctx.send("No channel configured. Use `!loop channel #channel` first.")
            return
        if not filename:
            await ctx.send("No audio file configured. Use `!loop file <filename>` first.")
            return

        filepath = self.media_dir / filename
        if not filepath.exists():
            await ctx.send(f"Configured file not found: `{filename}`")
            return

        channel = ctx.guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.VoiceChannel):
            await ctx.send("Configured channel no longer exists.")
            return

        self.bot.config.set(ctx, "ambient_enabled", True)

        if await self._connect(ctx.guild):
            await ctx.send("Loop **enabled** and joined channel.")
        else:
            await ctx.send("Loop **enabled** but failed to join channel.")

    @loop.command(name="disable")
    @commands.check(is_admin)
    async def loop_disable(self, ctx):
        """Disable ambient audio and leave the voice channel."""
        self.bot.config.set(ctx, "ambient_enabled", False)
        await self._disconnect(ctx.guild)
        await ctx.send("Loop **disabled**.")

    @loop.command(name="optimize")
    @commands.check(is_admin)
    async def loop_optimize(self, ctx):
        """Convert the configured audio file to opus for lower CPU usage."""
        import subprocess

        filename = self.bot.config.get(ctx, "ambient_filename")
        if not filename:
            await ctx.send("No audio file configured.")
            return

        filepath = self.media_dir / filename
        if not filepath.exists():
            await ctx.send(f"File not found: `{filename}`")
            return

        if filepath.suffix.lower() in {".opus", ".ogg"}:
            await ctx.send(f"`{filename}` is already opus format.")
            return

        new_filename = filepath.stem + ".opus"
        new_filepath = self.media_dir / new_filename

        await ctx.send(f"Converting `{filename}` to opus...")

        try:
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", str(filepath), "-c:a", "libopus", "-b:a", "128k", str(new_filepath)],
                capture_output=True, text=True, timeout=300
            )

            if result.returncode != 0:
                await ctx.send(f"Conversion failed: {result.stderr[:500]}")
                return

            self.bot.config.set(ctx, "ambient_filename", new_filename)
            filepath.unlink()
            await ctx.send(f"Converted to `{new_filename}` and deleted original.")

        except subprocess.TimeoutExpired:
            await ctx.send("Conversion timed out.")
        except Exception as e:
            await ctx.send(f"Error: {e}")

    @loop.command(name="status")
    @commands.check(is_admin)
    async def loop_status(self, ctx):
        """Show current ambient audio configuration."""
        enabled = self.bot.config.get(ctx, "ambient_enabled", False)
        channel_id = self.bot.config.get(ctx, "ambient_channel_id")
        filename = self.bot.config.get(ctx, "ambient_filename")

        channel_name = "Not set"
        if channel_id:
            channel = ctx.guild.get_channel(channel_id)
            channel_name = channel.name if channel else f"Unknown ({channel_id})"

        vc = ctx.guild.voice_client

        if vc is None:
            status = "Not connected"
            debug = "None"
        else:
            connected = vc.is_connected()
            playing = vc.is_playing() if connected else False
            try:
                state = vc._connection.state.name
            except Exception:
                state = "error"

            debug = f"connected={connected}, playing={playing}, state={state}"

            if connected:
                status = f"Playing in {vc.channel.name}" if playing else f"Idle in {vc.channel.name}"
            else:
                status = f"ZOMBIE (state={state})"

        recovering = "Yes" if ctx.guild.id in self._recovering else "No"

        embed = discord.Embed(title="Ambient Audio Status", color=discord.Color.blue())
        embed.add_field(name="Enabled", value="Yes" if enabled else "No", inline=True)
        embed.add_field(name="Channel", value=channel_name, inline=True)
        embed.add_field(name="File", value=filename or "Not set", inline=True)
        embed.add_field(name="Status", value=status, inline=False)
        embed.add_field(name="Recovering", value=recovering, inline=True)
        embed.add_field(name="Keepalive", value="On" if KEEPALIVE_ENABLED else "Off", inline=True)
        embed.add_field(name="Debug", value=f"`{debug}`", inline=False)

        await ctx.send(embed=embed)

    @loop.command(name="nuke")
    @commands.check(is_admin)
    async def loop_nuke(self, ctx):
        """Force cleanup voice client (debug command)."""
        if not ctx.guild.voice_client:
            await ctx.send("No voice client to nuke.")
            return

        await self._force_cleanup(ctx.guild)
        await ctx.send("Nuked. Run `!loop status` to verify, then `!loop enable` to reconnect.")


async def setup(bot):
    await bot.add_cog(AmbientPlayer(bot))

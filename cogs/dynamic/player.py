import os
from pathlib import Path
from discord.ext import commands, tasks
import discord

from core.utils import is_admin
from utils.points import add_points

# Points awarded per minute of listening
POINTS_PER_MINUTE = 5


class AmbientPlayer(commands.Cog):
    """Ambient audio player - loops a single audio file in a voice channel."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.media_dir = Path("media")

    async def cog_load(self):
        """Called when the cog is loaded - join channels if bot is already ready."""
        self.listening_reward_loop.start()
        if self.bot.is_ready():
            for guild in self.bot.guilds:
                await self._join_ambient_channel(guild)

    def cog_unload(self):
        """Called when the cog is unloaded - stop the reward loop."""
        self.listening_reward_loop.cancel()

    @tasks.loop(minutes=1)
    async def listening_reward_loop(self):
        """Award points to users listening in ambient channels."""
        for guild in self.bot.guilds:
            voice_client = guild.voice_client
            if not voice_client or not voice_client.is_connected():
                continue

            if not voice_client.is_playing():
                continue

            # Award points to all non-bot, non-deafened members in channel
            for member in voice_client.channel.members:
                if member.bot:
                    continue
                if member.voice and (member.voice.deaf or member.voice.self_deaf):
                    continue
                add_points(self.bot, member, POINTS_PER_MINUTE)
                self.logger.debug(f"[AMBIENT] Awarded {POINTS_PER_MINUTE} points to {member.name}")

    @listening_reward_loop.before_loop
    async def before_listening_reward_loop(self):
        """Wait for bot to be ready before starting the loop."""
        await self.bot.wait_until_ready()

    def _get_audio_file_path(self, guild_id: int) -> Path | None:
        """Get the full path to the configured audio file."""
        filename = self.bot.config.get(guild_id, "ambient_filename")
        if not filename:
            return None
        filepath = self.media_dir / filename
        if not filepath.exists():
            return None
        return filepath

    def _is_channel_occupied(self, channel: discord.VoiceChannel) -> bool:
        """Check if there are any non-bot members in the channel."""
        return any(not member.bot for member in channel.members)

    def _restart_playback(self, guild: discord.Guild):
        """Stop current playback and start the new file."""
        voice_client = guild.voice_client
        if not voice_client or not voice_client.is_connected():
            return

        if voice_client.is_playing():
            voice_client.stop()

        if self._is_channel_occupied(voice_client.channel):
            self._play_loop(guild)

    def _play_loop(self, guild: discord.Guild):
        """Start or restart the audio loop."""
        voice_client = guild.voice_client
        if not voice_client or not voice_client.is_connected():
            return

        filepath = self._get_audio_file_path(guild.id)
        if not filepath:
            return

        # Don't start if already playing
        if voice_client.is_playing():
            return

        # Callback to loop the audio
        def after_playback(error):
            if error:
                self.logger.error(f"[AMBIENT] Playback error in {guild.name}: {error}")
            # Re-queue if still connected and channel is occupied
            if voice_client.is_connected():
                channel = voice_client.channel
                if self._is_channel_occupied(channel):
                    self._play_loop(guild)

        # Use opus passthrough for .opus/.ogg files, otherwise decode to PCM
        if filepath.suffix.lower() in {".opus", ".ogg"}:
            source = discord.FFmpegOpusAudio(str(filepath), codec="copy")
        else:
            source = discord.FFmpegPCMAudio(str(filepath))

        voice_client.play(source, after=after_playback)
        self.logger.debug(f"[AMBIENT] Started playback in {guild.name}")

    async def _join_ambient_channel(self, guild: discord.Guild) -> bool:
        """Join the configured ambient channel for a guild. Returns True if successful."""
        if not self.bot.config.get(guild.id, "ambient_enabled", False):
            return False

        channel_id = self.bot.config.get(guild.id, "ambient_channel_id")
        if not channel_id:
            return False

        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.VoiceChannel):
            return False

        filepath = self._get_audio_file_path(guild.id)
        if not filepath:
            return False

        try:
            if guild.voice_client:
                await guild.voice_client.move_to(channel)
            else:
                await channel.connect()

            # Start playback if channel is occupied
            if self._is_channel_occupied(channel):
                self._play_loop(guild)

            self.logger.info(f"[AMBIENT] Joined {channel.name} in {guild.name}")
            return True
        except Exception as e:
            self.logger.error(f"[AMBIENT] Failed to join channel in {guild.name}: {e}")
            return False

    @commands.Cog.listener()
    async def on_ready(self):
        """Join configured ambient channels on bot startup."""
        for guild in self.bot.guilds:
            await self._join_ambient_channel(guild)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handle voice channel join/leave events."""
        guild = member.guild

        if not self.bot.config.get(guild.id, "ambient_enabled", False):
            return

        ambient_channel_id = self.bot.config.get(guild.id, "ambient_channel_id")
        if not ambient_channel_id:
            return

        voice_client = guild.voice_client
        if not voice_client or not voice_client.is_connected():
            return

        # Only care about the ambient channel
        if voice_client.channel.id != ambient_channel_id:
            return

        ambient_channel = voice_client.channel

        # Someone joined the ambient channel
        if after.channel and after.channel.id == ambient_channel_id:
            if not member.bot and not voice_client.is_playing():
                self._play_loop(guild)

        # Someone left the ambient channel
        if before.channel and before.channel.id == ambient_channel_id:
            if not self._is_channel_occupied(ambient_channel):
                if voice_client.is_playing():
                    voice_client.stop()
                    self.logger.debug(f"[AMBIENT] Stopped playback (channel empty) in {guild.name}")

    @commands.group(name="loop", invoke_without_command=True)
    @commands.check(is_admin)
    async def loop(self, ctx):
        """Ambient audio player commands. Use !loop status to see current config."""
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

        # Check if it's a URL
        if filename.startswith("http://") or filename.startswith("https://"):
            url = filename
            parsed = urlparse(url)
            url_filename = unquote(Path(parsed.path).name)

            if not url_filename or not Path(url_filename).suffix.lower() in audio_extensions:
                await ctx.send(f"URL must point to an audio file ({', '.join(audio_extensions)})")
                return

            filepath = self.media_dir / url_filename

            await ctx.send(f"Downloading `{url_filename}`...")

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            await ctx.send(f"Download failed: HTTP {resp.status}")
                            return

                        with open(filepath, 'wb') as f:
                            async for chunk in resp.content.iter_chunked(8192):
                                f.write(chunk)

                self.bot.config.set(ctx, "ambient_filename", url_filename)

                # Restart playback with new file
                self._restart_playback(ctx.guild)

                hint = ""
                if Path(url_filename).suffix.lower() not in {".opus", ".ogg"}:
                    hint = "\nRun `!loop optimize` to reduce CPU usage."

                await ctx.send(f"Downloaded and set to **{url_filename}**{hint}")
                return

            except Exception as e:
                await ctx.send(f"Download failed: {e}")
                return

        # Local file lookup
        # Build a case-insensitive lookup of available audio files
        available_files = {f.name.lower(): f.name for f in self.media_dir.iterdir()
                         if f.is_file() and f.suffix.lower() in audio_extensions}

        # Try exact match first (case-insensitive)
        filename_lower = filename.lower()
        matched_filename = available_files.get(filename_lower)

        # If not found, try adding extensions
        if not matched_filename:
            for ext in audio_extensions:
                matched_filename = available_files.get(f"{filename_lower}{ext}")
                if matched_filename:
                    break

        if not matched_filename:
            if available_files:
                file_list = "\n".join(f"• {f}" for f in available_files.values())
                await ctx.send(f"File not found: `{filename}`\n\nAvailable files:\n{file_list}")
            else:
                await ctx.send(f"File not found: `{filename}`\n\nNo audio files found in media/")
            return

        self.bot.config.set(ctx, "ambient_filename", matched_filename)

        # Restart playback with new file
        self._restart_playback(ctx.guild)

        await ctx.send(f"File set to **{matched_filename}**")

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
            await ctx.send("Configured channel no longer exists or is not a voice channel.")
            return

        self.bot.config.set(ctx, "ambient_enabled", True)

        try:
            if ctx.guild.voice_client:
                await ctx.guild.voice_client.move_to(channel)
            else:
                await channel.connect()

            # Start playback if channel is occupied
            if self._is_channel_occupied(channel):
                self._play_loop(ctx.guild)

            await ctx.send("Loop **enabled** and joined channel.")
        except Exception as e:
            self.logger.error(f"[AMBIENT] Failed to join channel: {e}")
            await ctx.send(f"Loop **enabled** but failed to join channel: {e}")

    @loop.command(name="disable")
    @commands.check(is_admin)
    async def loop_disable(self, ctx):
        """Disable ambient audio and leave the voice channel."""
        self.bot.config.set(ctx, "ambient_enabled", False)

        if ctx.guild.voice_client:
            await ctx.guild.voice_client.disconnect()

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

        # New filename with .opus extension
        new_filename = filepath.stem + ".opus"
        new_filepath = self.media_dir / new_filename

        await ctx.send(f"Converting `{filename}` to opus...")

        try:
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", str(filepath), "-c:a", "libopus", "-b:a", "128k", str(new_filepath)],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                await ctx.send(f"Conversion failed: {result.stderr[:500]}")
                return

            # Update config to use new file
            self.bot.config.set(ctx, "ambient_filename", new_filename)

            # Delete original file
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

        voice_client = ctx.guild.voice_client
        status = "Not connected"
        if voice_client and voice_client.is_connected():
            if voice_client.is_playing():
                status = f"Playing in {voice_client.channel.name}"
            else:
                status = f"Connected to {voice_client.channel.name} (paused - channel empty)"

        embed = discord.Embed(title="Ambient Audio Status", color=discord.Color.blue())
        embed.add_field(name="Enabled", value="Yes" if enabled else "No", inline=True)
        embed.add_field(name="Channel", value=channel_name, inline=True)
        embed.add_field(name="File", value=filename or "Not set", inline=True)
        embed.add_field(name="Status", value=status, inline=False)

        await ctx.send(embed=embed)


async def setup(bot):
    """Every cog needs a setup function like this."""
    await bot.add_cog(AmbientPlayer(bot))

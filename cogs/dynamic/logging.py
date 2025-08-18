from discord.ext import commands
import discord
import random
from datetime import datetime
from core.permissions import is_admin, is_superadmin

class Logging(commands.Cog):
    """Writes status messages to a log channel."""
    def __init__(self, bot):
        self.bot = bot

    def get_log_channel(self, guild):
        # Prefer configured channel id; fallback to a channel named 'log'
        channel_id = self.bot.config.get(guild, "log_channel_id", None)
        if channel_id:
            ch = guild.get_channel(channel_id)
            if ch and isinstance(ch, discord.TextChannel):
                return ch
        return discord.utils.get(guild.text_channels, name="log")

    @commands.command(name="setlogchannel")
    @commands.check(is_admin)
    async def set_log_channel(self, ctx, channel: discord.TextChannel = None):
        """Set this server's log channel (defaults to current channel)."""
        target = channel or ctx.channel
        if not isinstance(target, discord.TextChannel):
            await ctx.send("This isn’t a text channel.")
            return
        self.bot.config.set(ctx, "log_channel_id", target.id)
        await ctx.send(f"Log channel set to {target.mention}.")

    @commands.command(name="showlogchannel")
    @commands.check(is_admin)
    async def show_log_channel(self, ctx):
        """Show the current log channel for this server."""
        configured_id = self.bot.config.get(ctx, "log_channel_id", None)
        if configured_id:
            ch = ctx.guild.get_channel(configured_id)
            if ch and isinstance(ch, discord.TextChannel):
                await ctx.send(f"Current log channel: {ch.mention}")
                return
            await ctx.send(f"A log channel is configured but not found (ID: `{configured_id}`).")
            return

        fallback = discord.utils.get(ctx.guild.text_channels, name="log")
        if fallback:
            await ctx.send(f"No configured log channel. Will fall back to: {fallback.mention}")
        else:
            await ctx.send("No configured log channel and no #log channel found.")

    @commands.command(name="showlogchannel")
    @commands.check(is_admin)
    async def show_log_channel(self, ctx):
        """Show the current server log channel."""
        cid = self.bot.config.get(ctx, "log_channel_id", None)
        if cid:
            ch = ctx.guild.get_channel(cid) if ctx.guild else None
            if ch:
                await ctx.send(f"Current log channel: {ch.mention}")
                return
            await ctx.send(f"Log channel id is set to {cid}, but the channel was not found.")
            return
        fallback = discord.utils.get(ctx.guild.text_channels, name="log") if ctx.guild else None
        if fallback:
            await ctx.send(f"No configured log channel; would fall back to {fallback.mention}.")
        else:
            await ctx.send("No log channel configured and no #log channel exists.")

    # Global error log is managed by cogs.static.error_handler:seterrorlog

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = self.get_log_channel(member.guild)
        if not channel:
            return
        await channel.send(f"Welcome <@{member.id}>")
            
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        channel = self.get_log_channel(member.guild)
        if channel:
            await channel.send(f"<@{member.id}> AKA {member.name} has left the server")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        channel = self.get_log_channel(before.guild)
        if channel and before.name and after.name and before.name != after.name:
            await channel.send(f"{before.name} changed their name to {after.name}")
            
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        if (after.channel is not None and "Voice Chat" in after.channel.name) or (before.channel is not None and 'Voice Chat' in before.channel.name):
            return
        if before.channel is None and before.channel != after.channel:
            channel = self.get_log_channel(after.channel.guild)
            if channel:
                await channel.send(f"{member.name} joined **{after.channel.name}**")
        if after.channel is None and before.channel != after.channel:
            channel = self.get_log_channel(before.channel.guild)
            if channel:
                await channel.send(f"{member.name} left **{before.channel.name}**")
        if before.channel is not None and after.channel is not None and before.channel != after.channel and before.channel.guild.id == after.channel.guild.id:
            channel = self.get_log_channel(before.channel.guild)
            if channel:
                await channel.send(f"{member.name} moved from **{before.channel.name}** to **{after.channel.name}**")

async def setup(bot):
    await bot.add_cog(Logging(bot))

from discord.ext import commands
import discord
from discord import app_commands
from typing import Optional
import re

from features.points import add_points
from core.permissions import is_admin_interaction

class Counter(commands.Cog):
    """Cog for managing a counting channel."""
    def __init__(self, bot):
        self.bot = bot
        # Track last valid number per channel id
        self.last_number_by_channel = {}

    @commands.Cog.listener()
    async def on_ready(self):
        """Auto-register a 'counting' channel per guild if none configured."""
        for guild in self.bot.guilds:
            try:
                configured = self.bot.config.get(guild, 'counting_channels', [])
                if configured:
                    continue
                # Try to detect a channel named 'counting'
                channel = next((c for c in guild.text_channels if c.name.lower() == 'counting'), None)
                if channel:
                    self.bot.config.set(guild, 'counting_channels', [channel.id])
            except Exception:
                continue

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore bot messages
        if message.author.bot:
            return
            
        # Only process messages in guild channels that are registered as counting channels
        if not hasattr(message.channel, 'id'):
            return
        counting_channels = self.bot.config.get(message.guild, 'counting_channels', []) if message.guild else []
        if message.channel.id not in counting_channels:
            return
        
        # Lazy load: if channel not seen, search last 10 messages for the highest count
        channel_last = self.last_number_by_channel.get(message.channel.id, None)
        if channel_last is None:
            highest_found = -1
            async for msg in message.channel.history(limit=10):
                if msg.id == message.id:
                    continue
                try:
                    count = int(msg.content.strip())
                    if count > highest_found:
                        highest_found = count
                except ValueError:
                    continue
            if highest_found != -1:
                self.last_number_by_channel[message.channel.id] = highest_found
            else:
                self.last_number_by_channel[message.channel.id] = 0
        
        try:
            num = int(message.content.strip())
        except ValueError:
            await message.delete()
            return

        if num != self.last_number_by_channel[message.channel.id] + 1:
            await message.delete()
        else:
            self.last_number_by_channel[message.channel.id] = num
            
            # Award 1 point for valid counting
            add_points(self.bot.config, message.author, 1)
    
    @app_commands.command(name="counting_rewards", description="Enable automatic counting reward protocols")
    @app_commands.describe(enabled="Enable or disable automatic reward collection")
    async def counting_rewards(self, interaction: discord.Interaction, enabled: bool):
        """Toggle automatic reward collection for counting."""
        self.bot.config.set_user(interaction.user, 'auto_claim_gacha', enabled)
        
        if enabled:
            await interaction.response.send_message(
                "Counting protocols integrated. Automatic reward processing enabled.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Automatic reward protocols suspended.",
                ephemeral=True
            )

    @app_commands.command(name="counting_register", description="Register this channel (or selected) as a counting channel")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.check(is_admin_interaction)
    @app_commands.guild_only()
    @app_commands.describe(channel="Channel to register; defaults to current")
    async def counting_register(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("This isn’t a text channel.", ephemeral=True)
            return
        chans = self.bot.config.get(target.guild, 'counting_channels', []) or []
        if target.id not in chans:
            chans.append(target.id)
            self.bot.config.set(target.guild, 'counting_channels', chans)
        await interaction.response.send_message(f"Registered {target.mention} for counting.", ephemeral=True)

    @app_commands.command(name="counting_unregister", description="Unregister a counting channel")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.check(is_admin_interaction)
    @app_commands.guild_only()
    @app_commands.describe(channel="Channel to unregister; defaults to current")
    async def counting_unregister(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("This isn’t a text channel.", ephemeral=True)
            return
        chans = self.bot.config.get(target.guild, 'counting_channels', []) or []
        if target.id in chans:
            chans = [c for c in chans if c != target.id]
            self.bot.config.set(target.guild, 'counting_channels', chans)
        await interaction.response.send_message(f"Unregistered {target.mention} from counting.", ephemeral=True)

    @app_commands.command(name="counting_list", description="List registered counting channels for this server")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.check(is_admin_interaction)
    @app_commands.guild_only()
    async def counting_list(self, interaction: discord.Interaction):
        chans = self.bot.config.get(interaction.guild, 'counting_channels', []) or []
        if not chans:
            await interaction.response.send_message("No counting channels registered.", ephemeral=True)
            return
        mentions = []
        for cid in chans:
            ch = interaction.guild.get_channel(cid)
            mentions.append(ch.mention if ch else f"#{cid}")
        await interaction.response.send_message(
            "Registered counting channels: " + ", ".join(mentions),
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Counter(bot))
from discord.ext import commands
import discord
from discord import app_commands
import re

class Counter(commands.Cog):
    """Cog for managing a counting channel."""
    def __init__(self, bot):
        self.bot = bot
        self.last_number = -1

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore bot messages
        if message.author.bot:
            return
            
        # Only process messages in guild channels named "counting"
        if not hasattr(message.channel, 'name') or message.channel.name != "counting":
            return
        
        # Check for auto-claim trigger phrase FIRST (before deletion logic)
        trigger_pattern = r'\bmy\s+mind\s+requires\s+counting\s+protocols\b'
        if re.search(trigger_pattern, message.content, re.IGNORECASE):
            self.bot.config.set_user(message.author, 'auto_claim_gacha', True)
            await message.reply("Counting protocols integrated. Automatic reward processing enabled.", mention_author=False)
            return  # Don't delete this message, allow it to stay
        
        # Lazy load: if last_number is -1, search last 10 messages for the highest count
        if self.last_number == -1:
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
                self.last_number = highest_found
        
        try:
            num = int(message.content.strip())
        except ValueError:
            await message.delete()
            return

        if num != self.last_number + 1:
            await message.delete()
        else:
            self.last_number = num
            
            # Award 1 point for valid counting
            current_points = self.bot.config.get_user(message.author, 'points', 0)
            new_total = max(0, current_points + 1)
            self.bot.config.set_user(message.author, 'points', new_total)
    
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

async def setup(bot):
    await bot.add_cog(Counter(bot))
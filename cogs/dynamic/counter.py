from discord.ext import commands
import discord

class Counter(commands.Cog):
    """Cog for managing a counting channel."""
    def __init__(self, bot):
        self.bot = bot
        self.last_number = 0

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore bot messages and messages not in "counting" channel.
        if message.author.bot or message.channel.name != "counting":
            return
        
        try:
            num = int(message.content.strip())
        except ValueError:
            await message.delete()
            return

        if num != self.last_number + 1:
            await message.delete()
        else:
            self.last_number = num

async def setup(bot):
    await bot.add_cog(Counter(bot))
from discord.ext import commands
import discord

class Counter(commands.Cog):
    """Cog for managing a counting channel."""
    def __init__(self, bot):
        self.bot = bot
        self.last_number = -1

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore bot messages and messages not in "counting" channel.
        if message.author.bot or message.channel.name != "counting":
            return
        
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

async def setup(bot):
    await bot.add_cog(Counter(bot))
from discord.ext import commands
import discord

class Test(commands.Cog):
    """This is a cog with role commands."""
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger


@commands.command(name="getconfig")
async def get_config(ctx):
    """Get the current configuration."""
    config = ctx.bot.config
    await ctx.send(f"Current config: {config}")

async def setup(bot):
    """Every cog needs a setup function like this."""
    await bot.add_cog(Test(bot))

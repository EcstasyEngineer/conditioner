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


@commands.command(name="helloworld")
async def hello_world(ctx):
    """A simple command that responds with 'Hello, World!'."""
    await ctx.send("Hello, World!")

async def setup(bot):
    """Every cog needs a setup function like this."""
    await bot.add_cog(Test(bot))

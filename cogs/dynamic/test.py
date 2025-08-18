from discord.ext import commands
import discord

from core.permissions import is_superadmin, is_admin

class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger


    @commands.command(name="getconfig")
    @commands.check(is_admin)
    async def get_config(self, ctx):
        """Get the current configuration."""
        config = self.bot.config
        await ctx.send(f"Current user config: {config.get_user(ctx.author)}")
        await ctx.send(f"Current guild config: {config.get_guild(ctx.guild)}")

        await ctx.send(f"Current user config (id): {config.get_user(ctx.author.id)}")
        await ctx.send(f"Current guild config (id): {config.get_guild(ctx.guild.id)}")


    @commands.command(name="helloworld", hidden=True)
    @commands.check(is_admin)
    async def hello_world(self, ctx):
        """A simple command that responds with 'Hello, World!'."""
        await ctx.send("Hello, World!")


    @commands.command(name="throw", aliases=["crash", "boom"], hidden=True)
    @commands.check(is_superadmin)
    async def throw_error(self, ctx, *, message: str = "Intentional test error"):
        """Raise an error intentionally to test logging."""
        raise RuntimeError(f"TestError: {message}")

async def setup(bot):
    """Every cog needs a setup function like this."""
    await bot.add_cog(Test(bot))
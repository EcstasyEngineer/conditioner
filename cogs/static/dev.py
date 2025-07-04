from discord.ext import commands
import discord
from sys import version_info as sysv
from os import listdir
import subprocess
from datetime import datetime
import sys


def is_server_admin(ctx):
    """Check if user is server admin (bot admin, Discord admin, or server owner)."""
    if ctx.guild is None:
        return False
    
    # Check if user is in bot's admin list for this guild
    bot = ctx.bot
    admins = bot.config.get(ctx, "admins", [])
    if ctx.author.id in admins:
        return True
    
    # Check Discord server permissions
    if ctx.author.guild_permissions.administrator or ctx.author == ctx.guild.owner:
        return True
    
    return False

def is_superadmin(ctx):
    """Check if user is global superadmin."""
    bot = ctx.bot
    superadmins = bot.config.get_global("superadmins", [])
    return ctx.author.id in superadmins

class Dev(commands.Cog):
    """This is a cog with owner-only commands.
    Note:
        All cogs inherits from `commands.Cog`_.
        All cogs are classes, so they need self as first argument in their methods.
        All cogs use different decorators for commands and events (see example below).
        All cogs needs a setup function (see below).
    Documentation:
        https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html
    """
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger

    @commands.Cog.listener()
    #This is the decorator for events (inside of cogs).
    async def on_ready(self):
        self.logger.info(f'Python {sysv.major}.{sysv.minor}.{sysv.micro} - Discord.py {discord.__version__}')

    def check_cog(self, cog):
        """Returns the name of the cog in the correct format.
        Args:
            self
            cog (str): The cogname to check
        
        Returns:
            cog if cog starts with `cogs.`, otherwise an fstring with this format`cogs.{cog}`_.
        Note:
            All cognames are made lowercase with `.lower()`_.
        """
        if (cog.lower()).startswith('cogs.dynamic.') == True:
            return cog.lower()
        return f'cogs.dynamic.{cog.lower()}'

    @commands.command(name='load', hidden=True)
    @commands.is_owner()
    async def load(self, ctx, *, cog: str):
        """This commands loads the selected cog, as long as that cog is in the `./cogs` folder.
                
        Args:
            cog (str): The name of the cog to load. The name is checked with `.check_cog(cog)`_.
        
        Note:
            This command can be used only from the bot owner.
            This command is hidden from the help menu.
            This command deletes its messages after 20 seconds.
        """
        self.logger.info(f"{ctx.author} (ID: {ctx.author.id}) invoked load on {cog}")
        message = await ctx.send('Loading...')
        await ctx.message.delete()
        try:
            await self.bot.load_extension(self.check_cog(cog))
        except Exception as exc:
            self.logger.error(f"Error loading {cog} by {ctx.author}", exc_info=True)
            await message.edit(content=f'An error has occurred: {exc}', delete_after=20)
        else:
            self.logger.info(f"Loaded {cog} successfully by {ctx.author}")
            await message.edit(content=f'{self.check_cog(cog)} has been loaded.', delete_after=20)

    @commands.command(name='unload', hidden=True)
    @commands.is_owner()
    async def unload(self, ctx, *, cog: str):
        """This commands unloads the selected cog, as long as that cog is in the `./cogs` folder.
        
        Args:
            cog (str): The name of the cog to unload. The name is checked with `.check_cog(cog)`_.
        Note:
            This command can be used only from the bot owner.
            This command is hidden from the help menu.
            This command deletes its messages after 20 seconds.
        """
		
        self.logger.info(f"{ctx.author} (ID: {ctx.author.id}) invoked unload on {cog}")
        message = await ctx.send('Unloading...')
        await ctx.message.delete()
        try:
            await self.bot.unload_extension(self.check_cog(cog))
        except Exception as exc:
            self.logger.error(f"Error unloading {cog} by {ctx.author}", exc_info=True)
            await message.edit(content=f'An error has occurred: {exc}', delete_after=20)
        else:
            self.logger.info(f"Unloaded {cog} successfully by {ctx.author}")
            await message.edit(content=f'{self.check_cog(cog)} has been unloaded.', delete_after=20)
            
    @commands.command(name='reload', hidden=True)#This command is hidden from the help menu.
    @commands.is_owner()
    async def reload(self, ctx, cog=None):
        """This commands reloads a specific cog or all cogs in the `./cogs/dynamic` folder.
        
        Note:
            This command can be used only from the bot owner.
            This command is hidden from the help menu.
            This command deletes its messages after 20 seconds."""

        self.logger.info(f"{ctx.author} (ID: {ctx.author.id}) invoked reload on {cog or 'all dynamic'}")
        await ctx.message.delete()
        
        if cog is None:
            cogs_to_unload = [c for c in self.bot.extensions if c.startswith("cogs.dynamic.")]
            cogs_to_load = [f'cogs.dynamic.{filename[:-3]}' for filename in listdir('./cogs/dynamic') if filename.endswith('.py')]
        else:
            cogs_to_unload = [self.check_cog(cog)]
            cogs_to_load = [self.check_cog(cog)]

        errors = []
        message = await ctx.send(f'Reloading...')
        for cog in cogs_to_unload:
            if cog not in self.bot.extensions:
                continue
            try:
                await self.bot.unload_extension(cog)
            except Exception as exc:
                self.logger.error(f"Error unloading {cog} during reload by {ctx.author}", exc_info=True)
                errors.append(f'Error unloading {cog}: {exc}')
        
        for cog in cogs_to_load:
            try:
                await self.bot.load_extension(cog)
            except Exception as exc:
                self.logger.error(f"Error loading {cog} during reload by {ctx.author}", exc_info=True)
                errors.append(f'Error loading {cog}: {exc}')
        
        if errors:
            formatted_errors = '\n'.join([f"- {error}" for error in errors])
            response = f'Errors occurred:\n{formatted_errors}'
        else:
            formatted_cogs = '\n'.join([f"- {cog}" for cog in cogs_to_load])
            response = f'All cogs reloaded successfully:\n{formatted_cogs}'

        await message.edit(content=response, delete_after=20)
        
    @commands.command(name='update', hidden=True)
    @commands.check(is_server_admin)
    async def update(self, ctx):
        """This command executes a git pull command in the current environment to update the code.
        
        Note:
            This command can be used by server admins.
            This command is hidden from the help menu.
        """
        self.logger.info(f"{ctx.author} invoked update command")
        message = await ctx.send('Updating code...')
        await ctx.message.delete()
        try:
            result = subprocess.run(['git', 'pull'], capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info(f"Git pull success: {result.stdout.strip()}")
                commit_info = subprocess.run(['git', 'log', '-1', '--format="%H %ct"'], capture_output=True, text=True)
                commit_hash, commit_timestamp = commit_info.stdout.replace("\"","").strip().split()
                human_time = datetime.fromtimestamp(int(commit_timestamp)).strftime("%Y-%m-%d %H:%M")
                await message.edit(content=f'Code updated successfully:\nCommit Hash: {commit_hash}\nTimestamp: {human_time}', delete_after=20)
            else:
                self.logger.error(f"Git pull error: {result.stderr.strip()}")
                await message.edit(content=f'Error updating code:\n{result.stderr}', delete_after=20)
        except Exception as exc:
            self.logger.error("Exception during update", exc_info=True)
            await message.edit(content=f'An error has occurred: {exc}', delete_after=20)

    @commands.command(name='list_cogs', aliases=['listcogs'], hidden=True)
    @commands.is_owner()
    async def list_cogs(self, ctx):
        """This command lists all the cogs in the `cogs/dynamic` directory.
        
        Note:
            This command can be used only from the bot owner.
            This command is hidden from the help menu.
        """
        self.logger.info(f"{ctx.author} invoked list_cogs")
        message = await ctx.send('Listing all cogs...')
        await ctx.message.delete()
        try:
            cogs = [cog[:-3] for cog in listdir('./cogs/dynamic') if cog.endswith('.py')]
            await message.edit(content=f'Available cogs: {", ".join(cogs)}', delete_after=20)
        except Exception as exc:
            self.logger.error("Error listing cogs", exc_info=True)
            await message.edit(content=f'An error has occurred: {exc}', delete_after=20)
            
    @commands.command(name='shutdown', aliases=['restart'], hidden=True)
    @commands.check(is_superadmin)
    async def shutdown(self, ctx):
        """This command shuts down the bot (expects systemctl auto-restart).
        
        Note:
            This command can be used by superadmins only.
            This command is hidden from the help menu.
            Use 'restart' alias for cleaner command.
        """
        self.logger.info(f"{ctx.author} invoked shutdown")
        
        # Send message first
        message = await ctx.send('Restarting...')
        
        # Try to delete original message if possible (skip if DM)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass  # Can't delete in DMs, that's fine
        
        # Actually shut down
        try:
            await self.bot.close()
            sys.exit()
        except Exception as exc:
            self.logger.error("Error during shutdown", exc_info=True)
            await message.edit(content=f'An error has occurred: {exc}', delete_after=20)
            
    @commands.command(name='sync_dev', aliases=['syncdev'], hidden=True)
    @commands.is_owner()
    async def sync_dev(self, ctx):
        """Fast guild sync for immediate testing (creates temporary overrides).
        
        Note:
            This command can be used only from the bot owner.
            This command is hidden from the help menu.
            Use sync_clean to remove guild overrides after testing.
        """
        self.logger.info(f"{ctx.author} invoked sync_dev for guild {ctx.guild.id}")
        message = await ctx.send('Fast syncing for testing...')
        await ctx.message.delete()
        try:
            self.bot.tree.copy_global_to(guild=ctx.guild)
            await self.bot.tree.sync(guild=ctx.guild)
            await message.edit(content='✅ Dev commands synced (guild override active)\n💡 Remember to run !sync_clean when done testing', delete_after=20)
        except Exception as exc:
            self.logger.error("Error syncing dev commands", exc_info=True)
            await message.edit(content=f'An error has occurred: {exc}', delete_after=20)
    
    @commands.command(name='sync_clean', aliases=['syncclean'], hidden=True)
    @commands.is_owner()
    async def sync_clean(self, ctx):
        """Remove guild command overrides, return to global commands only.
        
        Note:
            This command can be used only from the bot owner.
            This command is hidden from the help menu.
            Clears guild-specific commands to prevent duplicates.
        """
        self.logger.info(f"{ctx.author} invoked sync_clean for guild {ctx.guild.id}")
        message = await ctx.send('Cleaning guild overrides...')
        await ctx.message.delete()
        try:
            self.bot.tree.clear_commands(guild=ctx.guild)
            await self.bot.tree.sync(guild=ctx.guild)
            await message.edit(content='✅ Guild overrides cleared (global commands active)', delete_after=20)
        except Exception as exc:
            self.logger.error("Error cleaning guild commands", exc_info=True)
            await message.edit(content=f'An error has occurred: {exc}', delete_after=20)

async def setup(bot):
    """Every cog needs a setup function like this."""
    await bot.add_cog(Dev(bot))

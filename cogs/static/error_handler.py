"""
Simple admin commands for error logging.
"""

import discord
from discord.ext import commands


class SimpleErrorAdmin(commands.Cog):
    """Simple admin commands for error logging configuration."""
    
    def __init__(self, bot):
        self.bot = bot
    
    def cog_check(self, ctx):
        """Only allow superadmins and guild admins to use these commands."""
        superadmins = self.bot.config.get_global("superadmins", [])
        is_superadmin = ctx.author.id in superadmins
        is_guild_admin = (ctx.guild is not None and 
                         (ctx.author.guild_permissions.administrator or ctx.author == ctx.guild.owner))
        return is_superadmin or is_guild_admin
    
    @commands.command(hidden=True)
    async def seterrorlog(self, ctx, channel: discord.TextChannel = None):
        """Set the channel for error logging reports."""
        # If no channel provided, show current config
        if not channel:
            current_id = self.bot.config.get_global("error_channel_id")
            if current_id:
                current_channel = self.bot.get_channel(current_id)
                if current_channel:
                    await ctx.send(f"Current error log channel: {current_channel.mention}")
                else:
                    await ctx.send(f"Current error log channel ID: {current_id} (channel not found)")
            else:
                await ctx.send("No error log channel configured. Usage: `!seterrorlog #channel`")
            return
        
        # Set the error channel
        self.bot.config.set_global("error_channel_id", channel.id)
        
        # Send confirmation
        embed = discord.Embed(
            title="✅ Error Logging Configured",
            description=f"Error reports will now be sent to {channel.mention}",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Rate Limit",
            value="5 minutes between duplicate errors",
            inline=True
        )
        
        await ctx.send(embed=embed)
        
        # Send test message to confirm it works
        test_embed = discord.Embed(
            title="🔧 Error Logging Test",
            description="Error logging has been successfully configured for this channel.",
            color=discord.Color.blue()
        )
        test_embed.add_field(
            name="Features",
            value="• Automatic error detection\n• Rate limiting (5min cooldown)\n• Detailed tracebacks\n• Context information",
            inline=False
        )
        test_embed.set_footer(text="Simple Error Logging System")
        
        await channel.send(embed=test_embed)
    
    @commands.command(hidden=True)
    async def testerror(self, ctx):
        """Trigger a test error to verify error logging system."""
        await ctx.send("Triggering test error...")
        
        # This will cause a ZeroDivisionError and trigger on_command_error
        result = 1 / 0


async def setup(bot):
    """Set up the simple error admin cog."""
    await bot.add_cog(SimpleErrorAdmin(bot))
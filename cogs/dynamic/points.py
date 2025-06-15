from discord.ext import commands
import discord
from datetime import datetime

class Points(commands.Cog):
    """Cog for managing user points across the bot ecosystem."""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger if hasattr(bot, 'logger') else None
    
    # ===================
    # HELPER FUNCTIONS FOR OTHER COGS
    # ===================
    
    def add_points(self, user, amount):
        """
        Add points to a user (can be negative to subtract).
        
        Args:
            user: Discord user object or user ID
            amount: Points to add (can be negative)
            
        Returns:
            int: New point total
        """
        current_points = self.bot.config.get_user(user, 'points', 0)
        new_total = max(0, current_points + amount)  # Prevent going below 0
        self.bot.config.set_user(user, 'points', new_total)
        return new_total
    
    def get_points(self, user):
        """
        Get current point balance for a user.
        
        Args:
            user: Discord user object or user ID
            
        Returns:
            int: Current point balance
        """
        return self.bot.config.get_user(user, 'points', 0)
    
    # ===================
    # USER COMMANDS
    # ===================
    
    @commands.command(name='points', aliases=['balance', 'score'])
    async def check_points(self, ctx, member: discord.Member = None):
        """Check your point balance or another user's balance."""
        target = member if member else ctx.author
        points = self.get_points(target)
        
        if target == ctx.author:
            await ctx.send(f"💎 You have **{points:,}** points")
        else:
            await ctx.send(f"💎 {target.mention} has **{points:,}** points")
    
    @commands.command(name='leaderboard', aliases=['top', 'rankings'])
    async def leaderboard(self, ctx, limit: int = 10):
        """Show the points leaderboard."""
        if limit > 20:
            limit = 20
        elif limit < 1:
            limit = 10
        
        # This is a simple implementation - for better performance,
        # you might want to cache leaderboards or use a database
        guild_members = []
        
        # Get all guild members and their points
        for member in ctx.guild.members:
            if not member.bot:
                points = self.get_points(member)
                if points > 0:
                    guild_members.append((member, points))
        
        # Sort by points descending
        guild_members.sort(key=lambda x: x[1], reverse=True)
        
        if not guild_members:
            await ctx.send("No one has any points yet!")
            return
        
        # Build leaderboard message
        description = ""
        for i, (member, points) in enumerate(guild_members[:limit], 1):
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = f"{i}."
            
            description += f"{emoji} {member.display_name} - **{points:,}** points\n"
        
        embed = discord.Embed(
            title="🏆 Points Leaderboard",
            description=description,
            color=0x9932cc
        )
        
        # Show user's rank if they're not in top list
        user_rank = None
        for i, (member, points) in enumerate(guild_members, 1):
            if member == ctx.author:
                user_rank = i
                break
        
        if user_rank and user_rank > limit:
            user_points = self.get_points(ctx.author)
            embed.set_footer(text=f"Your rank: #{user_rank} with {user_points:,} points")
        
        await ctx.send(embed=embed)
    
    
    # ===================
    # ADMIN COMMANDS
    # ===================
    
    @commands.command(name='add_points', aliases=['addpoints'])
    @commands.has_permissions(administrator=True)
    async def admin_add_points(self, ctx, member: discord.Member, amount: int):
        """Add points to a user (Admin only). Amount can be negative to subtract."""
        new_total = self.add_points(member, amount)
        
        if amount > 0:
            await ctx.send(f"✅ Added {amount:,} points to {member.mention}. New balance: {new_total:,}")
        else:
            await ctx.send(f"✅ Removed {abs(amount):,} points from {member.mention}. New balance: {new_total:,}")
    
    @commands.command(name='set_points', aliases=['setpoints'])
    @commands.has_permissions(administrator=True)
    async def admin_set_points(self, ctx, member: discord.Member, amount: int):
        """Set a user's points to a specific amount (Admin only)."""
        if amount < 0:
            await ctx.send("Amount cannot be negative!")
            return
        
        old_balance = self.get_points(member)
        self.bot.config.set_user(member, 'points', amount)
        
        await ctx.send(f"✅ Set {member.mention}'s points to {amount:,} (was {old_balance:,})")
async def setup(bot):
    await bot.add_cog(Points(bot))
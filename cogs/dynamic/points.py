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
    
    @commands.command(name='add_points')
    @commands.has_permissions(administrator=True)
    async def admin_add_points(self, ctx, member: discord.Member, amount: int):
        """Add points to a user (Admin only). Amount can be negative to subtract."""
        new_total = self.add_points(member, amount)
        
        if amount > 0:
            await ctx.send(f"✅ Added {amount:,} points to {member.mention}. New balance: {new_total:,}")
        else:
            await ctx.send(f"✅ Removed {abs(amount):,} points from {member.mention}. New balance: {new_total:,}")
    
    @commands.command(name='set_points')
    @commands.has_permissions(administrator=True)
    async def admin_set_points(self, ctx, member: discord.Member, amount: int):
        """Set a user's points to a specific amount (Admin only)."""
        if amount < 0:
            await ctx.send("Amount cannot be negative!")
            return
        
        old_balance = self.get_points(member)
        self.bot.config.set_user(member, 'points', amount)
        
        await ctx.send(f"✅ Set {member.mention}'s points to {amount:,} (was {old_balance:,})")
    
    # ===================
    # TEMPORARY BACKFILL COMMANDS
    # ===================
    
    @commands.command(name='backfill_counting_history')
    @commands.has_permissions(administrator=True)
    async def backfill_counting_history(self, ctx, limit: int = 10000):
        """Analyze counting channel history and automatically backfill points (Admin only, one-time use)."""
        counting_channel = discord.utils.get(ctx.guild.channels, name="counting")
        if not counting_channel:
            await ctx.send("❌ No #counting channel found!")
            return
        
        await ctx.send(f"🔍 Analyzing up to {limit:,} messages in #counting and applying backfill...")
        
        user_counts = {}
        total_messages = 0
        valid_counts = 0
        
        # Analyze message history
        async for message in counting_channel.history(limit=limit):
            if message.author.bot:
                continue
                
            total_messages += 1
            
            # Try to parse as number
            try:
                num = int(message.content.strip())
                if message.author.id not in user_counts:
                    user_counts[message.author.id] = {
                        'user': message.author,
                        'valid_counts': 0,
                        'estimated_rewards': 0
                    }
                
                user_counts[message.author.id]['valid_counts'] += 1
                valid_counts += 1
                
            except ValueError:
                # Not a valid number
                continue
        
        if not user_counts:
            await ctx.send("❌ No valid counting messages found!")
            return
        
        # Calculate estimated rewards (20% chance, weighted by tier)
        REWARD_CHANCE = 0.20
        tier_points = {"common": 2, "uncommon": 3, "rare": 4, "epic": 5}
        tier_weights = {"common": 8, "uncommon": 4, "rare": 2, "epic": 1}
        total_weight = sum(tier_weights.values())  # 15
        
        # Calculate weighted average reward points
        avg_reward_points = sum(
            (tier_weights[tier] / total_weight) * tier_points[tier] 
            for tier in tier_points
        )  # ≈ 2.67 points per reward
        
        # Apply backfill points
        backfill_results = []
        total_points_awarded = 0
        
        for user_id, data in user_counts.items():
            user = data['user']
            counts = data['valid_counts']
            estimated_reward_points = counts * REWARD_CHANCE * avg_reward_points
            total_backfill = counts + round(estimated_reward_points)
            
            # Apply the points
            new_balance = self.add_points(user, total_backfill)
            total_points_awarded += total_backfill
            
            backfill_results.append({
                'user': user,
                'counts': counts,
                'rewards': round(estimated_reward_points),
                'total': total_backfill,
                'new_balance': new_balance
            })
        
        # Sort by total points awarded
        backfill_results.sort(key=lambda x: x['total'], reverse=True)
        
        # Build result message
        result_lines = [
            f"✅ **Counting History Backfill Complete!**",
            f"Analyzed {total_messages:,} messages, found {valid_counts:,} valid counts",
            f"Total points awarded: {total_points_awarded:,}",
            "",
            "**Points Awarded:**"
        ]
        
        mentions = []
        for i, data in enumerate(backfill_results, 1):
            user = data['user']
            counts = data['counts']
            rewards = data['rewards']
            total = data['total']
            new_balance = data['new_balance']
            
            result_lines.append(
                f"{i}. {user.mention}: {counts:,} + {rewards:,} = **{total:,}** pts (Balance: {new_balance:,})"
            )
            mentions.append(user.mention)
        
        # Split into multiple messages if too long
        current_message = ""
        for line in result_lines:
            if len(current_message + line + "\n") > 1900:
                await ctx.send(current_message)
                current_message = line + "\n"
            else:
                current_message += line + "\n"
        
        if current_message:
            await ctx.send(current_message)
        
        # Ping everyone involved
        if mentions:
            chunks = []
            current_chunk = ""
            for mention in mentions:
                if len(current_chunk + mention + " ") > 1900:
                    chunks.append(current_chunk.strip())
                    current_chunk = mention + " "
                else:
                    current_chunk += mention + " "
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            for chunk in chunks:
                await ctx.send(f"🎉 **Backfill complete for:** {chunk}")

async def setup(bot):
    await bot.add_cog(Points(bot))
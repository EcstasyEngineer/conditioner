import discord
from discord.ext import commands
import random
import os
import json
import re
from pathlib import Path

# Configuration
# Overall chance of getting any reward
OVERALL_REWARD_CHANCE = 1/5  # 20% chance of any reward

# Relative weights for tier distribution when a reward is earned
# Higher numbers = more common within rewards
TIER_WEIGHTS = {
    "common": 8,     # Most common tier
    "uncommon": 4,   # Half as common as common
    "rare": 2,       # Half as common as uncommon  
    "epic": 1,       # Rarest tier
}

# Calculate total weight for normalization
TOTAL_WEIGHT = sum(TIER_WEIGHTS.values())

TIER_EMOJIS = {
    "common": "<:whitespiral:1358827227243872486>",
    "uncommon": "<:bluespiral:1358827225847435355>",
    "rare": "<:greenspiral:1358827224349802609>",
    "epic": "<:purplespiral:1358827222437200048>",
}

TIER_MEDIA_PATHS = {
    "common": "media/common/",
    "uncommon": "media/uncommon/",
    "rare": "media/rare/",
    "epic": "media/epic/",
}

class GachaRewards(commands.Cog):
    """Cog for managing gacha-style rewards in counting channel."""
    
    def __init__(self, bot):
        self.bot = bot
        # In-memory tracking of active reward listeners
        self.listeners = {}  # {message_id: {"user_id": user_id, "tier": tier_name}}
        # Load file counts for "X out of Y" display
        self.file_counts = self.load_file_counts()
        
    def load_file_counts(self):
        """Load file counts from JSON for 'X out of Y' display."""
        try:
            with open('media_file_counts.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Fallback: count files directly
            counts = {}
            for tier in TIER_MEDIA_PATHS:
                path = Path(TIER_MEDIA_PATHS[tier])
                if path.exists():
                    valid_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.mp3', '.mp4', '.txt')
                    files = [f for f in path.glob('*') if f.suffix.lower() in valid_extensions and f.name.lower() != 'sample.gif']
                    counts[tier] = len(files)
                else:
                    counts[tier] = 0
            return counts

    def calculate_tier_probabilities(self, exclude_common=False):
        """Calculate normalized probabilities for each tier."""
        weights = TIER_WEIGHTS.copy()
        if exclude_common:
            weights.pop('common', None)
        
        total = sum(weights.values())
        if total == 0:
            return {}
        
        return {tier: weight / total for tier, weight in weights.items()}
    
    def select_tier_by_weight(self, exclude_common=False):
        """Select a tier based on relative weights."""
        probabilities = self.calculate_tier_probabilities(exclude_common)
        if not probabilities:
            return None
            
        roll = random.random()
        cumulative = 0
        
        for tier, prob in probabilities.items():
            cumulative += prob
            if roll < cumulative:
                return tier
        
        # Fallback to last tier
        return list(probabilities.keys())[-1]

    def get_reward_tier(self, count_number=None):
        """Two-stage probability check: first check if any reward, then which tier.
        Special guarantees for 69 and 420 endings."""
        
        # Check for special number guarantees (69, 420 endings)
        if count_number is not None:
            if str(count_number).endswith('69') or str(count_number).endswith('420'):
                # 100% chance of reward, 1/3 epic, 2/3 rare
                return "epic" if random.random() < 1/3 else "rare"
        
        # Stage 1: Check if we get any reward at all
        if random.random() >= OVERALL_REWARD_CHANCE:
            return None  # No reward
        
        # Stage 2: Select which tier based on relative weights
        return self.select_tier_by_weight()

    def get_random_media_file(self, tier):
        """Select a random media file from the tier's directory."""
        path = Path(TIER_MEDIA_PATHS[tier])
        
        # Get all media files including .txt files
        valid_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.mp3', '.mp4', '.mov', '.webm', '.txt')
        # Get all valid media files
        media_files = [f for f in path.glob('*') if f.suffix.lower() in valid_extensions]
        
        # If there are multiple files, filter out sample.gif
        if len(media_files) > 1:
            media_files = [f for f in media_files if f.name.lower() != 'sample.gif']
        
        if not media_files:
            return None
            
        selected_file = random.choice(media_files)
        
        # For numbered files, extract the number for "X out of Y" display
        file_number = None
        if selected_file.stem.isdigit():
            file_number = int(selected_file.stem)
        
        return selected_file, file_number
    
    def has_auto_claim(self, user):
        """Check if a user has auto-claim enabled via user config."""
        return self.bot.config.get_user(user, 'auto_claim_gacha', False)
    
    async def send_reward(self, user, tier, channel, is_auto_claim=False):
        """Send reward to user, either instantly or after manual claim."""
        result = self.get_random_media_file(tier)
        
        if result:
            media_file, file_number = result
            
            # Get total count for this tier
            total_count = self.file_counts.get(tier, 0)
            
            # Create "X out of Y" message part for DM
            count_info = ""
            if file_number and total_count > 0:
                count_info = f" ({file_number}/{total_count})"
            
            # Determine deletion timing based on tier
            delete_after = 30.0 if tier == "common" else (7200.0 if tier == "uncommon" else None)
            
            # Create mysterious/alluring public messages based on tier and claim type
            if is_auto_claim:
                messages = {
                    "common": f"*{user.mention} has been... instantly rewarded*",
                    "uncommon": f"✨ *Something special manifests for {user.mention}* ✨", 
                    "rare": f"🌙 *The depths instantly respond to {user.mention}* 🌙",
                    "epic": f"🌟 *{user.mention} has been blessed with something... extraordinary* 🌟"
                }
            else:
                messages = {
                    "common": f"*{user.mention} has been... rewarded*",
                    "uncommon": f"✨ *Something special awaits {user.mention}* ✨", 
                    "rare": f"🌙 *The depths call to {user.mention}* 🌙",
                    "epic": f"🌟 *{user.mention} has earned something... extraordinary* 🌟"
                }
            
            await channel.send(
                messages[tier],
                delete_after=delete_after,
            )
            
            # Send the media file or link content as DM with collection info
            if media_file.suffix.lower() == '.txt':
                # Read and send link content
                try:
                    with open(media_file, 'r') as f:
                        link_content = f.read().strip()
                    await user.send(f"Your {tier} reward{count_info}:\n{link_content}")
                except Exception as e:
                    await user.send(f"Error reading {tier} reward: {e}")
            else:
                # Send media file with collection info
                await user.send(f"Your {tier} reward{count_info}:", file=discord.File(media_file))
    
    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore bot messages and messages not in "counting" channel
        if message.author.bot or message.channel.name != "counting":
            return
        
        # Try to parse the message as a number
        try:
            count_number = int(message.content.strip())
        except ValueError:
            return
            
        # This is only processed for valid count messages that weren't deleted
        # Do the gacha roll for rewards (pass number for special guarantees)
        reward_tier = self.get_reward_tier(count_number)
        
        # Check for auto-claim trigger phrase
        trigger_pattern = r'\bi\s+am\s+an?\s+addicted\s+count[-\s]?slut\b'
        if re.search(trigger_pattern, message.content, re.IGNORECASE):
            self.bot.config.set_user(message.author, 'auto_claim_gacha', True)
            await message.add_reaction('💫')  # Subtle confirmation
            # Continue processing for potential reward
        
        if reward_tier:
            # Check if user has auto-claim enabled
            if self.has_auto_claim(message.author):
                # Send instant reward without emoji interaction
                await self.send_reward(message.author, reward_tier, message.channel, is_auto_claim=True)
            else:
                # Normal emoji-based interaction
                # Add appropriate reaction based on tier
                emoji = discord.PartialEmoji.from_str(TIER_EMOJIS[reward_tier])
                await message.add_reaction(emoji)
                
                # Store message in listeners
                self.listeners[message.id] = {
                    "user_id": message.author.id,
                    "tier": reward_tier
                }
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return
            
        message_id = payload.message_id
        
        # Check if this is a message we're tracking
        if message_id not in self.listeners:
            return
            
        # Get the reward info
        reward_info = self.listeners[message_id]
        
        # Check if the emoji matches the reward tier
        expected_emoji = TIER_EMOJIS[reward_info["tier"]]
        if str(payload.emoji.id) not in expected_emoji:
            return
            
        # Get channel to send responses
        channel = await self.bot.fetch_channel(payload.channel_id)
        
        # Check if the user who reacted is the one who earned the reward
        if payload.user_id == reward_info["user_id"]:
            # User claimed their own reward
            user = self.bot.get_user(payload.user_id)
            if user:
                await self.send_reward(user, reward_info["tier"], channel, is_auto_claim=False)
            
            # Remove this message from listeners
            del self.listeners[message_id]
        else:
            # Someone else tried to claim the reward
            try:
                # Get the message to reply to
                message = await channel.fetch_message(payload.message_id)
                # Get the user who tried to claim and send them a DM
                user = self.bot.get_user(payload.user_id)
                if user:
                    await user.send("Only the winner can redeem this reward. Try your luck by counting!")
            except discord.NotFound:
                # Message was deleted
                pass
    
    @commands.command(name='disable_auto_gacha', aliases=['stop_auto_gacha', 'gacha_normal'])
    async def disable_auto_gacha(self, ctx):
        """Disable auto-claim for gacha rewards (return to normal emoji claiming)."""
        self.bot.config.set_user(ctx.author, 'auto_claim_gacha', False)
        await ctx.send("Auto-claim disabled. You'll need to react to claim rewards again.")
    
    @commands.command(name='gacha_status')
    async def gacha_status(self, ctx):
        """Check your current gacha auto-claim status."""
        is_auto = self.bot.config.get_user(ctx.author, 'auto_claim_gacha', False)
        if is_auto:
            await ctx.send("🌀 Auto-claim is **enabled** - you receive rewards instantly!")
        else:
            await ctx.send("⭐ Auto-claim is **disabled** - react to emojis to claim rewards.")
    
    @commands.command(name='gacha_help')
    async def gacha_help(self, ctx):
        """Show help for gacha system including secret trigger."""
        help_text = """
**🎰 Gacha Reward System 🎰**

**How it works:**
• 20% chance of reward when counting
• React to the spiral emoji to claim your reward
• Special guarantees for numbers ending in 69 or 420

**Reward Tiers:**
• <:whitespiral:1358827227243872486> Common (30s auto-delete)
• <:bluespiral:1358827225847435355> Uncommon (2h auto-delete)  
• <:greenspiral:1358827224349802609> Rare (permanent)
• <:purplespiral:1358827222437200048> Epic (permanent)

**Auto-Claim Mode:**
• Type "I am an addicted countslut" to enable instant rewards
• Use `!disable_auto_gacha` to return to normal mode
• Use `!gacha_status` to check your current mode

*In auto-claim mode, Discord notifications become your conditioning trigger* 💫
        """
        await ctx.send(help_text)

async def setup(bot):
    await bot.add_cog(GachaRewards(bot))
import discord
from discord.ext import commands
import random
import os
from pathlib import Path

# Configuration
TIER_PROBABILITIES = {
    "common": 1/10,
    "uncommon": 1/20,
    "rare": 1/40,
    "epic": 1/80,
}

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
        
    def get_reward_tier(self):
        """Stateless probability check to determine if a reward should be given and which tier.
        Rarer tiers are checked first to ensure they take priority."""
        roll = random.random()
        cumulative_prob = 0
        
        # Process tiers from rarest to most common
        for tier in ["epic", "rare", "uncommon", "common"]:
            cumulative_prob += TIER_PROBABILITIES[tier]
            if roll < cumulative_prob:
                return tier
        
        return None  # No reward

    def get_random_media_file(self, tier):
        """Select a random media file from the tier's directory."""
        path = Path(TIER_MEDIA_PATHS[tier])
        
        # Get all image/gif files in the directory
        valid_extensions = ('.png', '.jpg', '.jpeg', '.gif', ".mp3", ".mp4")
        # Get all valid media files
        media_files = [f for f in path.glob('*') if f.suffix.lower() in valid_extensions]
        
        # If there are multiple files, filter out sample.gif
        if len(media_files) > 1:
            media_files = [f for f in media_files if f.name.lower() != 'sample.gif']
        
        if not media_files:
            return None
            
        return random.choice(media_files)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore bot messages and messages not in "counting" channel
        if message.author.bot or message.channel.name != "counting":
            return
        
        # Try to parse the message as a number
        try:
            int(message.content.strip())
        except ValueError:
            return
            
        # This is only processed for valid count messages that weren't deleted
        # Do the gacha roll for rewards
        reward_tier = self.get_reward_tier()
        
        if reward_tier:
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
            media_file = self.get_random_media_file(reward_info["tier"])
            
            if media_file:
                # Determine message and deletion timing based on tier
                tier = reward_info["tier"]
                delete_after = 30.0 if tier == "common" else (7200.0 if tier == "uncommon" else None)
                
                # Create increasingly festive messages based on tier
                messages = {
                    "common": f"You claimed a common reward!",
                    "uncommon": f"✨ You claimed an uncommon reward! ✨",
                    "rare": f"🎉✨ You claimed a RARE reward! ✨🎉",
                    "epic": f"🌟🎊 You claimed an EPIC reward!!! 🎊🌟"
                }
                
                await channel.send(
                    messages[tier],
                    delete_after=delete_after,
                )
                # Send the media file as dm
                user = self.bot.get_user(payload.user_id)
                if user:
                    await user.send(file=discord.File(media_file))
                
            # Remove emoji reactions
            # message = await channel.fetch_message(message_id)
            # await message.clear_reactions()
                
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

async def setup(bot):
    await bot.add_cog(GachaRewards(bot))
import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import random
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import os
from typing import List, Dict, Optional
import difflib

class MantraSystem(commands.Cog):
    """Hypnotic mantra capture system with adaptive delivery."""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger if hasattr(bot, 'logger') else None
        self.mantras_dir = Path("mantras/themes")
        self.themes = self.load_themes()
        
        # Public channel for bonus points (can be set by admin)
        self.public_channel_id = None  # Will be loaded from guild config
        self.public_bonus_multiplier = 2.0  # Double points for public mantras
        
        # Start the mantra delivery task
        self.mantra_delivery.start()
        
        # Track active mantra challenges
        self.active_challenges = {}  # user_id: {"mantra": str, "theme": str, "difficulty": str, "base_points": int, "sent_at": datetime}
        
    async def cog_load(self):
        """Load public channel configuration when cog loads."""
        # Load public channel from guild configs
        for guild in self.bot.guilds:
            public_channel = self.bot.config.get(guild, 'mantra_public_channel', None)
            if public_channel:
                self.public_channel_id = public_channel
                break  # Use first configured channel found
    
    def cog_unload(self):
        """Clean up when cog is unloaded."""
        self.mantra_delivery.cancel()
        
    def load_themes(self) -> Dict[str, Dict]:
        """Load all theme files from the mantras directory."""
        themes = {}
        
        if not self.mantras_dir.exists():
            if self.logger:
                self.logger.warning("Mantras directory not found")
            return themes
            
        for theme_file in self.mantras_dir.glob("*.json"):
            try:
                with open(theme_file, 'r') as f:
                    theme_data = json.load(f)
                    themes[theme_data["theme"]] = theme_data
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to load theme {theme_file}: {e}")
                    
        return themes
    
    def get_user_mantra_config(self, user) -> Dict:
        """Get user's mantra configuration."""
        default_config = {
            "enrolled": False,
            "themes": [],
            "pet_name": "puppet",
            "dominant_title": "Master",
            "frequency": 1.0,  # encounters per day
            "last_encounter": None,
            "next_encounter": None,
            "encounters": [],
            "consecutive_timeouts": 0,
            "total_points_earned": 0,
            "online_only": True
        }
        
        config = self.bot.config.get_user(user, 'mantra_system', {})
        
        # If config is empty or not a dict, use defaults
        if not isinstance(config, dict):
            config = default_config.copy()
        else:
            # Ensure all fields exist
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
                    
        return config
    
    def save_user_mantra_config(self, user, config):
        """Save user's mantra configuration."""
        self.bot.config.set_user(user, 'mantra_system', config)
        # Force save to disk
        self.bot.config.flush()
    
    def format_mantra(self, mantra_text: str, pet_name: str, dominant_title: str) -> str:
        """Replace template variables in mantra text."""
        return mantra_text.format(
            pet_name=pet_name,
            dominant_title=dominant_title
        )
    
    def calculate_speed_bonus(self, response_time_seconds: int) -> int:
        """Calculate speed bonus based on response time."""
        if response_time_seconds <= 30:
            return 20
        elif response_time_seconds <= 60:
            return 15
        elif response_time_seconds <= 120:
            return 10
        elif response_time_seconds <= 300:
            return 5
        else:
            return 0
    
    def check_mantra_match(self, user_response: str, expected_mantra: str) -> bool:
        """Check if user response matches mantra with typo tolerance."""
        # Exact match (case insensitive)
        if user_response.lower() == expected_mantra.lower():
            return True
            
        # Calculate similarity ratio
        ratio = difflib.SequenceMatcher(None, user_response.lower(), expected_mantra.lower()).ratio()
        
        # Accept if 80% similar or better
        return ratio >= 0.8
    
    async def should_send_mantra(self, user) -> bool:
        """Check if we should send a mantra to this user."""
        config = self.get_user_mantra_config(user)
        
        # Not enrolled
        if not config["enrolled"]:
            return False
            
        # No themes selected
        if not config["themes"]:
            return False
            
        # Check online status if required
        if config["online_only"]:
            # Check if user is online/idle/dnd (not offline or invisible)
            # Need to check member status in at least one mutual guild
            is_online = False
            for guild in self.bot.guilds:
                member = guild.get_member(user.id)
                if member and member.status != discord.Status.offline:
                    is_online = True
                    break
            
            if not is_online:
                return False
        
        
        # Check if it's time for next encounter
        if config["next_encounter"]:
            next_time = datetime.fromisoformat(config["next_encounter"])
            if datetime.now() < next_time:
                return False
                
        return True
    
    def select_mantra_for_user(self, config: Dict) -> Optional[Dict]:
        """Select a mantra based on user's themes and progression."""
        available_mantras = []
        
        # Collect mantras from selected themes
        for theme_name in config["themes"]:
            if theme_name in self.themes:
                theme = self.themes[theme_name]
                for mantra in theme["mantras"]:
                    # For now, include all difficulties
                    # TODO: Add progression gating for extreme content
                    available_mantras.append({
                        **mantra,
                        "theme": theme_name
                    })
        
        if not available_mantras:
            return None
            
        # Weight selection toward moderate difficulty
        # Could be enhanced with user performance tracking
        return random.choice(available_mantras)
    
    def schedule_next_encounter(self, config: Dict):
        """Schedule the next mantra encounter based on frequency."""
        # Base frequency is encounters per day
        frequency = config["frequency"]
        
        # Calculate average hours between encounters
        if frequency > 0:
            hours_between = 24 / frequency
            
            # Add randomization (-25% to +25%)
            variation = random.uniform(0.75, 1.25)
            actual_hours = hours_between * variation
            
            # Minimum 2 hours between encounters
            actual_hours = max(2.0, actual_hours)
            
            next_time = datetime.now() + timedelta(hours=actual_hours)
            config["next_encounter"] = next_time.isoformat()
        else:
            # Frequency 0 means disabled
            config["next_encounter"] = None
    
    def adjust_frequency(self, config: Dict, success: bool, response_time: Optional[int] = None):
        """Adjust encounter frequency based on engagement."""
        current_freq = config["frequency"]
        
        if success:
            # Reset timeout counter on success
            config["consecutive_timeouts"] = 0
            
            # Increase frequency for fast responses
            if response_time and response_time < 120:  # Under 2 minutes
                new_freq = min(3.0, current_freq * 1.1)  # Max 3/day
            else:
                new_freq = min(3.0, current_freq * 1.05)
                
            config["frequency"] = new_freq
        else:
            # Timeout/miss
            config["consecutive_timeouts"] += 1
            
            # Decrease frequency
            new_freq = max(0.33, current_freq * 0.9)  # Min 1 per 3 days
            config["frequency"] = new_freq
            
            # Auto-disable after 2 consecutive timeouts
            if config["consecutive_timeouts"] >= 2:
                config["enrolled"] = False
                config["frequency"] = 1.0  # Reset to default for re-enrollment
                return True  # Signal that we auto-disabled
                
        return False
    
    @tasks.loop(minutes=5)
    async def mantra_delivery(self):
        """Main task loop for delivering mantras."""
        # Get all user configs
        for user_id in list(self.active_challenges.keys()):
            # Check for expired challenges (20 minute timeout)
            challenge = self.active_challenges[user_id]
            if datetime.now() > challenge["sent_at"] + timedelta(minutes=20):
                # Challenge expired
                user = self.bot.get_user(user_id)
                if user:
                    config = self.get_user_mantra_config(user)
                    
                    # Record the miss
                    encounter = {
                        "timestamp": challenge["sent_at"].isoformat(),
                        "mantra": challenge["mantra"],
                        "theme": challenge["theme"],
                        "difficulty": challenge["difficulty"],
                        "base_points": challenge["base_points"],
                        "completed": False,
                        "expired": True
                    }
                    config["encounters"].append(encounter)
                    
                    # Adjust frequency and check for auto-disable
                    auto_disabled = self.adjust_frequency(config, success=False)
                    
                    # Send expiration message
                    try:
                        if auto_disabled:
                            await user.send(
                                "Mantra expired. Due to multiple timeouts, mantras have been disabled.\n"
                                "Use `/mantra enroll` to re-enable when you're ready!"
                            )
                        else:
                            await user.send(
                                "Mantra expired.\n"
                                f"You missed: '{challenge['mantra']}'"
                            )
                    except discord.Forbidden:
                        pass
                    
                    self.save_user_mantra_config(user, config)
                    
                # Remove from active challenges
                del self.active_challenges[user_id]
        
        # Check for users who need mantras
        all_users = self.bot.users
        for user in all_users:
            if user.bot or user.id in self.active_challenges:
                continue
                
            if await self.should_send_mantra(user):
                config = self.get_user_mantra_config(user)
                
                # Select a mantra
                mantra_data = self.select_mantra_for_user(config)
                if not mantra_data:
                    continue
                
                # Format the mantra
                formatted_mantra = self.format_mantra(
                    mantra_data["text"],
                    config["pet_name"],
                    config["dominant_title"]
                )
                
                # Send the challenge
                try:
                    embed = discord.Embed(
                        title="🌀 Mantra Challenge",
                        description=f"Repeat this for **{mantra_data['base_points']} points**:\n\n**{formatted_mantra}**",
                        color=discord.Color.purple()
                    )
                    embed.set_footer(text="You have 20 minutes to respond")
                    
                    await user.send(embed=embed)
                    
                    # Track the challenge
                    self.active_challenges[user.id] = {
                        "mantra": formatted_mantra,
                        "theme": mantra_data["theme"],
                        "difficulty": mantra_data["difficulty"],
                        "base_points": mantra_data["base_points"],
                        "sent_at": datetime.now()
                    }
                    
                    # Update last encounter time and schedule next
                    config["last_encounter"] = datetime.now().isoformat()
                    self.schedule_next_encounter(config)
                    self.save_user_mantra_config(user, config)
                    
                except discord.Forbidden:
                    # Can't DM user
                    if self.logger:
                        self.logger.info(f"Cannot DM user {user.id} for mantra delivery")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error sending mantra to {user.id}: {e}")
    
    @mantra_delivery.before_loop
    async def before_mantra_delivery(self):
        """Wait for bot to be ready before starting delivery loop."""
        await self.bot.wait_until_ready()
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for mantra responses in DMs and public channel."""
        # Ignore bot messages
        if message.author.bot:
            return
            
        # Check if user has an active challenge
        if message.author.id not in self.active_challenges:
            return
            
        challenge = self.active_challenges[message.author.id]
        
        # Determine if this is a valid response channel
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_public = self.public_channel_id and message.channel.id == self.public_channel_id
        
        if not (is_dm or is_public):
            return
        
        # Check if message matches the mantra
        if self.check_mantra_match(message.content, challenge["mantra"]):
            # Calculate response time and speed bonus
            response_time = (datetime.now() - challenge["sent_at"]).total_seconds()
            speed_bonus = self.calculate_speed_bonus(int(response_time))
            base_total = challenge["base_points"] + speed_bonus
            
            # Apply public bonus if applicable
            if is_public:
                total_points = int(base_total * self.public_bonus_multiplier)
                public_bonus = total_points - base_total
            else:
                total_points = base_total
                public_bonus = 0
            
            # Award points
            points_cog = self.bot.get_cog("Points")
            if points_cog:
                points_cog.add_points(message.author, total_points)
            
            # Update user config
            config = self.get_user_mantra_config(message.author)
            config["total_points_earned"] += total_points
            
            # Record the capture
            encounter = {
                "timestamp": challenge["sent_at"].isoformat(),
                "mantra": challenge["mantra"],
                "theme": challenge["theme"],
                "difficulty": challenge["difficulty"],
                "base_points": challenge["base_points"],
                "speed_bonus": speed_bonus,
                "public_bonus": public_bonus,
                "completed": True,
                "response_time": int(response_time),
                "was_public": is_public
            }
            config["encounters"].append(encounter)
            
            # Adjust frequency
            self.adjust_frequency(config, success=True, response_time=int(response_time))
            self.save_user_mantra_config(message.author, config)
            
            # Send success message with positive reinforcement
            # Vary praise based on response time
            if response_time <= 30:
                praise = f"Excellent {config['pet_name']}! Such quick obedience!"
            elif response_time <= 60:
                praise = f"Very good {config['pet_name']}!"
            elif response_time <= 120:
                praise = f"Good {config['pet_name']}!"
            else:
                praise = f"Good {config['pet_name']}."
                
            embed = discord.Embed(
                title="✨ Success!",
                description=f"{praise} You earned **{total_points} points**!",
                color=discord.Color.green()
            )
            
            # Build breakdown
            breakdown_lines = [f"Base: {challenge['base_points']} pts"]
            if speed_bonus > 0:
                breakdown_lines.append(f"Speed bonus: +{speed_bonus} pts")
            if public_bonus > 0:
                breakdown_lines.append(f"Public bonus: +{public_bonus} pts")
            
            if len(breakdown_lines) > 1:
                embed.add_field(
                    name="Breakdown",
                    value="\n".join(breakdown_lines),
                    inline=False
                )
            
            # Add tip about public channel if configured and this was a DM response
            if self.public_channel_id and is_dm and random.random() < 0.33:  # Show 1/3 of the time
                embed.add_field(
                    name="💡 Tip",
                    value=f"Say mantras in <#{self.public_channel_id}> for {self.public_bonus_multiplier}x points!",
                    inline=False
                )
            
            current_points = points_cog.get_points(message.author) if points_cog else 0
            embed.set_footer(text=f"Total points: {current_points:,}")
            
            await message.reply(embed=embed)
            
            # Remove from active challenges
            del self.active_challenges[message.author.id]
    
    # Slash Commands - Using a group for better organization
    mantra_group = app_commands.Group(name="mantra", description="Hypnotic mantra training system")
    
    @mantra_group.command(name="enroll", description="Enroll in the mantra training system")
    @app_commands.describe(
        themes="Comma-separated list of themes (e.g., 'suggestibility,acceptance')",
        pet_name="Your preferred pet name (type custom or select from list)",
        dominant_title="Master or Mistress"
    )
    @app_commands.choices(dominant_title=[
        app_commands.Choice(name="Master", value="Master"),
        app_commands.Choice(name="Mistress", value="Mistress")
    ])
    async def mantra_enroll(
        self,
        interaction: discord.Interaction,
        themes: Optional[str] = None,
        pet_name: Optional[str] = None,
        dominant_title: Optional[str] = None
    ):
        """Enroll in the mantra training system."""
        await self.enroll_user(interaction, themes, pet_name, dominant_title)
    
    @mantra_group.command(name="status", description="Check your mantra training status")
    async def mantra_status(self, interaction: discord.Interaction):
        """Show user's mantra status and stats."""
        await self.show_status(interaction)
    
    @mantra_group.command(name="settings", description="Update your mantra settings")
    @app_commands.describe(
        pet_name="Your preferred pet name",
        dominant_title="Master or Mistress",
        theme1="First theme choice",
        theme2="Second theme choice (optional)",
        theme3="Third theme choice (optional)",
        online_only="Only receive mantras when online"
    )
    # TODO: Ideally we'd have a multi-select dropdown or allow setting themes one at a time
    # Current workaround uses theme1/theme2/theme3 due to Discord limitations
    @app_commands.choices(
        pet_name=[
            app_commands.Choice(name="puppet", value="puppet"),
            app_commands.Choice(name="puppy", value="puppy"),
            app_commands.Choice(name="kitten", value="kitten"),
            app_commands.Choice(name="pet", value="pet"),
            app_commands.Choice(name="toy", value="toy"),
            app_commands.Choice(name="doll", value="doll"),
            app_commands.Choice(name="slave", value="slave"),
            app_commands.Choice(name="slut", value="slut"),
            app_commands.Choice(name="bimbo", value="bimbo"),
            app_commands.Choice(name="drone", value="drone")
        ],
        dominant_title=[
            app_commands.Choice(name="Master", value="Master"),
            app_commands.Choice(name="Mistress", value="Mistress")
        ],
        theme1=[
            app_commands.Choice(name="Suggestibility", value="suggestibility"),
            app_commands.Choice(name="Acceptance", value="acceptance")
        ],
        theme2=[
            app_commands.Choice(name="None", value="none"),
            app_commands.Choice(name="Suggestibility", value="suggestibility"),
            app_commands.Choice(name="Acceptance", value="acceptance")
        ],
        theme3=[
            app_commands.Choice(name="None", value="none"),
            app_commands.Choice(name="Suggestibility", value="suggestibility"),
            app_commands.Choice(name="Acceptance", value="acceptance")
        ]
    )
    async def mantra_settings(
        self,
        interaction: discord.Interaction,
        pet_name: Optional[str] = None,
        dominant_title: Optional[str] = None,
        theme1: Optional[str] = None,
        theme2: Optional[str] = None,
        theme3: Optional[str] = None,
        online_only: Optional[bool] = None
    ):
        """Update mantra settings."""
        # Collect themes
        themes_list = []
        if theme1 and theme1 != "none":
            themes_list.append(theme1)
        if theme2 and theme2 != "none" and theme2 not in themes_list:
            themes_list.append(theme2)
        if theme3 and theme3 != "none" and theme3 not in themes_list:
            themes_list.append(theme3)
        
        await self.update_settings(interaction, pet_name, dominant_title, themes_list, online_only)
    
    @mantra_group.command(name="disable", description="Disable mantra training")
    async def mantra_disable(self, interaction: discord.Interaction):
        """Disable mantra encounters."""
        await self.disable_mantras(interaction)
    
    
    async def enroll_user(
        self,
        interaction: discord.Interaction,
        themes_str: Optional[str],
        pet_name: Optional[str],
        dominant_title: Optional[str]
    ):
        """Enroll user in mantra system."""
        config = self.get_user_mantra_config(interaction.user)
        
        # Parse themes
        if themes_str:
            requested_themes = [t.strip().lower() for t in themes_str.split(",")]
            valid_themes = [t for t in requested_themes if t in self.themes]
            
            if not valid_themes:
                await interaction.response.send_message(
                    "No valid themes found. Use `/mantra themes` to see available themes.",
                    ephemeral=True
                )
                return
        else:
            valid_themes = ["suggestibility", "acceptance"]  # Default starter themes
        
        # Update config
        config["enrolled"] = True
        config["themes"] = valid_themes
        config["pet_name"] = pet_name or config["pet_name"]
        config["dominant_title"] = dominant_title if dominant_title else config["dominant_title"]
        config["consecutive_timeouts"] = 0  # Reset on re-enrollment
        
        # Schedule first encounter
        self.schedule_next_encounter(config)
        self.save_user_mantra_config(interaction.user, config)
        
        # Debug log
        if self.logger:
            self.logger.info(f"Enrolled {interaction.user} with config: {config}")
            # Verify save
            saved_config = self.get_user_mantra_config(interaction.user)
            self.logger.info(f"Verified saved config: enrolled={saved_config['enrolled']}, themes={saved_config['themes']}")
        
        # Send confirmation
        embed = discord.Embed(
            title="🌀 Enrolled in Mantra Training!",
            description="You will receive mantra challenges via DM.",
            color=discord.Color.purple()
        )
        embed.add_field(name="Pet Name", value=config["pet_name"], inline=True)
        embed.add_field(name="Dominant", value=config["dominant_title"], inline=True)
        embed.add_field(name="Themes", value=", ".join(config["themes"]), inline=False)
        embed.add_field(
            name="Next Steps",
            value="• Wait for mantras to appear in DMs\n"
                  "• Repeat them quickly for bonus points\n"
                  "• Use `/mantra status` to check progress",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def show_status(self, interaction: discord.Interaction):
        """Show user's mantra status and stats."""
        config = self.get_user_mantra_config(interaction.user)
        
        if not config["enrolled"]:
            await interaction.response.send_message(
                "You're not enrolled in mantra training. Use `/mantra enroll` to start!",
                ephemeral=True
            )
            return
        
        # Create main embed
        embed = discord.Embed(
            title="🌀 Your Mantra Profile",
            color=discord.Color.purple()
        )
        
        # Settings section
        embed.add_field(name="Pet Name", value=config["pet_name"], inline=True)
        embed.add_field(name="Dominant", value=config["dominant_title"], inline=True)
        embed.add_field(name="Themes", value=", ".join(config["themes"]) or "None", inline=True)
        embed.add_field(name="Frequency", value=f"{config['frequency']:.1f}/day", inline=True)
        embed.add_field(name="Online Only", value="Yes" if config["online_only"] else "No", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Empty field for alignment
        
        # Stats section
        total_sent = len(config["encounters"])
        if total_sent > 0:
            total_captured = sum(1 for e in config["encounters"] if e.get("completed", False))
            capture_rate = (total_captured / total_sent * 100)
            
            # Average response time for completed mantras
            response_times = [e["response_time"] for e in config["encounters"] 
                             if e.get("completed", False) and "response_time" in e]
            avg_response = sum(response_times) / len(response_times) if response_times else 0
            
            embed.add_field(name="\u200b", value="**📊 Statistics**", inline=False)
            embed.add_field(name="Total Sent", value=str(total_sent), inline=True)
            embed.add_field(name="Captured", value=str(total_captured), inline=True)
            embed.add_field(name="Capture Rate", value=f"{capture_rate:.1f}%", inline=True)
            embed.add_field(name="Points Earned", value=f"{config['total_points_earned']:,}", inline=True)
            embed.add_field(name="Avg Response", value=f"{avg_response:.0f}s", inline=True)
            embed.add_field(name="Public Captures", value=sum(1 for e in config["encounters"] if e.get("was_public", False)), inline=True)
            
            # Recent mantras
            recent = config["encounters"][-5:]  # Last 5
            if recent:
                recent_text = []
                for enc in reversed(recent):
                    if enc.get("completed"):
                        pts = enc['base_points'] + enc.get('speed_bonus', 0) + enc.get('public_bonus', 0)
                        public = "🌍 " if enc.get("was_public", False) else ""
                        recent_text.append(f"✅ {public}{enc['theme']} ({pts}pts)")
                    else:
                        recent_text.append(f"❌ {enc['theme']} (missed)")
                
                embed.add_field(
                    name="Recent Mantras",
                    value="\n".join(recent_text),
                    inline=False
                )
        else:
            embed.add_field(name="\u200b", value="*No mantras sent yet*", inline=False)
        
        embed.set_footer(text="Use /mantra settings to update your preferences")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    
    async def update_settings(
        self,
        interaction: discord.Interaction,
        pet_name: Optional[str],
        dominant_title: Optional[str],
        themes_list: Optional[List[str]],
        online_only: Optional[bool]
    ):
        """Update user's mantra settings."""
        config = self.get_user_mantra_config(interaction.user)
        
        # Track what was updated
        updates = []
        
        if pet_name is not None:
            config["pet_name"] = pet_name
            updates.append(f"Pet name → {pet_name}")
        
        if dominant_title is not None:
            config["dominant_title"] = dominant_title
            updates.append(f"Dominant → {dominant_title}")
        
        if themes_list is not None:
            config["themes"] = themes_list
            updates.append(f"Themes → {', '.join(themes_list) if themes_list else 'None'}")
        
        if online_only is not None:
            config["online_only"] = online_only
            updates.append(f"Online only → {'Yes' if online_only else 'No'}")
        
        if not updates:
            await interaction.response.send_message(
                "No settings were provided to update.",
                ephemeral=True
            )
            return
        
        # Save the updated config
        self.save_user_mantra_config(interaction.user, config)
        
        # Send confirmation
        embed = discord.Embed(
            title="✅ Settings Updated",
            description="\n".join(updates),
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    
    async def disable_mantras(self, interaction: discord.Interaction):
        """Disable mantra encounters."""
        config = self.get_user_mantra_config(interaction.user)
        config["enrolled"] = False
        config["next_encounter"] = None
        self.save_user_mantra_config(interaction.user, config)
        
        # Remove any active challenge
        if interaction.user.id in self.active_challenges:
            del self.active_challenges[interaction.user.id]
        
        embed = discord.Embed(
            title="❌ Mantras Disabled",
            description="You will no longer receive mantra challenges.\n\n"
                       "Use `/mantra enroll` to re-enable at any time!",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(MantraSystem(bot))
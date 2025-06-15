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
        
        # Start the mantra delivery task
        self.mantra_delivery.start()
        
        # Track active mantra challenges
        self.active_challenges = {}  # user_id: {"mantra": str, "theme": str, "difficulty": str, "base_points": int, "sent_at": datetime}
        
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
            "pet_name": "pet",
            "dominant_title": "Master",
            "frequency": 1.0,  # encounters per day
            "last_encounter": None,
            "next_encounter": None,
            "encounters": [],
            "consecutive_timeouts": 0,
            "total_points_earned": 0,
            "online_only": True,
            "active_hours": [8, 23],  # 8 AM to 11 PM
            "public_channel": None
        }
        
        config = self.bot.config.get_user(user, 'mantra_system', default_config)
        
        # Ensure all fields exist (for users with old configs)
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
                
        return config
    
    def save_user_mantra_config(self, user, config):
        """Save user's mantra configuration."""
        self.bot.config.set_user(user, 'mantra_system', config)
    
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
            member = self.bot.get_user(user.id)
            if member and member.status == discord.Status.offline:
                return False
        
        # Check active hours
        current_hour = datetime.now().hour
        start_hour, end_hour = config["active_hours"]
        if start_hour <= end_hour:
            if not (start_hour <= current_hour < end_hour):
                return False
        else:  # Handles overnight ranges like 22-6
            if not (current_hour >= start_hour or current_hour < end_hour):
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
                                "The mantra escaped... Due to multiple timeouts, mantras have been disabled.\n"
                                "Use `/mantra enroll` to re-enable when you're ready!"
                            )
                        else:
                            await user.send(
                                "The mantra escaped... Better luck next time!\n"
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
                        title="🌀 A wild mantra appears!",
                        description=f"Repeat this for **{mantra_data['base_points']} points**:\n\n**{formatted_mantra}**",
                        color=discord.Color.purple()
                    )
                    embed.add_field(
                        name="Speed Bonuses",
                        value="🏃 0-30s: +20pts\n⚡ 31-60s: +15pts\n🚶 61-120s: +10pts\n🐌 121-300s: +5pts",
                        inline=True
                    )
                    embed.set_footer(text="You have 20 minutes to capture this mantra!")
                    
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
        """Listen for mantra responses in DMs."""
        # Only process DMs
        if not isinstance(message.channel, discord.DMChannel):
            return
            
        # Ignore bot messages
        if message.author.bot:
            return
            
        # Check if user has an active challenge
        if message.author.id not in self.active_challenges:
            return
            
        challenge = self.active_challenges[message.author.id]
        
        # Check if message matches the mantra
        if self.check_mantra_match(message.content, challenge["mantra"]):
            # Calculate response time and speed bonus
            response_time = (datetime.now() - challenge["sent_at"]).total_seconds()
            speed_bonus = self.calculate_speed_bonus(int(response_time))
            total_points = challenge["base_points"] + speed_bonus
            
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
                "completed": True,
                "response_time": int(response_time)
            }
            config["encounters"].append(encounter)
            
            # Adjust frequency
            self.adjust_frequency(config, success=True, response_time=int(response_time))
            self.save_user_mantra_config(message.author, config)
            
            # Send success message
            embed = discord.Embed(
                title="✨ Mantra Captured!",
                description=f"You earned **{total_points} points**!",
                color=discord.Color.green()
            )
            
            if speed_bonus > 0:
                embed.add_field(
                    name="Breakdown",
                    value=f"Base: {challenge['base_points']} pts\nSpeed bonus: +{speed_bonus} pts",
                    inline=False
                )
            
            # Add tip about public channel if configured
            if config.get("public_channel"):
                embed.add_field(
                    name="💡 Tip",
                    value=f"Say mantras in <#{config['public_channel']}> for double points!",
                    inline=False
                )
            
            current_points = points_cog.get_points(message.author) if points_cog else 0
            embed.set_footer(text=f"Total points: {current_points:,}")
            
            await message.reply(embed=embed)
            
            # Remove from active challenges
            del self.active_challenges[message.author.id]
    
    # Slash Commands
    
    @app_commands.command(name="mantra", description="Manage your mantra training")
    @app_commands.describe(
        action="What would you like to do?",
        themes="Comma-separated list of themes (for enroll action)",
        pet_name="Your preferred pet name (for enroll action)",
        dominant_title="Master or Mistress (for enroll action)"
    )
    async def mantra_command(
        self, 
        interaction: discord.Interaction,
        action: discord.app_commands.Choice[str],
        themes: Optional[str] = None,
        pet_name: Optional[str] = None,
        dominant_title: Optional[discord.app_commands.Choice[str]] = None
    ):
        """Main mantra system command."""
        
        if action.value == "enroll":
            await self.enroll_user(interaction, themes, pet_name, dominant_title)
        elif action.value == "status":
            await self.show_status(interaction)
        elif action.value == "settings":
            await self.show_settings(interaction)
        elif action.value == "themes":
            await self.list_themes(interaction)
        elif action.value == "disable":
            await self.disable_mantras(interaction)
    
    @mantra_command.autocomplete("action")
    async def mantra_action_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        actions = [
            app_commands.Choice(name="Enroll in mantra training", value="enroll"),
            app_commands.Choice(name="Check your status", value="status"),
            app_commands.Choice(name="View/update settings", value="settings"),
            app_commands.Choice(name="List available themes", value="themes"),
            app_commands.Choice(name="Disable mantras", value="disable"),
        ]
        return [a for a in actions if current.lower() in a.name.lower()]
    
    @mantra_command.autocomplete("dominant_title")
    async def dominant_title_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name="Master", value="Master"),
            app_commands.Choice(name="Mistress", value="Mistress"),
        ]
    
    async def enroll_user(
        self,
        interaction: discord.Interaction,
        themes_str: Optional[str],
        pet_name: Optional[str],
        dominant_title: Optional[discord.app_commands.Choice[str]]
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
        config["dominant_title"] = dominant_title.value if dominant_title else config["dominant_title"]
        config["consecutive_timeouts"] = 0  # Reset on re-enrollment
        
        # Schedule first encounter
        self.schedule_next_encounter(config)
        self.save_user_mantra_config(interaction.user, config)
        
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
        
        # Calculate stats
        total_sent = len(config["encounters"])
        total_captured = sum(1 for e in config["encounters"] if e.get("completed", False))
        capture_rate = (total_captured / total_sent * 100) if total_sent > 0 else 0
        
        # Average response time for completed mantras
        response_times = [e["response_time"] for e in config["encounters"] 
                         if e.get("completed", False) and "response_time" in e]
        avg_response = sum(response_times) / len(response_times) if response_times else 0
        
        embed = discord.Embed(
            title="📊 Your Mantra Status",
            color=discord.Color.purple()
        )
        embed.add_field(name="Total Sent", value=str(total_sent), inline=True)
        embed.add_field(name="Captured", value=str(total_captured), inline=True)
        embed.add_field(name="Capture Rate", value=f"{capture_rate:.1f}%", inline=True)
        embed.add_field(name="Points Earned", value=f"{config['total_points_earned']:,}", inline=True)
        embed.add_field(name="Avg Response", value=f"{avg_response:.0f}s", inline=True)
        embed.add_field(name="Daily Rate", value=f"{config['frequency']:.1f}/day", inline=True)
        
        # Recent mantras
        recent = config["encounters"][-5:]  # Last 5
        if recent:
            recent_text = []
            for enc in reversed(recent):
                if enc.get("completed"):
                    recent_text.append(f"✅ {enc['theme']} ({enc['base_points']}+{enc.get('speed_bonus', 0)}pts)")
                else:
                    recent_text.append(f"❌ {enc['theme']} (missed)")
            
            embed.add_field(
                name="Recent Mantras",
                value="\n".join(recent_text),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def show_settings(self, interaction: discord.Interaction):
        """Show current settings."""
        config = self.get_user_mantra_config(interaction.user)
        
        embed = discord.Embed(
            title="⚙️ Mantra Settings",
            color=discord.Color.purple()
        )
        embed.add_field(name="Status", value="Enrolled" if config["enrolled"] else "Not enrolled", inline=True)
        embed.add_field(name="Pet Name", value=config["pet_name"], inline=True)
        embed.add_field(name="Dominant", value=config["dominant_title"], inline=True)
        embed.add_field(name="Themes", value=", ".join(config["themes"]) or "None", inline=False)
        embed.add_field(name="Frequency", value=f"{config['frequency']:.1f} per day", inline=True)
        embed.add_field(name="Online Only", value="Yes" if config["online_only"] else "No", inline=True)
        
        start_hour, end_hour = config["active_hours"]
        embed.add_field(
            name="Active Hours",
            value=f"{start_hour}:00 - {end_hour}:00",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def list_themes(self, interaction: discord.Interaction):
        """List available themes."""
        embed = discord.Embed(
            title="📚 Available Mantra Themes",
            description="Use theme names when enrolling",
            color=discord.Color.purple()
        )
        
        for theme_name, theme_data in self.themes.items():
            mantra_count = len(theme_data["mantras"])
            embed.add_field(
                name=theme_name.title(),
                value=f"{theme_data['description']}\n*{mantra_count} mantras*",
                inline=False
            )
        
        embed.set_footer(text="More themes coming soon!")
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
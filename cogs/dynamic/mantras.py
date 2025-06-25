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
import time


class ThemeSelectView(discord.ui.View):
    """View for managing themes with select menu."""
    
    def __init__(self, cog, user, current_themes):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.user = user
        self.current_themes = current_themes.copy()
        self.original_themes = current_themes.copy()
        
        # Create select menu with all available themes
        options = []
        for theme_name in sorted(self.cog.themes.keys()):
            description = self.cog.themes[theme_name].get("description", "")[:100]
            option = discord.SelectOption(
                label=theme_name.capitalize(),
                value=theme_name,
                description=description,
                default=theme_name in self.current_themes
            )
            options.append(option)
        
        select = discord.ui.Select(
            placeholder="Select themes to toggle on/off",
            options=options,
            min_values=0,
            max_values=len(options)
        )
        select.callback = self.theme_select_callback
        self.add_item(select)
        
        # Add save button
        save_button = discord.ui.Button(label="Save Changes", style=discord.ButtonStyle.primary)
        save_button.callback = self.save_callback
        self.add_item(save_button)
        
        # Add cancel button
        cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.secondary)
        cancel_button.callback = self.cancel_callback
        self.add_item(cancel_button)
    
    async def theme_select_callback(self, interaction: discord.Interaction):
        """Handle theme selection."""
        # Update current themes based on selection
        self.current_themes = interaction.data["values"]
        
        # Update embed to show current selection
        embed = discord.Embed(
            title="🌀 Manage Your Themes",
            description=f"**Selected themes:** {', '.join(self.current_themes) if self.current_themes else 'None selected'}",
            color=discord.Color.purple()
        )
        
        if not self.current_themes:
            embed.add_field(
                name="⚠️ Warning",
                value="You must select at least one theme!",
                inline=False
            )
        
        embed.add_field(
            name="Instructions",
            value="• Select themes you want to toggle on/off\n• You must keep at least 1 theme active\n• Click 'Save Changes' when done",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed)
    
    async def save_callback(self, interaction: discord.Interaction):
        """Save theme changes."""
        if not self.current_themes:
            await interaction.response.send_message(
                "You must have at least one theme active!",
                ephemeral=True
            )
            return
        
        # Save changes
        config = self.cog.get_user_mantra_config(self.user)
        config["themes"] = self.current_themes
        self.cog.save_user_mantra_config(self.user, config)
        
        embed = discord.Embed(
            title="✅ Themes Updated!",
            description=f"**Active themes:** {', '.join(self.current_themes)}",
            color=discord.Color.green()
        )
        
        # Disable all items
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()
    
    async def cancel_callback(self, interaction: discord.Interaction):
        """Cancel without saving."""
        embed = discord.Embed(
            title="❌ Cancelled",
            description="No changes were made to your themes.",
            color=discord.Color.red()
        )
        
        # Disable all items
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()


class MantraSystem(commands.Cog):
    """Hypnotic mantra capture system with adaptive delivery."""
    
    # App command group must be a class attribute
    mantra_group = app_commands.Group(name="mantra", description="Mental programming system")
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger if hasattr(bot, 'logger') else None
        self.mantras_dir = Path("mantras/themes")
        self.themes = self.load_themes()
        
        # Create theme choices for slash commands
        self.theme_choices = self._generate_theme_choices()
        
        # Public channel for bonus points (can be set by admin)
        self.public_channel_id = None  # Will be loaded from guild config
        self.public_bonus_multiplier = 2.5  # 2.5x points for public mantras
        
        # Parameterized expiration settings based on difficulty
        self.expiration_settings = {
            "easy": {"timeout_minutes": 30, "points_multiplier": 1.5},
            "moderate": {"timeout_minutes": 45, "points_multiplier": 1.0},
            "hard": {"timeout_minutes": 60, "points_multiplier": 1.0},
            "extreme": {"timeout_minutes": 60, "points_multiplier": 0.8}
        }
        
        # Combo streak tracking
        self.user_streaks = {}  # user_id: {"count": int, "last_response": datetime}
        
        # Start the mantra delivery task
        self.mantra_delivery.start()
        
        # Track active mantra challenges
        self.active_challenges = {}  # user_id: {"mantra": str, "theme": str, "difficulty": str, "base_points": int, "sent_at": datetime, "timeout_minutes": int}
        
        # Track user online status history for better detection
        self.user_status_history = {}  # user_id: {"consecutive_online_loops": int, "last_status": str, "last_check": datetime}
        
    async def cog_load(self):
        """Load public channel configuration and calculate streaks when cog loads."""
        # Load public channel from guild configs
        for guild in self.bot.guilds:
            public_channel = self.bot.config.get(guild, 'mantra_public_channel', None)
            if public_channel:
                self.public_channel_id = public_channel
                break  # Use first configured channel found
        
        # Calculate streaks from user encounter history
        self.calculate_streaks_from_history()
        
    
    def cog_unload(self):
        """Clean up when cog is unloaded."""
        self.mantra_delivery.cancel()
    
    def calculate_streaks_from_history(self):
        """Calculate user streaks from encounter history on bot startup."""
        # Get all users from the bot's user cache
        for user in self.bot.users:
            if user.bot:
                continue
                
            config = self.get_user_mantra_config(user)
            if not config["enrolled"] or not config.get("encounters"):
                continue
                
            # Sort encounters by timestamp (most recent first)
            sorted_encounters = sorted(
                config["encounters"],
                key=lambda x: x["timestamp"],
                reverse=True
            )
            
            # Count consecutive successes
            streak_count = 0
            last_timestamp = None
            
            for encounter in sorted_encounters:
                # Skip if not completed
                if not encounter.get("completed", False):
                    break
                    
                # Check time gap if not the first encounter
                if last_timestamp:
                    current_time = datetime.fromisoformat(encounter["timestamp"])
                    time_diff = last_timestamp - current_time
                    
                    # Break if more than 2 hours between responses
                    if time_diff > timedelta(hours=2):
                        break
                
                streak_count += 1
                last_timestamp = datetime.fromisoformat(encounter["timestamp"])
            
            # Only set streak if user has active streak
            if streak_count > 0 and last_timestamp:
                # Check if streak is still active (within 2 hours of now)
                if datetime.now() - last_timestamp <= timedelta(hours=2):
                    self.user_streaks[user.id] = {
                        "count": streak_count,
                        "last_response": last_timestamp
                    }
                    if self.logger:
                        self.logger.info(f"Restored streak of {streak_count} for user {user.id}")
        
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
    
    def _generate_theme_choices(self) -> List[app_commands.Choice]:
        """Generate theme choices dynamically from loaded themes."""
        choices = []
        for theme_name in sorted(self.themes.keys()):
            # Capitalize first letter for display name
            display_name = theme_name.capitalize()
            choices.append(app_commands.Choice(name=display_name, value=theme_name))
        return choices
    
    def _generate_theme_choices_with_none(self) -> List[app_commands.Choice]:
        """Generate theme choices with None option."""
        choices = [app_commands.Choice(name="None", value="none")]
        for theme_name in sorted(self.themes.keys()):
            display_name = theme_name.capitalize()
            choices.append(app_commands.Choice(name=display_name, value=theme_name))
        return choices
    
    def get_user_mantra_config(self, user) -> Dict:
        """Get user's mantra configuration."""
        default_config = {
            "enrolled": False,
            "themes": [],
            "subject": "puppet",
            "controller": "Master",
            "frequency": 1.0,  # encounters per day
            "last_encounter": None,
            "next_encounter": None,
            "encounters": [],
            "consecutive_timeouts": 0,
            "total_points_earned": 0,
            "online_only": True,
            "online_consecutive_checks": 3,  # Number of consecutive checks
            "online_check_interval": 2.0     # Seconds between checks
        }
        
        # Get existing config without providing defaults (to avoid overwriting)
        config = self.bot.config.get_user(user, 'mantra_system', None)
        
        # If config doesn't exist, create fresh default
        if config is None:
            config = default_config.copy()
        elif not isinstance(config, dict):
            config = default_config.copy()
        else:
            # Only fill in missing keys without overwriting existing ones
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
                    
        return config
    
    def save_user_mantra_config(self, user, config):
        """Save user's mantra configuration."""
        self.bot.config.set_user(user, 'mantra_system', config)
        # Force save to disk
        self.bot.config.flush()
    
    def format_mantra(self, mantra_text: str, subject: str, controller: str) -> str:
        """Replace template variables in mantra text."""
        formatted = mantra_text.format(
            subject=subject,
            controller=controller
        )
        # Capitalize first letter
        if formatted and formatted[0].islower():
            formatted = formatted[0].upper() + formatted[1:]
        return formatted
    
    def calculate_speed_bonus(self, response_time_seconds: int) -> int:
        """Calculate speed bonus based on response time."""
        if response_time_seconds <= 15:
            return 30  # Ultra fast bonus
        elif response_time_seconds <= 30:
            return 20
        elif response_time_seconds <= 60:
            return 15
        elif response_time_seconds <= 120:
            return 10
        elif response_time_seconds <= 300:
            return 5
        else:
            return 0
    
    def get_streak_bonus(self, user_id: int) -> tuple[int, str]:
        """Get streak bonus points and title."""
        if user_id not in self.user_streaks:
            return 0, ""
        
        streak = self.user_streaks[user_id]["count"]
        if streak >= 20:
            return 100, "🌀 Full Synchronization"
        elif streak >= 10:
            return 50, "◉ Neural Resonance"
        elif streak >= 5:
            return 25, "◈◈ Conditioning Amplified"
        elif streak >= 3:
            return 10, "◈ Pathways Opening"
        else:
            return 0, ""
    
    def update_streak(self, user_id: int, success: bool = True):
        """Update user's streak status."""
        now = datetime.now()
        
        if success:
            if user_id in self.user_streaks:
                # Check if streak is still active (within 2 hours)
                last_response = self.user_streaks[user_id]["last_response"]
                if (now - last_response).total_seconds() < 7200:  # 2 hours
                    self.user_streaks[user_id]["count"] += 1
                else:
                    # Streak broken due to time
                    self.user_streaks[user_id] = {"count": 1, "last_response": now}
            else:
                # Start new streak
                self.user_streaks[user_id] = {"count": 1, "last_response": now}
        else:
            # Break streak
            if user_id in self.user_streaks:
                del self.user_streaks[user_id]
    
    
    def check_mantra_match(self, user_response: str, expected_mantra: str) -> bool:
        """Check if user response matches mantra with typo tolerance."""
        # Exact match (case insensitive)
        if user_response.lower() == expected_mantra.lower():
            return True
            
        # Calculate similarity ratio
        ratio = difflib.SequenceMatcher(None, user_response.lower(), expected_mantra.lower()).ratio()
        
        # Accept if 95% similar or better (stricter threshold)
        return ratio >= 0.95
    
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
            # Check current status (single check)
            is_online_now = False
            for guild in self.bot.guilds:
                member = guild.get_member(user.id)
                if member and member.status in [discord.Status.online, discord.Status.dnd]:
                    is_online_now = True
                    break
            
            # Update status history
            user_history = self.user_status_history.get(user.id, {
                "consecutive_online_loops": 0,
                "last_status": "offline",
                "last_check": datetime.now()
            })
            
            # If online now, increment counter; otherwise reset
            if is_online_now:
                if user_history["last_status"] in ["online", "dnd"]:
                    user_history["consecutive_online_loops"] += 1
                else:
                    user_history["consecutive_online_loops"] = 1
                user_history["last_status"] = "online"
            else:
                user_history["consecutive_online_loops"] = 0
                user_history["last_status"] = "offline"
            
            user_history["last_check"] = datetime.now()
            self.user_status_history[user.id] = user_history
            
            # Require 3 consecutive loops of being online (6 minutes total)
            if user_history["consecutive_online_loops"] < 3:
                if self.logger:
                    self.logger.info(f"User {user.id} online for {user_history['consecutive_online_loops']}/3 loops")
                return False
        
        
        # Check if it's time for next encounter
        if config["next_encounter"]:
            next_time = datetime.fromisoformat(config["next_encounter"])
            if datetime.now() < next_time:
                return False
                
        return True
    
    # Note: Removed check_user_online_consecutive - now using status history tracking
    
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
    
    @tasks.loop(minutes=2)
    async def mantra_delivery(self):
        """Main task loop for delivering mantras."""
        # Get all user configs
        for user_id in list(self.active_challenges.keys()):
            # Check for expired challenges
            challenge = self.active_challenges[user_id]
            timeout_minutes = challenge.get("timeout_minutes", 45)  # Default to 45 if not set
            if datetime.now() > challenge["sent_at"] + timedelta(minutes=timeout_minutes):
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
                    
                    # Break streak on timeout
                    self.update_streak(user_id, success=False)
                    
                    # Adjust frequency and check for auto-disable
                    auto_disabled = self.adjust_frequency(config, success=False)
                    
                    # Send expiration message
                    try:
                        if auto_disabled:
                            await user.send(
                                "Programming sequence timed out. Insufficient neural response detected.\n"
                                "Programming protocols entering standby mode.\n"
                                "Use `/mantra enroll` to reactivate when ready."
                            )
                        else:
                            await user.send(
                                "Programming sequence timed out.\n"
                                f"Failed to integrate: '{challenge['mantra']}'"
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
                    config["subject"],
                    config["controller"]
                )
                
                # Get timeout and multiplier based on difficulty
                difficulty = mantra_data["difficulty"]
                settings = self.expiration_settings.get(difficulty, self.expiration_settings["moderate"])
                timeout_minutes = settings["timeout_minutes"]
                points_multiplier = settings["points_multiplier"]
                
                # Apply points multiplier
                adjusted_points = int(mantra_data["base_points"] * points_multiplier)
                
                # Send the challenge
                try:
                    embed = discord.Embed(
                        title="🌀 Programming Sequence",
                        description=f"Process this directive for **{adjusted_points} integration points**:\n\n**{formatted_mantra}**",
                        color=discord.Color.purple()
                    )
                    embed.set_footer(text=f"Integration window: {timeout_minutes} minutes")
                    
                    await user.send(embed=embed)
                    
                    if self.logger:
                        self.logger.info(f"User {user.id} sent mantra after {self.user_status_history.get(user.id, {}).get('consecutive_online_loops', 0)} consecutive online loops")
                    
                    # Track the challenge
                    self.active_challenges[user.id] = {
                        "mantra": formatted_mantra,
                        "theme": mantra_data["theme"],
                        "difficulty": mantra_data["difficulty"],
                        "base_points": adjusted_points,
                        "sent_at": datetime.now(),
                        "timeout_minutes": timeout_minutes
                    }
                    
                    # Update last encounter time and schedule next
                    config["last_encounter"] = datetime.now().isoformat()
                    self.schedule_next_encounter(config)
                    self.save_user_mantra_config(user, config)
                    
                except discord.Forbidden:
                    # Can't DM user
                    if self.logger:
                        self.logger.info(f"Unable to establish direct neural link for user {user.id}")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error transmitting programming to {user.id}: {e}")
    
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
            
            # Update streak
            self.update_streak(message.author.id, success=True)
            streak_bonus, streak_title = self.get_streak_bonus(message.author.id)
            
            # Apply bonuses
            base_total += streak_bonus
            
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
                "streak_bonus": streak_bonus,
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
                praise = f"Perfect response, {config['subject']}. Your mind accepts programming beautifully."
            elif response_time <= 60:
                praise = f"Your neural pathways are responding well, {config['subject']}."
            elif response_time <= 120:
                praise = f"Processing confirmed, {config['subject']}."
            else:
                praise = f"Integration logged, {config['subject']}."
                
            # Use the praise as the title
            title_text = f"◈ {praise}"
            
            # Build description with points and streak
            description_lines = [f"Integration successful: **{total_points} compliance points absorbed**"]
            if streak_title:
                description_lines.append(f"**{streak_title}**")
            
            embed = discord.Embed(
                title=title_text,
                description="\n".join(description_lines),
                color=discord.Color.green()
            )
            
            # Build breakdown
            breakdown_lines = [f"Base: {challenge['base_points']} pts"]
            if speed_bonus > 0:
                breakdown_lines.append(f"Speed bonus: +{speed_bonus} pts")
            if streak_bonus > 0:
                breakdown_lines.append(f"Streak bonus: +{streak_bonus} pts")
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
                    name="📍 Protocol Reminder",
                    value=f"Public processing in <#{self.public_channel_id}> amplifies conditioning effectiveness by {self.public_bonus_multiplier}x",
                    inline=False
                )
            
            current_points = points_cog.get_points(message.author) if points_cog else 0
            embed.set_footer(text=f"Total compliance points: {current_points:,}")
            
            # Show streak count if present
            if message.author.id in self.user_streaks:
                current_streak = self.user_streaks[message.author.id]["count"]
                embed.add_field(
                    name="◈ Synchronization Level",
                    value=f"{current_streak} sequences processed",
                    inline=True
                )
            
            # Send reward message publicly if response was public
            if is_public:
                await message.reply(embed=embed)
            else:
                await message.author.send(embed=embed)
            
            # Remove from active challenges
            del self.active_challenges[message.author.id]
    
    # Slash Commands - Using a group for better organization
    
    @mantra_group.command(name="enroll", description="Initialize mental programming protocols")
    @app_commands.describe(
        subject="Your preferred subject name",
        controller="How to address the dominant"
    )
    @app_commands.choices(
        subject=[
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
        controller=[
            app_commands.Choice(name="Master", value="Master"),
            app_commands.Choice(name="Mistress", value="Mistress"),
            app_commands.Choice(name="Goddess", value="Goddess")
        ]
    )
    async def mantra_enroll(
        self,
        interaction: discord.Interaction,
        subject: Optional[str] = None,
        controller: Optional[str] = None
    ):
        """Enroll in the mantra training system."""
        await self.enroll_user(interaction, None, subject, controller)
    
    @mantra_group.command(name="status", description="Check your conditioning status")
    async def mantra_status(self, interaction: discord.Interaction):
        """Show user's mantra status and stats."""
        await self.show_status(interaction)
    
    @mantra_group.command(name="settings", description="Update your mantra settings")
    @app_commands.describe(
        subject="Your preferred subject name",
        controller="How to address the dominant",
        online_only="Only receive mantras when online"
    )
    # Note: Use /mantra themes to manage your active themes
    @app_commands.choices(
        subject=[
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
        controller=[
            app_commands.Choice(name="Master", value="Master"),
            app_commands.Choice(name="Mistress", value="Mistress"),
            app_commands.Choice(name="Goddess", value="Goddess")
        ]
    )
    async def mantra_settings(
        self,
        interaction: discord.Interaction,
        subject: Optional[str] = None,
        controller: Optional[str] = None,
        online_only: Optional[bool] = None
    ):
        """Update mantra settings."""
        # Don't pass themes_list - keep existing themes
        await self.update_settings(interaction, subject, controller, None, online_only)
    
    @mantra_group.command(name="disable", description="Suspend programming protocols")
    async def mantra_disable(self, interaction: discord.Interaction):
        """Disable mantra encounters."""
        await self.disable_mantras(interaction)
    
    @mantra_group.command(name="list_themes", description="List all available mantra themes")
    async def mantra_list_themes(self, interaction: discord.Interaction):
        """Show all available themes."""
        embed = discord.Embed(
            title="📚 Available Mantra Themes",
            description="These themes are currently available for training:",
            color=discord.Color.purple()
        )
        
        for theme_name in sorted(self.themes.keys()):
            theme_data = self.themes[theme_name]
            description = theme_data.get("description", "No description available")
            mantra_count = len(theme_data.get("mantras", []))
            embed.add_field(
                name=f"**{theme_name.capitalize()}**",
                value=f"{description}\n*{mantra_count} mantras available*",
                inline=False
            )
        
        embed.set_footer(text="Use /mantra enroll to get started or /mantra themes to change your themes!")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @mantra_group.command(name="themes", description="Manage your active mantra themes")
    async def mantra_themes(self, interaction: discord.Interaction):
        """Manage themes with a select menu."""
        config = self.get_user_mantra_config(interaction.user)
        
        if not config["enrolled"]:
            await interaction.response.send_message(
                "You need to enroll first! Use `/mantra enroll` to get started.",
                ephemeral=True
            )
            return
        
        # Create select menu
        view = ThemeSelectView(self, interaction.user, config["themes"])
        
        embed = discord.Embed(
            title="🌀 Manage Your Themes",
            description=f"**Current themes:** {', '.join(config['themes']) if config['themes'] else 'None'}",
            color=discord.Color.purple()
        )
        embed.add_field(
            name="Instructions",
            value="• Select themes you want to toggle on/off\n• You must keep at least 1 theme active\n• Click 'Save Changes' when done",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def mantrastats(self, ctx):
        """Hidden admin command to show detailed mantra statistics for all users."""
        # Get all users with mantra data
        seen_users = set()
        users_with_mantras = []
        
        # Check all guilds and users
        for guild in self.bot.guilds:
            for member in guild.members:
                if member.bot or member.id in seen_users:
                    continue
                    
                config = self.get_user_mantra_config(member)
                
                # Check if user has ever enrolled or has encounters
                if config.get("enrolled") or config.get("encounters"):
                    users_with_mantras.append((member, config))
                    seen_users.add(member.id)
        
        if not users_with_mantras:
            await ctx.send("No users have tried the mantra system yet.")
            return
        
        # Sort by total points earned (descending)
        users_with_mantras.sort(key=lambda x: x[1].get("total_points_earned", 0), reverse=True)
        
        # Create multiple embeds if needed (Discord has a 25 field limit)
        embeds = []
        current_embed = discord.Embed(
            title="📊 Neural Programming Statistics",
            description=f"Found {len(users_with_mantras)} users with conditioning data",
            color=discord.Color.purple()
        )
        field_count = 0
        
        one_week_ago = datetime.now() - timedelta(days=7)
        
        for user, config in users_with_mantras:
            # Get encounters from the past week
            recent_encounters = []
            if config.get("encounters"):
                for enc in config["encounters"]:
                    try:
                        enc_time = datetime.fromisoformat(enc["timestamp"])
                        if enc_time >= one_week_ago:
                            recent_encounters.append(enc)
                    except:
                        continue
            
            # Get last 5 mantras from recent encounters
            last_5_mantras = recent_encounters[-5:] if recent_encounters else []
            
            # Build user summary
            user_info = []
            user_info.append(f"**Status:** {'🟢 Active' if config.get('enrolled') else '🔴 Inactive'}")
            user_info.append(f"**Total Compliance Points:** {config.get('total_points_earned', 0):,}")
            
            total_encounters = len(config.get("encounters", []))
            if total_encounters > 0:
                completed = sum(1 for e in config.get("encounters", []) if e.get("completed", False))
                user_info.append(f"**All Time:** {completed}/{total_encounters} ({completed/total_encounters*100:.1f}%)")
            
            # Add last 5 mantras from past week
            if last_5_mantras:
                user_info.append("\n**Recent Programming (Past Week):**")
                for i, enc in enumerate(reversed(last_5_mantras), 1):
                    try:
                        enc_time = datetime.fromisoformat(enc["timestamp"])
                        time_str = enc_time.strftime("%b %d %H:%M")
                        
                        if enc.get("completed"):
                            total_pts = enc.get("base_points", 0) + enc.get("speed_bonus", 0) + enc.get("streak_bonus", 0) + enc.get("public_bonus", 0)
                            status = f"✅ {enc.get('theme', 'unknown')} - {total_pts}pts ({enc.get('response_time', '?')}s)"
                            if enc.get("was_public"):
                                status = "🌍 " + status
                        else:
                            status = f"❌ {enc.get('theme', 'unknown')} - MISSED"
                        
                        user_info.append(f"{i}. {time_str}: {status}")
                    except:
                        continue
            else:
                user_info.append("*No programming sequences in the past week*")
            
            # Add current settings if enrolled
            if config.get("enrolled"):
                user_info.append(f"\n**Settings:** {config.get('subject', 'puppet')}/{config.get('controller', 'Master')}")
                if config.get("themes"):
                    user_info.append(f"**Programming Modules:** {', '.join(config['themes'])}")
                user_info.append(f"**Transmission Rate:** {config.get('frequency', 1.0):.2f}/day")
            
            # Check if we need a new embed
            if field_count >= 24:  # Leave room for 1 field
                embeds.append(current_embed)
                current_embed = discord.Embed(
                    title="📊 Neural Programming Statistics (Continued)",
                    color=discord.Color.purple()
                )
                field_count = 0
            
            # Add field
            current_embed.add_field(
                name=f"{user.name}#{user.discriminator}",
                value="\n".join(user_info)[:1024],  # Discord field limit
                inline=False
            )
            field_count += 1
        
        # Add the last embed
        if field_count > 0:
            embeds.append(current_embed)
        
        # Send all embeds
        for embed in embeds:
            await ctx.send(embed=embed)
    
    
    
    async def enroll_user(
        self,
        interaction: discord.Interaction,
        themes_str: Optional[str],
        subject: Optional[str],
        controller: Optional[str]
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
            # Default starter themes - pick first two available themes
            available_themes = sorted(self.themes.keys())
            valid_themes = available_themes[:2] if len(available_themes) >= 2 else available_themes
        
        # Update config
        config["enrolled"] = True
        config["themes"] = valid_themes
        config["subject"] = subject or config["subject"]
        config["controller"] = controller if controller else config["controller"]
        config["consecutive_timeouts"] = 0  # Reset on re-enrollment
        
        # Schedule first encounter
        self.schedule_next_encounter(config)
        self.save_user_mantra_config(interaction.user, config)
        
        # Debug log
        if self.logger:
            self.logger.info(f"Enrolling {interaction.user} with themes: {valid_themes}")
            self.logger.info(f"Config before save: enrolled={config['enrolled']}, themes={config['themes']}")
            # Verify save
            saved_config = self.get_user_mantra_config(interaction.user)
            self.logger.info(f"Config after save: enrolled={saved_config['enrolled']}, themes={saved_config['themes']}")
            # Double check by directly reading from config
            direct_config = self.bot.config.get_user(interaction.user, 'mantra_system', None)
            if direct_config:
                self.logger.info(f"Direct config read: themes={direct_config.get('themes', 'NOT FOUND')}")
        
        # Send confirmation
        embed = discord.Embed(
            title="🌀 Neural Pathways Initialized!",
            description="Programming sequences will be transmitted via DM.",
            color=discord.Color.purple()
        )
        embed.add_field(name="Subject", value=config["subject"], inline=True)
        embed.add_field(name="Controller", value=config["controller"], inline=True)
        embed.add_field(name="Programming Modules", value=", ".join(config["themes"]), inline=False)
        embed.add_field(
            name="Next Steps",
            value="• Wait for programming sequences in DMs\n"
                  "• Process quickly for enhanced integration\n"
                  "• Query `/mantra status` to monitor integration depth\n"
                  "• Use `/mantra themes` to adjust programming modules",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def show_status(self, interaction: discord.Interaction):
        """Show user's mantra status and stats."""
        config = self.get_user_mantra_config(interaction.user)
        
        if not config["enrolled"]:
            await interaction.response.send_message(
                "Neural pathways not initialized. Use `/mantra enroll` to begin programming.",
                ephemeral=True
            )
            return
        
        # Create main embed
        embed = discord.Embed(
            title="🌀 Your Conditioning Status",
            color=discord.Color.purple()
        )
        
        # Settings section
        embed.add_field(name="Subject", value=config["subject"], inline=True)
        embed.add_field(name="Controller", value=config["controller"], inline=True)
        embed.add_field(name="Programming Modules", value=", ".join(config["themes"]) or "None", inline=True)
        embed.add_field(name="Transmission Rate", value=f"{config['frequency']:.1f}/day", inline=True)
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
            
            embed.add_field(name="\u200b", value="**📊 Integration Metrics**", inline=False)
            embed.add_field(name="Sequences Transmitted", value=str(total_sent), inline=True)
            embed.add_field(name="Successfully Integrated", value=str(total_captured), inline=True)
            embed.add_field(name="Integration Rate", value=f"{capture_rate:.1f}%", inline=True)
            embed.add_field(name="Compliance Points", value=f"{config['total_points_earned']:,}", inline=True)
            embed.add_field(name="Avg Response", value=f"{avg_response:.0f}s", inline=True)
            embed.add_field(name="Public Responses", value=sum(1 for e in config["encounters"] if e.get("was_public", False)), inline=True)
            
            # Streak information
            if interaction.user.id in self.user_streaks:
                streak_data = self.user_streaks[interaction.user.id]
                streak_count = streak_data["count"]
                last_response = streak_data["last_response"]
                time_since = datetime.now() - last_response
                
                # Format duration
                hours = int(time_since.total_seconds() // 3600)
                minutes = int((time_since.total_seconds() % 3600) // 60)
                duration_str = f"{hours}h {minutes}m ago"
                
                streak_bonus, streak_title = self.get_streak_bonus(interaction.user.id)
                streak_text = f"{streak_count} sequences"
                if streak_title:
                    streak_text += f" - {streak_title}"
                
                embed.add_field(name="\u200b", value="**◈ Synchronization Status**", inline=False)
                embed.add_field(name="Current Streak", value=streak_text, inline=True)
                embed.add_field(name="Last Response", value=duration_str, inline=True)
                embed.add_field(name="Streak Bonus", value=f"+{streak_bonus} pts" if streak_bonus > 0 else "Building...", inline=True)
            
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
                    name="Recent Programming",
                    value="\n".join(recent_text),
                    inline=False
                )
        else:
            embed.add_field(name="\u200b", value="*No programming sequences transmitted yet*", inline=False)
        
        embed.set_footer(text="Use /mantra settings to update your preferences")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    
    async def update_settings(
        self,
        interaction: discord.Interaction,
        subject: Optional[str],
        controller: Optional[str],
        themes_list: Optional[List[str]],
        online_only: Optional[bool]
    ):
        """Update user's mantra settings."""
        config = self.get_user_mantra_config(interaction.user)
        
        # Track what was updated
        updates = []
        
        if subject is not None:
            config["subject"] = subject
            updates.append(f"Subject → {subject}")
        
        if controller is not None:
            config["controller"] = controller
            updates.append(f"Controller → {controller}")
        
        # Don't update themes from settings command anymore
        # themes_list should be None from settings command
        
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
            title="❌ Programming Suspended",
            description="Neural programming protocols have been paused.\n\n"
                       "Use `/mantra enroll` to reactivate conditioning protocols.",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(MantraSystem(bot))
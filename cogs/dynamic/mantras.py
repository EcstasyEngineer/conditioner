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


def log_encounter(user_id: int, encounter: Dict):
    """Log encounter to JSONL file for performance."""
    encounters_dir = Path('logs/encounters')
    encounters_dir.mkdir(parents=True, exist_ok=True)
    
    encounters_file = encounters_dir / f'user_{user_id}.jsonl'
    with open(encounters_file, 'a') as f:
        f.write(json.dumps(encounter) + '\n')

def load_encounters(user_id: int) -> List[Dict]:
    """Load all encounters from JSONL file."""
    encounters_file = Path('logs/encounters') / f'user_{user_id}.jsonl'
    
    if not encounters_file.exists():
        return []
    
    encounters = []
    try:
        with open(encounters_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    encounters.append(json.loads(line))
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading encounters for user {user_id}: {e}")
        return []
    
    return encounters

def load_recent_encounters(user_id: int, days: int = 7) -> List[Dict]:
    """Load encounters from the past N days for performance."""
    cutoff_date = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff_date.isoformat()
    
    encounters = []
    encounters_file = Path('logs/encounters') / f'user_{user_id}.jsonl'
    
    if not encounters_file.exists():
        return []
    
    try:
        with open(encounters_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    encounter = json.loads(line)
                    if encounter.get('timestamp', '') >= cutoff_str:
                        encounters.append(encounter)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading recent encounters for user {user_id}: {e}")
        return []
    
    return encounters


class ThemeSelectView(discord.ui.View):
    """View for managing themes with select menu."""
    
    def __init__(self, cog, user, current_themes):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.user = user
        self.current_themes = current_themes.copy()
        self.original_themes = current_themes.copy()
        self._is_finished = False  # Track if we've already handled a button press
        
        # Create select menu with all available themes
        options = []
        for theme_name in sorted(self.cog.themes.keys()):
            option = discord.SelectOption(
                label=theme_name.capitalize(),
                value=theme_name,
                default=theme_name in self.current_themes
            )
            options.append(option)
        
        select = discord.ui.Select(
            placeholder="Select modules to toggle on/off",
            options=options,
            min_values=0,
            max_values=len(options)
        )
        select.callback = self.theme_select_callback
        self.add_item(select)
        
        # Add save button
        save_button = discord.ui.Button(label="Confirm Parameters", style=discord.ButtonStyle.primary)
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
        
        # Use defer with ephemeral=True to match the original message
        await interaction.response.defer(ephemeral=True)
    
    async def save_callback(self, interaction: discord.Interaction):
        """Save theme changes."""
        # Prevent double-processing
        if self._is_finished:
            return
        self._is_finished = True
        
        if not self.current_themes:
            await interaction.response.send_message(
                "You must have at least one conditioning module active!",
                ephemeral=True
            )
            self._is_finished = False  # Reset since we didn't actually finish
            return
        
        # Save changes
        config = self.cog.get_user_mantra_config(self.user)
        config["themes"] = self.current_themes
        self.cog.save_user_mantra_config(self.user, config)
        
        embed = discord.Embed(
            title="✅ Parameters Adjusted",
            description=f"**Active conditioning modules:** {', '.join(self.current_themes)}",
            color=discord.Color.green()
        )
        
        # Disable all components first
        for item in self.children:
            item.disabled = True
        
        # Remove the view entirely
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
    
    async def cancel_callback(self, interaction: discord.Interaction):
        """Cancel without saving."""
        embed = discord.Embed(
            title="❌ Cancelled",
            description="No changes were made to your conditioning parameters.",
            color=discord.Color.red()
        )
        
        # Remove the view entirely
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()


class MantraSystem(commands.Cog):
    """Hypnotic mantra capture system with adaptive delivery."""
    
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
            "basic": {"timeout_minutes": 20},
            "light": {"timeout_minutes": 30},
            "moderate": {"timeout_minutes": 45},
            "deep": {"timeout_minutes": 60},
            "extreme": {"timeout_minutes": 75}
        }
        
        # Online status checking configuration
        self.MANTRA_DELIVERY_INTERVAL_MINUTES = 2  # How often to check for mantra delivery
        self.REQUIRED_CONSECUTIVE_ONLINE_CHECKS = 3  # Consecutive online checks needed
        
        # Combo streak tracking
        self.user_streaks = {}  # user_id: {"count": int, "last_response": datetime}
        
        # Start the mantra delivery task with configured interval
        self.mantra_delivery.change_interval(minutes=self.MANTRA_DELIVERY_INTERVAL_MINUTES)
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
        if self.logger:
            self.logger.info("Starting streak calculation from history...")
            
        # Get all users from the bot's user cache
        for user in self.bot.users:
            if user.bot:
                continue
                
            encounters = load_encounters(user.id)
            if not encounters:
                continue
                
            # Sort encounters by timestamp (most recent first)
            sorted_encounters = sorted(
                encounters,
                key=lambda x: x["timestamp"],
                reverse=True
            )
            
            # Count consecutive successes from most recent until first failure
            streak_count = 0
            last_successful_timestamp = None
            
            for encounter in sorted_encounters:
                if encounter.get("completed", False):
                    streak_count += 1
                    if last_successful_timestamp is None:  # First successful encounter (most recent)
                        last_successful_timestamp = datetime.fromisoformat(encounter["timestamp"])
                else:
                    # Hit a failure - stop counting
                    break
            
            # Set streak if user has any consecutive successes
            if streak_count > 0 and last_successful_timestamp:
                self.user_streaks[user.id] = {
                    "count": streak_count,
                    "last_response": last_successful_timestamp
                }
                if self.logger:
                    self.logger.info(f"Restored streak of {streak_count} for user {user.id} ({user.name})")
            elif self.logger:
                if streak_count == 0:
                    self.logger.info(f"No streak for user {user.id} ({user.name}) - most recent encounter was a failure or no encounters")
                
        if self.logger:
            self.logger.info(f"Streak calculation complete. Active streaks: {len(self.user_streaks)}")
        
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
            "next_encounter": None,  # Object format: {timestamp, mantra, theme, difficulty, base_points}
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
                # Continue existing streak
                self.user_streaks[user_id]["count"] += 1
                self.user_streaks[user_id]["last_response"] = now
            else:
                # Start new streak
                self.user_streaks[user_id] = {"count": 1, "last_response": now}
        else:
            # Break streak on failure only
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
            
            # Initialize or get rotating buffer for this user
            if user.id not in self.user_status_history:
                self.user_status_history[user.id] = {
                    "checks": [False] * self.REQUIRED_CONSECUTIVE_ONLINE_CHECKS,  # Rotating buffer of online status
                    "current_index": 0,  # Current position in rotating buffer
                    "total_checks": 0    # Total number of checks performed (for initial filling)
                }
            
            user_history = self.user_status_history[user.id]
            
            # Add current check to rotating buffer
            user_history["checks"][user_history["current_index"]] = is_online_now
            user_history["current_index"] = (user_history["current_index"] + 1) % self.REQUIRED_CONSECUTIVE_ONLINE_CHECKS
            user_history["total_checks"] += 1
            
            # Count consecutive online checks from most recent
            consecutive_online = 0
            checks_to_examine = min(user_history["total_checks"], self.REQUIRED_CONSECUTIVE_ONLINE_CHECKS)
            
            # Walk backwards from current position counting consecutive True values
            for i in range(checks_to_examine):
                # Calculate index going backwards from current position
                check_index = (user_history["current_index"] - 1 - i) % self.REQUIRED_CONSECUTIVE_ONLINE_CHECKS
                if user_history["checks"][check_index]:
                    consecutive_online += 1
                else:
                    break  # Stop at first False
            
            # Require self.REQUIRED_CONSECUTIVE_ONLINE_CHECKS consecutive loops of being online
            if consecutive_online < self.REQUIRED_CONSECUTIVE_ONLINE_CHECKS:
                if self.logger:
                    self.logger.info(f"User {user.id} online for {consecutive_online}/{self.REQUIRED_CONSECUTIVE_ONLINE_CHECKS} loops")
                return False
        
        
        # Check if it's time for next encounter
        if config["next_encounter"]:
            next_time = datetime.fromisoformat(config["next_encounter"]["timestamp"])
            
            if datetime.now() < next_time:
                return False
                
        return True
    
    # Note: Removed check_user_online_consecutive - now using status history tracking
    
    def select_mantra_for_user(self, config: Dict) -> Optional[Dict]:
        """Select a mantra with balanced theme weighting."""
        if not config["themes"]:
            return None
        
        # First select a theme randomly (equal probability per theme)
        selected_theme = random.choice(config["themes"])
        
        # Then select from mantras in that theme
        if selected_theme in self.themes:
            theme_mantras = self.themes[selected_theme]["mantras"]
            if theme_mantras:
                mantra = random.choice(theme_mantras)
                return {
                    **mantra,
                    "theme": selected_theme
                }
        
        return None
    
    def schedule_next_encounter(self, config: Dict, first_enrollment: bool = False):
        """Schedule the next mantra encounter with pre-planned content."""
        
        # Handle first enrollment with special pre-canned message
        if first_enrollment:
            next_time = datetime.now() + timedelta(seconds=30)
            config["next_encounter"] = {
                "timestamp": next_time.isoformat(),
                "mantra": "My thoughts are being reprogrammed.",
                "theme": "enrollment",
                "difficulty": "moderate",
                "base_points": 100
            }
            return
        
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
            
            # Pre-select the mantra for this encounter
            mantra_data = self.select_mantra_for_user(config)
            if mantra_data:
                config["next_encounter"] = {
                    "timestamp": next_time.isoformat(),
                    "mantra": mantra_data["text"],  # Keep templated format
                    "theme": mantra_data["theme"],
                    "difficulty": mantra_data["difficulty"],
                    "base_points": mantra_data["base_points"]
                }
            else:
                # No mantras available, disable scheduling
                config["next_encounter"] = None
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
    
    @tasks.loop(minutes=2)  # Default interval, overridden in __init__ with self.MANTRA_DELIVERY_INTERVAL_MINUTES
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
                    log_encounter(user.id, encounter)
                    
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
                
                # Use pre-planned encounter if available
                if config["next_encounter"] and isinstance(config["next_encounter"], dict):
                    planned_encounter = config["next_encounter"]
                    mantra_text = planned_encounter["mantra"]
                    difficulty = planned_encounter["difficulty"]
                    adjusted_points = planned_encounter["base_points"]
                    theme = planned_encounter["theme"]
                else:
                    # Fallback to old method if no planned encounter
                    mantra_data = self.select_mantra_for_user(config)
                    if not mantra_data:
                        continue
                    mantra_text = mantra_data["text"]
                    difficulty = mantra_data["difficulty"]
                    adjusted_points = mantra_data["base_points"]
                    theme = mantra_data["theme"]
                
                # Format the mantra (applies templating)
                formatted_mantra = self.format_mantra(
                    mantra_text,
                    config["subject"],
                    config["controller"]
                )
                
                # Get timeout based on difficulty
                settings = self.expiration_settings.get(difficulty, self.expiration_settings["moderate"])
                timeout_minutes = settings["timeout_minutes"]
                
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
                        "theme": theme,
                        "difficulty": difficulty,
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
            
            # Award points directly
            current_points = self.bot.config.get_user(message.author, 'points', 0)
            new_total = max(0, current_points + total_points)
            self.bot.config.set_user(message.author, 'points', new_total)
            
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
            log_encounter(message.author.id, encounter)
            
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
            
            current_points = self.bot.config.get_user(message.author, 'points', 0)
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
    mantra_group = app_commands.Group(name="mantra", description="Hypnotic mantra training system")
    
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
    
    @mantra_group.command(name="list_modules", description="List all available mantra modules")
    async def mantra_list_modules(self, interaction: discord.Interaction):
        """Show all available modules."""
        embed = discord.Embed(
            title="📚 Available Conditioning Modules",
            description="These modules are currently available for programming:",
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
        
        embed.set_footer(text="Use /mantra enroll to get started or /mantra modules to change your active modules!")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @mantra_group.command(name="modules", description="Manage your active conditioning modules")
    async def mantra_modules(self, interaction: discord.Interaction):
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
            title="🌀 Adjust Conditioning Themes",
            description=f"**Active modules:** {', '.join(config['themes']) if config['themes'] else 'None'}",
            color=discord.Color.purple()
        )
        embed.add_field(
            name="Directives",
            value="• Select the conditioning module you wish to activate or deactivate.\n• At least one stream must remain active.\n• Click 'Confirm Parameters' to apply changes.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @commands.command(hidden=True)
    async def mantrasummary(self, ctx):
        """Admin command to show brief mantra summary for all users."""
        # Check if user is superadmin (for DM access) or guild admin
        superadmins = self.bot.config.get_global("superadmins", [])
        is_superadmin = ctx.author.id in superadmins
        is_guild_admin = (ctx.guild is not None and 
                         (ctx.author.guild_permissions.administrator or ctx.author == ctx.guild.owner))
        
        if not (is_superadmin or is_guild_admin):
            await ctx.send("You need administrator permissions or superadmin status to use this command.")
            return
        # Get all users with mantra data
        seen_users = set()
        users_with_mantras = []
        
        # Check all guilds and users
        for guild in self.bot.guilds:
            for member in guild.members:
                if member.bot or member.id in seen_users:
                    continue
                    
                config = self.get_user_mantra_config(member)
                
                # Check if user has ever enrolled or has encounters (check JSONL files)
                has_encounters = len(load_encounters(member.id)) > 0
                if config.get("enrolled") or has_encounters:
                    users_with_mantras.append((member, config))
                    seen_users.add(member.id)
        
        if not users_with_mantras:
            await ctx.send("No users have tried the mantra system yet.")
            return
        
        # Sort by total points earned (descending)
        users_with_mantras.sort(key=lambda x: x[1].get("total_points_earned", 0), reverse=True)
        
        # Calculate dynamic theme column width (find longest theme abbreviation)
        max_theme_width = 0
        for user, config in users_with_mantras:
            themes = config.get("themes", [])
            if themes:
                theme_abbr = "/".join([t[:4] for t in themes])  # 4 letters now
            else:
                theme_abbr = "none"
            max_theme_width = max(max_theme_width, len(theme_abbr))
        
        # Ensure minimum width for readability
        theme_width = max(max_theme_width, 12)
        
        # Build summary lines
        summary_lines = [f"**Neural Programming Summary** ({len(users_with_mantras)} users):\n```"]
        
        for user, config in users_with_mantras:
            # Status
            status = "🟢" if config.get("enrolled") else "🔴"
            
            # Abbreviated themes (first 4 letters)
            themes = config.get("themes", [])
            if themes:
                theme_abbr = "/".join([t[:4] for t in themes])
            else:
                theme_abbr = "none"
            
            # Subject/Controller (4 letters each)
            subject = config.get("subject", "puppet")[:4]
            controller = config.get("controller", "Master")[:4]
            
            # Points
            points = config.get("total_points_earned", 0)
            
            # Success rate from JSONL files
            encounters = load_encounters(user.id)
            total_encounters = len(encounters)
            if total_encounters > 0:
                completed = sum(1 for e in encounters if e.get("completed", False))
                rate = f"{completed}/{total_encounters}"
            else:
                rate = "0/0"
            
            # Daily rate from frequency setting
            daily_rate = config.get("frequency", 1.0)
            
            # Format: STATUS NAME SUBJ/CTRL THEMES POINTS RATE DAILY_RATE
            line = f"{status} {user.name[:12]:<12} {subject}/{controller} {theme_abbr:<{theme_width}} {points:>4}pts {rate:>7} {daily_rate:>4.2f}"
            summary_lines.append(line)
        
        summary_lines.append("```")
        
        # Send in chunks if needed (Discord message limit)
        message = "\n".join(summary_lines)
        if len(message) <= 2000:
            await ctx.send(message)
        else:
            # Split into multiple messages
            current_chunk = [summary_lines[0]]  # Header
            for line in summary_lines[1:-1]:  # Skip header and closing ```
                if len("\n".join(current_chunk + [line, "```"])) > 1990:
                    await ctx.send("\n".join(current_chunk) + "\n```")
                    current_chunk = ["```"]
                current_chunk.append(line)
            await ctx.send("\n".join(current_chunk) + "\n```")
    
    @commands.command(hidden=True)
    async def mantrastats(self, ctx):
        """Hidden admin command to show detailed mantra statistics for all users."""
        # Check if user is superadmin (for DM access) or guild admin
        superadmins = self.bot.config.get_global("superadmins", [])
        is_superadmin = ctx.author.id in superadmins
        is_guild_admin = (ctx.guild is not None and 
                         (ctx.author.guild_permissions.administrator or ctx.author == ctx.guild.owner))
        
        if not (is_superadmin or is_guild_admin):
            await ctx.send("You need administrator permissions or superadmin status to use this command.")
            return
        # Get all users with mantra data
        seen_users = set()
        users_with_mantras = []
        
        # Check all guilds and users
        for guild in self.bot.guilds:
            for member in guild.members:
                if member.bot or member.id in seen_users:
                    continue
                    
                config = self.get_user_mantra_config(member)
                
                # Check if user has ever enrolled or has encounters (check JSONL files)
                has_encounters = len(load_encounters(member.id)) > 0
                if config.get("enrolled") or has_encounters:
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
        
        for user_index, (user, config) in enumerate(users_with_mantras):
            # Get encounters from the past week using JSONL
            recent_encounters = load_recent_encounters(user.id, days=7)
            
            # Get last 5 mantras from recent encounters
            last_5_mantras = recent_encounters[-5:] if recent_encounters else []
            
            # Build user summary
            user_info = []
            user_info.append(f"**Status:** {'🟢 Active' if config.get('enrolled') else '🔴 Inactive'}")
            
            # Get all encounters from JSONL files
            all_encounters = load_encounters(user.id)
            total_encounters = len(all_encounters)
            if total_encounters > 0:
                completed = sum(1 for e in all_encounters if e.get("completed", False))
                user_info.append(f"**All Time:** {completed}/{total_encounters} ({completed/total_encounters*100:.1f}%)")
            
            # Add current settings if enrolled
            if config.get("enrolled"):
                user_info.append(f"**Settings:** {config.get('subject', 'puppet')}/{config.get('controller', 'Master')}")
                if config.get("themes"):
                    user_info.append(f"**Programming Modules:** {', '.join(config['themes'])}")
                user_info.append(f"**Transmission Rate:** {config.get('frequency', 1.0):.2f}/day")
            
            # Add last 5 mantras from past week (moved to end)
            if last_5_mantras:
                user_info.append("\n**Recent Programming:**")
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
                user_info.append("\n*No recent programming sequences*")
            
            # Check if we need a new embed
            if field_count >= 24:  # Leave room for 1 field
                embeds.append(current_embed)
                current_embed = discord.Embed(
                    title="📊 Neural Programming Statistics (Continued)",
                    color=discord.Color.purple()
                )
                field_count = 0
            
            # Add field with better spacing
            current_embed.add_field(
                name=f"{user.name}#{user.discriminator}",
                value="\n".join(user_info)[:1024],  # Discord field limit
                inline=False
            )
            
            field_count += 1
            
            # Add spacer field for better readability (except for last user)
            if user_index < len(users_with_mantras) - 1:
                current_embed.add_field(
                    name="\u200b",  # Zero-width space
                    value="─────────────────────────────",
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
            # Only set default themes if user doesn't already have themes
            if not config.get("themes"):
                # Default starter themes - acceptance and suggestibility
                default_themes = ["acceptance", "suggestibility"]
                valid_themes = [t for t in default_themes if t in self.themes]
                
                # Fallback to first two available if defaults not found
                if not valid_themes:
                    available_themes = sorted(self.themes.keys())
                    valid_themes = available_themes[:2] if len(available_themes) >= 2 else available_themes
            else:
                # Keep existing themes on re-enrollment
                valid_themes = config["themes"]
        
        # Check user's current online status
        user_status = discord.Status.offline
        for guild in self.bot.guilds:
            member = guild.get_member(interaction.user.id)
            if member:
                user_status = member.status
                break
        
        # Update config
        config["enrolled"] = True
        # Only update themes if we determined new ones (either from user input or defaults for new users)
        if themes_str or not config.get("themes"):
            config["themes"] = valid_themes
        config["subject"] = subject or config["subject"]
        config["controller"] = controller if controller else config["controller"]
        config["consecutive_timeouts"] = 0  # Reset on re-enrollment
        
        # Set online_only based on user's current status
        if user_status in [discord.Status.idle, discord.Status.offline]:
            config["online_only"] = False
        
        # Check if this is a first enrollment or re-enrollment after a long time
        is_first_enrollment = False
        if config.get("last_encounter") is None:
            is_first_enrollment = True
        else:
            try:
                last_encounter = datetime.fromisoformat(config["last_encounter"])
                if datetime.now() - last_encounter > timedelta(days=1):
                    is_first_enrollment = True
            except:
                is_first_enrollment = True
        
        # Schedule first encounter
        self.schedule_next_encounter(config, first_enrollment=is_first_enrollment)
        
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
        
        # Add timing info for first-time enrollments
        if is_first_enrollment:
            next_steps_value = "• **First sequence arriving soon!**\n"
        else:
            next_steps_value = "• Wait for programming sequences in DMs\n"
        
        next_steps_value += (
            "• Process quickly for enhanced integration\n"
            "• Query `/mantra status` to monitor integration depth\n"
            "• Use `/mantra modules` to adjust programming modules"
        )
        
        embed.add_field(
            name="Next Steps",
            value=next_steps_value,
            inline=False
        )
        
        # Add note about online-only setting if we changed it
        if user_status in [discord.Status.idle, discord.Status.offline]:
            embed.add_field(
                name="📍 Status Note",
                value="Online-only mode disabled (you appear idle/offline)",
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
        
        # Stats section from JSONL files
        encounters = load_encounters(interaction.user.id)
        total_sent = len(encounters)
        if total_sent > 0:
            total_captured = sum(1 for e in encounters if e.get("completed", False))
            capture_rate = (total_captured / total_sent * 100)
            
            # Average response time for completed mantras
            response_times = [e["response_time"] for e in encounters 
                             if e.get("completed", False) and "response_time" in e]
            avg_response = sum(response_times) / len(response_times) if response_times else 0
            
            embed.add_field(name="\u200b", value="**📊 Integration Metrics**", inline=False)
            embed.add_field(name="Sequences Transmitted", value=str(total_sent), inline=True)
            embed.add_field(name="Successfully Integrated", value=str(total_captured), inline=True)
            embed.add_field(name="Integration Rate", value=f"{capture_rate:.1f}%", inline=True)
            embed.add_field(name="Compliance Points", value=f"{config['total_points_earned']:,}", inline=True)
            embed.add_field(name="Avg Response", value=f"{avg_response:.0f}s", inline=True)
            embed.add_field(name="Public Responses", value=sum(1 for e in encounters if e.get("was_public", False)), inline=True)
            
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
            
            # Recent mantras from JSONL
            recent = encounters[-5:]  # Last 5
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
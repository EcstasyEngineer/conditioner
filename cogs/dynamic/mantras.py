import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

from core.utils import is_admin
from utils.points import get_points, add_points
from utils.encounters import log_encounter, load_encounters
from utils.mantras import (
    calculate_speed_bonus, check_mantra_match, format_mantra_text,
    select_mantra_from_themes,
    generate_mantra_stats, schedule_next_encounter, adjust_user_frequency,
    save_user_mantra_config, get_user_mantra_config
)
def get_max_themes_for_user(bot, user):
    """Calculate maximum allowed themes based on user points.
    
    Tier System:
    - Initiate (0+ points): 3 themes
    - Intermediate (500+ points): 5 themes  
    - Advanced (1500+ points): 7 themes
    - Master (3000+ points): 10 themes
    """
    points = get_points(bot, user)
    
    if points >= 3000:      # Master tier
        return 10
    elif points >= 1500:    # Advanced tier  
        return 7
    elif points >= 500:     # Intermediate tier
        return 5
    else:                   # Initiate tier
        return 3


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
            # Convert underscores to spaces and capitalize each word
            display_name = theme_name.replace('_', ' ').title()
            option = discord.SelectOption(
                label=display_name,
                value=theme_name,
                default=theme_name in self.current_themes
            )
            options.append(option)
        
        # Calculate max themes user can select based on their points
        max_user_themes = get_max_themes_for_user(self.cog.bot, self.user)
        
        select = discord.ui.Select(
            placeholder="Select modules to toggle on/off",
            options=options,
            min_values=0,
            max_values=min(len(options), max_user_themes)
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
        
        # Check theme limit based on user points
        max_themes = get_max_themes_for_user(self.cog.bot, self.user)
        if len(self.current_themes) > max_themes:
            user_points = get_points(self.cog.bot, self.user)
            
            # Determine tier name for message
            if user_points >= 3000:
                tier_name = "Master"
            elif user_points >= 1500:
                tier_name = "Advanced"
            elif user_points >= 500:
                tier_name = "Intermediate"
            else:
                tier_name = "Initiate"
            
            await interaction.response.send_message(
                f"**Theme limit exceeded!**\n"
                f"Your current tier (**{tier_name}** - {user_points:,} points) allows maximum {max_themes} themes.\n"
                f"You selected {len(self.current_themes)} themes.\n\n"
                f"**Earn more points to unlock additional theme slots:**\n"
                f"• 500+ points: 5 themes (Intermediate)\n"
                f"• 1,500+ points: 7 themes (Advanced)\n"
                f"• 3,000+ points: 10 themes (Master)",
                ephemeral=True
            )
            self._is_finished = False  # Reset since we didn't actually finish
            return
        
        # Save changes
        config = get_user_mantra_config(self.cog.bot.config, self.user)
        config["themes"] = self.current_themes
        save_user_mantra_config(self.cog.bot.config, self.user, config)
        
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
        self.mantras_dir = Path("mantras")
        self.themes = self.load_themes()
        
        # Create theme choices for slash commands
        self.theme_choices = self._generate_theme_choices()
        
        # Public channel for bonus points (can be set by admin)
        self.public_channel_id = None  # Will be loaded from guild config
        self.public_bonus_multiplier = 2.5  # 2.5x points for public mantras
        
        # Parameterized expiration settings based on difficulty
        self.expiration_settings = {
            "basic": {"timeout_minutes": 30},
            "light": {"timeout_minutes": 30},
            "moderate": {"timeout_minutes": 45},
            "deep": {"timeout_minutes": 60},
            "extreme": {"timeout_minutes": 75}
        }
        
        # Online status checking configuration
        self.MANTRA_DELIVERY_INTERVAL_MINUTES = 1 
        self.REQUIRED_CONSECUTIVE_ONLINE_CHECKS = 1
        
        # Start the mantra delivery task with configured interval
        self.mantra_delivery.change_interval(minutes=self.MANTRA_DELIVERY_INTERVAL_MINUTES)
        self.mantra_delivery.start()
        
        # Track active mantra challenges
        self.active_challenges = {} 
        # Track user online status history for better detection
        self.user_status_history = {}  
        
    async def cog_load(self):
        """Load public channel configuration and calculate streaks when cog loads."""
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
    
    
    
    async def should_send_mantra(self, user) -> bool:
        """Check if we should send a mantra to this user."""
        config = get_user_mantra_config(self.bot.config, user)

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
    
    @tasks.loop(minutes=2)  # Default interval, overridden in __init__ with self.MANTRA_DELIVERY_INTERVAL_MINUTES
    async def mantra_delivery(self):
        """Main task loop for delivering mantras."""
        # Get all user configs
        for user_id in list(self.active_challenges.keys()):
            config = get_user_mantra_config(self.bot.config, user_id)
            # Check for expired challenges
            challenge = self.active_challenges[user_id]
            timeout_minutes = challenge.get("timeout_minutes", 60)  # Default to 60 if not set
            if datetime.now() > challenge["sent_at"] + timedelta(minutes=timeout_minutes):
                # Record the missed challenge
                encounter = {
                    "timestamp": challenge["sent_at"].isoformat(),
                    "mantra": challenge["mantra"],
                    "theme": challenge["theme"],
                    "difficulty": challenge["difficulty"],
                    "base_points": challenge["base_points"],
                    "completed": False,
                    "expired": True
                }
                log_encounter(user_id, encounter)
                
                # Adjust frequency and check for auto-disable or break offer
                adjust_user_frequency(config, success=False)

                # Create Embed showing that the challenge has expired
                embed = discord.Embed(
                    title="Challenge Expired",
                    description=f"Mantra challenge has expired:\n\n**{challenge['mantra']}**",
                    color=discord.Color.red()
                )

                if config.get("consecutive_timeouts", 0) > 8:
                    embed.add_field(
                        name="Auto-disabled",
                        value="Programming has been disabled due to repeated timeouts.",
                        inline=False
                    )
                    config["enrolled"] = False

                # Add a reminder that you can pause
                elif config.get("consecutive_timeouts", 0) > 3:
                    # get the User's subject name from config, and capitalize the first letter
                    subject_name = config.get("subject", "")
                    subject_predicate = f", {subject_name}" if subject_name else ""
                    embed.add_field(
                        name="Need a break?",
                        value=f"You missed several challenges in a row{subject_predicate}. Use `/mantra disable` to pause programming protocols.",
                        inline=False
                    )
                embed.set_footer(text=f"Theme: {challenge['theme']} | Difficulty: {challenge['difficulty']} | Base Points: {challenge['base_points']}")
                
                # Try to update the last message to reduce spam
                challenge_msg = challenge.get("last_encounter_msg", None)
                if challenge_msg:
                    try:
                        await challenge_msg.edit(embed=embed)
                    except:
                        await user.send(embed=embed)
                else:
                    await user.send(embed=embed)

                # Create a new challenge
                schedule_next_encounter(config, self.themes)
                save_user_mantra_config(self.bot.config, user_id, config)
                    
                # Remove from active challenges
                del self.active_challenges[user_id]
        
        # Check for users who need mantras
        all_users = self.bot.users
        for user in all_users:
            if user.bot or user.id in self.active_challenges:
                continue
                
            if await self.should_send_mantra(user):
                config = get_user_mantra_config(self.bot.config, user)

                # Format the mantra (applies templating)
                formatted_mantra = format_mantra_text(
                    config["next_encounter"]["mantra"],
                    config["subject"],
                    config["controller"]
                )

                # Get timeout based on difficulty (needed if we reconstruct an active challenge)
                settings = self.expiration_settings.get(
                    config["next_encounter"]["difficulty"],
                    self.expiration_settings["moderate"]
                )
                timeout_minutes = settings["timeout_minutes"]

                # Quick check: did we already send this mantra before a reboot?
                # If next_encounter_ts is before bot.start_time, it's likely unrecorded
                if datetime.fromisoformat(config["next_encounter"]["timestamp"]) < self.bot.start_time:
                    # Look through the user's DM channel history for a matching message
                    dm = user.dm_channel or await user.create_dm()
                    already_sent = False
                    async for message in dm.history(limit=5):
                        found = False
                        # Check embeds first (we send mantras via embed description)
                        if message.embeds:
                            for e in message.embeds:
                                try:
                                    if e.description and "Process this directive" in e.description and formatted_mantra in e.description:
                                        found = True
                                        self.logger.info(f"Found previously sent mantra from before reboot: {formatted_mantra}")
                                        break
                                except Exception:
                                    pass
                        # Fallback to plain content
                        if not found and message.content:
                            if "Process this directive" in message.content and formatted_mantra in message.content:
                                found = True

                        if found:
                            # Recreate the active challenge so the user can respond
                            self.active_challenges[user.id] = {
                                "mantra": formatted_mantra,
                                "theme": config['next_encounter']['theme'],
                                "difficulty": config['next_encounter']['difficulty'],
                                "base_points": config['next_encounter']['base_points'],
                                "sent_at": datetime.now(),
                                "timeout_minutes": timeout_minutes,
                                "last_encounter_msg": message
                            }
                            already_sent = True
                            break

                    if already_sent:
                        # Skip sending again for this user in this cycle
                        continue


                embed = discord.Embed(
                    title="🌀 Programming Sequence",
                    description=f"Process this directive for **{config['next_encounter']['base_points']} integration points**:\n\n**{formatted_mantra}**",
                    color=discord.Color.purple()
                )
                embed.set_footer(text=f"Integration window: {timeout_minutes} minutes")

                sent_message = await user.send(embed=embed)
                self.active_challenges[user.id] = {
                    "mantra": formatted_mantra,
                    "theme": config['next_encounter']['theme'],
                    "difficulty": config['next_encounter']['difficulty'],
                    "base_points": config['next_encounter']['base_points'],
                    "sent_at": datetime.now(),
                    "timeout_minutes": timeout_minutes,
                    "last_encounter_msg": sent_message
                }
    
    
    @mantra_delivery.before_loop
    async def before_mantra_delivery(self):
        """Wait for bot to be ready before starting delivery loop."""
        await self.bot.wait_until_ready()
    
    @mantra_delivery.error
    async def mantra_delivery_error(self, error):
        """Handle errors in the mantra delivery task loop."""
        if self.logger:
            self.logger.error(f"Error in mantra_delivery task: {error}", exc_info=True)
        
        # Import error handler at function level to avoid circular imports
        from core.error_handler import log_error_to_discord
        
        # Send to Discord error channel
        await log_error_to_discord(self.bot, error, "task_mantra_delivery")
    
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
        if check_mantra_match(message.content, challenge["mantra"]):
            # Remove from active challenges
            del self.active_challenges[message.author.id]

            # Calculate response time and speed bonus
            response_time = (datetime.now() - challenge["sent_at"]).total_seconds()
            speed_bonus = min(calculate_speed_bonus(int(response_time)), challenge["base_points"]) # the 5 point manual challenges cant be cheesed
            base_total = challenge["base_points"] + speed_bonus
            
            # Apply public bonus if applicable
            if is_public:
                total_points = int(base_total * self.public_bonus_multiplier)
                public_bonus = total_points - base_total
            else:
                total_points = base_total
                public_bonus = 0
            
            # Award points directly
            add_points(self.bot, message.author, total_points)
            
            # Update user config
            config = get_user_mantra_config(self.bot.config, message.author)
            
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

            # record to jsonl
            log_encounter(message.author.id, encounter)
            
            # Adjust frequency and schedule next encounter
            adjust_user_frequency(config, success=True, response_time=int(response_time))
            schedule_next_encounter(config, self.themes)
            save_user_mantra_config(self.bot.config, message.author, config)

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
            
            embed = discord.Embed(
                title=title_text,
                description="\n".join(description_lines),
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
                    name="📍 Protocol Reminder",
                    value=f"Public processing in <#{self.public_channel_id}> amplifies conditioning effectiveness by {self.public_bonus_multiplier}x",
                    inline=False
                )
            
            current_points = get_points(self.bot, message.author)
            embed.set_footer(text=f"Total compliance points: {current_points:,}")
            
            # Send reward message publicly if response was public
            if is_public:
                await message.reply(embed=embed)
            else:
                await message.author.send(embed=embed)
            
    # Slash Commands - Using a group for better organization
    mantra_group = app_commands.Group(name="mantra", description="Hypnotic mantra training system")
    
    @mantra_group.command(name="enroll", description="Initialize mental programming protocols")
    @app_commands.describe(
        subject="Preferred subject pet name",
        dominant="Preferred dominant honorific"
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
        dominant=[
            app_commands.Choice(name="Master", value="Master"),
            app_commands.Choice(name="Mistress", value="Mistress"),
            app_commands.Choice(name="Goddess", value="Goddess"),
            app_commands.Choice(name="Daddy", value="Daddy")
        ]
    )
    async def mantra_enroll(
        self,
        interaction: discord.Interaction,
        subject: Optional[str] = None,
        dominant: Optional[str] = None
    ):
        """Enroll in the mantra training system."""
        await self.enroll_user(interaction, None, subject, dominant)

    @mantra_group.command(name="status", description="Check your conditioning status")
    async def mantra_status(self, interaction: discord.Interaction):
        """Show user's mantra status and stats."""
        await self.show_status(interaction)
    
    @mantra_group.command(name="settings", description="Update your mantra settings")
    @app_commands.describe(
        subject="Preferred subject pet name",
        dominant="Preferred dominant honorific",
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
        dominant=[
            app_commands.Choice(name="Master", value="Master"),
            app_commands.Choice(name="Mistress", value="Mistress"),
            app_commands.Choice(name="Goddess", value="Goddess"),
            app_commands.Choice(name="Daddy", value="Daddy")
        ]
    )
    async def mantra_settings(
        self,
        interaction: discord.Interaction,
        subject: Optional[str] = None,
        dominant: Optional[str] = None,
        online_only: Optional[bool] = None
    ):
        """Update mantra settings."""
        # Don't pass themes_list - keep existing themes
        await self.update_settings(interaction, subject, dominant, online_only)
    
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
            # Convert underscores to spaces and capitalize each word
            display_name = theme_name.replace('_', ' ').title()
            embed.add_field(
                name=f"**{display_name}**",
                value=f"{description}\n*{mantra_count} mantras available*",
                inline=False
            )
        
        embed.set_footer(text="Use /mantra enroll to get started or /mantra modules to change your active modules!")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @mantra_group.command(name="modules", description="Manage your active conditioning modules")
    async def mantra_modules(self, interaction: discord.Interaction):
        """Manage themes with a select menu."""
        config = get_user_mantra_config(self.bot.config, interaction.user)
        
        if not config["enrolled"]:
            await interaction.response.send_message(
                "You need to enroll first! Use `/mantra enroll` to get started.",
                ephemeral=True
            )
            return
        
        # Get user's current tier info
        user_points = get_points(self.bot, interaction.user)
        max_themes = get_max_themes_for_user(self.bot, interaction.user)
        
        if user_points >= 3000:
            tier_name = "Master"
            next_tier = None
        elif user_points >= 1500:
            tier_name = "Advanced"
            next_tier = f"Master (3,000 points) - 10 themes"
        elif user_points >= 500:
            tier_name = "Intermediate"
            next_tier = f"Advanced (1,500 points) - 7 themes"
        else:
            tier_name = "Initiate"
            next_tier = f"Intermediate (500 points) - 5 themes"
        
        # Create select menu
        view = ThemeSelectView(self, interaction.user, config["themes"])
        
        embed = discord.Embed(
            title="🌀 Adjust Conditioning Themes",
            description=f"**Active modules:** {', '.join(config['themes']) if config['themes'] else 'None'} ({len(config['themes'])}/{max_themes})",
            color=discord.Color.purple()
        )
        embed.add_field(
            name="Current Tier",
            value=f"**{tier_name}** ({user_points:,} points) - Maximum {max_themes} themes",
            inline=False
        )
        if next_tier:
            embed.add_field(
                name="Next Tier",
                value=next_tier,
                inline=False
            )
        embed.add_field(
            name="Directives",
            value="• Select the conditioning module you wish to activate or deactivate.\n• At least one stream must remain active.\n• Click 'Confirm Parameters' to apply changes.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @commands.command(name="mantra_test", hidden=True)
    @commands.check(is_admin)
    async def get_new_mantra(self, ctx):
        # Get user config
        config = get_user_mantra_config(self.bot.config, ctx.author)
        if not config["enrolled"]:
            await ctx.send("You need to enroll first! Use `/mantra enroll` to get started.")
            return
        if not config["themes"]:
            await ctx.send("You need to have at least one theme selected. Use `/mantra modules` to choose themes.")
            return  
    
        # simply set the next encounter to now
        config["next_encounter"]["timestamp"] = datetime.now().isoformat()
        config["next_encounter"]["base_points"] = 5  # dont let people cheese points
        save_user_mantra_config(self.bot.config, ctx.author, config)
        await ctx.send("New mantra scheduled for immediate delivery.")
    
    @commands.command(hidden=True, aliases=['mstats'])
    #@commands.check(is_admin)
    async def mantrastats(self, ctx):
        """Admin command to show detailed mantra statistics for all users."""
        # Generate stats using utils (simple husk)
        embeds = generate_mantra_stats(self.bot)
        
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
        config = get_user_mantra_config(self.bot.config, interaction.user)
        
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
        recent_encounters = load_encounters(interaction.user.id)
        recent_enroll = None
        now = datetime.now()
        # Find last enrollment or disable event (theme == 'enrollment')
        for enc in reversed(recent_encounters[-5:]):
            if enc.get("theme") == "enrollment":
                recent_enroll = enc
                break
        # If last enrollment was within 6 hours, treat as abuse attempt
        abuse_window = timedelta(hours=6)
        low_enroll_points = 50
        normal_enroll_points = 100
        enroll_delay_seconds = 30
        abuse_delay_seconds = 3600  # 1 hour
        if config.get("last_encounter") is None:
            is_first_enrollment = True
        else:
            try:
                last_encounter = datetime.fromisoformat(config["last_encounter"])
                if now - last_encounter > timedelta(days=1):
                    is_first_enrollment = True
            except:
                is_first_enrollment = True

        # If recent enrollment, lower points and delay
        if recent_enroll and (now - datetime.fromisoformat(recent_enroll["timestamp"]) < abuse_window):
            next_time = now + timedelta(seconds=abuse_delay_seconds)
            config["next_encounter"] = {
                "timestamp": next_time.isoformat(),
                "mantra": "My thoughts are being reprogrammed.",
                "theme": "enrollment",
                "difficulty": "moderate",
                "base_points": low_enroll_points
            }
        elif is_first_enrollment:
            next_time = now + timedelta(seconds=enroll_delay_seconds)
            config["next_encounter"] = {
                "timestamp": next_time.isoformat(),
                "mantra": "My thoughts are being reprogrammed.",
                "theme": "enrollment",
                "difficulty": "moderate",
                "base_points": normal_enroll_points
            }
        else:
            # Schedule next encounter as normal
            schedule_next_encounter(config, self.themes, first_enrollment=False)

        save_user_mantra_config(self.bot.config, interaction.user, config)

        # Send confirmation
        embed = discord.Embed(
            title="🌀 Neural Pathways Initialized!",
            description="Programming sequences will be transmitted soon.",
            color=discord.Color.purple()
        )
        embed.add_field(name="Subject", value=config["subject"], inline=True)
        embed.add_field(name="Dominant", value=config["controller"], inline=True)
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
        config = get_user_mantra_config(self.bot.config, interaction.user)
        
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
            
            # Calculate total points earned from encounters
            total_points_earned = 0
            for e in encounters:
                if e.get("completed", False):
                    total_points_earned += e.get("base_points", 0)
                    total_points_earned += e.get("speed_bonus", 0) 
                    total_points_earned += e.get("public_bonus", 0)
            
            # Average response time for completed mantras
            response_times = [e["response_time"] for e in encounters 
                             if e.get("completed", False) and "response_time" in e]
            avg_response = sum(response_times) / len(response_times) if response_times else 0
            
            embed.add_field(name="\u200b", value="**📊 Integration Metrics**", inline=False)
            embed.add_field(name="Sequences Transmitted", value=str(total_sent), inline=True)
            embed.add_field(name="Successfully Integrated", value=str(total_captured), inline=True)
            embed.add_field(name="Integration Rate", value=f"{capture_rate:.1f}%", inline=True)
            embed.add_field(name="Compliance Points", value=f"{total_points_earned:,}", inline=True)
            embed.add_field(name="Avg Response", value=f"{avg_response:.0f}s", inline=True)
            embed.add_field(name="Public Responses", value=sum(1 for e in encounters if e.get("was_public", False)), inline=True)
        
            
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
        online_only: Optional[bool]
    ):
        """Update user's mantra settings."""
        config = get_user_mantra_config(self.bot.config, interaction.user)
        
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
        save_user_mantra_config(self.bot.config, interaction.user, config)
        
        # Send confirmation
        embed = discord.Embed(
            title="✅ Settings Updated",
            description="\n".join(updates),
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    
    async def disable_mantras(self, interaction: discord.Interaction):
        """Disable mantra encounters."""
        config = get_user_mantra_config(self.bot.config, interaction.user)
        config["enrolled"] = False
        config["next_encounter"] = None
        save_user_mantra_config(self.bot.config, interaction.user, config)
        
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
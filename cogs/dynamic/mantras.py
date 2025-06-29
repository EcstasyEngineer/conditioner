import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
import os
from typing import List, Dict, Optional
import difflib

from utils.points import get_points, add_points
from utils.encounters import log_encounter, load_encounters, load_recent_encounters, calculate_user_streak_from_history
from utils.mantras import (
    calculate_speed_bonus, get_streak_bonus, check_mantra_match, format_mantra_text,
    select_mantra_from_themes, validate_mantra_config, generate_mantra_summary,
    generate_mantra_stats_embeds, schedule_next_encounter, adjust_user_frequency,
    get_user_mantra_config, save_user_mantra_config, update_streak
)
from utils.ui import MantraRequestView, MantraResponseView, MantraDisableOfferView, MantraResetView, create_mantra_request_embed, create_mantra_success_embed


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
        self.mantras_dir = Path("mantras/themes")
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
        self.MANTRA_DELIVERY_INTERVAL_MINUTES = 2  # How often to check for mantra delivery
        self.REQUIRED_CONSECUTIVE_ONLINE_CHECKS = 4  # Consecutive online checks needed (8 minutes total)
        
        # Combo streak tracking
        self.user_streaks = {}  # user_id: {"count": int, "last_response": datetime}
        
        # Start the mantra delivery task with configured interval
        self.mantra_delivery.change_interval(minutes=self.MANTRA_DELIVERY_INTERVAL_MINUTES)
        self.mantra_delivery.start()
        
        # Track active mantra challenges
        self.active_challenges = {}  # user_id: {"mantra": str, "theme": str, "difficulty": str, "base_points": int, "sent_at": datetime, "timeout_minutes": int, "view": MantraRequestView, "message": discord.Message}
        
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
                
            # Use util function to calculate streak
            streak_data = calculate_user_streak_from_history(user.id)
            if streak_data:
                self.user_streaks[user.id] = streak_data
                if self.logger:
                    self.logger.info(f"Restored streak of {streak_data['count']} for user {user.id} ({user.name})")
            elif self.logger:
                self.logger.info(f"No streak for user {user.id} ({user.name}) - no valid streak found")
                
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
                return False
        
        
        # Check if it's time for next encounter
        if config["next_encounter"]:
            next_time = datetime.fromisoformat(config["next_encounter"]["timestamp"])
            
            if datetime.now() < next_time:
                return False
                
        return True
    
    # Note: Removed check_user_online_consecutive - now using status history tracking
    
    
    
    
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
                    config = get_user_mantra_config(self.bot.config, user)
                    
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
                    update_streak(self.user_streaks, user_id, success=False)
                    
                    # Adjust frequency and check for auto-disable or break offer
                    disable_action = adjust_user_frequency(config, success=False)
                    
                    # View timeout will handle all the UI updates and messaging
                    # Just save the config here
                    pass
                    
                    save_user_mantra_config(self.bot.config, user, config)
                    
                # Remove from active challenges
                del self.active_challenges[user_id]
        
        # Check for users who need mantras
        all_users = self.bot.users
        for user in all_users:
            if user.bot or user.id in self.active_challenges:
                continue
                
            if await self.should_send_mantra(user):
                config = get_user_mantra_config(self.bot.config, user)
                
                # Check for significant delay between intended and actual send time
                extended_timeout_hours = 0
                if config["next_encounter"] and isinstance(config["next_encounter"], dict):
                    intended_time = datetime.fromisoformat(config["next_encounter"]["timestamp"])
                    actual_time = datetime.now()
                    delay_seconds = (actual_time - intended_time).total_seconds()
                    
                    # If delay is more than 2 hours (suggesting brief online blip), extend timeout
                    if delay_seconds > 7200:  # 2 hours in seconds
                        extended_timeout_hours = min(2.0, delay_seconds / 3600 * 0.5)  # Up to 2 hours extension
                        if self.logger:
                            self.logger.info(f"User {user.id} delayed delivery by {delay_seconds/3600:.1f}h, extending timeout by {extended_timeout_hours:.1f}h")
                
                # Use pre-planned encounter if available
                if config["next_encounter"] and isinstance(config["next_encounter"], dict):
                    planned_encounter = config["next_encounter"]
                    mantra_text = planned_encounter["mantra"]
                    difficulty = planned_encounter["difficulty"]
                    adjusted_points = planned_encounter["base_points"]
                    theme = planned_encounter["theme"]
                else:
                    # Fallback to old method if no planned encounter
                    mantra_data = select_mantra_from_themes(config["themes"], self.themes)
                    if not mantra_data:
                        continue
                    mantra_text = mantra_data["text"]
                    difficulty = mantra_data["difficulty"]
                    adjusted_points = mantra_data["base_points"]
                    theme = mantra_data["theme"]
                
                # Format the mantra (applies templating)
                formatted_mantra = format_mantra_text(
                    mantra_text,
                    config["subject"],
                    config["controller"]
                )
                
                # Get timeout based on difficulty and apply extension if needed
                settings = self.expiration_settings.get(difficulty, self.expiration_settings["moderate"])
                base_timeout_minutes = settings["timeout_minutes"]
                timeout_minutes = base_timeout_minutes + int(extended_timeout_hours * 60)
                
                # Send the challenge with UI view
                try:
                    embed = create_mantra_request_embed(formatted_mantra, adjusted_points, timeout_minutes)
                    view = MantraRequestView(
                        formatted_mantra, adjusted_points, timeout_minutes,
                        bot_config=self.bot.config, user=user, themes=self.themes,
                        user_streaks=self.user_streaks
                    )
                    
                    message = await user.send(embed=embed, view=view)
                    view.set_message(message)
                    
                    if self.logger and extended_timeout_hours > 0:
                        self.logger.info(f"Extended timeout for user {user.id}: {base_timeout_minutes}min -> {timeout_minutes}min")
                    
                    # Track the challenge
                    self.active_challenges[user.id] = {
                        "mantra": formatted_mantra,
                        "theme": theme,
                        "difficulty": difficulty,
                        "base_points": adjusted_points,
                        "sent_at": datetime.now(),
                        "timeout_minutes": timeout_minutes,
                        "view": view,
                        "message": message
                    }
                    
                    # Update last encounter time and schedule next
                    config["last_encounter"] = datetime.now().isoformat()
                    schedule_next_encounter(config, self.themes)
                    save_user_mantra_config(self.bot.config, user, config)
                    
                except discord.Forbidden:
                    # Can't DM user - only log if debug mode
                    pass
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
        if check_mantra_match(message.content, challenge["mantra"]):
            # Calculate response time and speed bonus
            response_time = (datetime.now() - challenge["sent_at"]).total_seconds()
            speed_bonus = calculate_speed_bonus(int(response_time))
            base_total = challenge["base_points"] + speed_bonus
            
            # Update streak
            update_streak(self.user_streaks, message.author.id, success=True)
            # Get streak bonus from user's current streak
            if message.author.id in self.user_streaks:
                streak_count = self.user_streaks[message.author.id]["count"]
                streak_bonus, streak_title = get_streak_bonus(streak_count)
            else:
                streak_bonus, streak_title = 0, ""
            
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
            add_points(self.bot, message.author, total_points)
            
            # Update user config
            config = get_user_mantra_config(self.bot.config, message.author)
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
            adjust_user_frequency(config, success=True, response_time=int(response_time))
            save_user_mantra_config(self.bot.config, message.author, config)
            
            # Mark the view as completed to prevent timeout editing
            if message.author.id in self.active_challenges and "view" in self.active_challenges[message.author.id]:
                self.active_challenges[message.author.id]["view"].mark_completed()
            
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
            
            # Build breakdown
            breakdown_lines = [f"Base: {challenge['base_points']} pts"]
            if speed_bonus > 0:
                breakdown_lines.append(f"Speed bonus: +{speed_bonus} pts")
            if streak_bonus > 0:
                breakdown_lines.append(f"Streak bonus: +{streak_bonus} pts")
            if public_bonus > 0:
                breakdown_lines.append(f"Public bonus: +{public_bonus} pts")
            
            current_points = get_points(self.bot, message.author)
            current_streak = self.user_streaks[message.author.id]["count"] if message.author.id in self.user_streaks else None
            
            # Create success embed using utility function
            embed = create_mantra_success_embed(
                praise=praise,
                total_points=total_points,
                streak_title=streak_title,
                breakdown_lines=breakdown_lines if len(breakdown_lines) > 1 else None,
                current_points=current_points,
                current_streak=current_streak,
                public_channel_id=self.public_channel_id,
                public_bonus_multiplier=self.public_bonus_multiplier,
                is_dm=is_dm
            )
            
            # Create response view with action buttons
            view = MantraResponseView(bot_config=self.bot.config)
            
            # Send reward message publicly if response was public
            if is_public:
                await message.reply(embed=embed, view=view)
            else:
                await message.author.send(embed=embed, view=view)
            
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
        await self.update_settings(interaction, subject, controller, online_only)
    
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
        config = get_user_mantra_config(self.bot.config, interaction.user)
        
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
    
    @commands.command(hidden=True, aliases=['msummary'])
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
        
        # Generate summary using utils (simple husk)
        summary = generate_mantra_summary(self.bot)
        
        # Send in chunks if needed (Discord message limit)
        if len(summary) <= 2000:
            await ctx.send(summary)
        else:
            # Split into multiple messages at code block boundaries
            lines = summary.split('\n')
            current_chunk = []
            
            for line in lines:
                if len('\n'.join(current_chunk + [line])) > 1990:
                    await ctx.send('\n'.join(current_chunk))
                    current_chunk = [line]
                else:
                    current_chunk.append(line)
            
            if current_chunk:
                await ctx.send('\n'.join(current_chunk))
    
    @commands.command(hidden=True, aliases=['mstats'])
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
        
        # Generate stats using utils (simple husk)
        embeds = generate_mantra_stats_embeds(self.bot)
        
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
        schedule_next_encounter(config, self.themes, first_enrollment=is_first_enrollment)
        
        save_user_mantra_config(self.bot.config, interaction.user, config)
        
        # Debug log
        if self.logger:
            self.logger.info(f"Enrolling {interaction.user} with themes: {valid_themes}")
            self.logger.info(f"Config before save: enrolled={config['enrolled']}, themes={config['themes']}")
            # Verify save
            saved_config = get_user_mantra_config(self.bot.config, interaction.user)
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
        config = get_user_mantra_config(self.bot.config, interaction.user)
        
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
                
                streak_bonus, streak_title = get_streak_bonus(streak_count)
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
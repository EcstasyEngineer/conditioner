"""
Mantra System V2 - Hypnotic mantra capture with adaptive learning.

This cog implements the V2 mantra system with:
- Prediction error learning for user availability patterns
- Probability integration scheduling
- Two-timestamp state machine
- TCP-style frequency adjustment

Commands are kept thin - all business logic is in utils/mantra_service.py
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from core.utils import is_admin, is_superadmin
from utils.points import get_points, add_points
from utils.encounters import load_recent_encounters, log_encounter
from utils.response_messages import get_response_message
from utils.mantra_service import (
    get_default_config,
    enroll_user,
    unenroll_user,
    should_deliver_mantra,
    check_for_timeout,
    deliver_mantra,
    handle_mantra_response,
    CONSECUTIVE_FAILURES_THRESHOLD,
    DISABLE_OFFER_THRESHOLD,
)
from utils.mantra_scheduler import (
    DELIVERY_MODE_ADAPTIVE,
    DELIVERY_MODE_LEGACY,
    DELIVERY_MODE_FIXED,
    DEFAULT_LEGACY_INTERVAL_HOURS,
    DEFAULT_FIXED_TIMES,
    validate_fixed_times
)


def get_max_themes_for_user(bot, user):
    """
    Calculate maximum allowed themes based on user points.

    Tier System:
    - Initiate (0+ points): 3 themes
    - Intermediate (500+ points): 5 themes
    - Advanced (1500+ points): 7 themes
    - Master (3000+ points): 10 themes
    """
    points = get_points(bot, user)

    if points >= 3000:
        return 10
    elif points >= 1500:
        return 7
    elif points >= 500:
        return 5
    else:
        return 3


class FavoriteButton(discord.ui.Button):
    """Button for adding a mantra to favorites."""

    def __init__(self, cog, user, mantra_text):
        super().__init__(label="⭐ Favorite", style=discord.ButtonStyle.secondary)
        self.cog = cog
        self.user = user
        self.mantra_text = mantra_text

    async def callback(self, interaction: discord.Interaction):
        """Handle favorite button click."""
        # Load user config
        from utils.mantra_service import get_default_config

        config = self.cog.bot.config.get_user(self.user, 'mantra_system', get_default_config())

        # Check if already favorited
        favorites = config.get("favorite_mantras", [])
        if self.mantra_text in favorites:
            # Already favorited - just acknowledge silently
            await interaction.response.defer()
            return

        # Add to favorites
        favorites.append(self.mantra_text)
        config["favorite_mantras"] = favorites

        # Save config
        self.cog.bot.config.set_user(self.user, 'mantra_system', config)

        # Disable the button and update the message
        self.disabled = True
        self.label = "⭐ Favorited"

        # Get the original message view and update it
        view = self.view
        await interaction.response.edit_message(view=view)


class SettingsButton(discord.ui.Button):
    """Button for opening settings modal."""

    def __init__(self, cog, user):
        super().__init__(label="⚙️ Settings", style=discord.ButtonStyle.secondary)
        self.cog = cog
        self.user = user

    async def callback(self, interaction: discord.Interaction):
        """Handle settings button click."""
        await interaction.response.defer(ephemeral=True)

        # Load current config
        from utils.mantra_service import get_default_config

        config = self.cog.bot.config.get_user(self.user, 'mantra_system', get_default_config())

        # Get current values
        current_subject = config.get("subject", "puppet")
        current_controller = config.get("controller", "Master")
        current_themes = config.get("themes", [])
        current_delivery_mode = config.get("delivery_mode", DELIVERY_MODE_ADAPTIVE)

        # Create comprehensive settings view (same as enrollment)
        view = EnrollmentView(self.cog, self.user, current_subject, current_controller, current_themes, current_delivery_mode)

        # Remove the enroll/save button since settings auto-save
        for item in list(view.children):
            if isinstance(item, EnrollButton):
                view.remove_item(item)

        embed = discord.Embed(
            title="⚙️ Conditioning Settings",
            description="Update your conditioning parameters below:",
            color=discord.Color.purple()
        )

        embed.add_field(
            name="Subject/Pet",
            value=current_subject.capitalize(),
            inline=True
        )

        embed.add_field(
            name="Controller/Dominant",
            value=current_controller,
            inline=True
        )

        # Format delivery mode display
        mode_display = {
            DELIVERY_MODE_ADAPTIVE: "Adaptive (learns patterns)",
            DELIVERY_MODE_LEGACY: "Legacy (fixed intervals)",
            DELIVERY_MODE_FIXED: "Fixed (same times daily)"
        }
        embed.add_field(
            name="Delivery Mode",
            value=mode_display.get(current_delivery_mode, "Adaptive"),
            inline=False
        )

        if current_themes:
            embed.add_field(
                name="Themes",
                value=", ".join(t.capitalize() for t in current_themes),
                inline=False
            )
        else:
            embed.add_field(
                name="Themes",
                value="*None selected*",
                inline=False
            )

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class DisableButton(discord.ui.Button):
    """Button for disabling conditioning after multiple failures."""

    def __init__(self, cog, user):
        super().__init__(label="🛑 Disable Conditioning", style=discord.ButtonStyle.danger)
        self.cog = cog
        self.user = user

    async def callback(self, interaction: discord.Interaction):
        """Handle disable button click."""
        from utils.mantra_service import get_default_config, unenroll_user

        # Load config
        config = self.cog.bot.config.get_user(self.user, 'mantra_system', get_default_config())

        # Unenroll
        unenroll_user(config)

        # Save config
        self.cog.bot.config.set_user(self.user, 'mantra_system', config)

        await interaction.response.send_message(
            "Conditioning has been paused. Use `/mantra enroll` to resume when ready.",
            ephemeral=True
        )


class SubjectSelect(discord.ui.Select):
    """Dropdown for selecting subject/pet name."""

    def __init__(self, parent_view):
        self.parent_view = parent_view

        # Common subject names from prod data (10 most popular)
        subjects = ["pet", "puppet", "toy", "doll", "slave", "drone", "kitten", "puppy", "slut", "bimbo"]

        options = [
            discord.SelectOption(
                label=s.capitalize(),
                value=s,
                default=(s == parent_view.current_subject)
            ) for s in subjects
        ]

        super().__init__(
            placeholder="Select subject/pet name...",
            options=options,
            custom_id="subject_select"
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle subject selection."""
        self.parent_view.current_subject = self.values[0]

        # Auto-save if already enrolled
        from utils.mantra_service import get_default_config
        config = self.parent_view.cog.bot.config.get_user(
            self.parent_view.user,
            'mantra_system',
            get_default_config()
        )

        if config.get("enrolled"):
            config["subject"] = self.values[0]
            self.parent_view.cog.bot.config.set_user(self.parent_view.user, 'mantra_system', config)

        # Update the embed to show current selection
        await self.parent_view.update_display(interaction)


class ControllerSelect(discord.ui.Select):
    """Dropdown for selecting controller/dominant name."""

    def __init__(self, parent_view):
        self.parent_view = parent_view

        # Common controller names
        controllers = ["Master", "Mistress", "Goddess", "Owner"]

        options = [
            discord.SelectOption(
                label=c,
                value=c,
                default=(c == parent_view.current_controller)
            ) for c in controllers
        ]

        super().__init__(
            placeholder="Select controller/dominant name...",
            options=options,
            custom_id="controller_select"
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle controller selection."""
        self.parent_view.current_controller = self.values[0]

        # Auto-save if already enrolled
        from utils.mantra_service import get_default_config
        config = self.parent_view.cog.bot.config.get_user(
            self.parent_view.user,
            'mantra_system',
            get_default_config()
        )

        if config.get("enrolled"):
            config["controller"] = self.values[0]
            self.parent_view.cog.bot.config.set_user(self.parent_view.user, 'mantra_system', config)

        # Update the embed to show current selection
        await self.parent_view.update_display(interaction)


class DeliveryModeSelect(discord.ui.Select):
    """Dropdown for selecting delivery mode."""

    def __init__(self, parent_view):
        self.parent_view = parent_view

        options = [
            discord.SelectOption(
                label="Adaptive (Recommended)",
                value=DELIVERY_MODE_ADAPTIVE,
                description="Learns your availability patterns automatically",
                default=(parent_view.current_delivery_mode == DELIVERY_MODE_ADAPTIVE)
            ),
            discord.SelectOption(
                label="Legacy Interval",
                value=DELIVERY_MODE_LEGACY,
                description="Fixed hours between deliveries (e.g., every 4 hours)",
                default=(parent_view.current_delivery_mode == DELIVERY_MODE_LEGACY)
            ),
            discord.SelectOption(
                label="Fixed Times",
                value=DELIVERY_MODE_FIXED,
                description="Same times every day (e.g., 9am, 2pm, 7pm)",
                default=(parent_view.current_delivery_mode == DELIVERY_MODE_FIXED)
            )
        ]

        super().__init__(
            placeholder="Select delivery mode...",
            options=options,
            custom_id="delivery_mode_select"
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle delivery mode selection."""
        self.parent_view.current_delivery_mode = self.values[0]

        # Auto-save if already enrolled
        from utils.mantra_service import get_default_config
        config = self.parent_view.cog.bot.config.get_user(
            self.parent_view.user,
            'mantra_system',
            get_default_config()
        )

        if config.get("enrolled"):
            config["delivery_mode"] = self.values[0]
            self.parent_view.cog.bot.config.set_user(self.parent_view.user, 'mantra_system', config)

        # Update the embed to show current selection
        await self.parent_view.update_display(interaction)


class EnrollmentView(discord.ui.View):
    """Comprehensive view for enrollment with all settings."""

    def __init__(self, cog, user, current_subject="puppet", current_controller="Master", current_themes=None, current_delivery_mode=DELIVERY_MODE_ADAPTIVE):
        super().__init__(timeout=300)
        self.cog = cog
        self.user = user
        self.current_subject = current_subject
        self.current_controller = current_controller
        self.current_themes = current_themes or []
        self.current_delivery_mode = current_delivery_mode

        # Add all dropdowns
        self.add_item(SubjectSelect(self))
        self.add_item(ControllerSelect(self))
        self.add_item(DeliveryModeSelect(self))
        self.add_item(ThemeSelect(self))
        self.add_item(EnrollButton(self))

    async def update_display(self, interaction: discord.Interaction):
        """Update the embed to show current selections and recreate view with updated dropdowns."""
        # Create a NEW view with updated selections to refresh dropdown defaults
        new_view = EnrollmentView(
            self.cog,
            self.user,
            self.current_subject,
            self.current_controller,
            self.current_themes,
            self.current_delivery_mode
        )

        # Check if user is already enrolled to determine title
        from utils.mantra_service import get_default_config
        config = self.cog.bot.config.get_user(self.user, 'mantra_system', get_default_config())

        if config.get("enrolled"):
            title = "⚙️ Conditioning Settings"
            description = "Update your conditioning parameters below:"
            # Remove the enroll button for already enrolled users
            for item in list(new_view.children):
                if isinstance(item, EnrollButton):
                    new_view.remove_item(item)
        else:
            title = "🧠 Enrollment Settings"
            description = "Configure your conditioning parameters below:"

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.purple()
        )

        embed.add_field(
            name="Subject/Pet",
            value=self.current_subject.capitalize(),
            inline=True
        )

        embed.add_field(
            name="Controller/Dominant",
            value=self.current_controller,
            inline=True
        )

        # Format delivery mode display
        mode_display = {
            DELIVERY_MODE_ADAPTIVE: "Adaptive (learns patterns)",
            DELIVERY_MODE_LEGACY: "Legacy (fixed intervals)",
            DELIVERY_MODE_FIXED: "Fixed (same times daily)"
        }
        embed.add_field(
            name="Delivery Mode",
            value=mode_display.get(self.current_delivery_mode, "Adaptive"),
            inline=False
        )

        if self.current_themes:
            embed.add_field(
                name="Themes",
                value=", ".join(t.capitalize() for t in self.current_themes),
                inline=False
            )
        else:
            embed.add_field(
                name="Themes",
                value="*None selected - please select at least one*",
                inline=False
            )

        await interaction.response.edit_message(embed=embed, view=new_view)


class EnrollButton(discord.ui.Button):
    """Button to finalize enrollment."""

    def __init__(self, parent_view):
        super().__init__(
            label="✓ Enroll",
            style=discord.ButtonStyle.success,
            custom_id="enroll_button"
        )
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        """Handle enrollment."""
        from utils.mantra_service import get_default_config, enroll_user

        # Validate
        if not self.parent_view.current_themes:
            await interaction.response.send_message(
                "❌ Please select at least one theme before enrolling.",
                ephemeral=True
            )
            return

        # Load config
        config = self.parent_view.cog.bot.config.get_user(
            self.parent_view.user,
            'mantra_system',
            get_default_config()
        )

        # Enroll
        enroll_user(
            config,
            self.parent_view.current_themes,
            self.parent_view.current_subject,
            self.parent_view.current_controller
        )

        # Set delivery mode
        config["delivery_mode"] = self.parent_view.current_delivery_mode

        # Save
        self.parent_view.cog.bot.config.set_user(
            self.parent_view.user,
            'mantra_system',
            config
        )

        # Format delivery mode for display
        mode_display = {
            DELIVERY_MODE_ADAPTIVE: "Adaptive",
            DELIVERY_MODE_LEGACY: "Legacy Interval",
            DELIVERY_MODE_FIXED: "Fixed Times"
        }

        # Show confirmation
        embed = discord.Embed(
            title="🧠 Neural Programming Activated",
            description=f"**Subject:** {self.parent_view.current_subject.capitalize()}\n**Controller:** {self.parent_view.current_controller}\n**Delivery Mode:** {mode_display.get(self.parent_view.current_delivery_mode, 'Adaptive')}\n**Themes:** {', '.join(t.capitalize() for t in self.parent_view.current_themes)}\n\nYour first transmission will arrive shortly.",
            color=discord.Color.green()
        )

        await interaction.response.edit_message(embed=embed, view=None)


class ThemeSelectView(discord.ui.View):
    """View for managing themes with select menu."""

    def __init__(self, cog, user, current_themes):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.user = user
        self.current_themes = current_themes.copy()
        self.original_themes = current_themes.copy()
        self._is_finished = False

        # Add the select menu
        self.add_item(ThemeSelect(self))

    async def on_timeout(self):
        """Handle timeout by reverting changes."""
        if not self._is_finished:
            # Timeout - revert to original themes
            config = self.cog.bot.config.get_user(self.user, 'mantra_system', get_default_config())
            config['themes'] = self.original_themes
            self.cog.bot.config.set_user(self.user, 'mantra_system', config)


class ThemeSelect(discord.ui.Select):
    """Select menu for choosing themes."""

    def __init__(self, parent_view):
        self.parent_view = parent_view

        # Build options from available themes
        options = []
        for theme_name in sorted(parent_view.cog.themes.keys()):
            theme_data = parent_view.cog.themes[theme_name]
            display_name = theme_name.capitalize()
            description = theme_data.get("description", "")[:100]  # Discord limit

            is_selected = theme_name in parent_view.current_themes

            options.append(discord.SelectOption(
                label=display_name,
                value=theme_name,
                description=description,
                default=is_selected
            ))

        max_themes = get_max_themes_for_user(parent_view.cog.bot, parent_view.user)

        super().__init__(
            placeholder=f"Select up to {max_themes} themes...",
            min_values=0,
            max_values=min(max_themes, len(options)),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle theme selection."""
        self.parent_view.current_themes = self.values

        # Check if this is an EnrollmentView or ThemeSelectView
        if isinstance(self.parent_view, EnrollmentView):
            # Auto-save if already enrolled
            from utils.mantra_service import get_default_config
            config = self.parent_view.cog.bot.config.get_user(
                self.parent_view.user,
                'mantra_system',
                get_default_config()
            )

            if config.get("enrolled"):
                config["themes"] = self.values
                self.parent_view.cog.bot.config.set_user(self.parent_view.user, 'mantra_system', config)

            # Update the enrollment display
            await self.parent_view.update_display(interaction)
        else:
            # ThemeSelectView - just updating themes for already enrolled user
            from utils.mantra_service import get_default_config

            config = self.parent_view.cog.bot.config.get_user(
                self.parent_view.user,
                'mantra_system',
                get_default_config()
            )

            config['themes'] = self.values
            self.parent_view.cog.bot.config.set_user(self.parent_view.user, 'mantra_system', config)

            # Create a NEW view with updated selection to refresh the dropdown defaults
            new_view = ThemeSelectView(self.parent_view.cog, self.parent_view.user, self.values)

            # Update view to show current selection
            embed = discord.Embed(
                title="🧠 Theme Selection",
                description=f"Selected {len(self.values)} themes:\n" + "\n".join(f"• {t.capitalize()}" for t in self.values),
                color=discord.Color.purple()
            )

            await interaction.response.edit_message(embed=embed, view=new_view)


class MantraSystem(commands.Cog):
    """Hypnotic mantra capture system V2 with adaptive learning."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger if hasattr(bot, 'logger') else None
        self.mantras_dir = Path("mantras")
        self.themes = self.load_themes()

        # Create theme choices for slash commands
        self.theme_choices = self._generate_theme_choices()

        # Start the delivery task
        # Loop interval is set in decorator: @tasks.loop(seconds=30)
        self.mantra_delivery.start()

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
            display_name = theme_name.capitalize()
            choices.append(app_commands.Choice(name=display_name, value=theme_name))
        return choices

    @tasks.loop(seconds=30)
    async def mantra_delivery(self):
        """
        Background task to deliver mantras.

        Runs every 30 seconds, checks all enrolled users for:
        1. Pending deliveries (sent=None, time >= next_delivery)
        2. Timeouts (sent!=None, time >= next_delivery)
        """
        print(f"[MANTRA DELIVERY LOOP] Starting at {datetime.now()}")
        if not self.bot.is_ready():
            print("[MANTRA DELIVERY LOOP] Bot not ready, skipping")
            return

        # Load all user configs
        import os
        from pathlib import Path

        configs_dir = Path('configs')
        if not configs_dir.exists():
            return

        for config_file in configs_dir.glob('user_*.json'):
            try:
                user_id = int(config_file.stem.replace('user_', ''))
                user = self.bot.get_user(user_id)

                if not user or user.bot:
                    continue

                # Load config
                config = self.bot.config.get_user(user, 'mantra_system', get_default_config())

                if not config.get("enrolled"):
                    continue

                # Check for timeout first
                if check_for_timeout(config, self.themes):
                    # Log the encounter
                    if config.get("current_mantra"):
                        # Format mantra text for logging
                        from utils.mantras import format_mantra_text
                        formatted_text = format_mantra_text(
                            config["current_mantra"]["text"],
                            config.get("subject", "puppet"),
                            config.get("controller", "Master")
                        )

                        encounter = {
                            "timestamp": datetime.now().isoformat(),
                            "mantra": formatted_text,
                            "theme": config["current_mantra"]["theme"],
                            "difficulty": config["current_mantra"]["difficulty"],
                            "base_points": config["current_mantra"]["base_points"],
                            "completed": False,
                            "expired": True
                        }
                        log_encounter(user_id, encounter)

                    # Delete the original message (cleaner UX than editing to show timeout)
                    delivered_mantra = config.get("delivered_mantra")
                    if delivered_mantra and "message_id" in delivered_mantra:
                        try:
                            dm_channel = await user.create_dm()
                            message = await dm_channel.fetch_message(delivered_mantra["message_id"])
                            await message.delete()
                        except:
                            pass  # Message might be deleted already or DMs disabled

                    # Save updated config
                    self.bot.config.set_user(user, 'mantra_system', config)

                    # If auto-disabled, notify user
                    if not config.get("enrolled"):
                        try:
                            embed = discord.Embed(
                                title="🔴 Conditioning Paused",
                                description=f"You've been automatically unenrolled due to {CONSECUTIVE_FAILURES_THRESHOLD} consecutive timeouts.\n\nUse `/mantra enroll` to re-enroll when ready.",
                                color=discord.Color.red()
                            )
                            await user.send(embed=embed)
                        except:
                            pass  # DMs disabled
                    # If exactly 3 consecutive failures, offer disable button (only once)
                    elif config.get("consecutive_failures", 0) == DISABLE_OFFER_THRESHOLD:
                        try:
                            embed = discord.Embed(
                                title="⚠️ Multiple Missed Mantras",
                                description=f"You've missed {config['consecutive_failures']} mantras in a row.\n\nIf you'd like to pause conditioning, use the button below or use `/mantra unenroll`.",
                                color=discord.Color.orange()
                            )
                            view = discord.ui.View()
                            view.add_item(DisableButton(self, user))
                            await user.send(embed=embed, view=view)
                        except:
                            pass  # DMs disabled

                    continue

                # Check if we should deliver
                if should_deliver_mantra(config):
                    # Deliver the mantra
                    mantra = deliver_mantra(config, self.themes)

                    if mantra:
                        # Save updated config
                        self.bot.config.set_user(user, 'mantra_system', config)

                        # Format mantra text at display time (allows controller/subject changes)
                        from utils.mantras import format_mantra_text
                        formatted_text = format_mantra_text(
                            mantra['text'],
                            config.get("subject", "puppet"),
                            config.get("controller", "Master")
                        )

                        # Send DM to user
                        try:
                            embed = discord.Embed(
                                title="🧠 Neural Programming Transmission",
                                description=f"Type the following mantra to continue your conditioning:\n\n**{formatted_text}**",
                                color=discord.Color.purple()
                            )
                            embed.add_field(
                                name="Theme",
                                value=mantra['theme'].capitalize(),
                                inline=True
                            )
                            embed.add_field(
                                name="Base Points",
                                value=str(mantra['base_points']),
                                inline=True
                            )

                            message = await user.send(embed=embed)

                            # Store message ID in delivered_mantra for timeout editing
                            if "delivered_mantra" not in config:
                                config["delivered_mantra"] = {}
                            config["delivered_mantra"]["message_id"] = message.id

                        except discord.Forbidden:
                            # User has DMs disabled, mark as timeout
                            config["sent"] = None
                            self.bot.config.set_user(user, 'mantra_system', config)

            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error in mantra delivery loop for user {config_file}: {e}")

    @mantra_delivery.before_loop
    async def before_mantra_delivery(self):
        """Wait until the bot is ready before starting the task."""
        await self.bot.wait_until_ready()

    # Create command group
    mantra_group = app_commands.Group(name="mantra", description="Conditioning system commands")

    @mantra_group.command(name="enroll", description="Enroll in the conditioning system")
    async def mantra_enroll(self, interaction: discord.Interaction):
        """Enroll in the mantra system."""
        await interaction.response.defer(ephemeral=True)

        config = self.bot.config.get_user(interaction.user, 'mantra_system', get_default_config())

        if config.get("enrolled"):
            await interaction.followup.send(
                "❌ You are already enrolled. Use `/mantra unenroll` first if you want to change settings.",
                ephemeral=True
            )
            return

        # Use current config values as defaults
        current_subject = config.get("subject", "puppet")
        current_controller = config.get("controller", "Master")
        current_themes = config.get("themes", [])
        current_delivery_mode = config.get("delivery_mode", DELIVERY_MODE_ADAPTIVE)

        # Show comprehensive enrollment view
        view = EnrollmentView(self, interaction.user, current_subject, current_controller, current_themes, current_delivery_mode)

        embed = discord.Embed(
            title="🧠 Enrollment Settings",
            description="Configure your conditioning parameters below:",
            color=discord.Color.purple()
        )

        embed.add_field(
            name="Subject/Pet",
            value=current_subject.capitalize(),
            inline=True
        )

        embed.add_field(
            name="Controller/Dominant",
            value=current_controller,
            inline=True
        )

        # Format delivery mode display
        mode_display = {
            DELIVERY_MODE_ADAPTIVE: "Adaptive (learns patterns)",
            DELIVERY_MODE_LEGACY: "Legacy (fixed intervals)",
            DELIVERY_MODE_FIXED: "Fixed (same times daily)"
        }
        embed.add_field(
            name="Delivery Mode",
            value=mode_display.get(current_delivery_mode, "Adaptive"),
            inline=False
        )

        if current_themes:
            embed.add_field(
                name="Themes",
                value=", ".join(t.capitalize() for t in current_themes),
                inline=False
            )
        else:
            embed.add_field(
                name="Themes",
                value="*None selected - please select at least one*",
                inline=False
            )

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @mantra_group.command(name="unenroll", description="Disable conditioning")
    async def mantra_unenroll(self, interaction: discord.Interaction):
        """Unenroll from the mantra system."""
        await interaction.response.defer(ephemeral=True)

        config = self.bot.config.get_user(interaction.user, 'mantra_system', get_default_config())

        if not config.get("enrolled"):
            await interaction.followup.send("❌ You are not currently enrolled.", ephemeral=True)
            return

        unenroll_user(config)
        self.bot.config.set_user(interaction.user, 'mantra_system', config)

        embed = discord.Embed(
            title="🔴 Conditioning Paused",
            description="You have been unenrolled from the conditioning system.",
            color=discord.Color.red()
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @mantra_group.command(name="stats", description="View your conditioning statistics")
    async def mantra_stats(self, interaction: discord.Interaction):
        """View status and statistics."""
        await interaction.response.defer(ephemeral=True)

        config = self.bot.config.get_user(interaction.user, 'mantra_system', get_default_config())

        if not config.get("enrolled"):
            await interaction.followup.send("❌ You are not currently enrolled.", ephemeral=True)
            return

        # Build status embed
        embed = discord.Embed(
            title="📊 Conditioning Statistics",
            color=discord.Color.purple()
        )

        embed.add_field(
            name="Enrollment",
            value="✅ Active",
            inline=True
        )

        # Show delivery mode
        delivery_mode = config.get("delivery_mode", DELIVERY_MODE_ADAPTIVE)
        mode_display = {
            DELIVERY_MODE_ADAPTIVE: "Adaptive",
            DELIVERY_MODE_LEGACY: "Legacy Interval",
            DELIVERY_MODE_FIXED: "Fixed Times"
        }
        embed.add_field(
            name="Delivery Mode",
            value=mode_display.get(delivery_mode, "Adaptive"),
            inline=True
        )

        # Show frequency only for adaptive mode
        if delivery_mode == DELIVERY_MODE_ADAPTIVE:
            embed.add_field(
                name="Frequency",
                value=f"{config.get('frequency', 1.0):.2f}/day",
                inline=True
            )
        elif delivery_mode == DELIVERY_MODE_LEGACY:
            interval = config.get("legacy_interval_hours", DEFAULT_LEGACY_INTERVAL_HOURS)
            embed.add_field(
                name="Interval",
                value=f"Every {interval}h",
                inline=True
            )
        elif delivery_mode == DELIVERY_MODE_FIXED:
            times = config.get("fixed_times", DEFAULT_FIXED_TIMES)
            embed.add_field(
                name="Fixed Times",
                value=", ".join(times),
                inline=True
            )

        embed.add_field(
            name="Consecutive Failures",
            value=str(config.get("consecutive_failures", 0)),
            inline=True
        )

        if config.get("themes"):
            embed.add_field(
                name="Active Themes",
                value=", ".join(t.capitalize() for t in config["themes"]),
                inline=False
            )

        if config.get("next_delivery"):
            try:
                next_time = datetime.fromisoformat(config["next_delivery"])
                time_until = next_time - datetime.now()
                hours = int(time_until.total_seconds() // 3600)
                minutes = int((time_until.total_seconds() % 3600) // 60)

                if time_until.total_seconds() > 0:
                    embed.add_field(
                        name="Next Transmission",
                        value=f"In {hours}h {minutes}m",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="Next Transmission",
                        value="Overdue (processing...)",
                        inline=True
                    )
            except:
                pass

        if config.get("sent"):
            embed.add_field(
                name="Status",
                value="⏳ Awaiting response",
                inline=True
            )
        else:
            embed.add_field(
                name="Status",
                value="💤 Idle",
                inline=True
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @mantra_group.command(name="mode", description="Switch delivery mode")
    @app_commands.describe(
        mode="Delivery mode: adaptive (learns patterns), legacy (fixed intervals), or fixed (same times daily)",
        interval_hours="Hours between mantras (legacy mode only, 1-24)",
        fixed_times="Comma-separated times in HH:MM format (fixed mode only, e.g., '09:00,14:00,19:00')"
    )
    @app_commands.choices(mode=[
        app_commands.Choice(name="Adaptive (learns your availability)", value=DELIVERY_MODE_ADAPTIVE),
        app_commands.Choice(name="Legacy Interval (every N hours)", value=DELIVERY_MODE_LEGACY),
        app_commands.Choice(name="Fixed Times (same times daily)", value=DELIVERY_MODE_FIXED)
    ])
    async def mantra_mode(
        self,
        interaction: discord.Interaction,
        mode: app_commands.Choice[str],
        interval_hours: int = DEFAULT_LEGACY_INTERVAL_HOURS,
        fixed_times: str = None
    ):
        """Switch delivery mode."""
        await interaction.response.defer(ephemeral=True)

        config = self.bot.config.get_user(interaction.user, 'mantra_system', get_default_config())

        if not config.get("enrolled"):
            await interaction.followup.send(
                "You must be enrolled to change delivery mode. Use `/mantra enroll` first.",
                ephemeral=True
            )
            return

        mode_value = mode.value

        # Validate and set mode-specific parameters
        if mode_value == DELIVERY_MODE_LEGACY:
            # Validate interval
            if not (1 <= interval_hours <= 24):
                await interaction.followup.send(
                    "Interval hours must be between 1 and 24.",
                    ephemeral=True
                )
                return
            config["legacy_interval_hours"] = interval_hours

        elif mode_value == DELIVERY_MODE_FIXED:
            # Parse and validate fixed times
            if fixed_times:
                times_list = [t.strip() for t in fixed_times.split(",")]
            else:
                times_list = DEFAULT_FIXED_TIMES

            if not validate_fixed_times(times_list):
                await interaction.followup.send(
                    "Invalid time format. Use HH:MM format (24-hour), e.g., '09:00,14:00,19:00'",
                    ephemeral=True
                )
                return

            config["fixed_times"] = times_list

        # Set mode
        config["delivery_mode"] = mode_value

        # Reschedule next encounter with new mode
        from utils.mantra_service import schedule_next_encounter
        schedule_next_encounter(config, self.themes)

        # Save config
        self.bot.config.set_user(interaction.user, 'mantra_system', config)

        # Build confirmation message
        embed = discord.Embed(
            title="Delivery Mode Updated",
            color=discord.Color.green()
        )

        mode_names = {
            DELIVERY_MODE_ADAPTIVE: "Adaptive (learns your availability patterns)",
            DELIVERY_MODE_LEGACY: f"Legacy Interval (every {interval_hours} hours)",
            DELIVERY_MODE_FIXED: f"Fixed Times ({', '.join(times_list if mode_value == DELIVERY_MODE_FIXED else DEFAULT_FIXED_TIMES)})"
        }

        embed.add_field(
            name="New Mode",
            value=mode_names.get(mode_value, mode_value),
            inline=False
        )

        # Show next delivery time
        if config.get("next_delivery"):
            try:
                from datetime import datetime
                next_time = datetime.fromisoformat(config["next_delivery"])
                time_until = next_time - datetime.now()
                hours = int(time_until.total_seconds() // 3600)
                minutes = int((time_until.total_seconds() % 3600) // 60)

                if time_until.total_seconds() > 0:
                    embed.add_field(
                        name="Next Delivery",
                        value=f"In {hours}h {minutes}m",
                        inline=True
                    )
            except:
                pass

        await interaction.followup.send(embed=embed, ephemeral=True)

    @mantra_group.command(name="settings", description="Configure conditioning parameters")
    async def mantra_settings(self, interaction: discord.Interaction):
        """Open settings view."""
        await interaction.response.defer(ephemeral=True)

        config = self.bot.config.get_user(interaction.user, 'mantra_system', get_default_config())

        # Get current values
        current_subject = config.get("subject", "puppet")
        current_controller = config.get("controller", "Master")
        current_themes = config.get("themes", [])
        current_delivery_mode = config.get("delivery_mode", DELIVERY_MODE_ADAPTIVE)

        # Create comprehensive settings view (same as enrollment but for enrolled users)
        view = EnrollmentView(self, interaction.user, current_subject, current_controller, current_themes, current_delivery_mode)

        # Remove the enroll/save button since settings auto-save
        for item in list(view.children):
            if isinstance(item, EnrollButton):
                view.remove_item(item)

        embed = discord.Embed(
            title="⚙️ Conditioning Settings",
            description="Update your conditioning parameters below:",
            color=discord.Color.purple()
        )

        embed.add_field(
            name="Subject/Pet",
            value=current_subject.capitalize(),
            inline=True
        )

        embed.add_field(
            name="Controller/Dominant",
            value=current_controller,
            inline=True
        )

        # Format delivery mode display
        mode_display = {
            DELIVERY_MODE_ADAPTIVE: "Adaptive (learns patterns)",
            DELIVERY_MODE_LEGACY: "Legacy (fixed intervals)",
            DELIVERY_MODE_FIXED: "Fixed (same times daily)"
        }
        embed.add_field(
            name="Delivery Mode",
            value=mode_display.get(current_delivery_mode, "Adaptive"),
            inline=False
        )

        if current_themes:
            embed.add_field(
                name="Themes",
                value=", ".join(t.capitalize() for t in current_themes),
                inline=False
            )
        else:
            embed.add_field(
                name="Themes",
                value="*None selected*",
                inline=False
            )

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Listen for mantra responses in DMs.

        When a user sends a message in DMs while they have an active mantra,
        check if it matches and handle the response.
        """
        # Ignore bots
        if message.author.bot:
            return

        # Only DMs
        if not isinstance(message.channel, discord.DMChannel):
            return

        # Load config
        config = self.bot.config.get_user(message.author, 'mantra_system', get_default_config())

        # Check if they have an active mantra
        if not config.get("enrolled"):
            return

        if config.get("sent") is None:
            return  # No active mantra

        # Calculate response time
        try:
            sent_time = datetime.fromisoformat(config["sent"])
            response_time_seconds = int((datetime.now() - sent_time).total_seconds())
        except:
            response_time_seconds = 0

        # Handle the response
        result = handle_mantra_response(
            config,
            self.themes,
            message.content,
            response_time_seconds,
            was_public=False
        )

        if result.get("success"):
            # Log encounter
            log_encounter(message.author.id, result["encounter"])

            # Award points
            add_points(self.bot, message.author, result["points"])

            # Save updated config
            self.bot.config.set_user(message.author, 'mantra_system', config)

            # Get personalized response message
            subject = config.get("subject", "puppet")
            controller = config.get("controller", "Master")

            response_text = get_response_message(subject, response_time_seconds)
            response_text = response_text.format(subject=subject, controller=controller)

            # Get user's total points
            total_points = get_points(self.bot, message.author)

            # Send personalized success message
            embed = discord.Embed(
                description=response_text,
                color=discord.Color.green()
            )

            embed.add_field(name="Points Earned", value=f"+{result['points']}", inline=True)
            embed.add_field(name="Total Points", value=f"{total_points:,}", inline=True)
            embed.add_field(name="Response Time", value=f"{response_time_seconds}s", inline=True)

            if result["speed_bonus"] > 0:
                embed.add_field(name="Speed Bonus", value=f"+{result['speed_bonus']}", inline=True)

            embed.set_footer(text=f"Frequency: {config['frequency']:.2f}/day")

            # Create view with Favorite and Settings buttons
            view = discord.ui.View()

            # Get the mantra text that was just completed (raw template)
            delivered_mantra = config.get("delivered_mantra", {})
            mantra_text = delivered_mantra.get("text", "")

            if mantra_text:
                # Create favorite button
                fav_button = FavoriteButton(self, message.author, mantra_text)

                # Check if already favorited and pre-disable if so
                favorites = config.get("favorite_mantras", [])
                if mantra_text in favorites:
                    fav_button.disabled = True
                    fav_button.label = "⭐ Favorited"

                view.add_item(fav_button)

            view.add_item(SettingsButton(self, message.author))

            await message.reply(embed=embed, view=view)

        else:
            # Failed
            if result.get("error") == "Incorrect response":
                embed = discord.Embed(
                    title="❌ Incorrect",
                    description=f"That doesn't match. Try again:\n\n**{result['expected']}**",
                    color=discord.Color.red()
                )
                await message.reply(embed=embed)

    @commands.command(name="mstats", hidden=True)
    @commands.check(is_superadmin)
    async def mstats(self, ctx):
        """Show enrolled user statistics (superadmin only)."""
        # Collect enrolled users from configs
        enrolled_users = []

        for config_file in Path('configs').glob('user_*.json'):
            user_id = int(config_file.stem.replace('user_', ''))
            config = self.bot.config.get_user(user_id, 'mantra_system')

            if not config or not config.get('enrolled'):
                continue

            # Get recent encounters for success/failure stats
            recent = load_recent_encounters(user_id, limit=10)
            successes = sum(1 for e in recent if e.get('completed'))
            failures = len(recent) - successes

            # Calculate time until next delivery
            next_delivery_str = config.get('next_delivery')
            if next_delivery_str:
                try:
                    next_delivery = datetime.fromisoformat(next_delivery_str)
                    delta = next_delivery - datetime.now()
                    hours = int(delta.total_seconds() / 3600)
                    if hours < 0:
                        next_str = "overdue"
                    elif hours == 0:
                        next_str = "<1h"
                    else:
                        next_str = f"{hours}h"
                except:
                    next_str = "?"
            else:
                next_str = "?"

            # Get themes (store full list for display)
            themes = config.get('themes', [])

            # Get subject/controller
            subject = config.get('subject', '?')
            controller = config.get('controller', '?')

            # Get frequency
            freq = config.get('frequency', 1.0)

            enrolled_users.append({
                'user_id': user_id,
                'successes': successes,
                'failures': failures,
                'next': next_str,
                'next_delivery': next_delivery if next_delivery_str else datetime.max,
                'freq': freq,
                'themes': themes,
                'subject': subject,
                'controller': controller
            })

        # Sort by next delivery time
        enrolled_users.sort(key=lambda u: u['next_delivery'])

        if not enrolled_users:
            await ctx.send("No enrolled users found.")
            return

        # Build multi-row display (up to 20 users per message for readability)
        lines = []
        for user_data in enrolled_users[:20]:
            # Try to get username
            try:
                user = await self.bot.fetch_user(user_data['user_id'])
                username = user.name
            except:
                username = "Unknown"

            # Get full theme names (first 3)
            themes = user_data['themes']
            theme_list = ', '.join(themes[:3])
            if len(themes) > 3:
                theme_list += f" (+{len(themes) - 3} more)"

            # Build 3-row format per user
            total_encounters = user_data['successes'] + user_data['failures']
            lines.append(f"**{username}**")
            lines.append(f"  Stats: {user_data['successes']}/{total_encounters}  •  Next: {user_data['next']}  •  Freq: {user_data['freq']:.1f}x")
            lines.append(f"  Themes: {theme_list}")
            lines.append(f"  Identity: {user_data['subject']} → {user_data['controller']}")
            lines.append("")  # Blank line between users

        # Create embed
        embed = discord.Embed(
            title=f"📊 Active Mantra Users ({len(enrolled_users)})",
            description="\n".join(lines),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Stats = Successes/Total (last 10) • Next = Time until next delivery")

        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(MantraSystem(bot))

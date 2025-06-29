"""
UI Views and components for the Discord bot.

Contains reusable Discord UI components like views, buttons, and embeds
that can be used across different cogs.
"""

import discord
from datetime import datetime
from typing import Optional


class MantraRequestView(discord.ui.View):
    """View for mantra programming sequence requests."""
    
    def __init__(self, mantra_text: str, points: int, timeout_minutes: int, bot_config=None, user=None, themes=None, user_streaks=None, *, timeout: float = None):
        # Set timeout to match the mantra expiration time (convert minutes to seconds)
        super().__init__(timeout=timeout_minutes * 60 if timeout is None else timeout)
        self.mantra_text = mantra_text
        self.points = points
        self.timeout_minutes = timeout_minutes
        self.bot_config = bot_config
        self.user = user
        self.themes = themes
        self.user_streaks = user_streaks
        self._message = None
        self._expired = False
    
    async def on_timeout(self):
        """Handle view timeout - process consecutive failure logic directly."""
        if self._message and not self._expired:
            self._expired = True
            
            # Handle consecutive failure logic if we have access to the bot config
            if self.bot_config and self.user:
                try:
                    from utils.mantras import adjust_user_frequency, schedule_next_encounter, get_user_mantra_config, save_user_mantra_config, update_streak
                    
                    config = get_user_mantra_config(self.bot_config, self.user)
                    
                    # Get current count for display
                    current_timeouts = config.get("consecutive_timeouts", 0)
                    
                    # Don't log encounter here - the mantra delivery loop already handles expired encounters
                    # This prevents duplicate entries in the JSONL file
                    
                    # Use existing utils function to determine what should happen
                    result = adjust_user_frequency(config, success=False)
                    
                    # Update next encounter if continuing
                    if result == "continue":
                        schedule_next_encounter(config, self.themes)
                    elif result == "disabled":
                        config["enrolled"] = False
                        config["next_encounter"] = None
                    
                    save_user_mantra_config(self.bot_config, self.user, config)
                    if self.user_streaks is not None:
                        update_streak(self.user_streaks, self.user.id, success=False)
                    
                    # Create appropriate embed and view based on result
                    if result == "offer_break":
                        embed = discord.Embed(
                            title="⚠️ Neural Pathway Dysfunction Detected",
                            description=f"Consecutive integration failures detected ({current_timeouts + 1}/8).\n\nProtocol adjustment required. Select response:",
                            color=discord.Color.orange()
                        )
                        view = MantraDisableOfferView(self.bot_config, self.themes)
                    elif result == "disabled":
                        embed = discord.Embed(
                            title="⚠️ Critical Neural Pathway Failure",
                            description=f"Maximum consecutive failures reached ({current_timeouts + 1}/8).\n\nProgramming protocols automatically suspended.\n\nReactivation available when ready:",
                            color=discord.Color.red()
                        )
                        view = MantraResetView(self.bot_config, self.themes)
                    else:
                        # Continue - just show timeout
                        embed = discord.Embed(
                            title="⏱️ Programming Sequence Expired",
                            description=f"Failed to integrate: **{self.mantra_text}**",
                            color=discord.Color.orange()
                        )
                        view = None
                    
                except Exception as e:
                    # Fallback to simple timeout message
                    print(f"Error handling mantra timeout: {e}")
                    embed = discord.Embed(
                        title="⏱️ Programming Sequence Expired",
                        description=f"Failed to integrate: **{self.mantra_text}**",
                        color=discord.Color.orange()
                    )
                    view = None
            else:
                # No cog access - simple timeout
                embed = discord.Embed(
                    title="⏱️ Programming Sequence Expired",
                    description=f"Failed to integrate: **{self.mantra_text}**",
                    color=discord.Color.orange()
                )
                view = None
            
            try:
                await self._message.edit(embed=embed, view=view)
            except discord.NotFound:
                pass  # Message was deleted
            except discord.HTTPException:
                pass  # Other Discord API issues
    
    def set_message(self, message: discord.Message):
        """Store reference to the message for editing on timeout."""
        self._message = message
    
    def mark_completed(self):
        """Mark this view as completed to prevent timeout editing."""
        self._expired = True


class MantraResponseView(discord.ui.View):
    """View for successful mantra response confirmations."""
    
    def __init__(self, bot_config=None, *, timeout: float = 300):  # 5 minute timeout for response views
        super().__init__(timeout=timeout)
        self.bot_config = bot_config
    
    @discord.ui.button(label="View Status", style=discord.ButtonStyle.secondary, emoji="📊")
    async def view_status_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to view mantra status."""
        try:
            await interaction.response.send_message(
                "Use `/mantra status` to view your complete conditioning status and metrics.",
                ephemeral=True
            )
        except Exception as e:
            pass
    
    @discord.ui.button(label="Settings", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def adjust_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to adjust mantra settings."""
        try:
            await interaction.response.send_message(
                "Use `/mantra settings` to update your preferences.",
                ephemeral=True
            )
        except Exception as e:
            pass
    
    @discord.ui.button(label="Modules", style=discord.ButtonStyle.secondary, emoji="🧠")
    async def adjust_modules_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to adjust active modules."""
        try:
            await interaction.response.send_message(
                "Use `/mantra modules` to adjust your active conditioning modules.",
                ephemeral=True
            )
        except Exception as e:
            pass


class MantraDisableOfferView(discord.ui.View):
    """View offering user the option to suspend after consecutive failures."""
    
    def __init__(self, bot_config, themes=None, *, timeout: float = 600):  # 10 minute timeout
        super().__init__(timeout=timeout)
        self.bot_config = bot_config
        self.themes = themes
    
    @discord.ui.button(label="Suspend Protocol", style=discord.ButtonStyle.primary, emoji="⏸️")
    async def suspend_protocol_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to voluntarily disable mantra system."""
        try:
            from utils.mantras import get_user_mantra_config, save_user_mantra_config
            
            # Disable the mantra system directly
            config = get_user_mantra_config(self.bot_config, interaction.user)
            config["enrolled"] = False
            config["next_encounter"] = None
            config["consecutive_timeouts"] = 0  # Reset timeout counter
            save_user_mantra_config(self.bot_config, interaction.user, config)
            
            # Replace with reset option after suspension
            embed = discord.Embed(
                title="⏸️ Programming Protocols Suspended",
                description="Neural pathway conditioning has been paused.\n\nReactivation available when ready:",
                color=discord.Color.red()
            )
            
            # Create new view with only reset option
            reset_view = MantraResetView(self.bot_config, self.themes)
            await interaction.response.edit_message(embed=embed, view=reset_view)
            
        except Exception as e:
            await interaction.response.send_message(
                "Programming protocols have been paused. Use `/mantra enroll` to reactivate when ready.",
                ephemeral=True
            )


class MantraResetView(discord.ui.View):
    """View offering only reset option for suspended/disabled users."""
    
    def __init__(self, bot_config, themes=None, *, timeout: float = None):  # No timeout for reset views
        super().__init__(timeout=timeout)
        self.bot_config = bot_config
        self.themes = themes
    
    @discord.ui.button(label="Reset Protocol", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def reset_protocol_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to reset and restart conditioning protocol."""
        try:
            from datetime import datetime, timedelta
            from utils.mantras import get_user_mantra_config, save_user_mantra_config, schedule_next_encounter
            
            # Re-enroll the user with their existing settings using same anti-cheese logic as enrollment
            config = get_user_mantra_config(self.bot_config, interaction.user)
            
            # Reset consecutive timeouts and re-enable
            config["consecutive_timeouts"] = 0
            config["enrolled"] = True
            config["frequency"] = 1.0  # Reset to default frequency
            
            # Use same anti-cheese logic as enrollment command
            is_first_enrollment = False
            if config.get("last_encounter") is None:
                is_first_enrollment = True
            else:
                try:
                    last_encounter = datetime.fromisoformat(config["last_encounter"])
                    if datetime.now() - last_encounter > timedelta(days=3):
                        is_first_enrollment = True
                except:
                    is_first_enrollment = True
            
            # Schedule next encounter with proper anti-cheese logic
            schedule_next_encounter(config, self.themes, first_enrollment=is_first_enrollment)
            
            save_user_mantra_config(self.bot_config, interaction.user, config)
            
            embed = discord.Embed(
                title="🌀 Neural Pathways Reinitialized",
                description="Programming parameters have been recalibrated.\nConditioning protocols resuming with optimized settings.",
                color=discord.Color.green()
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            await interaction.response.send_message(
                "Programming parameters require recalibration.\n\n"
                "Use `/mantra enroll` to reinitialize neural pathways with optimized conditioning protocols.",
                ephemeral=True
            )


def create_mantra_request_embed(mantra_text: str, points: int, timeout_minutes: int) -> discord.Embed:
    """Create the embed for mantra programming requests."""
    embed = discord.Embed(
        title="🌀 Programming Sequence",
        description=f"Process this directive for **{points} integration points**:\n\n**{mantra_text}**",
        color=discord.Color.purple()
    )
    embed.set_footer(text=f"Integration window: {timeout_minutes} minutes")
    return embed


def create_mantra_success_embed(
    praise: str, 
    total_points: int, 
    streak_title: Optional[str] = None,
    breakdown_lines: Optional[list] = None,
    current_points: Optional[int] = None,
    current_streak: Optional[int] = None,
    public_channel_id: Optional[int] = None,
    public_bonus_multiplier: float = 2.5,
    is_dm: bool = True
) -> discord.Embed:
    """Create the embed for successful mantra responses."""
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
    
    # Add breakdown if provided
    if breakdown_lines and len(breakdown_lines) > 1:
        embed.add_field(
            name="Breakdown",
            value="\n".join(breakdown_lines),
            inline=False
        )
    
    # Add tip about public channel if configured and this was a DM response
    if public_channel_id and is_dm and len(embed.fields) < 2:  # Don't add if already have 2+ fields
        import random
        if random.random() < 0.33:  # Show 1/3 of the time
            embed.add_field(
                name="📍 Protocol Reminder",
                value=f"Public processing in <#{public_channel_id}> amplifies conditioning effectiveness by {public_bonus_multiplier}x",
                inline=False
            )
    
    # Add current points footer
    if current_points is not None:
        embed.set_footer(text=f"Total compliance points: {current_points:,}")
    
    # Show streak count if present
    if current_streak is not None:
        embed.add_field(
            name="◈ Synchronization Level",
            value=f"{current_streak} sequences processed",
            inline=True
        )
    
    return embed
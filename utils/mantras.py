"""
Mantra-specific utilities and admin report generation.

Contains mantra system logic, scoring calculations, and admin report
generation functions that are specific to the mantra cog.
"""

import discord
import json
import random
import difflib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from .encounters import load_encounters, load_recent_encounters


def calculate_speed_bonus(response_time_seconds: int) -> int:
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


def get_streak_bonus(streak_count: int) -> Tuple[int, str]:
    """Get streak bonus points and title."""
    if streak_count >= 20:
        return 100, "🌀 Full Synchronization"
    elif streak_count >= 10:
        return 50, "◉ Neural Resonance"
    elif streak_count >= 5:
        return 25, "◈◈ Conditioning Amplified"
    elif streak_count >= 3:
        return 10, "◈ Pathways Opening"
    else:
        return 0, ""


def check_mantra_match(user_response: str, expected_mantra: str) -> bool:
    """Check if user response matches mantra with typo tolerance."""
    # Exact match (case insensitive)
    if user_response.lower() == expected_mantra.lower():
        return True
        
    # Calculate similarity ratio
    ratio = difflib.SequenceMatcher(None, user_response.lower(), expected_mantra.lower()).ratio()
    
    # Accept if 95% similar or better (stricter threshold)
    return ratio >= 0.95


def format_mantra_text(mantra_text: str, subject: str, controller: str) -> str:
    """Replace template variables in mantra text."""
    formatted = mantra_text.format(
        subject=subject,
        controller=controller
    )
    # Capitalize first letter
    if formatted and formatted[0].islower():
        formatted = formatted[0].upper() + formatted[1:]
    return formatted


def select_mantra_from_themes(themes: List[str], available_themes: Dict[str, Dict]) -> Optional[Dict]:
    """Select a mantra with balanced theme weighting."""
    if not themes:
        return None
    
    # First select a theme randomly (equal probability per theme)
    selected_theme = random.choice(themes)
    
    # Then select from mantras in that theme
    if selected_theme in available_themes:
        theme_mantras = available_themes[selected_theme]["mantras"]
        if theme_mantras:
            mantra = random.choice(theme_mantras)
            return {
                **mantra,
                "theme": selected_theme
            }
    
    return None


def schedule_next_encounter(config: Dict, available_themes: Dict, first_enrollment: bool = False):
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
        mantra_data = select_mantra_from_themes(config["themes"], available_themes)
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


def calculate_next_encounter_time(frequency: float) -> datetime:
    """Calculate when the next encounter should be scheduled."""
    if frequency <= 0:
        return datetime.now() + timedelta(days=1)  # Default fallback
    
    # Calculate average hours between encounters
    hours_between = 24 / frequency
    
    # Add randomization (-25% to +25%)
    variation = random.uniform(0.75, 1.25)
    actual_hours = hours_between * variation
    
    # Minimum 2 hours between encounters
    actual_hours = max(2.0, actual_hours)
    
    return datetime.now() + timedelta(hours=actual_hours)


def adjust_user_frequency(config: Dict, success: bool, response_time: Optional[int] = None) -> str:
    """
    Adjust encounter frequency based on engagement.
    Updates the config dict in place.
    
    Returns:
        str: "disabled" if auto-disabled, "offer_break" if should offer break, "continue" if normal
    """
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
        return "continue"
    else:
        # Timeout/miss
        config["consecutive_timeouts"] += 1
        
        # Decrease frequency
        new_freq = max(0.33, current_freq * 0.9)  # Min 1 per 3 days
        config["frequency"] = new_freq
        
        # Auto-disable after 8 consecutive timeouts
        if config["consecutive_timeouts"] >= 8:
            config["enrolled"] = False
            config["frequency"] = 1.0  # Reset to default for re-enrollment
            return "disabled"  # Signal that we auto-disabled
        # Offer break after 3 consecutive timeouts
        elif config["consecutive_timeouts"] >= 3:
            return "offer_break"  # Signal to offer break option
            
    return "continue"


def should_auto_disable_user(consecutive_timeouts: int) -> bool:
    """Check if user should be auto-disabled due to consecutive timeouts."""
    return consecutive_timeouts >= 2


# =============================================================================
# ADMIN REPORT GENERATION
# =============================================================================

def generate_mantra_summary(bot, guild_members: List = None) -> str:
    """Generate brief mantra summary for all users (husk function for cog)."""
    users_with_mantras = []
    
    # Read user JSON files directly
    import os
    import json
    from pathlib import Path
    
    configs_dir = Path('configs')
    if not configs_dir.exists():
        return "No users have tried the mantra system yet."
    
    for config_file in configs_dir.glob('user_*.json'):
        try:
            user_id = int(config_file.stem.replace('user_', ''))
            
            # Read JSON file directly
            with open(config_file, 'r') as f:
                user_data = json.load(f)
            
            config = user_data.get('mantra_system', {})
            
            # Check if user has encounters or is enrolled
            has_encounters = len(load_encounters(user_id)) > 0
            if not (config.get("enrolled") or has_encounters):
                continue
            
            # Try to get user object (for display name)
            user = bot.get_user(user_id)
            if not user:
                # Create a minimal user-like object for display
                class FakeUser:
                    def __init__(self, user_id):
                        self.id = user_id
                        self.name = f"User_{user_id}"
                        self.bot = False
                user = FakeUser(user_id)
            elif user.bot:
                continue
                
            users_with_mantras.append((user, config))
            
        except (ValueError, json.JSONDecodeError, IOError):
            continue
    
    if not users_with_mantras:
        return "No users have tried the mantra system yet."
    
    # Sort by total points earned
    users_with_mantras.sort(key=lambda x: x[1].get("total_points_earned", 0), reverse=True)
    
    # Calculate dynamic theme column width
    max_theme_width = 0
    for user, config in users_with_mantras:
        themes = config.get("themes", [])
        if themes:
            theme_abbr = "/".join([t[:4] for t in themes])
        else:
            theme_abbr = "none"
        max_theme_width = max(max_theme_width, len(theme_abbr))
    
    theme_width = max(max_theme_width, 12)
    
    # Build summary
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
        
        # Success rate from encounters
        encounters = load_encounters(user.id)
        total_encounters = len(encounters)
        if total_encounters > 0:
            completed = sum(1 for e in encounters if e.get("completed", False))
            rate = f"{completed}/{total_encounters}"
        else:
            rate = "0/0"
        
        # Daily rate
        daily_rate = config.get("frequency", 1.0)
        
        # Format line
        line = f"{status} {user.name[:12]:<12} {subject}/{controller} {theme_abbr:<{theme_width}} {points:>4}pts {rate:>7} {daily_rate:>4.2f}"
        summary_lines.append(line)
    
    summary_lines.append("```")
    return "\n".join(summary_lines)


def generate_mantra_stats_embeds(bot, guild_members: List = None) -> List[discord.Embed]:
    """Generate detailed mantra statistics embeds (husk function for cog)."""
    users_with_mantras = []
    
    # Read user JSON files directly
    import os
    import json
    from pathlib import Path
    
    configs_dir = Path('configs')
    if not configs_dir.exists():
        embed = discord.Embed(
            title="📊 Neural Programming Statistics",
            description="No users have tried the mantra system yet.",
            color=discord.Color.purple()
        )
        return [embed]
    
    for config_file in configs_dir.glob('user_*.json'):
        try:
            user_id = int(config_file.stem.replace('user_', ''))
            
            # Read JSON file directly
            with open(config_file, 'r') as f:
                user_data = json.load(f)
            
            config = user_data.get('mantra_system', {})
            
            # Check if user has encounters or is enrolled
            has_encounters = len(load_encounters(user_id)) > 0
            if not (config.get("enrolled") or has_encounters):
                continue
            
            # Try to get user object (for display name)
            user = bot.get_user(user_id)
            if not user:
                # Create a minimal user-like object for display
                class FakeUser:
                    def __init__(self, user_id):
                        self.id = user_id
                        self.name = f"User_{user_id}"
                        self.bot = False
                user = FakeUser(user_id)
            elif user.bot:
                continue
                
            users_with_mantras.append((user, config))
            
        except (ValueError, json.JSONDecodeError, IOError):
            continue
    
    if not users_with_mantras:
        embed = discord.Embed(
            title="📊 Neural Programming Statistics",
            description="No users have tried the mantra system yet.",
            color=discord.Color.purple()
        )
        return [embed]
    
    # Sort by total points earned
    users_with_mantras.sort(key=lambda x: x[1].get("total_points_earned", 0), reverse=True)
    
    # Create embeds (max 25 fields per embed)
    embeds = []
    current_embed = discord.Embed(
        title="📊 Neural Programming Statistics",
        description=f"Found {len(users_with_mantras)} users with conditioning data",
        color=discord.Color.purple()
    )
    field_count = 0
    
    for user_index, (user, config) in enumerate(users_with_mantras):
        # Get recent encounters
        recent_encounters = load_recent_encounters(user.id, days=7)
        last_5_mantras = recent_encounters[-5:] if recent_encounters else []
        
        # Build user info
        user_info = []
        user_info.append(f"**Status:** {'🟢 Active' if config.get('enrolled') else '🔴 Inactive'}")
        
        # All time stats
        all_encounters = load_encounters(user.id)
        total_encounters = len(all_encounters)
        if total_encounters > 0:
            completed = sum(1 for e in all_encounters if e.get("completed", False))
            user_info.append(f"**All Time:** {completed}/{total_encounters} ({completed/total_encounters*100:.1f}%)")
        
        # Current settings if enrolled
        if config.get("enrolled"):
            user_info.append(f"**Settings:** {config.get('subject', 'puppet')}/{config.get('controller', 'Master')}")
            if config.get("themes"):
                user_info.append(f"**Programming Modules:** {', '.join(config['themes'])}")
            user_info.append(f"**Transmission Rate:** {config.get('frequency', 1.0):.2f}/day")
        
        # Recent programming
        if last_5_mantras:
            user_info.append("\n**Recent Programming:**")
            for i, enc in enumerate(reversed(last_5_mantras), 1):
                try:
                    enc_time = datetime.fromisoformat(enc["timestamp"])
                    time_str = enc_time.strftime("%b %d %H:%M")
                    
                    if enc.get("completed"):
                        total_pts = (enc.get("base_points", 0) + enc.get("speed_bonus", 0) + 
                                   enc.get("streak_bonus", 0) + enc.get("public_bonus", 0))
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
        
        # Add field
        current_embed.add_field(
            name=f"{user.name}#{user.discriminator}",
            value="\n".join(user_info)[:1024],  # Discord field limit
            inline=False
        )
        field_count += 1
        
        # Add spacer field for readability (except for last user)
        if user_index < len(users_with_mantras) - 1 and field_count < 24:
            current_embed.add_field(
                name="\u200b",  # Zero-width space
                value="─────────────────────────────",
                inline=False
            )
            field_count += 1
    
    # Add the last embed
    if field_count > 0:
        embeds.append(current_embed)
    
    return embeds


def get_user_mantra_config(bot_config, user) -> Dict:
    """Load user's mantra configuration with validation."""
    default_config = {
        "enrolled": False,
        "themes": [],
        "subject": "puppet",
        "controller": "the conditioning system",
        "frequency": 1.0,
        "last_encounter": None,
        "next_encounter": None,
        "total_points_earned": 0,
        "encounters_completed": 0,
        "online_only": True,
        "consecutive_timeouts": 0,
        "mantras_seen": []
    }
    
    config = bot_config.get_user(user, 'mantra_system', None)
    if config is None or not isinstance(config, dict):
        config = default_config.copy()
    else:
        # Merge with defaults for backward compatibility
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
    
    # Ensure we're using online-only mode for hypnotic themes
    if any(theme in ["brainwashing", "gaslighting", "dronification", "hypnosis", "intox", "drugging"] for theme in config.get("themes", [])):
        config["online_only"] = True
    
    # Validate the config
    return validate_mantra_config(config)


def save_user_mantra_config(bot_config, user, config: Dict):
    """Save user's mantra configuration."""
    bot_config.set_user(user, 'mantra_system', config)


def update_streak(user_streaks: Dict, user_id: int, success: bool = True) -> None:
    """Update user's streak status in the provided streaks dictionary."""
    from datetime import datetime
    now = datetime.now()
    
    if success:
        if user_id in user_streaks:
            # Continue existing streak
            user_streaks[user_id]["count"] += 1
            user_streaks[user_id]["last_response"] = now
        else:
            # Start new streak
            user_streaks[user_id] = {"count": 1, "last_response": now}
    else:
        # Break streak on failure only
        if user_id in user_streaks:
            del user_streaks[user_id]


def validate_mantra_config(config: Dict) -> Dict:
    """Validate and fill in missing keys in mantra config."""
    default_config = {
        "enrolled": False,
        "themes": [],
        "subject": "puppet", 
        "controller": "Master",
        "frequency": 1.0,
        "last_encounter": None,
        "next_encounter": None,
        "consecutive_timeouts": 0,
        "total_points_earned": 0,
        "online_only": True,
        "online_consecutive_checks": 3,
        "online_check_interval": 2.0
    }
    
    if config is None or not isinstance(config, dict):
        return default_config.copy()
    
    # Fill in missing keys
    for key, value in default_config.items():
        if key not in config:
            config[key] = value
    
    return config



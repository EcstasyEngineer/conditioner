"""
Mantra-specific utilities and admin report generation.

Contains mantra system logic, scoring calculations, and admin report
generation functions that are specific to the mantra cog.
"""

import discord
import re
import json
import random
import difflib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from .encounters import load_encounters, load_recent_encounters
from .scoring import get_tier, calculate_speed_bonus

def check_mantra_match(user_response: str, expected_mantra: str) -> bool:
    """Check if user response matches mantra with typo tolerance."""
    # Exact match (case insensitive)
    if user_response.lower() == expected_mantra.lower():
        return True
        
    # Calculate similarity ratio
    user_clean = re.sub(r'\W+', '', user_response.lower())
    expected_clean = re.sub(r'\W+', '', expected_mantra.lower())
    ratio = difflib.SequenceMatcher(None, user_clean, expected_clean).ratio()
    
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

# Helper function used by schedule_next_encounter to select the next random mantra
def select_mantra_from_themes(themes: List[str], available_themes: Dict[str, Dict], favorites: List[str] = None) -> Optional[Dict]:
    """
    Select a mantra with balanced theme weighting and favorite weighting.

    Args:
        themes: List of theme names to select from
        available_themes: Dict of available theme data
        favorites: List of favorited mantra texts (raw templates with {controller}/{subject})

    Returns:
        Dict with selected mantra data, or None if no mantras available
    """
    if not themes:
        return None

    if favorites is None:
        favorites = []

    # Collect all possible mantras from all themes
    all_mantras = []
    for theme in themes:
        if theme in available_themes:
            theme_mantras = available_themes[theme]["mantras"]
            for mantra in theme_mantras:
                all_mantras.append({
                    **mantra,
                    "theme": theme
                })

    if not all_mantras:
        return None

    # Build weighted pool - 2x weight for favorites
    weighted_mantras = []
    for mantra in all_mantras:
        weight = 2 if mantra["text"] in favorites else 1
        weighted_mantras.extend([mantra] * weight)

    # Select randomly from weighted pool
    return random.choice(weighted_mantras)


def schedule_next_encounter(config: Dict, available_themes: Dict, first_enrollment: bool = False):
    """Schedule the next mantra encounter with pre-planned content."""

    if not config.get("enrolled", False):
        return  # No enrollment, no scheduling
    
    # Handle first enrollment with special pre-canned message
    if first_enrollment:
        next_time = datetime.now() + timedelta(seconds=30)
        base_points = 100
        config["next_encounter"] = {
            "timestamp": next_time.isoformat(),
            "mantra": "My thoughts are being reprogrammed.",
            "theme": "enrollment",
            "difficulty": get_tier(base_points),
            "base_points": base_points
        }
        return
    
    # Base frequency is encounters per day
    frequency = max(config["frequency"],0.1)  # Avoid zeros and negatives

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
            "difficulty": get_tier(mantra_data["base_points"]),
            "base_points": mantra_data["base_points"]
        }
        
        


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


def adjust_user_frequency(config: Dict, success: bool, response_time: Optional[int] = None) -> None:
    """
    Adjust encounter frequency based on engagement.
    Updates the config dict in place.
    """
    current_freq = config["frequency"]
    
    if success:
        # Reset timeout counter on success
        config["consecutive_timeouts"] = 0
        
        # Increase frequency for fast responses
        if response_time and response_time < 120:  # Under 2 minutes
            new_freq = min(6.0, current_freq * 1.1)  # Max 6/day
        else:
            new_freq = min(6.0, current_freq * 1.05)
            
        config["frequency"] = new_freq

    else:
        # Timeout/miss
        config["consecutive_timeouts"] += 1
        
        # Decrease frequency
        new_freq = max(0.33, current_freq * 0.9)  # Min 1 per 3 days
        config["frequency"] = new_freq

def should_auto_disable_user(consecutive_timeouts: int) -> bool:
    """Check if user should be auto-disabled due to consecutive timeouts."""
    return consecutive_timeouts >= 2

def generate_mantra_stats(bot, guild_members: List = None) -> List[discord.Embed]:
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
    
    # Sort by total points earned (calculated from encounters)
    def get_user_total_points(user_config_tuple):
        user, config = user_config_tuple
        encounters = load_encounters(user.id)
        total_points = 0
        for e in encounters:
            if e.get("completed", False):
                total_points += e.get("base_points", 0)
                total_points += e.get("speed_bonus", 0)
                total_points += e.get("public_bonus", 0)
        return total_points

    users_with_mantras = [x for x in users_with_mantras if x[1].get("enrolled")]
    users_with_mantras.sort(key=get_user_total_points, reverse=True)

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
        recent_encounters = load_recent_encounters(user.id, limit=5)
        last_5_mantras = recent_encounters[-5:] if recent_encounters else []
        
        # Build user info
        user_info = []
        
        # Status with overdue detection and time until next mantra
        if config.get("enrolled"):
            # Start with base status color
            if config.get("online_only"):
                status = "🟢"  # Green for online-only users
            else:
                status = "⚪"  # Grey for offline-enabled users (always grey)
            
            time_info = ""
            
            # Always check timing if next_encounter exists, regardless of online_only
            if config.get("next_encounter"):
                try:
                    next_time = datetime.fromisoformat(config["next_encounter"]["timestamp"])
                    now = datetime.now()
                    time_diff = next_time - now
                    
                    if time_diff.total_seconds() < 0:
                        # Overdue - only change to yellow if online_only (grey overrides yellow)
                        if config.get("online_only"):
                            status = "🟡"
                        overdue_seconds = abs(time_diff.total_seconds())
                        overdue_hours = int(overdue_seconds // 3600)
                        overdue_minutes = int((overdue_seconds % 3600) // 60)
                        time_info = f"overdue {overdue_hours}h {overdue_minutes}m"
                    else:
                        # Upcoming
                        upcoming_hours = int(time_diff.total_seconds() // 3600)
                        upcoming_minutes = int((time_diff.total_seconds() % 3600) // 60)
                        time_info = f"next in {upcoming_hours}h {upcoming_minutes}m"
                        
                except (ValueError, KeyError, TypeError):
                    time_info = "scheduling error"
            else:
                time_info = "no encounter scheduled"
                
            user_info.append(f"**Status:** {status} {time_info}")
        else:
            user_info.append(f"**Status:** 🔴 Inactive")
        
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
            name=user.name,
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
        "controller": "Master",
        "frequency": 1.0,
        "last_encounter": None,
        "next_encounter": None,
        "online_only": True,
        "consecutive_timeouts": 0,

    }
    
    config = bot_config.get_user(user, 'mantra_system', {})
   
    # Merge with defaults for backward compatibility
    for key, value in default_config.items():
        if key not in config:
            config[key] = value

    # Ensure next_encounter is a dict if None exists
    if config.get("next_encounter") is None:
        # we cant use schedule_next_encounter here because it calls this function
        config["next_encounter"] = {
            "timestamp": datetime.now().isoformat(),
            "mantra": "Brainwashing is good for me",
            "theme": "placeholder",
            "difficulty": "placeholder",
            "base_points": 69
        }

    return config


def save_user_mantra_config(bot_config, user, config: Dict):
    """Save user's mantra configuration."""
    bot_config.set_user(user, 'mantra_system', config)


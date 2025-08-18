"""
Typed, static utilities for the prompt/mantra system.

This module avoids any reliance on `self` or mutable bot state; all inputs are
explicit, and configuration dictionaries are typed to reduce accidental breakage.
"""

from __future__ import annotations

import re
import random
import difflib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, TypedDict, Any

# Note: this module is deliberately Discord-agnostic; no discord imports here.

from .encounters import load_encounters, load_recent_encounters


class NextEncounter(TypedDict, total=False):
    timestamp: str
    mantra: str
    theme: str
    difficulty: str
    base_points: int


class MantraConfig(TypedDict, total=False):
    enrolled: bool
    themes: List[str]
    subject: str
    controller: str
    frequency: float
    last_encounter: Optional[Dict[str, Any]]
    next_encounter: Optional[NextEncounter]
    online_only: bool
    consecutive_timeouts: int


def calculate_speed_bonus(response_time_seconds: int) -> int:
    if response_time_seconds <= 15:
        return 30
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


def check_mantra_match(user_response: str, expected_mantra: str) -> bool:
    if user_response.lower() == expected_mantra.lower():
        return True
    user_clean = re.sub(r"\W+", "", user_response.lower())
    expected_clean = re.sub(r"\W+", "", expected_mantra.lower())
    ratio = difflib.SequenceMatcher(None, user_clean, expected_clean).ratio()
    return ratio >= 0.95


def format_mantra_text(mantra_text: str, subject: str, controller: str) -> str:
    formatted = mantra_text.format(subject=subject, controller=controller)
    if formatted and formatted[0].islower():
        formatted = formatted[0].upper() + formatted[1:]

    # Post-process possessives: if a name ends with 's' (e.g., Goddess),
    # convert “Goddess's” or “Goddess’s” to “Goddess’”. Apply broadly to the
    # formatted text so it works for controller/subject and other names.
    # Handles both straight and curly apostrophes and preserves following punctuation.
    formatted = re.sub(r"(?i)(\b[\w]+s)(?:'s|’s)(?=\b|[\s.,;:!?])", r"\1'", formatted)

    return formatted


def select_mantra_from_themes(themes: List[str], available_themes: Dict[str, Dict]) -> Optional[Dict]:
    if not themes:
        return None
    all_mantras: List[Dict[str, Any]] = []
    for theme in themes:
        if theme in available_themes:
            for mantra in available_themes[theme].get("mantras", []):
                all_mantras.append({**mantra, "theme": theme})
    if not all_mantras:
        return None
    return random.choice(all_mantras)


def schedule_next_encounter(config: MantraConfig, available_themes: Dict[str, Dict], first_enrollment: bool = False) -> None:
    if not config.get("enrolled", False):
        return
    if first_enrollment:
        next_time = datetime.now() + timedelta(seconds=30)
        config["next_encounter"] = NextEncounter(
            timestamp=next_time.isoformat(),
            mantra="My thoughts are being reprogrammed.",
            theme="enrollment",
            difficulty="moderate",
            base_points=100,
        )
        return

    frequency = max(float(config.get("frequency", 1.0)), 0.1)
    hours_between = 24 / frequency
    variation = random.uniform(0.75, 1.25)
    actual_hours = max(2.0, hours_between * variation)
    next_time = datetime.now() + timedelta(hours=actual_hours)

    mantra_data = select_mantra_from_themes(config.get("themes", []), available_themes)
    if mantra_data:
        config["next_encounter"] = NextEncounter(
            timestamp=next_time.isoformat(),
            mantra=mantra_data.get("text", ""),
            theme=mantra_data.get("theme", "unknown"),
            difficulty=mantra_data.get("difficulty", "unknown"),
            base_points=int(mantra_data.get("base_points", 0)),
        )


def calculate_next_encounter_time(frequency: float) -> datetime:
    if frequency <= 0:
        return datetime.now() + timedelta(days=1)
    hours_between = 24 / frequency
    variation = random.uniform(0.75, 1.25)
    actual_hours = max(2.0, hours_between * variation)
    return datetime.now() + timedelta(hours=actual_hours)


def adjust_user_frequency(config: MantraConfig, success: bool, response_time: Optional[int] = None) -> None:
    current_freq = float(config.get("frequency", 1.0))
    if success:
        config["consecutive_timeouts"] = 0
        if response_time and response_time < 120:
            new_freq = min(6.0, current_freq * 1.1)
        else:
            new_freq = min(6.0, current_freq * 1.05)
        config["frequency"] = new_freq
    else:
        config["consecutive_timeouts"] = int(config.get("consecutive_timeouts", 0)) + 1
        config["frequency"] = max(0.33, current_freq * 0.9)


def should_auto_disable_user(consecutive_timeouts: int) -> bool:
    return consecutive_timeouts >= 2


## Note: Presentation of mantra statistics (embeds, Discord objects) has moved into a Cog
## under `cogs/dynamic/mantra_stats.py` to keep features domain-logic pure.


def get_user_mantra_config(bot_config, user) -> MantraConfig:
    default_config: MantraConfig = {
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
    for k, v in default_config.items():
        if k not in config:
            config[k] = v

    if config.get("next_encounter") is None:
        config["next_encounter"] = NextEncounter(
            timestamp=datetime.now().isoformat(),
            mantra="Brainwashing is good for me",
            theme="placeholder",
            difficulty="placeholder",
            base_points=69,
        )

    return config  # type: ignore[return-value]


def save_user_mantra_config(bot_config, user, config: MantraConfig) -> None:
    bot_config.set_user(user, 'mantra_system', config)


def get_theme_tier_info(points: int) -> tuple[int, str, Optional[str]]:
    """Return (max_themes, tier_name, next_tier_str) for a given points total.

    next_tier_str describes the next tier unlock condition, or None if at top.
    """
    if points >= 3000:
        return 10, "Master", None
    if points >= 1500:
        return 7, "Advanced", "Master (3,000 points) - 10 themes"
    if points >= 500:
        return 5, "Intermediate", "Advanced (1,500 points) - 7 themes"
    return 3, "Initiate", "Intermediate (500 points) - 5 themes"


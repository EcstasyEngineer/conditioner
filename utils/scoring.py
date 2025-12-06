"""
Pure scoring functions for point calculations.

No Discord dependencies - can be imported by scripts and tests.
Tier boundaries defined here are the source of truth (documented in POINT_ECONOMY.md).
"""

# Tier boundaries (points)
TIER_BASIC_MAX = 45
TIER_LIGHT_MAX = 75
TIER_MODERATE_MAX = 110
TIER_DEEP_MAX = 150


def get_tier(points: int) -> str:
    """Return tier name for a given point value.

    Tier boundaries:
    20-45 basic, 45-75 light, 75-110 moderate, 110-150 deep, 150+ extreme
    """
    if points >= TIER_MODERATE_MAX:
        return "extreme" if points >= TIER_DEEP_MAX else "deep"
    elif points >= TIER_LIGHT_MAX:
        return "moderate"
    elif points >= TIER_BASIC_MAX:
        return "light"
    else:
        return "basic"


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

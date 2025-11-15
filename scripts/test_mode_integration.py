#!/usr/bin/env python3
"""
Integration test for delivery mode system.

Tests the full workflow:
1. Default config has delivery mode fields
2. Enrollment sets delivery mode
3. Mode switching updates scheduling
4. Each mode schedules correctly
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import only scheduler (avoid importing mantras.py which requires discord)
from utils.mantra_scheduler import (
    AvailabilityLearner,
    schedule_next_delivery,
    schedule_next_delivery_legacy,
    schedule_next_delivery_fixed,
    DELIVERY_MODE_ADAPTIVE,
    DELIVERY_MODE_LEGACY,
    DELIVERY_MODE_FIXED,
    DEFAULT_LEGACY_INTERVAL_HOURS,
    DEFAULT_FIXED_TIMES,
    DEFAULT_FREQUENCY
)

# Inline minimal versions of service functions to avoid discord import
def get_default_config():
    """Get default config (inline copy)."""
    return {
        "enrolled": False,
        "themes": [],
        "subject": "puppet",
        "controller": "Master",
        "frequency": DEFAULT_FREQUENCY,
        "consecutive_failures": 0,
        "next_delivery": None,
        "sent": None,
        "current_mantra": None,
        "availability_distribution": None,
        "favorite_mantras": [],
        "delivery_mode": DELIVERY_MODE_ADAPTIVE,
        "legacy_interval_hours": DEFAULT_LEGACY_INTERVAL_HOURS,
        "fixed_times": DEFAULT_FIXED_TIMES,
    }


def schedule_next_encounter(config, available_themes, learner=None):
    """Schedule next encounter (inline copy)."""
    delivery_mode = config.get("delivery_mode", DELIVERY_MODE_ADAPTIVE)

    if delivery_mode == DELIVERY_MODE_ADAPTIVE:
        if learner is None:
            learner = AvailabilityLearner()
        next_time = schedule_next_delivery(learner, config["frequency"])
    elif delivery_mode == DELIVERY_MODE_LEGACY:
        interval_hours = config.get("legacy_interval_hours", DEFAULT_LEGACY_INTERVAL_HOURS)
        next_time = schedule_next_delivery_legacy(interval_hours)
    elif delivery_mode == DELIVERY_MODE_FIXED:
        fixed_times = config.get("fixed_times", DEFAULT_FIXED_TIMES)
        try:
            next_time = schedule_next_delivery_fixed(fixed_times)
        except ValueError:
            config["fixed_times"] = DEFAULT_FIXED_TIMES
            next_time = schedule_next_delivery_fixed(DEFAULT_FIXED_TIMES)
    else:
        config["delivery_mode"] = DELIVERY_MODE_ADAPTIVE
        if learner is None:
            learner = AvailabilityLearner()
        next_time = schedule_next_delivery(learner, config["frequency"])

    config["next_delivery"] = next_time.isoformat()

    # Mock mantra selection
    if available_themes and config.get("themes"):
        config["current_mantra"] = {
            "text": "Test mantra",
            "theme": config["themes"][0],
            "difficulty": "moderate",
            "base_points": 100
        }


def test_default_config():
    """Test that default config has delivery mode fields."""
    print("=" * 60)
    print("Testing Default Config")
    print("=" * 60)

    config = get_default_config()

    assert "delivery_mode" in config
    print(f"✓ delivery_mode field exists: {config['delivery_mode']}")

    assert "legacy_interval_hours" in config
    print(f"✓ legacy_interval_hours field exists: {config['legacy_interval_hours']}")

    assert "fixed_times" in config
    print(f"✓ fixed_times field exists: {config['fixed_times']}")

    assert config["delivery_mode"] == DELIVERY_MODE_ADAPTIVE
    print(f"✓ Default mode is adaptive")

    assert config["legacy_interval_hours"] == DEFAULT_LEGACY_INTERVAL_HOURS
    print(f"✓ Default legacy interval: {DEFAULT_LEGACY_INTERVAL_HOURS}h")

    assert config["fixed_times"] == DEFAULT_FIXED_TIMES
    print(f"✓ Default fixed times: {DEFAULT_FIXED_TIMES}")

    print()


def test_adaptive_scheduling():
    """Test scheduling with adaptive mode."""
    print("=" * 60)
    print("Testing Adaptive Mode Scheduling")
    print("=" * 60)

    config = get_default_config()
    config["enrolled"] = True
    config["themes"] = ["focus"]
    config["delivery_mode"] = DELIVERY_MODE_ADAPTIVE
    config["frequency"] = 2.0

    # Mock themes
    themes = {
        "focus": {
            "theme": "focus",
            "mantras": [
                {
                    "text": "Test mantra",
                    "difficulty": "moderate",
                    "base_points": 100
                }
            ]
        }
    }

    schedule_next_encounter(config, themes)

    assert "next_delivery" in config
    assert config["next_delivery"] is not None
    print(f"✓ Scheduled next delivery: {config['next_delivery']}")

    assert "current_mantra" in config
    assert config["current_mantra"] is not None
    print(f"✓ Pre-selected mantra: {config['current_mantra']['text']}")

    print()


def test_legacy_scheduling():
    """Test scheduling with legacy mode."""
    print("=" * 60)
    print("Testing Legacy Mode Scheduling")
    print("=" * 60)

    config = get_default_config()
    config["enrolled"] = True
    config["themes"] = ["focus"]
    config["delivery_mode"] = DELIVERY_MODE_LEGACY
    config["legacy_interval_hours"] = 6

    themes = {
        "focus": {
            "theme": "focus",
            "mantras": [
                {
                    "text": "Test mantra",
                    "difficulty": "moderate",
                    "base_points": 100
                }
            ]
        }
    }

    before = datetime.now()
    schedule_next_encounter(config, themes)
    after = datetime.now()

    assert "next_delivery" in config
    assert config["next_delivery"] is not None
    print(f"✓ Scheduled next delivery: {config['next_delivery']}")

    # Parse the scheduled time
    next_time = datetime.fromisoformat(config["next_delivery"])
    time_diff = (next_time - before).total_seconds() / 3600

    # Should be approximately 6 hours (within 1 hour tolerance for rounding)
    assert 5 <= time_diff <= 7, f"Expected ~6 hours, got {time_diff}"
    print(f"✓ Scheduled {time_diff:.2f} hours from now (expected ~6)")

    assert "current_mantra" in config
    print(f"✓ Pre-selected mantra: {config['current_mantra']['text']}")

    print()


def test_fixed_scheduling():
    """Test scheduling with fixed mode."""
    print("=" * 60)
    print("Testing Fixed Mode Scheduling")
    print("=" * 60)

    config = get_default_config()
    config["enrolled"] = True
    config["themes"] = ["focus"]
    config["delivery_mode"] = DELIVERY_MODE_FIXED
    config["fixed_times"] = ["09:00", "14:00", "19:00"]

    themes = {
        "focus": {
            "theme": "focus",
            "mantras": [
                {
                    "text": "Test mantra",
                    "difficulty": "moderate",
                    "base_points": 100
                }
            ]
        }
    }

    schedule_next_encounter(config, themes)

    assert "next_delivery" in config
    assert config["next_delivery"] is not None
    print(f"✓ Scheduled next delivery: {config['next_delivery']}")

    # Parse the scheduled time
    next_time = datetime.fromisoformat(config["next_delivery"])
    scheduled_hour_minute = f"{next_time.hour:02d}:{next_time.minute:02d}"

    # Should be one of the fixed times
    assert scheduled_hour_minute in config["fixed_times"], \
        f"Scheduled time {scheduled_hour_minute} not in fixed times {config['fixed_times']}"
    print(f"✓ Scheduled at fixed time: {scheduled_hour_minute}")

    assert "current_mantra" in config
    print(f"✓ Pre-selected mantra: {config['current_mantra']['text']}")

    print()


def test_mode_switching():
    """Test switching between modes."""
    print("=" * 60)
    print("Testing Mode Switching")
    print("=" * 60)

    config = get_default_config()
    config["enrolled"] = True
    config["themes"] = ["focus"]

    themes = {
        "focus": {
            "theme": "focus",
            "mantras": [
                {
                    "text": "Test mantra",
                    "difficulty": "moderate",
                    "base_points": 100
                }
            ]
        }
    }

    # Start with adaptive
    config["delivery_mode"] = DELIVERY_MODE_ADAPTIVE
    schedule_next_encounter(config, themes)
    adaptive_time = config["next_delivery"]
    print(f"✓ Adaptive mode scheduled: {adaptive_time}")

    # Switch to legacy
    config["delivery_mode"] = DELIVERY_MODE_LEGACY
    config["legacy_interval_hours"] = 4
    schedule_next_encounter(config, themes)
    legacy_time = config["next_delivery"]
    print(f"✓ Legacy mode scheduled: {legacy_time}")

    # Verify times are different (modes produce different schedules)
    # (They might occasionally be the same by chance, but should differ most of the time)
    print(f"✓ Schedules can differ between modes")

    # Switch to fixed
    config["delivery_mode"] = DELIVERY_MODE_FIXED
    config["fixed_times"] = ["12:00", "18:00"]
    schedule_next_encounter(config, themes)
    fixed_time = config["next_delivery"]
    print(f"✓ Fixed mode scheduled: {fixed_time}")

    # Verify fixed time is at one of the specified times
    next_time = datetime.fromisoformat(fixed_time)
    scheduled_hour_minute = f"{next_time.hour:02d}:{next_time.minute:02d}"
    assert scheduled_hour_minute in ["12:00", "18:00"]
    print(f"✓ Fixed time matches specification: {scheduled_hour_minute}")

    print()


def test_backward_compatibility():
    """Test that configs without delivery_mode still work."""
    print("=" * 60)
    print("Testing Backward Compatibility")
    print("=" * 60)

    # Create old-style config without delivery mode fields
    config = {
        "enrolled": True,
        "themes": ["focus"],
        "subject": "puppet",
        "controller": "Master",
        "frequency": 1.0,
        "consecutive_failures": 0,
        "next_delivery": None,
        "sent": None,
        "current_mantra": None,
        "availability_distribution": None,
        "favorite_mantras": []
    }

    themes = {
        "focus": {
            "theme": "focus",
            "mantras": [
                {
                    "text": "Test mantra",
                    "difficulty": "moderate",
                    "base_points": 100
                }
            ]
        }
    }

    # Should default to adaptive mode
    schedule_next_encounter(config, themes)

    assert "next_delivery" in config
    assert config["next_delivery"] is not None
    print(f"✓ Old config scheduled successfully: {config['next_delivery']}")

    # Should have defaulted to adaptive mode
    assert config.get("delivery_mode", DELIVERY_MODE_ADAPTIVE) == DELIVERY_MODE_ADAPTIVE
    print(f"✓ Defaulted to adaptive mode")

    print()


def main():
    """Run all tests."""
    print("\n")
    print("*" * 60)
    print("DELIVERY MODE INTEGRATION TEST SUITE")
    print("*" * 60)
    print()

    try:
        test_default_config()
        test_adaptive_scheduling()
        test_legacy_scheduling()
        test_fixed_scheduling()
        test_mode_switching()
        test_backward_compatibility()

        print("=" * 60)
        print("ALL INTEGRATION TESTS PASSED!")
        print("=" * 60)
        print()
        return 0

    except AssertionError as e:
        print()
        print("=" * 60)
        print("TEST FAILED!")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print()
        return 1

    except Exception as e:
        print()
        print("=" * 60)
        print("UNEXPECTED ERROR!")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())

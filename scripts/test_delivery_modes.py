#!/usr/bin/env python3
"""
Test script for delivery mode implementations.

Tests:
1. Legacy mode scheduling (fixed intervals)
2. Fixed mode scheduling (same times daily)
3. Mode validation functions
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.mantra_scheduler import (
    schedule_next_delivery_legacy,
    schedule_next_delivery_fixed,
    validate_delivery_mode,
    validate_fixed_times,
    DELIVERY_MODE_ADAPTIVE,
    DELIVERY_MODE_LEGACY,
    DELIVERY_MODE_FIXED,
    DEFAULT_LEGACY_INTERVAL_HOURS,
    DEFAULT_FIXED_TIMES
)


def test_legacy_mode():
    """Test legacy mode scheduling."""
    print("=" * 60)
    print("Testing Legacy Mode Scheduling")
    print("=" * 60)

    current_time = datetime(2025, 11, 11, 14, 30, 45)

    # Test with 4-hour interval
    next_time = schedule_next_delivery_legacy(4, current_time)
    expected = datetime(2025, 11, 11, 18, 0, 0)
    assert next_time == expected, f"Expected {expected}, got {next_time}"
    print(f"✓ 4-hour interval: {current_time} -> {next_time}")

    # Test with 1-hour interval (minimum)
    next_time = schedule_next_delivery_legacy(1, current_time)
    expected = datetime(2025, 11, 11, 15, 0, 0)
    assert next_time == expected, f"Expected {expected}, got {next_time}"
    print(f"✓ 1-hour interval: {current_time} -> {next_time}")

    # Test with 24-hour interval (maximum)
    next_time = schedule_next_delivery_legacy(24, current_time)
    expected = datetime(2025, 11, 12, 14, 0, 0)
    assert next_time == expected, f"Expected {expected}, got {next_time}"
    print(f"✓ 24-hour interval: {current_time} -> {next_time}")

    # Test clamping (below minimum)
    next_time = schedule_next_delivery_legacy(0, current_time)
    expected = datetime(2025, 11, 11, 15, 0, 0)  # Clamped to 1 hour
    assert next_time == expected, f"Expected {expected}, got {next_time}"
    print(f"✓ Clamping (0 -> 1 hour): {current_time} -> {next_time}")

    # Test clamping (above maximum)
    next_time = schedule_next_delivery_legacy(30, current_time)
    expected = datetime(2025, 11, 12, 14, 0, 0)  # Clamped to 24 hours
    assert next_time == expected, f"Expected {expected}, got {next_time}"
    print(f"✓ Clamping (30 -> 24 hours): {current_time} -> {next_time}")

    print()


def test_fixed_mode():
    """Test fixed mode scheduling."""
    print("=" * 60)
    print("Testing Fixed Mode Scheduling")
    print("=" * 60)

    fixed_times = ["09:00", "14:00", "19:00"]

    # Test: Before first time of day
    current_time = datetime(2025, 11, 11, 8, 30, 0)
    next_time = schedule_next_delivery_fixed(fixed_times, current_time)
    expected = datetime(2025, 11, 11, 9, 0, 0)
    assert next_time == expected, f"Expected {expected}, got {next_time}"
    print(f"✓ Before first time: {current_time.time()} -> {next_time.time()}")

    # Test: Between first and second time
    current_time = datetime(2025, 11, 11, 10, 30, 0)
    next_time = schedule_next_delivery_fixed(fixed_times, current_time)
    expected = datetime(2025, 11, 11, 14, 0, 0)
    assert next_time == expected, f"Expected {expected}, got {next_time}"
    print(f"✓ Between times: {current_time.time()} -> {next_time.time()}")

    # Test: Between second and third time
    current_time = datetime(2025, 11, 11, 16, 30, 0)
    next_time = schedule_next_delivery_fixed(fixed_times, current_time)
    expected = datetime(2025, 11, 11, 19, 0, 0)
    assert next_time == expected, f"Expected {expected}, got {next_time}"
    print(f"✓ Between times: {current_time.time()} -> {next_time.time()}")

    # Test: After last time (should wrap to next day)
    current_time = datetime(2025, 11, 11, 20, 30, 0)
    next_time = schedule_next_delivery_fixed(fixed_times, current_time)
    expected = datetime(2025, 11, 12, 9, 0, 0)
    assert next_time == expected, f"Expected {expected}, got {next_time}"
    print(f"✓ After last time: {current_time} -> {next_time}")

    # Test: Exactly at a fixed time (should go to next)
    current_time = datetime(2025, 11, 11, 14, 0, 0)
    next_time = schedule_next_delivery_fixed(fixed_times, current_time)
    expected = datetime(2025, 11, 11, 19, 0, 0)
    assert next_time == expected, f"Expected {expected}, got {next_time}"
    print(f"✓ Exactly at time: {current_time.time()} -> {next_time.time()}")

    # Test: Single fixed time
    single_time = ["12:00"]
    current_time = datetime(2025, 11, 11, 10, 0, 0)
    next_time = schedule_next_delivery_fixed(single_time, current_time)
    expected = datetime(2025, 11, 11, 12, 0, 0)
    assert next_time == expected, f"Expected {expected}, got {next_time}"
    print(f"✓ Single fixed time: {current_time.time()} -> {next_time.time()}")

    # Test: Single fixed time (after, should wrap)
    current_time = datetime(2025, 11, 11, 13, 0, 0)
    next_time = schedule_next_delivery_fixed(single_time, current_time)
    expected = datetime(2025, 11, 12, 12, 0, 0)
    assert next_time == expected, f"Expected {expected}, got {next_time}"
    print(f"✓ Single fixed time wrap: {current_time} -> {next_time}")

    print()


def test_validation():
    """Test validation functions."""
    print("=" * 60)
    print("Testing Validation Functions")
    print("=" * 60)

    # Test delivery mode validation
    assert validate_delivery_mode(DELIVERY_MODE_ADAPTIVE) == True
    print(f"✓ Valid mode: {DELIVERY_MODE_ADAPTIVE}")

    assert validate_delivery_mode(DELIVERY_MODE_LEGACY) == True
    print(f"✓ Valid mode: {DELIVERY_MODE_LEGACY}")

    assert validate_delivery_mode(DELIVERY_MODE_FIXED) == True
    print(f"✓ Valid mode: {DELIVERY_MODE_FIXED}")

    assert validate_delivery_mode("invalid") == False
    print("✓ Invalid mode: 'invalid' -> False")

    # Test fixed times validation
    assert validate_fixed_times(["09:00", "14:00", "19:00"]) == True
    print("✓ Valid times: ['09:00', '14:00', '19:00']")

    assert validate_fixed_times(["00:00", "23:59"]) == True
    print("✓ Valid times: ['00:00', '23:59']")

    assert validate_fixed_times([]) == False
    print("✓ Empty list -> False")

    assert validate_fixed_times(["25:00"]) == False
    print("✓ Invalid hour: '25:00' -> False")

    assert validate_fixed_times(["12:60"]) == False
    print("✓ Invalid minute: '12:60' -> False")

    assert validate_fixed_times(["12"]) == False
    print("✓ Invalid format: '12' -> False")

    assert validate_fixed_times(["12:00:00"]) == False
    print("✓ Invalid format: '12:00:00' -> False")

    print()


def test_error_handling():
    """Test error handling for fixed mode."""
    print("=" * 60)
    print("Testing Error Handling")
    print("=" * 60)

    # Test empty fixed times
    try:
        schedule_next_delivery_fixed([])
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"✓ Empty list raises ValueError: {e}")

    # Test invalid time format
    try:
        schedule_next_delivery_fixed(["25:00"])
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"✓ Invalid hour raises ValueError: {e}")

    # Test invalid time format (minutes)
    try:
        schedule_next_delivery_fixed(["12:60"])
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"✓ Invalid minute raises ValueError: {e}")

    # Test invalid format
    try:
        schedule_next_delivery_fixed(["not-a-time"])
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"✓ Invalid format raises ValueError: {e}")

    print()


def main():
    """Run all tests."""
    print("\n")
    print("*" * 60)
    print("DELIVERY MODE TEST SUITE")
    print("*" * 60)
    print()

    try:
        test_legacy_mode()
        test_fixed_mode()
        test_validation()
        test_error_handling()

        print("=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        print()
        return 0

    except AssertionError as e:
        print()
        print("=" * 60)
        print("TEST FAILED!")
        print("=" * 60)
        print(f"Error: {e}")
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

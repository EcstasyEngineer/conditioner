"""
Tests for additive consecutive miss snowball system.
Formula: hours = (24 / base_freq) + (C × failures)
"""

import pytest
from utils.mantra_service import (
    get_effective_frequency,
    CONSECUTIVE_MISS_HOURS_ADDITIVE,
    CONSECUTIVE_FAILURES_THRESHOLD,
    DISABLE_OFFER_THRESHOLD
)


class TestAdditiveSnowball:
    """Test additive snowball mechanics."""

    def test_no_failures_no_penalty(self):
        """Test that 0 consecutive failures = no penalty."""
        base_freq = 2.0
        result = get_effective_frequency(base_freq, 0)
        assert result == base_freq, "No failures should not change frequency"

    def test_single_miss_penalty(self):
        """Test 1 miss adds C hours."""
        base_freq = 2.0  # 12hr interval
        result = get_effective_frequency(base_freq, 1)

        # Expected: 12hr + 4hr = 16hr = 1.5/day
        expected_freq = 24 / (12 + CONSECUTIVE_MISS_HOURS_ADDITIVE)
        assert result == pytest.approx(expected_freq)
        assert result == pytest.approx(1.5)

    def test_additive_progression(self):
        """Test that penalty grows linearly (additive)."""
        base_freq = 2.0  # 12hr base interval

        expected = [
            (0, 12, 2.0),    # 0 misses: 12hr
            (1, 16, 1.5),    # 1 miss: 12+4=16hr
            (2, 20, 1.2),    # 2 misses: 12+8=20hr
            (3, 24, 1.0),    # 3 misses: 12+12=24hr
            (5, 32, 0.75),   # 5 misses: 12+20=32hr
            (7, 40, 0.6),    # 7 misses: 12+28=40hr
        ]

        for failures, expected_hours, expected_freq in expected:
            effective = get_effective_frequency(base_freq, failures)
            effective_interval = 24 / effective

            assert effective_interval == pytest.approx(expected_hours, rel=0.01), \
                f"{failures} misses should give {expected_hours}hr interval"
            assert effective == pytest.approx(expected_freq, rel=0.01), \
                f"{failures} misses should give {expected_freq}/day"

    def test_high_frequency_user_progression(self):
        """Test 6/day user (4hr base interval)."""
        base_freq = 6.0

        expected = [
            (0, 4, 6.0),     # 0 misses: 4hr
            (1, 8, 3.0),     # 1 miss: 4+4=8hr
            (3, 16, 1.5),    # 3 misses: 4+12=16hr
            (5, 24, 1.0),    # 5 misses: 4+20=24hr (hits floor!)
            (7, 32, 0.75),   # 7 misses: 4+28=32hr
        ]

        for failures, expected_hours, expected_freq in expected:
            effective = get_effective_frequency(base_freq, failures)
            effective_interval = 24 / effective

            assert effective_interval == pytest.approx(expected_hours, rel=0.01)
            assert effective == pytest.approx(expected_freq, rel=0.01)

    def test_low_frequency_user_progression(self):
        """Test 0.3/day user (80hr base interval)."""
        base_freq = 0.3

        expected = [
            (0, 80, 0.3),      # 0 misses: 80hr
            (1, 84, 0.286),    # 1 miss: 80+4=84hr
            (3, 92, 0.261),    # 3 misses: 80+12=92hr
            (7, 108, 0.222),   # 7 misses: 80+28=108hr
        ]

        for failures, expected_hours, expected_freq in expected:
            effective = get_effective_frequency(base_freq, failures)
            effective_interval = 24 / effective

            assert effective_interval == pytest.approx(expected_hours, rel=0.01)
            assert effective == pytest.approx(expected_freq, rel=0.02)

    def test_24hr_floor_achievement(self):
        """Test when different frequencies hit 24hr floor."""
        test_cases = [
            (6.0, 5),  # 6/day hits 24hr at 5 misses
            (4.0, 5),  # 4/day hits 24hr at 5 misses (actually 26hr)
            (2.0, 3),  # 2/day hits 24hr at 3 misses
        ]

        for base_freq, expected_misses in test_cases:
            effective = get_effective_frequency(base_freq, expected_misses)
            effective_interval = 24 / effective

            assert effective_interval >= 24, \
                f"{base_freq}/day should hit ≥24hr by {expected_misses} misses"

    def test_consistent_absolute_delay(self):
        """Test that absolute delay is same across frequencies."""
        failures = 3

        # All users should get +12hr (3 × 4hr) regardless of base frequency
        for base_freq in [6.0, 4.0, 2.0, 1.0]:
            base_interval = 24 / base_freq
            effective = get_effective_frequency(base_freq, failures)
            effective_interval = 24 / effective

            absolute_delay = effective_interval - base_interval
            expected_delay = CONSECUTIVE_MISS_HOURS_ADDITIVE * failures

            assert absolute_delay == pytest.approx(expected_delay), \
                f"All frequencies should get +{expected_delay}hr for {failures} misses"

    def test_warning_threshold(self):
        """Test behavior at warning threshold (3 misses)."""
        base_freq = 2.0
        result = get_effective_frequency(base_freq, DISABLE_OFFER_THRESHOLD)

        # 2/day at 3 misses: 12hr + 12hr = 24hr = 1.0/day
        assert result == pytest.approx(1.0, rel=0.01)

    def test_auto_unenroll_threshold(self):
        """Test behavior at auto-unenroll threshold (8 misses)."""
        base_freq = 2.0
        result = get_effective_frequency(base_freq, CONSECUTIVE_FAILURES_THRESHOLD)

        # 2/day at 8 misses: 12hr + 32hr = 44hr = 0.545/day
        expected_interval = 12 + (CONSECUTIVE_MISS_HOURS_ADDITIVE * 8)
        expected_freq = 24 / expected_interval

        assert result == pytest.approx(expected_freq, rel=0.01)

    def test_negative_failures(self):
        """Test that negative failures are handled gracefully."""
        base_freq = 2.0
        result = get_effective_frequency(base_freq, -1)
        assert result == base_freq

    def test_zero_base_frequency(self):
        """Test edge case of zero base frequency."""
        # This would cause division by zero, should be avoided in practice
        # but let's verify it doesn't crash
        with pytest.raises(ZeroDivisionError):
            get_effective_frequency(0.0, 3)

    def test_c_value(self):
        """Verify C constant is set correctly."""
        assert CONSECUTIVE_MISS_HOURS_ADDITIVE == 4, \
            "Hours per miss should be 4"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

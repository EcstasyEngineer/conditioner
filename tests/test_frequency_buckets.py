"""
Tests for response time bucket frequency adjustments.
"""

import pytest
from utils.mantra_scheduler import (
    adjust_frequency,
    EAGER_THRESHOLD,
    QUICK_THRESHOLD,
    NORMAL_THRESHOLD,
    FREQUENCY_MULT_EAGER,
    FREQUENCY_MULT_QUICK,
    FREQUENCY_MULT_NORMAL,
    FREQUENCY_MULT_NEUTRAL,
    FREQUENCY_MULT_TIMEOUT,
    MIN_FREQUENCY,
    MAX_FREQUENCY
)


class TestFrequencyBuckets:
    """Test response time bucket frequency adjustments."""

    def test_eager_response(self):
        """Test eager response (<30s) gives +20% boost."""
        current = 2.0
        # Test various eager response times
        for response_time in [5, 15, 29]:
            result = adjust_frequency(current, success=True, response_time_seconds=response_time)
            expected = current * FREQUENCY_MULT_EAGER
            assert result == expected, f"Response time {response_time}s should get eager multiplier"

    def test_quick_response(self):
        """Test quick response (30s-2min) gives +15% boost."""
        current = 2.0
        # Test various quick response times
        for response_time in [30, 60, 119]:
            result = adjust_frequency(current, success=True, response_time_seconds=response_time)
            expected = current * FREQUENCY_MULT_QUICK
            assert result == expected, f"Response time {response_time}s should get quick multiplier"

    def test_normal_response(self):
        """Test normal response (2min-30min) gives +10% boost."""
        current = 2.0
        # Test various normal response times
        for response_time in [120, 600, 1799]:
            result = adjust_frequency(current, success=True, response_time_seconds=response_time)
            expected = current * FREQUENCY_MULT_NORMAL
            assert result == expected, f"Response time {response_time}s should get normal multiplier"

    def test_neutral_response(self):
        """Test neutral response (30min+) gives 0% change."""
        current = 2.0
        # Test various neutral response times (no upper limit)
        for response_time in [1800, 5400, 10800, 21600, 86400]:
            result = adjust_frequency(current, success=True, response_time_seconds=response_time)
            expected = current * FREQUENCY_MULT_NEUTRAL  # Should be 1.0 (no change)
            assert result == expected, f"Response time {response_time}s should get neutral multiplier (1.0)"
            assert result == current, f"Neutral response should not change frequency"

    def test_timeout_penalty(self):
        """Test timeout gives -15% penalty."""
        current = 2.0
        result = adjust_frequency(current, success=False)
        expected = current * FREQUENCY_MULT_TIMEOUT
        assert result == expected, "Timeout should apply timeout multiplier"

    def test_boundary_conditions(self):
        """Test exact threshold boundaries."""
        current = 2.0

        # Test boundary: 30s should be quick, not eager
        result_30 = adjust_frequency(current, success=True, response_time_seconds=30)
        assert result_30 == current * FREQUENCY_MULT_QUICK

        # Test boundary: 120s should be normal, not quick
        result_120 = adjust_frequency(current, success=True, response_time_seconds=120)
        assert result_120 == current * FREQUENCY_MULT_NORMAL

        # Test boundary: 1800s should be neutral, not normal
        result_1800 = adjust_frequency(current, success=True, response_time_seconds=1800)
        assert result_1800 == current * FREQUENCY_MULT_NEUTRAL

    def test_min_frequency_clamping(self):
        """Test frequency doesn't go below minimum."""
        current = MIN_FREQUENCY
        # Apply timeout penalty
        result = adjust_frequency(current, success=False)
        assert result >= MIN_FREQUENCY, "Frequency should not go below minimum"

    def test_max_frequency_clamping(self):
        """Test frequency doesn't exceed maximum."""
        current = MAX_FREQUENCY
        # Apply instant boost
        result = adjust_frequency(current, success=True, response_time_seconds=10)
        assert result <= MAX_FREQUENCY, "Frequency should not exceed maximum"

    def test_no_response_time_fallback(self):
        """Test fallback when response_time_seconds is None."""
        current = 2.0
        result = adjust_frequency(current, success=True, response_time_seconds=None)
        expected = current * FREQUENCY_MULT_NORMAL
        assert result == expected, "Should default to normal multiplier when no response time"

    def test_realistic_progression(self):
        """Test realistic frequency progression scenarios."""
        # Scenario 1: User starts slow, gets faster
        freq = 1.0  # Start at 1/day

        # Neutral response (42min)
        freq = adjust_frequency(freq, success=True, response_time_seconds=2500)
        assert freq == 1.0, "Neutral response should not change frequency"

        # Normal response (15min)
        freq = adjust_frequency(freq, success=True, response_time_seconds=900)
        assert freq == pytest.approx(1.1), "Normal response should increase 10%"

        # Quick response (90s)
        freq = adjust_frequency(freq, success=True, response_time_seconds=90)
        assert freq == pytest.approx(1.265), "Quick response should increase 15%"

        # Eager response (20s)
        freq = adjust_frequency(freq, success=True, response_time_seconds=20)
        assert freq == pytest.approx(1.518), "Eager response should increase 20%"

        # Scenario 2: User gets slower (no penalties, just neutral)
        freq = 3.0

        # Neutral response (4hr)
        freq = adjust_frequency(freq, success=True, response_time_seconds=14400)
        assert freq == 3.0, "Neutral response should not change frequency"

        # Neutral response (8hr)
        freq = adjust_frequency(freq, success=True, response_time_seconds=28800)
        assert freq == 3.0, "Neutral response should not change frequency"

        # Timeout (only penalty)
        freq = adjust_frequency(freq, success=False)
        assert freq == pytest.approx(2.55), "Timeout should decrease 15%"

    def test_multiplier_relationships(self):
        """Test that multipliers have correct relative relationships."""
        # Eager should be 2x the boost of normal
        eager_boost = FREQUENCY_MULT_EAGER - 1.0  # e.g., 1.20 - 1.0 = 0.20
        normal_boost = FREQUENCY_MULT_NORMAL - 1.0    # e.g., 1.10 - 1.0 = 0.10
        assert eager_boost == pytest.approx(normal_boost * 2.0), "Eager boost should be 2x normal boost"

        # Quick should be 1.5x the boost of normal
        quick_boost = FREQUENCY_MULT_QUICK - 1.0        # e.g., 1.15 - 1.0 = 0.15
        assert quick_boost == pytest.approx(normal_boost * 1.5), "Quick boost should be 1.5x normal boost"

        # Neutral should be exactly 1.0 (no change)
        assert FREQUENCY_MULT_NEUTRAL == 1.0, "Neutral should have no effect"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Mantra scheduling using prediction error learning and probability integration.

This module implements the core scheduling algorithm for the Mantra V2 system:
- AvailabilityLearner: Learns user availability patterns via prediction error
- schedule_next_delivery(): Schedules encounters by integrating probability distribution
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional


# Constants
LEARNING_RATE = 0.20
FLOOR = 0.1  # Minimum probability (prevents death spiral)
CEIL = 1.0   # Maximum probability
DEFAULT_FREQUENCY = 1.0  # Encounters per day
MIN_FREQUENCY = 0.33  # Minimum: 1 encounter per 3 days
MAX_FREQUENCY = 6.0   # Maximum: 6 encounters per day
FREQUENCY_INCREASE_FAST = 1.1  # Multiplier for fast responses (<2min)
FREQUENCY_INCREASE_NORMAL = 1.05  # Multiplier for normal responses
FREQUENCY_DECREASE = 0.9  # Multiplier for timeouts
MAX_LOOKAHEAD_HOURS = 168  # Check up to 7 days ahead

# Delivery mode constants
DELIVERY_MODE_ADAPTIVE = "adaptive"
DELIVERY_MODE_LEGACY = "legacy"
DELIVERY_MODE_FIXED = "fixed"
DEFAULT_DELIVERY_MODE = DELIVERY_MODE_ADAPTIVE
DEFAULT_LEGACY_INTERVAL_HOURS = 4
DEFAULT_FIXED_TIMES = ["09:00", "14:00", "19:00"]


class AvailabilityLearner:
    """
    Learns user availability patterns using prediction error algorithm.

    Based on Elo-style updates: large updates when surprised, small when expected.
    Updates are proportional to prediction error: delta = learning_rate * (actual - expected)

    Attributes:
        distribution: List of 24 floats (one per hour), representing availability probability
        learning_rate: How quickly to update (0.20 optimal from testing)
        floor: Minimum probability to prevent death spiral
        ceil: Maximum probability cap
    """

    def __init__(self, initial_distribution: Optional[List[float]] = None):
        """
        Initialize learner with optional pre-learned distribution.

        Args:
            initial_distribution: Optional list of 24 floats. If None, starts with uniform 0.5
        """
        if initial_distribution is not None:
            if len(initial_distribution) != 24:
                raise ValueError("Distribution must have exactly 24 values (one per hour)")
            self.distribution = initial_distribution.copy()
        else:
            # Start with uniform distribution
            self.distribution = [0.5 for _ in range(24)]

        self.learning_rate = LEARNING_RATE
        self.floor = FLOOR
        self.ceil = CEIL

    def update(self, dt: datetime, success: bool) -> None:
        """
        Update distribution based on encounter outcome.

        Uses prediction error learning: delta = learning_rate * (actual - expected)
        Values are automatically rounded to 3 decimals to keep config files clean.

        Args:
            dt: Datetime of the encounter
            success: True if user responded, False if timeout
        """
        hour = dt.hour
        actual = 1.0 if success else 0.0
        expected = self.distribution[hour]

        # Prediction error
        error = actual - expected
        delta = self.learning_rate * error

        # Update with floor/ceiling constraints
        new_value = self.distribution[hour] + delta
        clamped_value = max(self.floor, min(self.ceil, new_value))

        # Round to 3 decimals to keep config files clean
        self.distribution[hour] = round(clamped_value, 3)

    def get_prob(self, dt: datetime) -> float:
        """
        Get availability probability for a given datetime.

        Args:
            dt: Datetime to query

        Returns:
            Probability between 0.0 and 1.0
        """
        return self.distribution[dt.hour]

    def get_distribution(self) -> List[float]:
        """
        Get the full distribution array.

        Returns:
            Copy of the 24-hour distribution list
        """
        return self.distribution.copy()


def schedule_next_delivery(
    learner: AvailabilityLearner,
    frequency: float,
    current_time: Optional[datetime] = None
) -> datetime:
    """
    Schedule next encounter by integrating probability distribution.

    Walks forward in time, accumulating probability mass until target is reached.
    Higher frequency = less mass needed = schedules sooner.
    Naturally "squeezes away" from low-probability hours.

    Args:
        learner: AvailabilityLearner with learned distribution
        frequency: Encounters per day (e.g., 2.0 = twice per day)
        current_time: Optional starting time (defaults to now)

    Returns:
        Datetime for next scheduled delivery
    """
    if current_time is None:
        current_time = datetime.now()

    # Clamp frequency to valid range
    frequency = max(MIN_FREQUENCY, min(MAX_FREQUENCY, frequency))

    # Get distribution and normalize
    distribution = learner.get_distribution()
    distribution_sum = sum(distribution)

    # Calculate target probability mass to accumulate
    # Normalized by distribution sum so that shape matters, not absolute values
    # frequency = 1.0/day with uniform 0.5 distribution → target = 12.0 → ~24 hours
    # frequency = 2.0/day with uniform 0.5 distribution → target = 6.0 → ~12 hours
    target_mass = distribution_sum / frequency

    # Walk forward in time, accumulating probability
    accumulated_mass = 0.0

    for hours_ahead in range(1, MAX_LOOKAHEAD_HOURS + 1):
        check_time = current_time + timedelta(hours=hours_ahead)
        hour = check_time.hour

        # Get probability for this hour
        prob = distribution[hour]

        # Accumulate mass (1 hour * probability)
        accumulated_mass += prob

        # Have we reached target?
        if accumulated_mass >= target_mass:
            # Round to top of the hour
            return check_time.replace(minute=0, second=0, microsecond=0)

    # Fallback: If we couldn't schedule within a week, schedule 24 hours from now
    return (current_time + timedelta(hours=24)).replace(minute=0, second=0, microsecond=0)


def adjust_frequency(
    current_frequency: float,
    success: bool,
    response_time_seconds: Optional[int] = None
) -> float:
    """
    Adjust encounter frequency based on user engagement (TCP-style).

    On success:
        - Fast response (<120s): Increase by 10%
        - Normal response: Increase by 5%
    On timeout:
        - Decrease by 10%

    Args:
        current_frequency: Current encounters per day
        success: True if user responded, False if timeout
        response_time_seconds: Response time in seconds (only used if success=True)

    Returns:
        New frequency, clamped to valid range [MIN_FREQUENCY, MAX_FREQUENCY]
    """
    if success:
        # Increase frequency
        if response_time_seconds is not None and response_time_seconds < 120:
            new_frequency = current_frequency * FREQUENCY_INCREASE_FAST
        else:
            new_frequency = current_frequency * FREQUENCY_INCREASE_NORMAL
    else:
        # Decrease frequency on timeout
        new_frequency = current_frequency * FREQUENCY_DECREASE

    # Clamp to valid range
    return max(MIN_FREQUENCY, min(MAX_FREQUENCY, new_frequency))


def schedule_next_delivery_legacy(
    interval_hours: int,
    current_time: Optional[datetime] = None
) -> datetime:
    """
    Schedule next encounter using fixed interval (legacy mode).

    Simple interval-based scheduling like the old V1 system.
    Delivers mantras at regular intervals regardless of user patterns.

    Args:
        interval_hours: Hours between deliveries
        current_time: Optional starting time (defaults to now)

    Returns:
        Datetime for next scheduled delivery
    """
    if current_time is None:
        current_time = datetime.now()

    # Clamp interval to reasonable range (1-24 hours)
    interval_hours = max(1, min(24, interval_hours))

    # Schedule next delivery at interval from now
    next_time = current_time + timedelta(hours=interval_hours)

    # Round to top of the hour for consistency
    return next_time.replace(minute=0, second=0, microsecond=0)


def schedule_next_delivery_fixed(
    fixed_times: List[str],
    current_time: Optional[datetime] = None
) -> datetime:
    """
    Schedule next encounter at a fixed time of day (fixed mode).

    Delivers mantras at the same times every day (e.g., 9am, 2pm, 7pm).
    Finds the next scheduled time after current time.

    Args:
        fixed_times: List of time strings in "HH:MM" format (24-hour)
        current_time: Optional starting time (defaults to now)

    Returns:
        Datetime for next scheduled delivery

    Raises:
        ValueError: If fixed_times is empty or contains invalid time strings
    """
    if current_time is None:
        current_time = datetime.now()

    if not fixed_times:
        raise ValueError("fixed_times cannot be empty")

    # Parse all fixed times and create candidate datetimes for today
    candidates = []
    for time_str in fixed_times:
        try:
            # Parse time string
            hour, minute = map(int, time_str.split(":"))

            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError(f"Invalid time: {time_str}")

            # Create datetime for today at this time
            today_time = current_time.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0
            )

            # If this time hasn't passed today, add it
            if today_time > current_time:
                candidates.append(today_time)

            # Also add tomorrow's occurrence
            tomorrow_time = today_time + timedelta(days=1)
            candidates.append(tomorrow_time)

        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid time format: {time_str}. Use HH:MM format.") from e

    # Sort candidates and return the earliest
    if not candidates:
        raise ValueError("No valid future times found")

    candidates.sort()
    return candidates[0]


def validate_delivery_mode(mode: str) -> bool:
    """
    Validate delivery mode string.

    Args:
        mode: Delivery mode to validate

    Returns:
        True if valid, False otherwise
    """
    return mode in [DELIVERY_MODE_ADAPTIVE, DELIVERY_MODE_LEGACY, DELIVERY_MODE_FIXED]


def validate_fixed_times(fixed_times: List[str]) -> bool:
    """
    Validate fixed times list.

    Args:
        fixed_times: List of time strings to validate

    Returns:
        True if all times are valid, False otherwise
    """
    if not fixed_times:
        return False

    for time_str in fixed_times:
        try:
            hour, minute = map(int, time_str.split(":"))
            if not (0 <= hour < 24 and 0 <= minute < 60):
                return False
        except (ValueError, AttributeError):
            return False

    return True

"""
Mantra V2 service layer - Core business logic.

This module implements the state machine and business logic for the Mantra V2 system:
- Two-timestamp state machine (next_delivery + sent)
- Enrollment/unenrollment
- Encounter delivery and response handling
- Config management
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, List

from .mantra_scheduler import (
    AvailabilityLearner,
    schedule_next_delivery,
    schedule_next_delivery_legacy,
    schedule_next_delivery_fixed,
    adjust_frequency,
    DEFAULT_FREQUENCY,
    DELIVERY_MODE_ADAPTIVE,
    DELIVERY_MODE_LEGACY,
    DELIVERY_MODE_FIXED,
    DEFAULT_DELIVERY_MODE,
    DEFAULT_LEGACY_INTERVAL_HOURS,
    DEFAULT_FIXED_TIMES
)
from .mantras import (
    select_mantra_from_themes,
    format_mantra_text,
    check_mantra_match,
    calculate_speed_bonus,
    get_tier
)
from .encounters import log_encounter


# Constants
CONSECUTIVE_FAILURES_THRESHOLD = 8  # Auto-disable after this many consecutive failures
DISABLE_OFFER_THRESHOLD = 3  # Offer disable button after this many failures
INITIAL_ENROLLMENT_DELAY_SECONDS = 30  # Delay before first mantra
MISSED_PENALTY_RATE = 0.10  # Penalty rate for hours before response (weighted by probability)
CONSECUTIVE_MISS_HOURS_ADDITIVE = 4  # Hours added to interval per consecutive miss


def get_default_config() -> Dict:
    """
    Get default mantra configuration for new users.

    Returns:
        Dict with default configuration values
    """
    return {
        "enrolled": False,
        "themes": [],
        "subject": "puppet",
        "controller": "Master",
        "frequency": DEFAULT_FREQUENCY,
        "consecutive_failures": 0,
        "next_delivery": None,  # ISO timestamp string
        "sent": None,  # ISO timestamp string when current mantra was sent
        "current_mantra": None,  # Dict with mantra data
        "availability_distribution": None,  # List of 24 floats (managed by learner)
        "favorite_mantras": [],  # List of mantra texts that user has favorited
        "delivery_mode": DEFAULT_DELIVERY_MODE,  # "adaptive", "legacy", or "fixed"
        "legacy_interval_hours": DEFAULT_LEGACY_INTERVAL_HOURS,  # Hours between mantras in legacy mode
        "fixed_times": DEFAULT_FIXED_TIMES,  # List of "HH:MM" times for fixed mode
    }


def get_learner(config: Dict) -> AvailabilityLearner:
    """
    Get or create AvailabilityLearner from user config.

    Args:
        config: User configuration dict

    Returns:
        AvailabilityLearner instance (initialized from config or fresh)
    """
    distribution = config.get("availability_distribution")
    return AvailabilityLearner(initial_distribution=distribution)


def save_learner(config: Dict, learner: AvailabilityLearner) -> None:
    """
    Save learner distribution back to config.

    Args:
        config: User configuration dict (modified in place)
        learner: AvailabilityLearner to save
    """
    config["availability_distribution"] = learner.get_distribution()


def get_effective_frequency(base_frequency: float, consecutive_failures: int) -> float:
    """
    Calculate effective frequency with consecutive miss additive penalty.

    Each consecutive miss adds a fixed number of hours to the delivery interval.
    This creates consistent absolute delays regardless of base frequency.

    Formula: hours_until_next = (24 / base_freq) + (C × failures)
             effective_freq = 24 / hours_until_next

    Examples (with C=4 hours per miss):
        Base freq 6/day (4hr intervals):
            0 misses: 4hr  → 6.0/day
            3 misses: 16hr → 1.5/day
            5 misses: 24hr → 1.0/day (hits 24hr floor)
            7 misses: 32hr → 0.75/day

        Base freq 2/day (12hr intervals):
            0 misses: 12hr → 2.0/day
            3 misses: 24hr → 1.0/day (hits 24hr floor)
            5 misses: 32hr → 0.75/day
            7 misses: 40hr → 0.6/day

    Args:
        base_frequency: Base encounters per day (from bucket adjustments)
        consecutive_failures: Number of consecutive misses

    Returns:
        Effective frequency with additive penalty applied
    """
    if consecutive_failures <= 0:
        return base_frequency

    # Calculate base interval
    base_interval_hours = 24 / base_frequency

    # Add penalty hours
    penalty_hours = CONSECUTIVE_MISS_HOURS_ADDITIVE * consecutive_failures
    total_interval_hours = base_interval_hours + penalty_hours

    # Convert back to frequency
    return 24 / total_interval_hours


def enroll_user(config: Dict, themes: List[str], subject: str, controller: str) -> None:
    """
    Enroll user in mantra system.

    Sets up initial state and schedules first encounter with a short delay.

    Args:
        config: User configuration dict (modified in place)
        themes: List of theme names to enable
        subject: Subject name (e.g., "puppet", "slave")
        controller: Controller name (e.g., "Master", "Mistress")
    """
    config["enrolled"] = True
    config["themes"] = themes
    config["subject"] = subject
    config["controller"] = controller
    config["frequency"] = DEFAULT_FREQUENCY
    config["consecutive_failures"] = 0
    config["sent"] = None

    # Schedule first encounter with short delay
    first_delivery = datetime.now() + timedelta(seconds=INITIAL_ENROLLMENT_DELAY_SECONDS)
    config["next_delivery"] = first_delivery.isoformat()

    # Pre-select first mantra (special enrollment message)
    base_points = 100
    config["current_mantra"] = {
        "text": "My thoughts are being reprogrammed.",
        "theme": "enrollment",
        "difficulty": get_tier(base_points),
        "base_points": base_points
    }


def unenroll_user(config: Dict) -> None:
    """
    Unenroll user from mantra system.

    Clears enrollment flag and pending encounters, but preserves learned distribution.

    Args:
        config: User configuration dict (modified in place)
    """
    config["enrolled"] = False
    config["sent"] = None
    config["current_mantra"] = None
    # Keep next_delivery, availability_distribution, and frequency for potential re-enrollment


def should_deliver_mantra(config: Dict) -> bool:
    """
    Check if it's time to deliver a mantra based on state machine.

    State interpretation:
        - sent == None: Waiting to send at next_delivery
        - sent != None: Already sent, awaiting response

    Args:
        config: User configuration dict

    Returns:
        True if we should deliver a mantra now
    """
    if not config.get("enrolled"):
        return False

    # Already sent, waiting for response
    if config.get("sent") is not None:
        return False

    # Check if it's time to deliver
    next_delivery_str = config.get("next_delivery")
    if next_delivery_str is None:
        return False

    try:
        next_delivery = datetime.fromisoformat(next_delivery_str)
        return datetime.now() >= next_delivery
    except (ValueError, TypeError):
        return False


def check_for_timeout(config: Dict, available_themes: Dict) -> bool:
    """
    Check if current encounter has timed out.

    A timeout occurs when:
        - Mantra was sent (sent != None)
        - We've reached the next_delivery time without a response

    Args:
        config: User configuration dict
        available_themes: Dict of theme data (for scheduling next mantra)

    Returns:
        True if a timeout was detected and handled
    """
    if not config.get("enrolled"):
        return False

    # Not sent yet, no timeout possible
    if config.get("sent") is None:
        return False

    # Check if we've hit the next delivery time (deadline)
    next_delivery_str = config.get("next_delivery")
    if next_delivery_str is None:
        return False

    try:
        next_delivery = datetime.fromisoformat(next_delivery_str)
        if datetime.now() < next_delivery:
            return False  # Still waiting

        # Timeout detected!
        handle_timeout(config, available_themes)
        return True

    except (ValueError, TypeError):
        return False


def handle_timeout(config: Dict, available_themes: Dict) -> None:
    """
    Handle encounter timeout.

    Updates state machine, logs failed encounter, adjusts frequency,
    and schedules next encounter.

    Args:
        config: User configuration dict (modified in place)
        available_themes: Dict of theme data
    """
    # Log failed encounter
    if config.get("current_mantra"):
        # Format the mantra for display
        formatted_text = format_mantra_text(
            config["current_mantra"]["text"],
            config.get("subject", "puppet"),
            config.get("controller", "Master")
        )
        encounter = {
            "timestamp": datetime.fromisoformat(config["sent"]).isoformat(),
            "mantra": formatted_text,
            "mantra_template": config["current_mantra"]["text"],
            "subject": config.get("subject", "puppet"),
            "controller": config.get("controller", "Master"),
            "theme": config["current_mantra"]["theme"],
            "difficulty": config["current_mantra"]["difficulty"],
            "base_points": config["current_mantra"]["base_points"],
            "completed": False,
            "expired": True
        }
        # Note: user_id will be added by caller
        # log_encounter(user_id, encounter)  # Caller must do this

    # Update learner (failure)
    # For timeouts, penalize ALL hours between sent and deadline
    # User had the entire window to respond but didn't
    learner = get_learner(config)
    sent_time = datetime.fromisoformat(config["sent"])
    deadline = datetime.fromisoformat(config["next_delivery"])

    # Penalize every hour in the window
    current_hour = sent_time.replace(minute=0, second=0, microsecond=0)
    deadline_hour = deadline.replace(minute=0, second=0, microsecond=0)

    while current_hour <= deadline_hour:
        # Use full learning rate for timeouts (not reduced penalty)
        learner.update(current_hour, success=False)
        current_hour += timedelta(hours=1)

    save_learner(config, learner)

    # Adjust frequency (decrease)
    config["frequency"] = adjust_frequency(config["frequency"], success=False)

    # Increment consecutive failures
    config["consecutive_failures"] = config.get("consecutive_failures", 0) + 1

    # Check for auto-disable
    if config["consecutive_failures"] >= CONSECUTIVE_FAILURES_THRESHOLD:
        config["enrolled"] = False

    # Clear sent timestamp
    config["sent"] = None

    # Set next_delivery to now for immediate re-delivery
    # (if still enrolled, the delivery loop will pick it up immediately)
    if config.get("enrolled"):
        config["next_delivery"] = datetime.now().isoformat()
        # Pre-select next mantra
        mantra = prepare_mantra_for_delivery(config, available_themes)
        if mantra:
            config["current_mantra"] = mantra


def prepare_mantra_for_delivery(config: Dict, available_themes: Dict) -> Optional[Dict]:
    """
    Prepare mantra for delivery (pre-select but keep as template).

    Selects a random mantra from user's themes. Text is kept as raw template
    and will be formatted at display time to allow controller/subject changes.

    Args:
        config: User configuration dict
        available_themes: Dict of theme data

    Returns:
        Dict with mantra data ready for delivery, or None if no themes available
    """
    # Pass favorites to selection function for 2x weighting
    favorites = config.get("favorite_mantras", [])
    mantra_data = select_mantra_from_themes(config["themes"], available_themes, favorites)
    if not mantra_data:
        return None

    # Store raw template (will be formatted at display time)
    return {
        "text": mantra_data["text"],  # Keep as template
        "theme": mantra_data["theme"],
        "difficulty": get_tier(mantra_data["base_points"]),
        "base_points": mantra_data["base_points"]
    }


def deliver_mantra(config: Dict, available_themes: Dict) -> Optional[Dict]:
    """
    Deliver a mantra to the user.

    Updates state machine to mark mantra as sent and schedules next delivery.

    Args:
        config: User configuration dict (modified in place)
        available_themes: Dict of theme data

    Returns:
        Dict with mantra data for display, or None if delivery failed
    """
    # Get current mantra (pre-selected during previous scheduling)
    mantra = config.get("current_mantra")
    if not mantra:
        # Fallback: prepare a new mantra now
        mantra = prepare_mantra_for_delivery(config, available_themes)
        if not mantra:
            return None

    # Mark as sent
    config["sent"] = datetime.now().isoformat()

    # Save the delivered mantra for validation (store as raw template)
    # current_mantra will be overwritten when we schedule next encounter
    config["delivered_mantra"] = mantra.copy()

    # Schedule next encounter (immediately, so deadline is set)
    learner = get_learner(config)
    schedule_next_encounter(config, available_themes, learner)

    # Return raw template (caller will format for display)
    return mantra


def schedule_next_encounter(
    config: Dict,
    available_themes: Dict,
    learner: Optional[AvailabilityLearner] = None
) -> None:
    """
    Schedule the next mantra encounter.

    Uses delivery mode to determine scheduling algorithm:
    - adaptive: Probability integration with learned availability patterns
    - legacy: Fixed interval scheduling
    - fixed: Same times every day

    Applies consecutive miss snowball penalty to scheduling (not base frequency).

    Pre-selects the mantra to be delivered.

    Args:
        config: User configuration dict (modified in place)
        available_themes: Dict of theme data
        learner: Optional AvailabilityLearner (created if not provided, only used for adaptive mode)
    """
    delivery_mode = config.get("delivery_mode", DEFAULT_DELIVERY_MODE)

    # Apply consecutive miss snowball to get effective frequency
    base_frequency = config["frequency"]
    consecutive_failures = config.get("consecutive_failures", 0)
    effective_frequency = get_effective_frequency(base_frequency, consecutive_failures)

    # Calculate next delivery time based on mode
    if delivery_mode == DELIVERY_MODE_ADAPTIVE:
        # Use prediction error learning and probability integration
        if learner is None:
            learner = get_learner(config)
        next_time = schedule_next_delivery(learner, effective_frequency)

    elif delivery_mode == DELIVERY_MODE_LEGACY:
        # Use fixed interval (adjust by additive penalty)
        base_interval_hours = config.get("legacy_interval_hours", DEFAULT_LEGACY_INTERVAL_HOURS)
        # Add penalty hours directly
        penalty_hours = CONSECUTIVE_MISS_HOURS_ADDITIVE * consecutive_failures
        adjusted_interval = base_interval_hours + penalty_hours
        next_time = schedule_next_delivery_legacy(int(adjusted_interval))

    elif delivery_mode == DELIVERY_MODE_FIXED:
        # Use fixed times of day (snowball doesn't apply to fixed times)
        fixed_times = config.get("fixed_times", DEFAULT_FIXED_TIMES)
        try:
            next_time = schedule_next_delivery_fixed(fixed_times)
        except ValueError:
            # Fallback to default times if invalid
            config["fixed_times"] = DEFAULT_FIXED_TIMES
            next_time = schedule_next_delivery_fixed(DEFAULT_FIXED_TIMES)

    else:
        # Fallback to adaptive mode if invalid
        config["delivery_mode"] = DEFAULT_DELIVERY_MODE
        if learner is None:
            learner = get_learner(config)
        next_time = schedule_next_delivery(learner, effective_frequency)

    config["next_delivery"] = next_time.isoformat()

    # Pre-select mantra for this encounter
    mantra = prepare_mantra_for_delivery(config, available_themes)
    if mantra:
        config["current_mantra"] = mantra


def handle_mantra_response(
    config: Dict,
    available_themes: Dict,
    user_response: str,
    response_time_seconds: int,
    was_public: bool = False
) -> Dict:
    """
    Handle user's response to a mantra.

    Checks if response matches, awards points, updates learner and frequency,
    logs encounter, and schedules next encounter.

    Args:
        config: User configuration dict (modified in place)
        available_themes: Dict of theme data
        user_response: User's typed response
        response_time_seconds: Time taken to respond (in seconds)
        was_public: Whether response was in public channel

    Returns:
        Dict with outcome data (success, points, etc.)
    """
    if config.get("sent") is None:
        return {"success": False, "error": "No active mantra"}

    # Use delivered_mantra (what was actually sent), not current_mantra (next one)
    delivered_mantra = config.get("delivered_mantra")
    if not delivered_mantra:
        return {"success": False, "error": "No mantra data"}

    # Format the expected text (delivered_mantra contains raw template)
    expected_text = format_mantra_text(
        delivered_mantra["text"],
        config.get("subject", "puppet"),
        config.get("controller", "Master")
    )

    # Check if response matches
    matches = check_mantra_match(user_response, expected_text)

    if not matches:
        return {
            "success": False,
            "error": "Incorrect response",
            "expected": expected_text
        }

    # Response is correct!
    base_points = delivered_mantra["base_points"]
    speed_bonus = calculate_speed_bonus(response_time_seconds)
    public_bonus = 50 if was_public else 0
    total_points = base_points + speed_bonus + public_bonus

    # Log successful encounter
    encounter = {
        "timestamp": datetime.fromisoformat(config["sent"]).isoformat(),
        "mantra": expected_text,
        "mantra_template": delivered_mantra["text"],
        "subject": config.get("subject", "puppet"),
        "controller": config.get("controller", "Master"),
        "theme": delivered_mantra["theme"],
        "difficulty": delivered_mantra["difficulty"],
        "base_points": base_points,
        "speed_bonus": speed_bonus,
        "public_bonus": public_bonus,
        "completed": True,
        "response_time": response_time_seconds,
        "was_public": was_public
    }
    # Note: user_id will be added by caller

    # Update learner (success)
    # Use response time, not send time, to learn when user is actually available
    learner = get_learner(config)
    response_time = datetime.now()
    sent_time = datetime.fromisoformat(config["sent"])

    # Positive update for response hour
    learner.update(response_time, success=True)

    # Penalize all missed hours between sent and response
    # This is the key improvement: we learn from ALL the hours where user didn't respond
    current_hour = sent_time.replace(minute=0, second=0, microsecond=0)
    response_hour_rounded = response_time.replace(minute=0, second=0, microsecond=0)

    while current_hour < response_hour_rounded:
        hour_to_penalize = current_hour.hour

        # Don't double-penalize the response hour
        if hour_to_penalize != response_time.hour:
            # Get current probability for this hour
            expected = learner.distribution[hour_to_penalize]

            # Weighted penalty (proportional to current probability)
            # Higher probability hours get bigger penalty (they were "wrong")
            weight = expected
            actual = 0.0  # They didn't respond during this hour
            error = actual - expected
            delta = MISSED_PENALTY_RATE * error * weight

            new_value = learner.distribution[hour_to_penalize] + delta
            learner.distribution[hour_to_penalize] = max(
                learner.floor,
                min(learner.ceil, new_value)
            )

        current_hour += timedelta(hours=1)

    save_learner(config, learner)

    # Adjust frequency (increase)
    config["frequency"] = adjust_frequency(
        config["frequency"],
        success=True,
        response_time_seconds=response_time_seconds
    )

    # Reset consecutive failures
    config["consecutive_failures"] = 0

    # Clear sent timestamp
    config["sent"] = None

    # Schedule next encounter
    schedule_next_encounter(config, available_themes, learner)

    return {
        "success": True,
        "points": total_points,
        "base_points": base_points,
        "speed_bonus": speed_bonus,
        "public_bonus": public_bonus,
        "encounter": encounter
    }

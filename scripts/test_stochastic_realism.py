#!/usr/bin/env python3
"""
Realistic stochastic user simulator for testing mantra delivery algorithms.

This simulator models actual user behavior including:
- Sleep schedules (hard unavailability)
- Work/school periods (low availability)
- Commute/errands (hard unavailability)
- Desktop-only users (only available at computer)
- Stochastic response delays (see notification but busy)
- Variable attention patterns

Tests both current algorithm and proposed improvements with missed-hour penalties.
"""

import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


# ============================================================================
# USER ARCHETYPES WITH REALISTIC BEHAVIOR
# ============================================================================

class DeviceAccess(Enum):
    """How user accesses Discord"""
    MOBILE_ALWAYS = "mobile_always"  # Phone always available
    DESKTOP_ONLY = "desktop_only"    # Only on computer
    MIXED = "mixed"                   # Both, but desktop preferred


@dataclass
class TimeBlock:
    """A period of time with specific availability"""
    start_hour: int      # 0-23
    end_hour: int        # 0-23 (wraps around if < start)
    base_prob: float     # 0.0-1.0 base probability of responding
    can_see: bool        # Can they see the notification?
    description: str


@dataclass
class UserArchetype:
    """Realistic user behavior pattern"""
    name: str
    device: DeviceAccess
    blocks: List[TimeBlock]
    response_delay_minutes: Tuple[int, int]  # (min, max) delay when responding
    see_but_ignore_prob: float  # Probability of seeing but not responding


def create_morning_person_mobile() -> UserArchetype:
    """Morning person with mobile access - can respond anytime awake"""
    return UserArchetype(
        name="Morning Person (Mobile)",
        device=DeviceAccess.MOBILE_ALWAYS,
        blocks=[
            # Sleep - truly unavailable
            TimeBlock(0, 6, 0.0, False, "Deep sleep"),
            # Morning routine - sees notification, might respond
            TimeBlock(6, 9, 0.85, True, "Morning routine"),
            # Work - lower availability
            TimeBlock(9, 17, 0.35, True, "At work"),
            # Evening - high availability
            TimeBlock(17, 22, 0.80, True, "Free time"),
            # Winding down
            TimeBlock(22, 24, 0.50, True, "Preparing for bed"),
        ],
        response_delay_minutes=(1, 45),  # Fast responder
        see_but_ignore_prob=0.15  # Sometimes busy
    )


def create_night_owl_desktop() -> UserArchetype:
    """Night owl who only has Discord on desktop computer"""
    return UserArchetype(
        name="Night Owl (Desktop Only)",
        device=DeviceAccess.DESKTOP_ONLY,
        blocks=[
            # Asleep
            TimeBlock(2, 11, 0.0, False, "Sleeping"),
            # Awake but not at computer
            TimeBlock(11, 14, 0.0, False, "Lunch/errands"),
            # Afternoon session
            TimeBlock(14, 18, 0.70, True, "At computer"),
            # Dinner/break
            TimeBlock(18, 20, 0.0, False, "Dinner/out"),
            # Peak hours
            TimeBlock(20, 2, 0.90, True, "Gaming/online"),
        ],
        response_delay_minutes=(2, 90),  # Variable attention
        see_but_ignore_prob=0.25  # Often in flow state, ignores
    )


def create_nine_to_five_strict() -> UserArchetype:
    """Office worker, mobile phone but can't use at work"""
    return UserArchetype(
        name="9-to-5 Worker (Mobile, strict work)",
        device=DeviceAccess.MIXED,
        blocks=[
            # Sleep
            TimeBlock(0, 7, 0.0, False, "Sleeping"),
            # Morning prep
            TimeBlock(7, 8, 0.60, True, "Getting ready"),
            # Commute - can see but often can't respond
            TimeBlock(8, 9, 0.15, True, "Commute to work"),
            # Work - can't use phone
            TimeBlock(9, 12, 0.0, False, "Work (morning)"),
            # Lunch break
            TimeBlock(12, 13, 0.75, True, "Lunch break"),
            # Work afternoon
            TimeBlock(13, 17, 0.0, False, "Work (afternoon)"),
            # Commute home
            TimeBlock(17, 18, 0.20, True, "Commute home"),
            # Evening - high availability
            TimeBlock(18, 23, 0.85, True, "Free evening"),
            # Pre-bed
            TimeBlock(23, 24, 0.40, True, "Winding down"),
        ],
        response_delay_minutes=(5, 120),  # Checks periodically
        see_but_ignore_prob=0.20
    )


def create_student_chaotic() -> UserArchetype:
    """College student with chaotic schedule"""
    return UserArchetype(
        name="College Student (Chaotic)",
        device=DeviceAccess.MOBILE_ALWAYS,
        blocks=[
            # Sleep (late)
            TimeBlock(3, 10, 0.0, False, "Sleeping in"),
            # Morning classes
            TimeBlock(10, 12, 0.30, True, "Classes/studying"),
            # Lunch/social
            TimeBlock(12, 14, 0.70, True, "Lunch/social"),
            # Afternoon variable
            TimeBlock(14, 18, 0.50, True, "Classes/library"),
            # Dinner/social
            TimeBlock(18, 20, 0.65, True, "Dinner/social"),
            # Evening study or procrastination
            TimeBlock(20, 3, 0.75, True, "Study/gaming/Discord"),
        ],
        response_delay_minutes=(1, 240),  # Highly variable
        see_but_ignore_prob=0.30  # Often distracted
    )


def create_shift_worker_rotating() -> UserArchetype:
    """Shift worker with rotating schedule (simplified to night shift)"""
    return UserArchetype(
        name="Night Shift Worker",
        device=DeviceAccess.MIXED,
        blocks=[
            # Sleep (day sleeper)
            TimeBlock(9, 17, 0.0, False, "Day sleep"),
            # Wake up routine
            TimeBlock(17, 19, 0.60, True, "Waking up"),
            # Commute
            TimeBlock(19, 20, 0.15, True, "Commute to work"),
            # Work
            TimeBlock(20, 4, 0.20, True, "At work (night shift)"),
            # Commute home
            TimeBlock(4, 5, 0.10, True, "Commute home"),
            # Decompression before bed
            TimeBlock(5, 9, 0.50, True, "Unwinding"),
        ],
        response_delay_minutes=(10, 180),
        see_but_ignore_prob=0.35
    )


def create_parent_fragmented() -> UserArchetype:
    """Parent with fragmented availability around childcare"""
    return UserArchetype(
        name="Parent (Fragmented Schedule)",
        device=DeviceAccess.MOBILE_ALWAYS,
        blocks=[
            # Sleep
            TimeBlock(23, 6, 0.0, False, "Sleeping"),
            # Morning chaos
            TimeBlock(6, 9, 0.10, True, "Morning routine/school drop-off"),
            # Mid-morning work
            TimeBlock(9, 12, 0.55, True, "Work/chores"),
            # Lunch/errands
            TimeBlock(12, 15, 0.30, True, "Errands/pickup"),
            # After-school chaos
            TimeBlock(15, 19, 0.15, True, "Kids home/dinner"),
            # Kids bedtime
            TimeBlock(19, 21, 0.40, True, "Bedtime routine"),
            # Finally free
            TimeBlock(21, 23, 0.80, True, "Personal time"),
        ],
        response_delay_minutes=(5, 300),  # Gets to it when kids allow
        see_but_ignore_prob=0.40  # Often interrupted
    )


# ============================================================================
# STOCHASTIC BEHAVIOR SIMULATOR
# ============================================================================

class StochasticUser:
    """Simulates realistic user with time-based availability"""

    def __init__(self, archetype: UserArchetype, seed: Optional[int] = None):
        self.archetype = archetype
        self.rng = random.Random(seed)

    def get_block_for_hour(self, hour: int) -> TimeBlock:
        """Find which time block this hour falls into"""
        for block in self.archetype.blocks:
            if block.start_hour <= block.end_hour:
                # Normal range (e.g., 9-17)
                if block.start_hour <= hour < block.end_hour:
                    return block
            else:
                # Wraps around midnight (e.g., 22-2)
                if hour >= block.start_hour or hour < block.end_hour:
                    return block
        # Shouldn't happen if blocks cover all 24 hours
        raise ValueError(f"No block found for hour {hour}")

    def can_see_notification(self, hour: int) -> bool:
        """Can user see a notification at this hour?"""
        block = self.get_block_for_hour(hour)
        return block.can_see

    def will_respond_if_seen(self, hour: int) -> bool:
        """If user sees notification, will they respond?"""
        block = self.get_block_for_hour(hour)

        if not block.can_see:
            return False

        # Check if they ignore despite seeing
        if self.rng.random() < self.archetype.see_but_ignore_prob:
            return False

        # Check base probability for this time block
        return self.rng.random() < block.base_prob

    def get_response_delay_minutes(self) -> int:
        """Get realistic response delay in minutes"""
        min_delay, max_delay = self.archetype.response_delay_minutes
        return self.rng.randint(min_delay, max_delay)

    def check_mantra_response(self, sent_hour: int, check_hour: int) -> Tuple[bool, Optional[int]]:
        """
        Check if user responds to mantra sent at sent_hour, checked at check_hour.

        Returns:
            (responded, delay_minutes) where delay_minutes is None if no response
        """
        # Did they see it when it was sent?
        if not self.can_see_notification(sent_hour):
            # They were asleep/unavailable, will check later
            # Walk forward from when they wake up
            for hour in range(sent_hour + 1, check_hour + 1):
                hour_mod = hour % 24
                if self.can_see_notification(hour_mod):
                    # First chance to see it
                    if self.will_respond_if_seen(hour_mod):
                        # Calculate delay
                        delay_hours = hour - sent_hour
                        delay_minutes = delay_hours * 60 + self.get_response_delay_minutes()
                        return (True, delay_minutes)
                    else:
                        # Saw it but ignored
                        return (False, None)
            # Never saw it before deadline
            return (False, None)
        else:
            # They saw it immediately
            if self.will_respond_if_seen(sent_hour):
                delay_minutes = self.get_response_delay_minutes()
                return (True, delay_minutes)
            else:
                return (False, None)

    def simulate_real_encounter(self, sent_time: datetime, deadline: datetime) -> Dict:
        """
        Simulate a real mantra encounter with realistic timing.

        Returns dict with:
            - responded: bool
            - response_time: datetime (if responded)
            - response_delay_minutes: int (if responded)
            - hours_checked: List[int] - all hours between sent and response/deadline
        """
        current = sent_time
        hours_checked = []

        while current < deadline:
            hour = current.hour
            hours_checked.append(hour)

            # Check if user would respond during this hour
            if self.can_see_notification(hour) and self.will_respond_if_seen(hour):
                # They respond!
                delay = self.get_response_delay_minutes()
                response_time = current + timedelta(minutes=delay)

                if response_time > deadline:
                    # Would respond but deadline passed
                    return {
                        "responded": False,
                        "response_time": None,
                        "response_delay_minutes": None,
                        "hours_checked": hours_checked,
                        "reason": "deadline_before_response"
                    }

                return {
                    "responded": True,
                    "response_time": response_time,
                    "response_delay_minutes": int((response_time - sent_time).total_seconds() / 60),
                    "hours_checked": hours_checked,
                    "reason": "success"
                }

            # Move to next hour
            current += timedelta(hours=1)

        # Deadline reached without response
        return {
            "responded": False,
            "response_time": None,
            "response_delay_minutes": None,
            "hours_checked": hours_checked,
            "reason": "timeout"
        }


# ============================================================================
# LEARNING ALGORITHMS
# ============================================================================

class CurrentAlgorithm:
    """Current V2 algorithm - only learns from response time"""

    def __init__(self, learning_rate: float = 0.20, floor: float = 0.1, ceil: float = 1.0):
        self.learning_rate = learning_rate
        self.floor = floor
        self.ceil = ceil
        self.distribution = [0.5 for _ in range(24)]

    def update(self, encounter: Dict) -> None:
        """Update based on encounter outcome"""
        if encounter["responded"]:
            # Learn from response time only
            response_hour = encounter["response_time"].hour
            actual = 1.0
            expected = self.distribution[response_hour]
            error = actual - expected
            delta = self.learning_rate * error
            new_value = self.distribution[response_hour] + delta
            self.distribution[response_hour] = max(self.floor, min(self.ceil, new_value))
        else:
            # Learn from sent time (which is wrong - they might not have been awake)
            sent_hour = encounter["sent_time"].hour
            actual = 0.0
            expected = self.distribution[sent_hour]
            error = actual - expected
            delta = self.learning_rate * error
            new_value = self.distribution[sent_hour] + delta
            self.distribution[sent_hour] = max(self.floor, min(self.ceil, new_value))

    def get_distribution(self) -> List[float]:
        return self.distribution.copy()


class MissedHourPenaltyAlgorithm:
    """Proposed improvement - penalize all missed hours"""

    def __init__(
        self,
        learning_rate: float = 0.20,
        missed_penalty_rate: float = 0.10,
        floor: float = 0.1,
        ceil: float = 1.0
    ):
        self.learning_rate = learning_rate
        self.missed_penalty_rate = missed_penalty_rate
        self.floor = floor
        self.ceil = ceil
        self.distribution = [0.5 for _ in range(24)]

    def update(self, encounter: Dict) -> None:
        """Update based on encounter outcome, penalizing missed hours"""
        hours_checked = encounter["hours_checked"]

        if encounter["responded"]:
            # Positive update for response hour
            response_hour = encounter["response_time"].hour
            actual = 1.0
            expected = self.distribution[response_hour]
            error = actual - expected
            delta = self.learning_rate * error
            new_value = self.distribution[response_hour] + delta
            self.distribution[response_hour] = max(self.floor, min(self.ceil, new_value))

            # Penalize all hours before response
            for hour in hours_checked:
                if hour != response_hour:
                    # They didn't respond during this hour (missed)
                    actual = 0.0
                    expected = self.distribution[hour]
                    error = actual - expected
                    delta = self.missed_penalty_rate * error
                    new_value = self.distribution[hour] + delta
                    self.distribution[hour] = max(self.floor, min(self.ceil, new_value))
        else:
            # Penalize all checked hours
            for hour in hours_checked:
                actual = 0.0
                expected = self.distribution[hour]
                error = actual - expected
                delta = self.learning_rate * error
                new_value = self.distribution[hour] + delta
                self.distribution[hour] = max(self.floor, min(self.ceil, new_value))

    def get_distribution(self) -> List[float]:
        return self.distribution.copy()


class WeightedMissedHourAlgorithm:
    """Variant - penalize missed hours proportional to their current probability"""

    def __init__(
        self,
        learning_rate: float = 0.20,
        missed_penalty_rate: float = 0.10,
        floor: float = 0.1,
        ceil: float = 1.0
    ):
        self.learning_rate = learning_rate
        self.missed_penalty_rate = missed_penalty_rate
        self.floor = floor
        self.ceil = ceil
        self.distribution = [0.5 for _ in range(24)]

    def update(self, encounter: Dict) -> None:
        """Update with probability-weighted penalties for missed hours"""
        hours_checked = encounter["hours_checked"]

        if encounter["responded"]:
            # Positive update for response hour
            response_hour = encounter["response_time"].hour
            actual = 1.0
            expected = self.distribution[response_hour]
            error = actual - expected
            delta = self.learning_rate * error
            new_value = self.distribution[response_hour] + delta
            self.distribution[response_hour] = max(self.floor, min(self.ceil, new_value))

            # Weighted penalize missed hours
            for hour in hours_checked:
                if hour != response_hour:
                    # Penalty proportional to current probability
                    weight = self.distribution[hour]
                    actual = 0.0
                    expected = self.distribution[hour]
                    error = actual - expected
                    delta = self.missed_penalty_rate * error * weight
                    new_value = self.distribution[hour] + delta
                    self.distribution[hour] = max(self.floor, min(self.ceil, new_value))
        else:
            # Full penalize all checked hours
            for hour in hours_checked:
                actual = 0.0
                expected = self.distribution[hour]
                error = actual - expected
                delta = self.learning_rate * error
                new_value = self.distribution[hour] + delta
                self.distribution[hour] = max(self.floor, min(self.ceil, new_value))

    def get_distribution(self) -> List[float]:
        return self.distribution.copy()


# ============================================================================
# SIMULATION ENGINE
# ============================================================================

def generate_true_distribution(archetype: UserArchetype) -> List[float]:
    """Generate ground truth availability distribution from archetype"""
    distribution = [0.0] * 24

    for hour in range(24):
        block = None
        for b in archetype.blocks:
            if b.start_hour <= b.end_hour:
                if b.start_hour <= hour < b.end_hour:
                    block = b
                    break
            else:
                if hour >= b.start_hour or hour < b.end_hour:
                    block = b
                    break

        if block:
            if block.can_see:
                # Actual availability = base_prob * (1 - ignore_prob)
                distribution[hour] = block.base_prob * (1 - archetype.see_but_ignore_prob)
            else:
                distribution[hour] = 0.0

    return distribution


def calculate_mae(true_dist: List[float], learned_dist: List[float]) -> float:
    """Calculate mean absolute error"""
    return sum(abs(t - l) for t, l in zip(true_dist, learned_dist)) / 24


def simulate_encounters(
    user: StochasticUser,
    algorithm,
    num_encounters: int,
    interval_hours: int = 6
) -> Dict:
    """
    Simulate encounters with realistic timing.

    Args:
        user: StochasticUser instance
        algorithm: Learning algorithm instance
        num_encounters: Number of encounters to simulate
        interval_hours: Hours between mantra deliveries

    Returns:
        Dict with simulation results
    """
    true_dist = generate_true_distribution(user.archetype)

    current_time = datetime(2025, 1, 1, 12, 0)  # Start at noon

    mae_timeline = {}
    checkpoints = [10, 20, 50, 100, 200, 300]

    encounters = []

    for i in range(num_encounters):
        # Send mantra
        sent_time = current_time
        deadline = sent_time + timedelta(hours=interval_hours)

        # Simulate encounter
        encounter = user.simulate_real_encounter(sent_time, deadline)
        encounter["sent_time"] = sent_time
        encounter["encounter_num"] = i + 1
        encounters.append(encounter)

        # Update algorithm
        algorithm.update(encounter)

        # Record MAE at checkpoints
        if (i + 1) in checkpoints:
            learned_dist = algorithm.get_distribution()
            mae = calculate_mae(true_dist, learned_dist)
            mae_timeline[i + 1] = mae

        # Move to next encounter time
        current_time = deadline

    # Final MAE
    final_learned = algorithm.get_distribution()
    final_mae = calculate_mae(true_dist, final_learned)

    # Calculate success rate
    success_rate = sum(1 for e in encounters if e["responded"]) / len(encounters)

    return {
        "mae_timeline": mae_timeline,
        "final_mae": final_mae,
        "final_distribution": final_learned,
        "true_distribution": true_dist,
        "success_rate": success_rate,
        "encounters": encounters
    }


# ============================================================================
# MAIN TEST SUITE
# ============================================================================

def main():
    print("=" * 80)
    print("STOCHASTIC REALISTIC USER BEHAVIOR SIMULATION")
    print("=" * 80)

    # Create archetypes
    archetypes = [
        create_morning_person_mobile(),
        create_night_owl_desktop(),
        create_nine_to_five_strict(),
        create_student_chaotic(),
        create_shift_worker_rotating(),
        create_parent_fragmented(),
    ]

    # Test configurations
    configs = [
        {
            "name": "Current Algorithm (response-time only)",
            "algorithm": CurrentAlgorithm,
            "params": {"learning_rate": 0.20}
        },
        {
            "name": "Missed Hour Penalty (lr=0.20, penalty=0.10)",
            "algorithm": MissedHourPenaltyAlgorithm,
            "params": {"learning_rate": 0.20, "missed_penalty_rate": 0.10}
        },
        {
            "name": "Missed Hour Penalty (lr=0.20, penalty=0.05)",
            "algorithm": MissedHourPenaltyAlgorithm,
            "params": {"learning_rate": 0.20, "missed_penalty_rate": 0.05}
        },
        {
            "name": "Weighted Missed Hour (lr=0.20, penalty=0.10)",
            "algorithm": WeightedMissedHourAlgorithm,
            "params": {"learning_rate": 0.20, "missed_penalty_rate": 0.10}
        },
    ]

    print(f"\nTesting {len(configs)} algorithms × {len(archetypes)} user types")
    print("Each test: 300 encounters with 6-hour intervals\n")

    all_results = []

    for archetype in archetypes:
        print(f"\n{'='*80}")
        print(f"USER: {archetype.name}")
        print(f"Device: {archetype.device.value}")
        print(f"{'='*80}\n")

        archetype_results = []

        for config in configs:
            # Create fresh user and algorithm
            user = StochasticUser(archetype, seed=42)
            algo = config["algorithm"](**config["params"])

            # Run simulation
            result = simulate_encounters(user, algo, 300, interval_hours=6)
            result["config_name"] = config["name"]
            result["archetype_name"] = archetype.name
            archetype_results.append(result)
            all_results.append(result)

        # Show results for this archetype
        print(f"{'Algorithm':<50} {'Final MAE':<12} {'Success Rate':<12}")
        print("-" * 80)

        archetype_results.sort(key=lambda x: x["final_mae"])

        for r in archetype_results:
            marker = " ← BEST" if r == archetype_results[0] else ""
            print(f"{r['config_name']:<50} {r['final_mae']:<12.4f} {r['success_rate']:<12.1%}{marker}")

    # Overall summary
    print(f"\n{'='*80}")
    print("OVERALL SUMMARY (Average across all user types)")
    print(f"{'='*80}\n")

    # Aggregate by config
    config_aggregates = {}
    for config in configs:
        config_name = config["name"]
        config_results = [r for r in all_results if r["config_name"] == config_name]

        avg_mae = sum(r["final_mae"] for r in config_results) / len(config_results)
        avg_success = sum(r["success_rate"] for r in config_results) / len(config_results)

        config_aggregates[config_name] = {
            "avg_mae": avg_mae,
            "avg_success": avg_success
        }

    # Sort by MAE
    sorted_configs = sorted(config_aggregates.items(), key=lambda x: x[1]["avg_mae"])

    print(f"{'Algorithm':<50} {'Avg MAE':<12} {'Avg Success':<12}")
    print("-" * 80)

    for i, (name, stats) in enumerate(sorted_configs):
        marker = " ← WINNER" if i == 0 else ""
        print(f"{name:<50} {stats['avg_mae']:<12.4f} {stats['avg_success']:<12.1%}{marker}")

    # Improvement analysis
    print(f"\n{'='*80}")
    print("IMPROVEMENT ANALYSIS")
    print(f"{'='*80}\n")

    current = config_aggregates["Current Algorithm (response-time only)"]
    best = sorted_configs[0]

    if best[0] != "Current Algorithm (response-time only)":
        improvement = (current["avg_mae"] - best[1]["avg_mae"]) / current["avg_mae"] * 100
        print(f"Best algorithm: {best[0]}")
        print(f"Improvement over current: {improvement:.1f}% reduction in MAE")
        print(f"\nCurrent MAE: {current['avg_mae']:.4f}")
        print(f"Best MAE: {best[1]['avg_mae']:.4f}")
    else:
        print("Current algorithm is already optimal for these scenarios.")

    print(f"\n{'='*80}")
    print("DEPLOYMENT RECOMMENDATION")
    print(f"{'='*80}\n")

    if improvement > 10:
        print("RECOMMENDATION: Implement missed-hour penalty algorithm")
        print(f"Expected improvement: {improvement:.1f}% better learning accuracy")
    elif improvement > 5:
        print("RECOMMENDATION: Consider implementing missed-hour penalty")
        print(f"Moderate improvement: {improvement:.1f}%")
        print("May be worth it for better user experience")
    else:
        print("RECOMMENDATION: Current algorithm is acceptable")
        print(f"Improvement: {improvement:.1f}% (marginal)")
        print("Deploy V2 as-is, iterate later if needed")

    print(f"\n{'='*80}")


if __name__ == "__main__":
    random.seed(42)
    main()

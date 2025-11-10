#!/usr/bin/env python3
"""
Simulate Mantra V2 scheduling algorithm to test convergence and accuracy.

Tests how well we can learn a user's "true" availability from encounter history.
"""

import random
import math
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple
import json


# ============================================================================
# GROUND TRUTH: Generate "True" User Availability
# ============================================================================

def generate_true_availability(archetype: str) -> Dict[str, Dict[int, float]]:
    """
    Generate a user's true availability distribution.

    Returns probability (0-1) for each hour, split by weekday/weekend.
    """
    weekday = {h: 0.1 for h in range(24)}  # Low baseline
    weekend = {h: 0.1 for h in range(24)}

    if archetype == "morning_person":
        # High availability 7-11am
        for h in range(7, 12):
            weekday[h] = 0.9
            weekend[h] = 0.85
        # Medium 1-5pm
        for h in range(13, 18):
            weekday[h] = 0.6
            weekend[h] = 0.7

    elif archetype == "night_owl":
        # High availability 8pm-2am
        for h in list(range(20, 24)) + list(range(0, 3)):
            weekday[h] = 0.85
            weekend[h] = 0.9
        # Medium afternoon
        for h in range(14, 18):
            weekday[h] = 0.5

    elif archetype == "nine_to_five":
        # Low during work hours
        for h in range(9, 18):
            weekday[h] = 0.2
        # High evenings
        for h in range(18, 23):
            weekday[h] = 0.85
        # Weekend more flexible
        for h in range(10, 22):
            weekend[h] = 0.7

    elif archetype == "weekend_warrior":
        # Low weekdays
        weekday = {h: 0.3 if 10 <= h <= 22 else 0.1 for h in range(24)}
        # High weekends
        for h in range(10, 23):
            weekend[h] = 0.9

    return {"weekday": weekday, "weekend": weekend}


def is_user_available(hour: int, is_weekend: bool, true_availability: Dict, noise: float = 0.1) -> bool:
    """
    Check if user would respond at this hour.

    Args:
        hour: Hour of day (0-23)
        is_weekend: Is it weekend?
        true_availability: Ground truth distribution
        noise: Random failure rate (0.1 = 10% chance they miss even when available)

    Returns:
        True if user responds, False otherwise
    """
    dist = true_availability["weekend" if is_weekend else "weekday"]
    base_prob = dist[hour]

    # Apply noise (random failures)
    actual_prob = base_prob * (1 - noise)

    return random.random() < actual_prob


# ============================================================================
# LEARNING: Build Distribution from History
# ============================================================================

def update_availability(encounter_history: List[Dict]) -> Dict[str, Dict[int, float]]:
    """
    Learn availability distribution from encounter history.

    Returns learned probability distribution.
    """
    if len(encounter_history) < 5:
        # Not enough data - return uniform
        return {
            "weekday": {h: 0.5 for h in range(24)},
            "weekend": {h: 0.5 for h in range(24)}
        }

    # Separate weekday/weekend
    weekday_stats = defaultdict(lambda: {'completed': 0, 'total': 0})
    weekend_stats = defaultdict(lambda: {'completed': 0, 'total': 0})

    for enc in encounter_history:
        dt = enc['timestamp']
        hour = dt.hour
        is_weekend = dt.weekday() >= 5

        stats = weekend_stats if is_weekend else weekday_stats
        stats[hour]['total'] += 1
        if enc['completed']:
            stats[hour]['completed'] += 1

    # Calculate probabilities with smoothing
    def calculate_probs(stats):
        probs = {}
        for hour in range(24):
            if stats[hour]['total'] >= 2:
                # Have data - use it
                probs[hour] = stats[hour]['completed'] / stats[hour]['total']
            else:
                # No data - use neighbor average or global default
                neighbors = []
                for offset in [-1, 1]:
                    neighbor_hour = (hour + offset) % 24
                    if stats[neighbor_hour]['total'] >= 2:
                        neighbors.append(stats[neighbor_hour]['completed'] / stats[neighbor_hour]['total'])

                if neighbors:
                    probs[hour] = sum(neighbors) / len(neighbors)
                else:
                    probs[hour] = 0.5  # Neutral default

        return probs

    return {
        "weekday": calculate_probs(weekday_stats),
        "weekend": calculate_probs(weekend_stats)
    }


# ============================================================================
# SCHEDULING: Use Learned Distribution
# ============================================================================

def schedule_next(current_time: datetime, learned_availability: Dict, frequency: float) -> datetime:
    """
    Schedule next encounter using probability integration.

    Args:
        current_time: Current datetime
        learned_availability: Learned distribution
        frequency: Encounters per day (e.g., 2.0)

    Returns:
        Scheduled datetime for next encounter
    """
    # Calculate target probability mass
    # Higher frequency = less mass needed = schedules sooner
    target_mass = 1.0 / frequency

    # Walk forward in time, accumulating probability
    accumulated_mass = 0.0

    for hours_ahead in range(1, 168):  # Check up to 7 days
        check_time = current_time + timedelta(hours=hours_ahead)
        hour = check_time.hour
        is_weekend = check_time.weekday() >= 5

        # Get probability for this hour
        dist = learned_availability["weekend" if is_weekend else "weekday"]
        prob = dist[hour]

        # Accumulate mass (1 hour * probability)
        accumulated_mass += prob

        # Reached target?
        if accumulated_mass >= target_mass:
            return check_time.replace(minute=0, second=0, microsecond=0)

    # Fallback: 24 hours from now
    return current_time + timedelta(hours=24)


# ============================================================================
# SIMULATION
# ============================================================================

def simulate_user(archetype: str, days: int, initial_frequency: float = 1.0, noise: float = 0.1) -> Dict:
    """
    Simulate a user over N days.

    Returns:
        - encounter_history: List of all encounters
        - learned_distributions: Snapshots of learned dist over time
        - metrics: Convergence metrics
    """
    true_availability = generate_true_availability(archetype)
    encounter_history = []
    learned_distributions = []  # Snapshots at intervals

    current_time = datetime(2025, 1, 1, 12, 0, 0)  # Start Jan 1, noon
    end_time = current_time + timedelta(days=days)

    frequency = initial_frequency

    # Start with default distribution
    learned_availability = {
        "weekday": {h: 0.5 for h in range(24)},
        "weekend": {h: 0.5 for h in range(24)}
    }

    next_delivery = current_time + timedelta(hours=24)  # First encounter tomorrow

    encounter_count = 0

    while current_time < end_time:
        # Check if it's time to deliver
        if current_time >= next_delivery:
            # Attempt delivery
            hour = current_time.hour
            is_weekend = current_time.weekday() >= 5

            # Would user respond?
            responded = is_user_available(hour, is_weekend, true_availability, noise)

            encounter = {
                'timestamp': current_time,
                'hour': hour,
                'is_weekend': is_weekend,
                'completed': responded,
                'frequency_at_delivery': frequency
            }
            encounter_history.append(encounter)
            encounter_count += 1

            # Update frequency (TCP-style)
            if responded:
                frequency = min(6.0, frequency * 1.05)
            else:
                frequency = max(0.33, frequency * 0.95)

            # Learn from history (every 5 encounters)
            if encounter_count % 5 == 0:
                learned_availability = update_availability(encounter_history)
                learned_distributions.append({
                    'encounter_count': encounter_count,
                    'distribution': learned_availability
                })

            # Schedule next
            next_delivery = schedule_next(current_time, learned_availability, frequency)

        # Advance time by 1 hour
        current_time += timedelta(hours=1)

    # Final learned distribution
    final_learned = update_availability(encounter_history)

    # Calculate metrics
    metrics = calculate_metrics(true_availability, final_learned, encounter_history)

    return {
        'archetype': archetype,
        'true_availability': true_availability,
        'encounter_history': encounter_history,
        'learned_distributions': learned_distributions,
        'final_learned': final_learned,
        'metrics': metrics
    }


def calculate_metrics(true_dist: Dict, learned_dist: Dict, history: List[Dict]) -> Dict:
    """Calculate how well we learned the true distribution."""

    # KL divergence (how different are the distributions?)
    def kl_divergence(p, q):
        """Calculate KL divergence between two distributions."""
        kl = 0.0
        for hour in range(24):
            p_prob = p[hour]
            q_prob = max(q[hour], 0.01)  # Avoid log(0)
            kl += p_prob * math.log(p_prob / q_prob)
        return kl

    # Calculate for weekday and weekend
    weekday_kl = kl_divergence(true_dist['weekday'], learned_dist['weekday'])
    weekend_kl = kl_divergence(true_dist['weekend'], learned_dist['weekend'])

    # Mean absolute error
    def mae(p, q):
        return sum(abs(p[h] - q[h]) for h in range(24)) / 24

    weekday_mae = mae(true_dist['weekday'], learned_dist['weekday'])
    weekend_mae = mae(true_dist['weekend'], learned_dist['weekend'])

    # Overall completion rate
    completed = len([e for e in history if e['completed']])
    completion_rate = completed / len(history) if history else 0

    return {
        'total_encounters': len(history),
        'completion_rate': completion_rate,
        'weekday_kl_divergence': weekday_kl,
        'weekend_kl_divergence': weekend_kl,
        'weekday_mae': weekday_mae,
        'weekend_mae': weekend_mae,
        'avg_kl': (weekday_kl + weekend_kl) / 2,
        'avg_mae': (weekday_mae + weekend_mae) / 2
    }


def print_comparison(true_dist: Dict, learned_dist: Dict, day_type: str):
    """Print side-by-side comparison of true vs learned."""
    print(f"\n{day_type.upper()} DISTRIBUTION")
    print("Hour | True | Learned | Error")
    print("-" * 35)

    true = true_dist[day_type]
    learned = learned_dist[day_type]

    for hour in range(24):
        error = abs(true[hour] - learned[hour])
        print(f"{hour:02d}:00 | {true[hour]:.2f} | {learned[hour]:.2f}  | {error:+.2f}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run simulations for different user archetypes."""

    print("=" * 70)
    print("MANTRA V2 SCHEDULING SIMULATION")
    print("=" * 70)

    archetypes = ["morning_person", "night_owl", "nine_to_five", "weekend_warrior"]

    for archetype in archetypes:
        print(f"\n{'='*70}")
        print(f"SIMULATING: {archetype.replace('_', ' ').title()}")
        print(f"{'='*70}")

        result = simulate_user(archetype, days=60, initial_frequency=1.0, noise=0.1)

        print(f"\nTotal encounters: {result['metrics']['total_encounters']}")
        print(f"Completion rate: {result['metrics']['completion_rate']*100:.1f}%")
        print(f"\nConvergence Metrics:")
        print(f"  Average MAE: {result['metrics']['avg_mae']:.3f}")
        print(f"  Average KL Divergence: {result['metrics']['avg_kl']:.3f}")

        # Show comparison
        print_comparison(result['true_availability'], result['final_learned'], "weekday")
        print_comparison(result['true_availability'], result['final_learned'], "weekend")

        # Show learning progression
        if result['learned_distributions']:
            print(f"\nLearning Progression (MAE over time):")
            for snapshot in result['learned_distributions'][::2]:  # Every other snapshot
                enc_count = snapshot['encounter_count']
                dist = snapshot['distribution']
                mae = calculate_metrics(result['true_availability'], dist, [])['avg_mae']
                print(f"  After {enc_count:3d} encounters: MAE = {mae:.3f}")

    print(f"\n{'='*70}")
    print("SIMULATION COMPLETE")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()

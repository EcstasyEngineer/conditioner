#!/usr/bin/env python3
"""
Show AvailabilityLearner with automatic rounding and what the config output looks like.
"""

import json
from datetime import datetime

class AvailabilityLearner:
    """Prediction error learning for user availability."""

    def __init__(self):
        # Hour buckets (24 per day)
        self.distribution = [0.5 for _ in range(24)]
        self.learning_rate = 0.20
        self.floor = 0.1
        self.ceil = 1.0

    def update(self, dt: datetime, success: bool):
        """Update based on prediction error (Elo-style)."""
        hour = dt.hour
        actual = 1.0 if success else 0.0
        expected = self.distribution[hour]

        # Prediction error
        error = actual - expected
        delta = self.learning_rate * error

        new_value = expected + delta
        clamped_value = max(self.floor, min(self.ceil, new_value))

        # Round to 3 decimals to keep config clean
        self.distribution[hour] = round(clamped_value, 3)

    def get_prob(self, dt: datetime) -> float:
        """Get probability for a given datetime."""
        return self.distribution[dt.hour]

    def get_distribution(self) -> list:
        """Get distribution as list."""
        return self.distribution.copy()


# Simulate some learning
learner = AvailabilityLearner()

# Morning person pattern
print("Simulating morning person pattern...")
print(f"Initial distribution (all 0.5): {learner.distribution[:6]}...\n")

# Simulate 50 encounters
import random
from datetime import timedelta

morning_hours = [7, 8, 9, 10, 11]
afternoon_hours = [14, 15, 16, 17]
night_hours = [0, 1, 2, 3, 4, 5, 22, 23]

base_time = datetime(2025, 11, 10, 0, 0, 0)

for i in range(50):
    # Random hour
    hour = random.randint(0, 23)
    test_time = base_time.replace(hour=hour)

    # Simulate availability (90% morning, 60% afternoon, 10% night)
    if hour in morning_hours:
        success = random.random() < 0.9
    elif hour in afternoon_hours:
        success = random.random() < 0.6
    else:
        success = random.random() < 0.1

    learner.update(test_time, success)

print(f"After 50 encounters:")
print(f"  Morning hours (7-11): {[learner.distribution[h] for h in morning_hours]}")
print(f"  Afternoon hours (14-17): {[learner.distribution[h] for h in afternoon_hours]}")
print(f"  Night hours (0-5,22-23): {[learner.distribution[h] for h in [0,1,2,3,4,5]]}\n")

# Show what config would look like
mock_config = {
    "mantra_system": {
        "enrolled": True,
        "themes": ["acceptance", "suggestibility"],
        "subject": "puppet",
        "controller": "Master",
        "frequency": 2.0,
        "next_delivery": "2025-11-11T14:00:00",
        "sent": None,
        "consecutive_failures": 0,
        "current_mantra": {
            "text": "I accept complete reprogramming",
            "theme": "acceptance",
            "difficulty": "extreme",
            "base_points": 90
        },
        "availability_distribution": learner.get_distribution()
    }
}

print("=" * 80)
print("MOCK CONFIG OUTPUT (standard json.dump with indent=4)")
print("=" * 80)
print(json.dumps(mock_config, indent=4))

print("\n" + "=" * 80)
print("KEY BENEFITS:")
print("=" * 80)
print("1. Values are 3 decimals max (0.5, 0.68, 0.732)")
print("2. No modification to config.py needed")
print("3. Rounding happens once during learning (not on every save)")
print("4. Array format is clean and index-based")
print("5. 24 lines of array is manageable")
print("6. Loss of precision is negligible (0.001 vs MAE of 0.088)")

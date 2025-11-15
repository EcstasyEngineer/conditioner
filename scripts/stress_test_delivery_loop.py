#!/usr/bin/env python3
"""
Stress test the mantra delivery loop to measure performance.

Simulates N users and measures how long the loop takes to process them all.
"""

import sys
sys.path.insert(0, '/home/dudebot/preconditioner')

import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from utils.mantra_service import (
    get_default_config,
    should_deliver_mantra,
    check_for_timeout,
    deliver_mantra,
)

# Mock themes data
MOCK_THEMES = {
    "acceptance": {
        "theme": "acceptance",
        "description": "Test theme",
        "mantras": [
            {
                "text": "I am a test mantra",
                "difficulty": "basic",
                "base_points": 50
            }
        ]
    }
}

def simulate_delivery_loop(num_users):
    """
    Simulate the delivery loop for N users.

    Returns:
        float: Time taken in seconds
    """
    # Create mock configs for N users
    configs = []
    for i in range(num_users):
        config = get_default_config()
        config["enrolled"] = True
        config["themes"] = ["acceptance"]

        # Half are waiting for delivery, half are awaiting response
        if i % 2 == 0:
            # Waiting for delivery (past time)
            config["next_delivery"] = (datetime.now() - timedelta(hours=1)).isoformat()
            config["sent"] = None
        else:
            # Awaiting response (sent but not timed out yet)
            config["next_delivery"] = (datetime.now() + timedelta(hours=1)).isoformat()
            config["sent"] = (datetime.now() - timedelta(minutes=30)).isoformat()

        configs.append(config)

    # Measure time to process all users
    start_time = time.time()

    deliveries = 0
    timeouts = 0

    for config in configs:
        # Check for timeout
        if check_for_timeout(config, MOCK_THEMES):
            timeouts += 1

        # Check for delivery
        elif should_deliver_mantra(config):
            deliver_mantra(config, MOCK_THEMES)
            deliveries += 1

    end_time = time.time()
    elapsed = end_time - start_time

    return elapsed, deliveries, timeouts


def main():
    """Run stress tests with increasing user counts."""
    print("=" * 70)
    print("MANTRA DELIVERY LOOP STRESS TEST")
    print("=" * 70)
    print()

    test_sizes = [10, 50, 100, 200, 300, 500, 1000]

    print(f"{'Users':<10} {'Time (ms)':<15} {'Per User (ms)':<15} {'Deliveries':<12} {'Timeouts':<10}")
    print("-" * 70)

    for num_users in test_sizes:
        # Run 3 times and average
        times = []
        for _ in range(3):
            elapsed, deliveries, timeouts = simulate_delivery_loop(num_users)
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        avg_time_ms = avg_time * 1000
        per_user_ms = avg_time_ms / num_users

        # Last run stats
        _, deliveries, timeouts = simulate_delivery_loop(num_users)

        print(f"{num_users:<10} {avg_time_ms:<15.2f} {per_user_ms:<15.3f} {deliveries:<12} {timeouts:<10}")

    print()
    print("=" * 70)
    print("ANALYSIS:")
    print("-" * 70)

    # Test with 300 users (your target)
    elapsed, deliveries, timeouts = simulate_delivery_loop(300)
    elapsed_ms = elapsed * 1000

    print(f"At 300 users:")
    print(f"  Total loop time: {elapsed_ms:.2f}ms")
    print(f"  Per-user processing: {elapsed_ms/300:.3f}ms")
    print()

    # Calculate safe interval
    safety_margin = 2.0  # 2x safety margin
    required_time_ms = elapsed_ms * safety_margin
    required_time_s = required_time_ms / 1000

    print(f"With 2x safety margin: {required_time_ms:.2f}ms ({required_time_s:.2f}s)")
    print()

    if required_time_s < 30:
        print(f"✅ SAFE for 30-second interval (uses {required_time_s/30*100:.1f}% of window)")
    else:
        print(f"❌ NOT SAFE for 30-second interval (needs {required_time_s:.1f}s)")

    if required_time_s < 60:
        print(f"✅ SAFE for 60-second interval (uses {required_time_s/60*100:.1f}% of window)")
    else:
        print(f"❌ NOT SAFE for 60-second interval (needs {required_time_s:.1f}s)")

    print()
    print("RECOMMENDATION:")
    print("-" * 70)
    if required_time_s < 10:
        print("✅ Can safely use 30-second interval")
        print("   Loop completes in <10s, leaving 20s buffer")
    elif required_time_s < 20:
        print("⚠️  30-second interval is cutting it close")
        print("   Consider 60-second interval for safety")
    else:
        print("❌ Must use 60-second or higher interval")
        print(f"   Loop takes {required_time_s:.1f}s with safety margin")

    print()

if __name__ == '__main__':
    main()

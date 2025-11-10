#!/usr/bin/env python3
"""
Test prediction error / Elo-style learning.

Core idea: Update based on surprise (how wrong we were).
- Success at 0.9: Small update (expected)
- Success at 0.1: Large update (surprising!)
- Failure at 0.9: Large penalty (surprising!)
- Failure at 0.2: Small penalty (expected)

Variants:
1. Start at 0.5 vs user baseline
2. With/without gaussian neighbors
3. With/without decay toward baseline
4. Different learning rates
"""

import random
import math
from typing import Dict, List, Tuple


# ============================================================================
# GROUND TRUTH
# ============================================================================

def generate_archetype(archetype: str) -> Dict[int, float]:
    """Generate known true availability."""
    dist = {h: 0.1 for h in range(24)}

    if archetype == "morning_person":
        for h in range(7, 12):
            dist[h] = 0.9
        for h in range(13, 18):
            dist[h] = 0.6

    elif archetype == "night_owl":
        for h in list(range(20, 24)) + list(range(0, 3)):
            dist[h] = 0.85
        for h in range(14, 18):
            dist[h] = 0.5

    elif archetype == "nine_to_five":
        for h in range(9, 18):
            dist[h] = 0.2
        for h in range(18, 23):
            dist[h] = 0.85

    elif archetype == "sparse":
        # Only available a few hours
        for h in [9, 10, 14, 15, 20]:
            dist[h] = 0.9

    return dist


def is_available(hour: int, true_dist: Dict[int, float], noise: float = 0.1) -> bool:
    """Check if user responds."""
    base_prob = true_dist[hour]
    actual_prob = base_prob * (1 - noise)
    return random.random() < actual_prob


# ============================================================================
# LEARNERS
# ============================================================================

class PredictionErrorLearner:
    """Gradient descent on prediction error."""

    def __init__(self, learning_rate: float = 0.15, width: int = 1,
                 sigma_mult: float = 0.5, start_baseline: float = 0.5,
                 use_gaussian: bool = True, floor: float = 0.1, ceil: float = 1.0):
        self.learning_rate = learning_rate
        self.width = width
        self.sigma = (width / 2.0) * sigma_mult if use_gaussian else 0.0
        self.use_gaussian = use_gaussian
        self.floor = floor
        self.ceil = ceil
        self.distribution = {h: start_baseline for h in range(24)}

        if use_gaussian:
            self.weights = self._calculate_weights()
        else:
            self.weights = {0: 1.0}  # Only center

    def _calculate_weights(self) -> Dict[int, float]:
        weights = {}
        for offset in range(-self.width, self.width + 1):
            weights[offset] = math.exp(-(offset ** 2) / (2 * self.sigma ** 2))
        return weights

    def update(self, hour: int, success: bool):
        """Update based on prediction error."""
        actual = 1.0 if success else 0.0

        for offset, gaussian_weight in self.weights.items():
            target_hour = (hour + offset) % 24
            expected = self.distribution[target_hour]

            # Prediction error
            error = actual - expected

            # Weighted update
            delta = self.learning_rate * error * gaussian_weight

            new_value = self.distribution[target_hour] + delta
            self.distribution[target_hour] = max(self.floor, min(self.ceil, new_value))

    def get_distribution(self) -> Dict[int, float]:
        return self.distribution.copy()


class PredictionErrorWithDecayLearner:
    """Prediction error with decay toward user baseline."""

    def __init__(self, learning_rate: float = 0.15, width: int = 1,
                 sigma_mult: float = 0.5, start_baseline: float = 0.5,
                 decay_rate: float = 0.005, use_gaussian: bool = True,
                 floor: float = 0.1, ceil: float = 1.0):
        self.learning_rate = learning_rate
        self.width = width
        self.sigma = (width / 2.0) * sigma_mult if use_gaussian else 0.0
        self.use_gaussian = use_gaussian
        self.decay_rate = decay_rate
        self.baseline = start_baseline
        self.floor = floor
        self.ceil = ceil
        self.distribution = {h: start_baseline for h in range(24)}

        if use_gaussian:
            self.weights = self._calculate_weights()
        else:
            self.weights = {0: 1.0}

    def _calculate_weights(self) -> Dict[int, float]:
        weights = {}
        for offset in range(-self.width, self.width + 1):
            weights[offset] = math.exp(-(offset ** 2) / (2 * self.sigma ** 2))
        return weights

    def update(self, hour: int, success: bool):
        """Update with prediction error + decay toward baseline."""
        actual = 1.0 if success else 0.0

        # Prediction error update
        for offset, gaussian_weight in self.weights.items():
            target_hour = (hour + offset) % 24
            expected = self.distribution[target_hour]
            error = actual - expected
            delta = self.learning_rate * error * gaussian_weight
            new_value = self.distribution[target_hour] + delta
            self.distribution[target_hour] = max(self.floor, min(self.ceil, new_value))

        # Decay toward baseline
        for h in range(24):
            if self.distribution[h] > self.baseline:
                self.distribution[h] = max(self.baseline, self.distribution[h] - self.decay_rate)
            elif self.distribution[h] < self.baseline:
                self.distribution[h] = min(self.baseline, self.distribution[h] + self.decay_rate)

    def get_distribution(self) -> Dict[int, float]:
        return self.distribution.copy()


# For comparison
class ProportionalLearner:
    """Multiplicative learning (current best)."""

    def __init__(self, learning_rate: float = 0.15, width: int = 1,
                 sigma_mult: float = 0.5, floor: float = 0.01):
        self.learning_rate = learning_rate
        self.width = width
        self.sigma = (width / 2.0) * sigma_mult
        self.floor = floor
        self.weights = self._calculate_weights()
        self.distribution = {h: 0.5 for h in range(24)}

    def _calculate_weights(self) -> Dict[int, float]:
        weights = {}
        for offset in range(-self.width, self.width + 1):
            weights[offset] = math.exp(-(offset ** 2) / (2 * self.sigma ** 2))
        return weights

    def update(self, hour: int, success: bool):
        direction = 1.0 if success else -1.0
        for offset, gaussian_weight in self.weights.items():
            target_hour = (hour + offset) % 24
            multiplier = 1.0 + (direction * self.learning_rate * gaussian_weight)
            new_value = self.distribution[target_hour] * multiplier
            self.distribution[target_hour] = max(self.floor, min(1.0, new_value))

    def get_distribution(self) -> Dict[int, float]:
        return self.distribution.copy()


# ============================================================================
# SIMULATION
# ============================================================================

def calculate_mae(true_dist: Dict, learned_dist: Dict) -> float:
    """Calculate mean absolute error."""
    return sum(abs(true_dist[h] - learned_dist[h]) for h in range(24)) / 24


def simulate_convergence(learner, archetype: str, max_encounters: int) -> Dict:
    """Simulate learning."""
    true_dist = generate_archetype(archetype)

    # Calculate true user baseline
    true_baseline = sum(true_dist.values()) / 24

    mae_timeline = {}
    checkpoints = [10, 20, 30, 50, 100, 200, 300]

    for encounter_num in range(1, max_encounters + 1):
        hour = random.randint(0, 23)
        success = is_available(hour, true_dist, noise=0.1)
        learner.update(hour, success)

        if encounter_num in checkpoints:
            learned_dist = learner.get_distribution()
            mae = calculate_mae(true_dist, learned_dist)
            mae_timeline[encounter_num] = mae

    final_learned = learner.get_distribution()
    final_mae = calculate_mae(true_dist, final_learned)

    return {
        'mae_timeline': mae_timeline,
        'final_mae': final_mae,
        'true_baseline': true_baseline
    }


def simulate_pattern_change(learner, max_encounters: int = 200) -> Dict:
    """Test recovery when pattern changes."""
    true_dist_1 = generate_archetype("morning_person")

    for _ in range(100):
        hour = random.randint(0, 23)
        success = is_available(hour, true_dist_1, noise=0.1)
        learner.update(hour, success)

    mae_before = calculate_mae(true_dist_1, learner.get_distribution())

    true_dist_2 = generate_archetype("night_owl")
    recovery_timeline = {}

    for encounter_num in range(1, max_encounters + 1):
        hour = random.randint(0, 23)
        success = is_available(hour, true_dist_2, noise=0.1)
        learner.update(hour, success)

        if encounter_num in [10, 20, 30, 50, 100]:
            mae = calculate_mae(true_dist_2, learner.get_distribution())
            recovery_timeline[encounter_num] = mae

    return {
        'mae_before_change': mae_before,
        'recovery_timeline': recovery_timeline
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("PREDICTION ERROR LEARNING - THE CREME DE LA CREME TEST")
    print("=" * 70)

    archetypes = ["morning_person", "night_owl", "nine_to_five", "sparse"]

    configs = []

    # Prediction error variants
    for lr in [0.10, 0.15, 0.20, 0.25]:
        for start in [0.5]:  # Start neutral
            configs.append({
                'name': f"PredErr lr={lr:.2f} start=0.5",
                'learner': lambda lr=lr, start=start: PredictionErrorLearner(
                    learning_rate=lr, width=1, sigma_mult=0.5,
                    start_baseline=start, use_gaussian=True,
                    floor=0.1, ceil=1.0
                ),
                'method': 'pred_err'
            })

    # With adaptive baseline (calculate from encounters so far)
    # Note: For simplicity, we'll test starting at different fixed baselines
    for lr in [0.15, 0.20]:
        for start in [0.6, 0.7, 0.8]:
            configs.append({
                'name': f"PredErr lr={lr:.2f} start={start:.1f}",
                'learner': lambda lr=lr, start=start: PredictionErrorLearner(
                    learning_rate=lr, width=1, sigma_mult=0.5,
                    start_baseline=start, use_gaussian=True,
                    floor=0.1, ceil=1.0
                ),
                'method': 'pred_err_baseline'
            })

    # Without gaussian (center only)
    for lr in [0.15, 0.20]:
        configs.append({
            'name': f"PredErr lr={lr:.2f} no-gaussian",
            'learner': lambda lr=lr: PredictionErrorLearner(
                learning_rate=lr, width=1, sigma_mult=0.5,
                start_baseline=0.5, use_gaussian=False,
                floor=0.1, ceil=1.0
            ),
            'method': 'pred_err_nogauss'
        })

    # With decay toward baseline
    for lr in [0.15, 0.20]:
        for decay in [0.005, 0.01]:
            configs.append({
                'name': f"PredErr lr={lr:.2f} decay={decay:.3f}",
                'learner': lambda lr=lr, decay=decay: PredictionErrorWithDecayLearner(
                    learning_rate=lr, width=1, sigma_mult=0.5,
                    start_baseline=0.5, decay_rate=decay,
                    use_gaussian=True, floor=0.1, ceil=1.0
                ),
                'method': 'pred_err_decay'
            })

    # Baseline: Proportional (current champion)
    configs.append({
        'name': "Proportional lr=0.15 (baseline)",
        'learner': lambda: ProportionalLearner(learning_rate=0.15, width=1, sigma_mult=0.5, floor=0.01),
        'method': 'proportional'
    })

    print(f"\nTesting {len(configs)} configurations × {len(archetypes)} archetypes")
    print("Running convergence tests (300 encounters each)...\n")

    all_results = []

    for config in configs:
        config_results = []

        for archetype in archetypes:
            learner = config['learner']()
            result = simulate_convergence(learner, archetype, 300)
            result['name'] = config['name']
            result['method'] = config['method']
            result['archetype'] = archetype
            config_results.append(result)
            all_results.append(result)

        avg_mae = sum(r['final_mae'] for r in config_results) / len(config_results)
        config['avg_mae'] = avg_mae

    # Show results
    print("=" * 70)
    print("CONVERGENCE RESULTS (Final MAE after 300 encounters)")
    print("=" * 70)

    configs.sort(key=lambda x: x['avg_mae'])

    print(f"\n{'Rank':<6} {'Method':<45} {'Avg MAE':<10}")
    print("-" * 65)

    for i, cfg in enumerate(configs):
        marker = "← WINNER" if i == 0 else ("← BASELINE" if cfg['method'] == 'proportional' else "")
        print(f"{i+1:<6} {cfg['name']:<45} {cfg['avg_mae']:<10.3f} {marker}")

    # Pattern change test
    print(f"\n{'='*70}")
    print("PATTERN CHANGE RECOVERY TEST")
    print(f"{'='*70}\n")

    recovery_results = []

    for config in configs[:10]:
        learner = config['learner']()
        result = simulate_pattern_change(learner, 100)
        result['name'] = config['name']
        recovery_results.append(result)

    recovery_results.sort(key=lambda x: x['recovery_timeline'][30])

    print(f"{'Method':<45} {'@10':<10} {'@20':<10} {'@30':<10} {'@50':<10}")
    print("-" * 85)

    for r in recovery_results:
        print(f"{r['name']:<45} {r['recovery_timeline'][10]:<10.3f} "
              f"{r['recovery_timeline'][20]:<10.3f} {r['recovery_timeline'][30]:<10.3f} "
              f"{r['recovery_timeline'][50]:<10.3f}")

    # Summary
    winner = configs[0]
    baseline = next(c for c in configs if c['method'] == 'proportional')

    print(f"\n{'='*70}")
    print("FINAL VERDICT")
    print(f"{'='*70}\n")

    print(f"WINNER: {winner['name']}")
    print(f"  Average MAE: {winner['avg_mae']:.3f}")

    print(f"\nBASELINE: {baseline['name']}")
    print(f"  Average MAE: {baseline['avg_mae']:.3f}")

    if winner['avg_mae'] < baseline['avg_mae']:
        improvement = (baseline['avg_mae'] - winner['avg_mae']) / baseline['avg_mae'] * 100
        print(f"\n🎯 PREDICTION ERROR WINS!")
        print(f"   Improvement: {improvement:.1f}%")
    else:
        decline = (winner['avg_mae'] - baseline['avg_mae']) / baseline['avg_mae'] * 100
        print(f"\n   Proportional still better by {decline:.1f}%")

    print(f"\n{'='*70}")
    print("TESTING COMPLETE")
    print(f"{'='*70}")


if __name__ == '__main__':
    random.seed(42)
    main()

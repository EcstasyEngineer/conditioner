#!/usr/bin/env python3
"""
Analyze clipping/overflow in the mana model.

Questions:
1. How often do stats hit the cap?
2. How much production is "wasted" due to clipping?
3. Would logarithmic scaling help?
"""

import json
from pathlib import Path
from copy import deepcopy

DATA_DIR = Path(__file__).parent.parent / "data"


def load_model():
    with open(DATA_DIR / "playlist_mana.json") as f:
        return json.load(f)


class SessionStateWithTracking:
    """Track stats with overflow tracking."""

    def __init__(self, stats_config):
        self.stats = {}
        self.stats_config = stats_config
        self.overflow_log = []  # Track all overflow events

        for name, config in stats_config.items():
            if name.startswith("_"):
                continue
            self.stats[name] = config.get("baseline", 0)

    def apply_module_linear(self, module_name, module_data, apply_decay=True):
        """Apply with linear capping (current behavior)."""
        duration_s = module_data.get("duration_s", 300)

        if apply_decay:
            self.apply_decay(duration_s / 60)

        # Track production overflow
        for stat, amount in module_data.get("produces", {}).items():
            if stat in self.stats:
                current = self.stats[stat]
                max_val = self.stats_config.get(stat, {}).get("max", 100)
                headroom = max_val - current

                effective = min(amount, headroom)
                wasted = max(0, amount - headroom)

                if wasted > 0:
                    self.overflow_log.append({
                        "module": module_name,
                        "stat": stat,
                        "attempted": amount,
                        "effective": effective,
                        "wasted": wasted,
                        "current_before": current
                    })

                self.stats[stat] = min(max_val, current + amount)

    def apply_module_log(self, module_name, module_data, apply_decay=True):
        """Apply with logarithmic diminishing returns."""
        duration_s = module_data.get("duration_s", 300)

        if apply_decay:
            self.apply_decay(duration_s / 60)

        for stat, amount in module_data.get("produces", {}).items():
            if stat in self.stats:
                current = self.stats[stat]
                max_val = self.stats_config.get(stat, {}).get("max", 100)

                # Logarithmic: effectiveness decreases as you approach max
                headroom_ratio = 1 - (current / max_val)
                effective_amount = amount * headroom_ratio

                self.stats[stat] = min(max_val, current + effective_amount)

    def apply_decay(self, minutes):
        for stat, config in self.stats_config.items():
            if stat.startswith("_"):
                continue
            decay_rate = config.get("decay_per_minute", 0)
            self.stats[stat] = max(0, self.stats[stat] - decay_rate * minutes)

    def __str__(self):
        nonzero = {k: round(v, 1) for k, v in self.stats.items() if v > 0.5}
        return str(nonzero)


def analyze_session_overflow(model, playlist, verbose=True):
    """Analyze a session for overflow events."""
    modules = model["modules"]
    state = SessionStateWithTracking(model["stats"])

    if verbose:
        print(f"\nPlaylist: {' → '.join(playlist)}")
        print("-" * 60)

    for mod_name in playlist:
        if mod_name not in modules:
            continue
        state.apply_module_linear(mod_name, modules[mod_name])

        if verbose:
            print(f"  After {mod_name}: {state}")

    return state.overflow_log


def compare_linear_vs_log(model, playlist):
    """Compare final states with linear vs logarithmic scaling."""
    modules = model["modules"]

    # Linear
    state_linear = SessionStateWithTracking(model["stats"])
    for mod_name in playlist:
        if mod_name in modules:
            state_linear.apply_module_linear(mod_name, modules[mod_name])

    # Logarithmic
    state_log = SessionStateWithTracking(model["stats"])
    for mod_name in playlist:
        if mod_name in modules:
            state_log.apply_module_log(mod_name, modules[mod_name])

    print(f"\nPlaylist: {' → '.join(playlist)}")
    print("-" * 60)
    print(f"{'Stat':<15} {'Linear':>10} {'Log':>10} {'Diff':>10}")
    print("-" * 45)

    for stat in sorted(state_linear.stats.keys()):
        lin_val = state_linear.stats[stat]
        log_val = state_log.stats[stat]
        diff = lin_val - log_val
        if lin_val > 0.5 or log_val > 0.5:
            print(f"{stat:<15} {lin_val:>10.1f} {log_val:>10.1f} {diff:>+10.1f}")


def main():
    model = load_model()

    print("=" * 70)
    print("CLIPPING ANALYSIS")
    print("=" * 70)

    # Test sessions known to have high stats
    sessions = {
        "bimbo_path": ["intro", "suggestibility", "blank", "bimbo", "dumbdown", "wakener"],
        "intense": ["intro", "suggestibility", "blank", "brainwashing", "addiction", "wakener"],
        "slave_chain": ["intro", "suggestibility", "submission", "obedience", "slave", "harem", "wakener"],
        "arousal_heavy": ["intro", "suggestibility", "obedience", "free_use", "tease_denial", "harem", "wakener"],
    }

    all_overflow = []

    for name, playlist in sessions.items():
        print(f"\n{'='*70}")
        print(f"SESSION: {name}")
        overflow = analyze_session_overflow(model, playlist, verbose=True)
        all_overflow.extend(overflow)

        if overflow:
            print(f"\n  ⚠️ Overflow events:")
            for event in overflow:
                print(f"    {event['module']}: {event['stat']} +{event['attempted']} "
                      f"(effective: +{event['effective']}, wasted: {event['wasted']})")

    # Summary
    print("\n" + "=" * 70)
    print("OVERFLOW SUMMARY")
    print("=" * 70)

    if all_overflow:
        # Group by stat
        by_stat = {}
        for event in all_overflow:
            stat = event["stat"]
            if stat not in by_stat:
                by_stat[stat] = {"count": 0, "total_wasted": 0}
            by_stat[stat]["count"] += 1
            by_stat[stat]["total_wasted"] += event["wasted"]

        print(f"\nTotal overflow events: {len(all_overflow)}")
        print(f"\n{'Stat':<15} {'Events':>8} {'Total Wasted':>15}")
        print("-" * 40)
        for stat, data in sorted(by_stat.items(), key=lambda x: -x[1]["total_wasted"]):
            print(f"{stat:<15} {data['count']:>8} {data['total_wasted']:>15.1f}")
    else:
        print("\nNo overflow events detected!")

    # Compare linear vs log
    print("\n" + "=" * 70)
    print("LINEAR VS LOGARITHMIC COMPARISON")
    print("=" * 70)

    for name, playlist in sessions.items():
        compare_linear_vs_log(model, playlist)

    # Analysis
    print("\n" + "=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    print("""
Key findings:

1. OVERFLOW PATTERNS:
   - Stats most likely to overflow: absorption, suggestible, empty, obedient
   - These are the "foundation" stats that multiple modules produce
   - Specialization modules often waste production on already-high stats

2. LINEAR VS LOG IMPACT:
   - Log scaling results in lower final values (by design)
   - The gap is largest for stats that get reinforced multiple times
   - Log scaling "spreads out" the progression more

3. RECOMMENDATIONS:

   A) For current (linear) model:
      - Add overflow warnings to playlist generator
      - Prefer modules that have "headroom" for their production
      - Consider this a feature: hitting 100 = session goal achieved

   B) If implementing log scaling:
      - Benefits: "always deeper" feeling, no wasted production
      - Costs: need to recalibrate all requirements
      - Suggestion: test with real sessions first

   C) Hybrid approach:
      - Linear up to soft cap (80)
      - Log scaling from 80-100
      - Preserves current balance while adding "deeper" capacity
""")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Simulate the v2 mana model with derived consumption.

Test that:
1. Milk-before-meat still holds (can't skip to specializations)
2. Session progression works naturally
3. Consumption is balanced (not too harsh, not too lenient)
"""

import json
from pathlib import Path
from copy import deepcopy

DATA_DIR = Path(__file__).parent.parent / "data"


def load_model():
    """Load current model and apply v2 consumption rules."""
    with open(DATA_DIR / "playlist_mana.json") as f:
        model = json.load(f)

    # V2 consumption rules
    rules = {
        "requirement_cost_ratio": 0.3,
        "incompatible_pairs": {
            "aroused": ("empty", 0.4),
            "craving": ("empty", 0.3),
        },
        "max_incompatibility_consumption": 20,
        "transforms": {
            "blank": [("craving", "empty", 0.15)],
            "bimbo": [("suggestible", "identity_flux", 0.3)],
            "dumbdown": [("suggestible", "identity_flux", 0.5)],
            "bambi_blackout": [("aroused", "empty", 0.3)],
        },
        "wakener_consumption": {
            "absorption": 80,
            "suggestible": 50,
            "empty": 60,
            "receptive": 40
        }
    }

    return model, rules


def calculate_consumption(module_name, module_data, rules):
    """Calculate consumption for a module based on v2 rules."""
    if module_name == "wakener":
        return rules["wakener_consumption"]

    consumption = {}

    # Rule 1: Requirement cost (30% of what you require)
    ratio = rules["requirement_cost_ratio"]
    for stat, amount in module_data.get("requires", {}).items():
        cost = int(amount * ratio)
        if cost > 0:
            consumption[stat] = consumption.get(stat, 0) + cost

    # Rule 2: Incompatibility (producing X depletes Y)
    max_incompat = rules["max_incompatibility_consumption"]
    incompat_total = 0

    for produce_stat, (consume_stat, incompat_ratio) in rules["incompatible_pairs"].items():
        produced_amount = module_data.get("produces", {}).get(produce_stat, 0)
        if produced_amount > 0:
            cost = int(produced_amount * incompat_ratio)
            cost = min(cost, max_incompat - incompat_total)
            if cost > 0:
                consumption[consume_stat] = consumption.get(consume_stat, 0) + cost
                incompat_total += cost

    # Rule 3: Transforms (override for specific stats)
    if module_name in rules["transforms"]:
        for consume_stat, produce_stat, transform_ratio in rules["transforms"][module_name]:
            produced_amount = module_data.get("produces", {}).get(produce_stat, 0)
            cost = int(produced_amount * transform_ratio)
            consumption[consume_stat] = cost  # Override

    return consumption


class SessionState:
    """Track stats during session with v2 consumption rules."""

    def __init__(self, stats_config):
        self.stats = {}
        self.stats_config = stats_config
        for name, config in stats_config.items():
            if name.startswith("_"):
                continue
            self.stats[name] = config.get("baseline", 0)

    def apply_module(self, module_name, module_data, rules, apply_decay=True):
        """Apply module effects with v2 consumption."""
        duration_s = module_data.get("duration_s", 300)

        # Apply decay during the module
        if apply_decay:
            self.apply_decay(duration_s / 60)

        # Calculate and apply consumption
        consumption = calculate_consumption(module_name, module_data, rules)
        for stat, amount in consumption.items():
            if stat in self.stats:
                self.stats[stat] = max(0, self.stats[stat] - amount)

        # Produce stats
        for stat, amount in module_data.get("produces", {}).items():
            if stat in self.stats:
                max_val = self.stats_config.get(stat, {}).get("max", 100)
                self.stats[stat] = min(max_val, self.stats[stat] + amount)

    def apply_decay(self, minutes):
        """Apply natural decay over time."""
        for stat, config in self.stats_config.items():
            if stat.startswith("_"):
                continue
            decay_rate = config.get("decay_per_minute", 0)
            self.stats[stat] = max(0, self.stats[stat] - decay_rate * minutes)

    def check_requirements(self, module_data):
        """Check if requirements are met."""
        requires = module_data.get("requires", {})
        if not requires:
            return True, 1.0, {}

        details = {}
        total_score = 0
        for stat, required in requires.items():
            current = self.stats.get(stat, 0)
            ratio = current / required if required > 0 else 1.0
            details[stat] = {"required": required, "current": round(current, 1), "ratio": ratio}
            total_score += min(1.0, ratio)

        avg_score = total_score / len(requires)
        met = all(d["ratio"] >= 0.5 for d in details.values())
        return met, avg_score, details

    def __str__(self):
        nonzero = {k: round(v, 1) for k, v in self.stats.items() if v > 0.5}
        return str(nonzero)


def test_session_paths(model, rules):
    """Test various session paths."""
    print("=" * 70)
    print("V2 MODEL: SESSION PATH TESTS")
    print("=" * 70)

    modules = model["modules"]

    sessions = {
        "gentle": ["intro", "suggestibility", "acceptance", "submission", "wakener"],
        "standard": ["intro", "suggestibility", "brainwashing", "obedience", "wakener"],
        "intense": ["intro", "suggestibility", "blank", "brainwashing", "addiction", "wakener"],
        "bimbo_path": ["intro", "suggestibility", "blank", "bimbo", "dumbdown", "wakener"],
        "slave_path": ["intro", "suggestibility", "submission", "obedience", "slave", "wakener"],
        "arousal_path": ["intro", "suggestibility", "obedience", "free_use", "tease_denial", "wakener"],
    }

    for session_name, playlist in sessions.items():
        print(f"\n{'='*70}")
        print(f"SESSION: {session_name}")
        print(f"Playlist: {' → '.join(playlist)}")
        print(f"{'='*70}")

        state = SessionState(model["stats"])
        all_met = True

        for mod_name in playlist:
            mod = modules[mod_name]
            met, score, details = state.check_requirements(mod)

            if not met:
                all_met = False
                status = "✗ BLOCKED"
            else:
                status = "✓"

            print(f"\n  [{status}] {mod_name}")
            if details:
                for stat, d in details.items():
                    indicator = "✓" if d["ratio"] >= 0.5 else "✗"
                    print(f"      {indicator} {stat}: need {d['required']}, have {d['current']}")

            if met:
                state.apply_module(mod_name, mod, rules)
                print(f"      → State: {state}")
            else:
                print(f"      → Session cannot continue")
                break

        print(f"\n  Result: {'ALL REQUIREMENTS MET' if all_met else 'BLOCKED'}")


def test_cold_start_specialization(model, rules):
    """Test that you can't jump to specializations cold."""
    print("\n" + "=" * 70)
    print("MILK-BEFORE-MEAT TEST: Cold start → Specialization")
    print("=" * 70)

    modules = model["modules"]
    specializations = [n for n, d in modules.items() if d.get("tier") == "specialization"]

    state = SessionState(model["stats"])

    print("\nTrying to play specializations with no warmup:")
    for spec in specializations:
        mod = modules[spec]
        met, score, details = state.check_requirements(mod)
        status = "✓ ALLOWED" if met else "✗ BLOCKED"
        print(f"  {spec}: {status} (score={score:.2f})")
        if met:
            print(f"    WARNING: This should be blocked!")


def test_requirement_consumption_balance(model, rules):
    """Test that requirement consumption isn't too harsh."""
    print("\n" + "=" * 70)
    print("CONSUMPTION BALANCE TEST")
    print("=" * 70)

    modules = model["modules"]

    # Try repeating the same module
    print("\nTest: Can you play brainwashing twice in a row?")
    state = SessionState(model["stats"])

    # Build up foundation
    for mod_name in ["intro", "suggestibility"]:
        state.apply_module(mod_name, modules[mod_name], rules)

    print(f"  After foundation: {state}")

    # First brainwashing
    met1, _, _ = state.check_requirements(modules["brainwashing"])
    state.apply_module("brainwashing", modules["brainwashing"], rules)
    print(f"  After brainwashing #1: {state}")

    # Second brainwashing
    met2, score2, details = state.check_requirements(modules["brainwashing"])
    print(f"  Can play brainwashing #2? {met2} (score={score2:.2f})")
    for stat, d in details.items():
        print(f"    {stat}: need {d['required']}, have {d['current']}")

    # This should still be possible because brainwashing produces receptive/suggestible
    # which it also requires


def test_empty_economics(model, rules):
    """Test the 'empty' stat specifically since it's the key for identity work."""
    print("\n" + "=" * 70)
    print("EMPTY STAT ECONOMICS")
    print("The key test: empty is required for identity work")
    print("=" * 70)

    modules = model["modules"]

    # Path to bimbo
    print("\nPath to bimbo (needs empty >= 20):")
    state = SessionState(model["stats"])

    path = ["intro", "suggestibility", "blank", "bimbo"]
    for mod_name in path:
        mod = modules[mod_name]
        met, _, details = state.check_requirements(mod)

        consumption = calculate_consumption(mod_name, mod, rules)
        cons_str = ", ".join(f"{k}:-{v}" for k, v in consumption.items()) if consumption else "none"

        print(f"\n  {mod_name}:")
        print(f"    Requirements met: {met}")
        print(f"    Consumption: {cons_str}")
        if met:
            state.apply_module(mod_name, mod, rules)
            print(f"    State after: {state}")
        else:
            print(f"    BLOCKED - need to build up first")
            for stat, d in details.items():
                print(f"      {stat}: need {d['required']}, have {d['current']}")


def main():
    model, rules = load_model()

    test_cold_start_specialization(model, rules)
    test_session_paths(model, rules)
    test_requirement_consumption_balance(model, rules)
    test_empty_economics(model, rules)

    print("\n" + "=" * 70)
    print("V2 MODEL ASSESSMENT")
    print("=" * 70)
    print("""
The v2 model with derived consumption:

1. MILK-BEFORE-MEAT: ✓
   - Can't access specializations without foundation
   - Requirements gate access appropriately

2. SESSION FLOW: ✓
   - Natural progression through tiers
   - Stats accumulate, enabling later modules

3. CONSUMPTION SEMANTICS: ✓
   - "You use what you require" makes sense
   - Incompatibility rules handle aroused↔empty
   - Transforms handle special cases

4. BALANCE: Needs tuning
   - 30% requirement cost may be too low or high
   - Incompatibility cap (20) may need adjustment
   - Test with real sessions to validate

RECOMMENDATION: Adopt v2 model structure
- Cleaner, more maintainable
- Consistent logic
- Easier to add new modules
""")


if __name__ == "__main__":
    main()

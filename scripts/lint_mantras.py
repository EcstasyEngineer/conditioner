#!/usr/bin/env python3
"""
Lint mantra files for style and formatting issues.

Checks (errors - CI will fail):
- No emdashes or endashes in mantra text
- No trailing periods
- Valid JSON structure
- Required fields present
- Mantra count within bounds (17-35)
- Entry ramp minimum (basic + light >= 7)
- Valid placeholders only ({subject}, {controller})

Checks (warnings - informational):
- Smart quotes/apostrophes
- Missing extreme tier
- Tier distribution imbalances

Usage:
    python3 scripts/lint_mantras.py
"""

import json
import re
import sys
from pathlib import Path

# Add project root for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.scoring import get_tier

MANTRAS_DIR = Path(__file__).parent.parent / "mantras"

# Characters that must not appear in mantras (hard errors)
FORBIDDEN_CHARS = {
    "\u2014": "emdash (use comma instead)",  # —
    "\u2013": "endash (use hyphen instead)",  # –
}

# Characters that generate warnings but don't fail the lint
WARN_CHARS = {
    "\u201c": "smart quote (use straight quotes)",  # "
    "\u201d": "smart quote (use straight quotes)",  # "
    "\u2018": "smart apostrophe (use straight apostrophe)",  # '
    "\u2019": "smart apostrophe (use straight apostrophe)",  # '
}

REQUIRED_MANTRA_FIELDS = {"text", "base_points"}

# Valid placeholders (anything else is an error)
VALID_PLACEHOLDERS = {"{subject}", "{controller}"}

# Distribution constraints
MIN_MANTRAS = 17  # Minimum mantras per theme
MAX_MANTRAS = 35  # Maximum mantras per theme
MIN_ENTRY_RAMP = 7  # Minimum basic + light mantras (accessibility)
TIERS = ["basic", "light", "moderate", "deep", "extreme"]


def lint_file(filepath: Path) -> tuple[list[str], list[str]]:
    """Lint a single mantra file. Returns (errors, warnings)."""
    errors = []
    warnings = []

    try:
        content = filepath.read_text()
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return [f"{filepath.name}: Invalid JSON - {e}"], []

    if "mantras" not in data:
        errors.append(f"{filepath.name}: Missing 'mantras' array")
        return errors, warnings

    if "theme" not in data:
        errors.append(f"{filepath.name}: Missing 'theme' field")

    mantras = data.get("mantras", [])
    theme = data.get("theme", filepath.stem)

    # Check mantra count bounds
    count = len(mantras)
    if count < MIN_MANTRAS:
        errors.append(f"{filepath.name}: Only {count} mantras (minimum {MIN_MANTRAS})")
    if count > MAX_MANTRAS:
        errors.append(f"{filepath.name}: Has {count} mantras (maximum {MAX_MANTRAS})")

    # Track tier distribution
    tier_counts = {t: 0 for t in TIERS}

    for i, mantra in enumerate(mantras):
        prefix = f"{filepath.name}[{i}]"

        # Check required fields
        missing = REQUIRED_MANTRA_FIELDS - set(mantra.keys())
        if missing:
            errors.append(f"{prefix}: Missing fields: {missing}")
            continue

        text = mantra["text"]

        # Check forbidden characters (hard errors)
        for char, description in FORBIDDEN_CHARS.items():
            if char in text:
                errors.append(f"{prefix}: Contains {description}: {text!r}")

        # Check trailing period (hard error)
        if text.rstrip().endswith("."):
            errors.append(f"{prefix}: Trailing period: {text!r}")

        # Check placeholders (hard error)
        placeholders = re.findall(r"\{[^}]+\}", text)
        for placeholder in placeholders:
            if placeholder not in VALID_PLACEHOLDERS:
                errors.append(f"{prefix}: Invalid placeholder {placeholder!r}: {text!r}")

        # Check mismatched braces (hard error)
        if text.count("{") != text.count("}"):
            errors.append(f"{prefix}: Mismatched braces: {text!r}")

        # Check warn characters (soft warnings)
        for char, description in WARN_CHARS.items():
            if char in text:
                warnings.append(f"{prefix}: Contains {description}: {text!r}")

        # Check base_points is positive integer
        points = mantra.get("base_points")
        if not isinstance(points, int) or points <= 0:
            errors.append(f"{prefix}: base_points must be positive integer, got {points!r}")
        else:
            tier_counts[get_tier(points)] += 1

    # Check entry ramp (basic + light minimum)
    entry_ramp = tier_counts["basic"] + tier_counts["light"]
    if entry_ramp < MIN_ENTRY_RAMP:
        errors.append(
            f"{filepath.name}: Entry ramp too small: {entry_ramp} "
            f"(need {MIN_ENTRY_RAMP}+ basic/light mantras)"
        )

    # Warn on missing extreme tier (not an error - some themes may not need it)
    if tier_counts["extreme"] == 0:
        warnings.append(f"{filepath.name}: No extreme tier mantras")

    # Warn on heavily skewed distributions
    if count >= MIN_MANTRAS:
        # Check if any single tier dominates (>60% of total)
        for tier, tier_count in tier_counts.items():
            pct = tier_count / count * 100
            if pct > 60:
                warnings.append(
                    f"{filepath.name}: {tier} tier is {pct:.0f}% of mantras ({tier_count}/{count})"
                )

    return errors, warnings


def main():
    all_errors = []
    all_warnings = []

    mantra_files = sorted(MANTRAS_DIR.glob("*.json"))
    if not mantra_files:
        print(f"No mantra files found in {MANTRAS_DIR}")
        sys.exit(1)

    for filepath in mantra_files:
        errors, warnings = lint_file(filepath)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    # Print warnings (don't fail on these)
    if all_warnings:
        print(f"Warnings ({len(all_warnings)}):\n")
        for warning in all_warnings[:15]:  # Show first 15
            print(f"  {warning}")
        if len(all_warnings) > 15:
            print(f"  ... and {len(all_warnings) - 15} more warnings")
        print()

    # Print errors and fail
    if all_errors:
        print(f"Errors ({len(all_errors)}):\n")
        for error in all_errors:
            print(f"  {error}")
        sys.exit(1)
    else:
        print(f"All {len(mantra_files)} mantra files passed lint checks")
        sys.exit(0)


if __name__ == "__main__":
    main()

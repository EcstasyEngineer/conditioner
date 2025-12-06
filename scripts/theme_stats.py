#!/usr/bin/env python3
"""
Theme Statistics Analyzer

Analyzes a mantra theme JSON file and outputs distribution statistics.
Useful for comparing scoring across themes and identifying imbalances.

TODO(#48): Update tier names to low/mid/high/max after full rescore.
"""

import json
import sys
from pathlib import Path


def get_tier(points: int) -> str:
    """Return tier name for a given point value.

    Tier boundaries from docs/POINT_ECONOMY.md:
    20-40 basic, 40-70 light, 70-120 moderate, 120-180 deep, 180+ extreme
    """
    if points >= 120:
        return "extreme" if points >= 180 else "deep"
    elif points >= 70:
        return "moderate"
    elif points >= 40:
        return "light"
    else:
        return "basic"


def analyze_theme(filepath: Path) -> dict:
    """Analyze a theme file and return statistics."""
    with open(filepath) as f:
        data = json.load(f)

    theme_name = data.get("theme", filepath.stem)
    mantras = data.get("mantras", [])

    if not mantras:
        return {"theme": theme_name, "error": "No mantras found"}

    # Extract points
    points = [m["base_points"] for m in mantras]

    # Basic stats
    total = len(points)
    avg = sum(points) / total
    points_sorted = sorted(points)
    median = points_sorted[total // 2] if total % 2 else (points_sorted[total // 2 - 1] + points_sorted[total // 2]) / 2
    min_pts = min(points)
    max_pts = max(points)

    # Tier distribution (derived from points)
    tier_counts = {"basic": 0, "light": 0, "moderate": 0, "deep": 0, "extreme": 0}
    for p in points:
        tier_counts[get_tier(p)] += 1

    # Placeholder usage
    has_controller = sum(1 for m in mantras if "{controller}" in m["text"])
    has_subject = sum(1 for m in mantras if "{subject}" in m["text"])
    has_both = sum(1 for m in mantras if "{controller}" in m["text"] and "{subject}" in m["text"])
    no_placeholders = total - (has_controller + has_subject - has_both)

    return {
        "theme": theme_name,
        "total": total,
        "avg": avg,
        "median": median,
        "min": min_pts,
        "max": max_pts,
        "range": max_pts - min_pts,
        "tier_counts": tier_counts,
        "tier_percentages": {k: (v / total * 100) for k, v in tier_counts.items()},
        "placeholders": {
            "controller_only": has_controller - has_both,
            "subject_only": has_subject - has_both,
            "both": has_both,
            "none": no_placeholders,
        },
    }


def format_bar(value: float, max_width: int = 30) -> str:
    """Create a simple ASCII bar chart segment."""
    filled = int(value / 100 * max_width)
    return "█" * filled + "░" * (max_width - filled)


def print_stats(stats: dict):
    """Print formatted statistics."""
    if "error" in stats:
        print(f"Error: {stats['error']}")
        return

    print(f"\n{'=' * 60}")
    print(f"Theme: {stats['theme'].upper()}")
    print(f"{'=' * 60}")

    print(f"\n📊 Basic Stats:")
    print(f"  Total mantras: {stats['total']}")
    print(f"  Average points: {stats['avg']:.1f}")
    print(f"  Median points:  {stats['median']:.1f}")
    print(f"  Range: {stats['min']} - {stats['max']} (span: {stats['range']})")

    print(f"\n📈 Tier Distribution:")
    for tier in ["basic", "light", "moderate", "deep", "extreme"]:
        count = stats["tier_counts"][tier]
        pct = stats["tier_percentages"][tier]
        bar = format_bar(pct)
        print(f"  {tier:10} {count:3} ({pct:5.1f}%) {bar}")

    print(f"\n🔧 Placeholder Usage:")
    ph = stats["placeholders"]
    print(f"  {{controller}} only: {ph['controller_only']}")
    print(f"  {{subject}} only:    {ph['subject_only']}")
    print(f"  Both:              {ph['both']}")
    print(f"  None:              {ph['none']}")

    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python theme_stats.py <theme.json> [theme2.json ...]")
        print("       python theme_stats.py mantras/*.json")
        sys.exit(1)

    all_stats = []
    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.exists():
            print(f"File not found: {arg}")
            continue

        stats = analyze_theme(path)
        all_stats.append(stats)
        print_stats(stats)

    # Summary comparison if multiple files
    if len(all_stats) > 1:
        print(f"\n{'=' * 60}")
        print("COMPARISON SUMMARY")
        print(f"{'=' * 60}")
        print(f"\n{'Theme':<15} {'Count':>6} {'Avg':>7} {'Med':>7} {'Range':>12}")
        print("-" * 50)
        for s in sorted(all_stats, key=lambda x: x.get("avg", 0), reverse=True):
            if "error" not in s:
                print(f"{s['theme']:<15} {s['total']:>6} {s['avg']:>7.1f} {s['median']:>7.1f} {s['min']:>4}-{s['max']:<4}")

        print(f"\nTier breakdown by theme:")
        print(f"{'Theme':<15} {'basic':>8} {'light':>8} {'mod':>8} {'deep':>8} {'extr':>8}")
        print("-" * 60)
        for s in sorted(all_stats, key=lambda x: x.get("avg", 0), reverse=True):
            if "error" not in s:
                t = s["tier_counts"]
                print(f"{s['theme']:<15} {t['basic']:>8} {t['light']:>8} {t['moderate']:>8} {t['deep']:>8} {t['extreme']:>8}")


if __name__ == "__main__":
    main()

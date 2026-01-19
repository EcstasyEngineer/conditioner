#!/usr/bin/env python3
"""
Cleanup script for V1 mantra config cruft.

Two operations:
1. Delete user config files that have no meaningful data (no points, no V2 data, unenrolled)
2. Remove orphaned V1 fields from remaining configs

Usage:
    python3 scripts/cleanup_v1_configs.py --dry-run          # Preview deletions
    python3 scripts/cleanup_v1_configs.py --delete           # Actually delete empty configs
    python3 scripts/cleanup_v1_configs.py --clean-v1         # Remove V1 cruft from remaining
    python3 scripts/cleanup_v1_configs.py --clean-v1 --dry-run  # Preview V1 cruft removal
"""

import os
import sys
import json
import argparse
from pathlib import Path

CONFIGS_DIR = Path(__file__).parent.parent / "configs"

# V1-only fields that should be removed
V1_FIELDS = ["next_encounter", "last_encounter", "online_only", "consecutive_timeouts"]

# V2 fields that indicate meaningful data
V2_FIELDS = ["next_delivery", "sent", "current_mantra", "delivered_mantra", "availability_distribution", "delivery_mode"]


def has_v2_data(mantra_system: dict) -> bool:
    """Check if mantra_system has any V2 fields with data."""
    for field in V2_FIELDS:
        if mantra_system.get(field) is not None:
            return True
    return False


def has_v1_cruft(mantra_system: dict) -> bool:
    """Check if mantra_system has any V1 fields."""
    for field in V1_FIELDS:
        if field in mantra_system:
            return True
    return False


def has_meaningful_data(config: dict) -> bool:
    """Check if config has any data worth keeping."""
    # Has points
    if config.get("points", 0) > 0:
        return True

    # Has any non-mantra_system keys (like auto_claim_gacha, etc.)
    other_keys = [k for k in config.keys() if k not in ("mantra_system", "points")]
    if other_keys:
        return True

    mantra = config.get("mantra_system", {})

    # Is enrolled
    if mantra.get("enrolled"):
        return True

    # Has V2 data (was enrolled at some point)
    if has_v2_data(mantra):
        return True

    # Has custom themes (user configured but didn't enroll)
    themes = mantra.get("themes", [])
    if themes and len(themes) > 0:
        return True

    # Has custom subject/controller (non-default)
    if mantra.get("subject") not in (None, "puppet"):
        return True
    if mantra.get("controller") not in (None, "Master"):
        return True

    return False


def analyze_configs():
    """Analyze all user configs and categorize them."""
    results = {
        "delete": [],      # Files safe to delete
        "keep": [],        # Files with meaningful data
        "clean_v1": [],    # Files that need V1 cruft removed
    }

    for fname in os.listdir(CONFIGS_DIR):
        if not fname.startswith("user_") or not fname.endswith(".json"):
            continue

        path = CONFIGS_DIR / fname
        with open(path) as f:
            config = json.load(f)

        mantra = config.get("mantra_system", {})

        if has_meaningful_data(config):
            results["keep"].append({
                "file": fname,
                "points": config.get("points", 0),
                "enrolled": mantra.get("enrolled", False),
                "has_v2": has_v2_data(mantra),
                "has_v1": has_v1_cruft(mantra),
            })
            if has_v1_cruft(mantra):
                results["clean_v1"].append(fname)
        else:
            results["delete"].append({
                "file": fname,
                "points": config.get("points", 0),
            })

    return results


def delete_empty_configs(dry_run: bool = True):
    """Move config files with no meaningful data to a staging folder for review."""
    results = analyze_configs()
    staging_dir = CONFIGS_DIR / "staged_for_deletion"

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Configs to MOVE to staged_for_deletion/ ({len(results['delete'])}):")
    print("-" * 60)

    if not dry_run:
        staging_dir.mkdir(exist_ok=True)

    for item in results["delete"]:
        print(f"  {item['file']}")
        if not dry_run:
            src = CONFIGS_DIR / item["file"]
            dst = staging_dir / item["file"]
            src.rename(dst)

    print(f"\nConfigs to KEEP ({len(results['keep'])}):")
    print("-" * 60)

    for item in sorted(results["keep"], key=lambda x: -x["points"]):
        status = []
        if item["enrolled"]:
            status.append("enrolled")
        if item["has_v2"]:
            status.append("v2")
        if item["has_v1"]:
            status.append("v1-cruft")
        print(f"  {item['file']}: {item['points']} pts [{', '.join(status)}]")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Summary:")
    print(f"  Would move to staging: {len(results['delete'])} files")
    print(f"  Would keep: {len(results['keep'])} files")
    print(f"  Need V1 cleanup: {len(results['clean_v1'])} files")

    if dry_run:
        print("\nRun with --delete to move files to staged_for_deletion/ folder.")
    else:
        print(f"\nFiles moved to: {staging_dir}/")
        print("Review them, then delete the folder when satisfied.")


def clean_v1_cruft(dry_run: bool = True):
    """Remove V1 fields from configs that have them."""
    results = analyze_configs()

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Cleaning V1 cruft from {len(results['clean_v1'])} files:")
    print("-" * 60)

    for fname in results["clean_v1"]:
        path = CONFIGS_DIR / fname
        with open(path) as f:
            config = json.load(f)

        mantra = config.get("mantra_system", {})
        removed = []

        for field in V1_FIELDS:
            if field in mantra:
                removed.append(field)
                if not dry_run:
                    del mantra[field]

        print(f"  {fname}: removing {removed}")

        if not dry_run:
            with open(path, "w") as f:
                json.dump(config, f, indent=4)

    if dry_run:
        print("\nRun with --clean-v1 (without --dry-run) to actually clean files.")


def main():
    parser = argparse.ArgumentParser(description="Cleanup V1 mantra config cruft")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without making them")
    parser.add_argument("--delete", action="store_true", help="Delete empty config files")
    parser.add_argument("--clean-v1", action="store_true", help="Remove V1 fields from remaining configs")

    args = parser.parse_args()

    if not args.delete and not args.clean_v1:
        # Default to dry-run analysis
        args.dry_run = True
        args.delete = True

    if args.delete:
        delete_empty_configs(dry_run=args.dry_run)

    if args.clean_v1:
        clean_v1_cruft(dry_run=args.dry_run)


if __name__ == "__main__":
    main()

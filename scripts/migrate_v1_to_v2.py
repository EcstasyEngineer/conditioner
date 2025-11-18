#!/usr/bin/env python3
"""
Migrate V1 mantra configs to V2 format.

This script:
1. Backs up all configs
2. For enrolled users: Migrates to V2 with adjusted frequency
3. For unenrolled users: Wipes mantra_system section
4. Sets next_delivery to 3 hours from now for enrolled users
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from shutil import copy2

PROD_CONFIG_DIR = Path("/home/dudebot/conditioner/configs")
BACKUP_DIR = Path("/home/dudebot/conditioner/configs_backup_v1")

# Your user ID for testing
TEST_USER_ID = "125839498150936576"


def backup_configs():
    """Backup all config files before migration."""
    print("Backing up configs...")
    BACKUP_DIR.mkdir(exist_ok=True)

    backed_up = 0
    for config_file in PROD_CONFIG_DIR.glob("*.json"):
        backup_path = BACKUP_DIR / config_file.name
        copy2(config_file, backup_path)
        backed_up += 1

    print(f"✓ Backed up {backed_up} config files to {BACKUP_DIR}")


def load_themes():
    """Load available themes for mantra selection."""
    mantras_dir = Path(__file__).parent.parent / "mantras"
    themes = {}

    for theme_file in mantras_dir.glob("*.json"):
        with open(theme_file) as f:
            theme_data = json.load(f)
            themes[theme_data["theme"]] = theme_data

    return themes


def select_random_mantra(themes_list, available_themes):
    """Simple mantra selection without discord imports."""
    import random

    # Collect all mantras from user's themes
    all_mantras = []
    for theme_name in themes_list:
        if theme_name in available_themes:
            theme_data = available_themes[theme_name]
            for mantra in theme_data.get("mantras", []):
                all_mantras.append({
                    "text": mantra["text"],
                    "theme": theme_name,
                    "difficulty": mantra.get("difficulty", "moderate"),
                    "base_points": mantra.get("base_points", 50)
                })

    if not all_mantras:
        return None

    return random.choice(all_mantras)


def migrate_enrolled_user(old_config: dict, available_themes: dict) -> dict:
    """Migrate an enrolled user from V1 to V2 format."""
    old_mantra = old_config.get("mantra_system", {})

    # Adjust frequency
    old_freq = old_mantra.get("frequency", 1.0)
    was_online_only = old_mantra.get("online_only", False)

    if was_online_only:
        # Was stuck in online-only mode, start conservative
        new_freq = 1.0
    elif old_freq >= 6:
        # Cap at 4 for migration
        new_freq = 4.0
    else:
        # Keep existing frequency
        new_freq = old_freq

    # Pre-select first mantra
    themes = old_mantra.get("themes", ["obedience"])
    mantra_data = select_random_mantra(themes, available_themes)

    if not mantra_data:
        # Fallback to simple mantra if theme not found
        current_mantra = {
            "text": "I accept my programming",
            "theme": "acceptance",
            "difficulty": "moderate",
            "base_points": 50
        }
    else:
        current_mantra = {
            "text": mantra_data["text"],
            "theme": mantra_data["theme"],
            "difficulty": mantra_data["difficulty"],
            "base_points": mantra_data["base_points"]
        }

    # Build V2 config
    new_config = {
        "enrolled": True,
        "themes": themes,
        "subject": old_mantra.get("subject", "puppet"),
        "controller": old_mantra.get("controller", "Master"),
        "frequency": new_freq,
        "consecutive_failures": 0,
        "next_delivery": (datetime.now() + timedelta(hours=3)).isoformat(),
        "sent": None,
        "current_mantra": current_mantra,
        "availability_distribution": [0.5] * 24,
        "delivered_mantra": None,
        "favorite_mantras": [],
        "delivery_mode": "adaptive"
    }

    return new_config


def migrate_unenrolled_user() -> None:
    """For unenrolled users, just return None (wipe mantra_system)."""
    return None


def migrate_config_file(config_path: Path, available_themes: dict):
    """Migrate a single config file."""
    with open(config_path) as f:
        config = json.load(f)

    # Check if has mantra_system
    if "mantra_system" not in config:
        print(f"  Skipping {config_path.name} (no mantra_system)")
        return

    old_mantra = config["mantra_system"]
    is_enrolled = old_mantra.get("enrolled", False)

    if is_enrolled:
        # Migrate enrolled user
        print(f"  Migrating enrolled user: {config_path.name}")
        config["mantra_system"] = migrate_enrolled_user(config, available_themes)
    else:
        # Wipe mantra_system for unenrolled users
        print(f"  Wiping mantra_system for unenrolled: {config_path.name}")
        del config["mantra_system"]

    # Write back
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)


def main():
    print("=" * 70)
    print("MANTRA V1 → V2 MIGRATION")
    print("=" * 70)
    print()

    # Check directories exist
    if not PROD_CONFIG_DIR.exists():
        print(f"✗ Config directory not found: {PROD_CONFIG_DIR}")
        return 1

    # Backup first
    backup_configs()
    print()

    # Load themes for mantra selection
    print("Loading themes...")
    available_themes = load_themes()
    print(f"✓ Loaded {len(available_themes)} themes")
    print()

    # Find user configs
    user_configs = list(PROD_CONFIG_DIR.glob("user_*.json"))
    print(f"Found {len(user_configs)} user configs")
    print()

    # Migrate each config
    print("Migrating configs...")
    for config_path in sorted(user_configs):
        migrate_config_file(config_path, available_themes)

    print()
    print("=" * 70)
    print("MIGRATION COMPLETE")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Review migrated configs in:", PROD_CONFIG_DIR)
    print("2. Test with user:", TEST_USER_ID)
    print("3. If issues, restore from:", BACKUP_DIR)
    print("4. Restart bot: sudo systemctl restart conditioner")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())

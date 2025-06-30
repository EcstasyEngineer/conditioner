#!/usr/bin/env python3
"""
Script to remove confirmed data litter from user configs.
"""
import json
import os
from pathlib import Path

# Keys confirmed as data litter (redundant or never used)
KEYS_TO_REMOVE = [
    "total_points_earned",      # Can be calculated from JSONL
    "online_consecutive_checks", # Only in default, never used
    "online_check_interval",     # Only in default, never used  
    "encounters_completed",      # Only in default, never used
    "mantras_seen"              # Only in default, never used
]

def cleanup_config_file(file_path):
    """Remove data litter keys from a single config file."""
    try:
        with open(file_path, 'r') as f:
            config = json.load(f)
        
        changes_made = False
        
        # Check if this file has mantra_system config
        if "mantra_system" in config:
            mantra_config = config["mantra_system"]
            
            for key in KEYS_TO_REMOVE:
                if key in mantra_config:
                    del mantra_config[key]
                    changes_made = True
                    print(f"  Removed {key} from {file_path}")
        
        # Save the file if changes were made
        if changes_made:
            with open(file_path, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"  Updated {file_path}")
        
        return changes_made
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    configs_dir = Path("configs")
    
    if not configs_dir.exists():
        print("No configs directory found!")
        return
    
    print("Starting cleanup of user config data litter...")
    print(f"Removing keys: {', '.join(KEYS_TO_REMOVE)}")
    print()
    
    total_files = 0
    updated_files = 0
    
    # Process all user config files
    for config_file in configs_dir.glob("user_*.json"):
        total_files += 1
        print(f"Processing {config_file.name}...")
        
        if cleanup_config_file(config_file):
            updated_files += 1
        else:
            print(f"  No changes needed for {config_file.name}")
    
    print()
    print(f"Cleanup complete!")
    print(f"Files processed: {total_files}")
    print(f"Files updated: {updated_files}")
    
    print("\nRemember to also update the default config in utils/mantras.py")

if __name__ == "__main__":
    main()
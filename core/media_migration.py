#!/usr/bin/env python3
"""
Auto-migration system for media files.
Runs on bot startup and handles incremental renaming of new files.
"""

import os
import shutil
from pathlib import Path
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Configuration
MEDIA_BASE = Path("media")
TIER_DIRS = {
    "common": MEDIA_BASE / "common",
    "uncommon": MEDIA_BASE / "uncommon", 
    "rare": MEDIA_BASE / "rare",
    "epic": MEDIA_BASE / "epic"
}

VALID_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.mp3', '.mp4', '.mov', '.webm', '.txt'}
SAMPLE_FILES = {'sample.gif', 'sample.png', 'sample.jpg', 'sample.jpeg', 'sample.mp3', 'sample.mp4', 'sample.mov', 'sample.webm', 'sample.txt'}

def get_unnumbered_files(directory):
    """Get files that need renaming (not numbered and not samples)."""
    if not directory.exists():
        return []
    
    files = []
    for file_path in directory.iterdir():
        if (file_path.is_file() and 
            file_path.suffix.lower() in VALID_EXTENSIONS and
            file_path.name.lower() not in SAMPLE_FILES and
            not file_path.stem.isdigit()):
            files.append(file_path)
    
    # Sort by modification time (oldest first)
    return sorted(files, key=lambda x: x.stat().st_mtime)

def get_next_available_number(directory):
    """Find the next available number in the sequence."""
    if not directory.exists():
        return 1
    
    numbered_files = []
    for file_path in directory.iterdir():
        if (file_path.is_file() and 
            file_path.suffix.lower() in VALID_EXTENSIONS and
            file_path.name.lower() not in SAMPLE_FILES and
            file_path.stem.isdigit()):
            numbered_files.append(int(file_path.stem))
    
    if not numbered_files:
        return 1
    
    # Find first gap in sequence, or next number after max
    numbered_files.sort()
    for i, num in enumerate(numbered_files, 1):
        if i != num:
            return i
    
    return max(numbered_files) + 1

def rename_new_files_in_tier(tier_name, tier_dir):
    """Rename any unnumbered files in a tier directory."""
    unnumbered_files = get_unnumbered_files(tier_dir)
    
    if not unnumbered_files:
        return 0
    
    logger.info(f"Found {len(unnumbered_files)} new files in {tier_name} to rename")
    
    renamed_count = 0
    next_number = get_next_available_number(tier_dir)
    
    for file_path in unnumbered_files:
        new_name = f"{next_number:03d}{file_path.suffix}"
        new_path = tier_dir / new_name
        
        # Avoid conflicts
        while new_path.exists():
            next_number += 1
            new_name = f"{next_number:03d}{file_path.suffix}"
            new_path = tier_dir / new_name
        
        logger.info(f"Renaming {file_path.name} -> {new_name}")
        file_path.rename(new_path)
        renamed_count += 1
        next_number += 1
    
    return renamed_count

def count_media_files(directory):
    """Count numbered media files in directory."""
    if not directory.exists():
        return 0
    
    count = 0
    for file_path in directory.iterdir():
        if (file_path.is_file() and 
            file_path.suffix.lower() in VALID_EXTENSIONS and
            file_path.name.lower() not in SAMPLE_FILES):
            count += 1
    
    return count

def update_file_counts():
    """Update the file counts JSON."""
    counts = {}
    for tier_name, tier_dir in TIER_DIRS.items():
        counts[tier_name] = count_media_files(tier_dir)
    
    config_path = Path("media_file_counts.json")
    with open(config_path, 'w') as f:
        json.dump(counts, f, indent=2)
    
    logger.info(f"Updated file counts: {counts}")
    return counts

def run_migration():
    """Run incremental migration on bot startup."""
    logger.info("Starting media file migration check...")
    
    total_renamed = 0
    
    # Process each tier directory
    for tier_name, tier_dir in TIER_DIRS.items():
        tier_dir.mkdir(exist_ok=True)  # Ensure directory exists
        renamed_count = rename_new_files_in_tier(tier_name, tier_dir)
        total_renamed += renamed_count
    
    # Update file counts
    file_counts = update_file_counts()
    
    if total_renamed > 0:
        logger.info(f"Migration complete: renamed {total_renamed} files")
    else:
        logger.info("No new files to rename")
    
    return total_renamed, file_counts

if __name__ == "__main__":
    # For testing
    logging.basicConfig(level=logging.INFO)
    run_migration()
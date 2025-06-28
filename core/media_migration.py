#!/usr/bin/env python3
"""
Auto-migration system for media files.
Runs on bot startup and handles incremental renaming of new files.
Includes duplicate resolution and proper sequential numbering.
"""

import os
from pathlib import Path
import json
from datetime import datetime
import logging
import hashlib
import time

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

def get_highest_numbered_file(directory):
    """Find the highest numbered file in directory."""
    if not directory.exists():
        return 0
    
    highest = 0
    for file_path in directory.iterdir():
        if (file_path.is_file() and 
            file_path.suffix.lower() in VALID_EXTENSIONS and
            file_path.name.lower() not in SAMPLE_FILES and
            file_path.stem.isdigit()):
            highest = max(highest, int(file_path.stem))
    
    return highest

def find_numbered_gaps(directory):
    """Find gaps in the numbering sequence."""
    if not directory.exists():
        return []
    
    numbered_files = []
    for file_path in directory.iterdir():
        if (file_path.is_file() and 
            file_path.suffix.lower() in VALID_EXTENSIONS and
            file_path.name.lower() not in SAMPLE_FILES and
            file_path.stem.isdigit()):
            numbered_files.append(int(file_path.stem))
    
    if not numbered_files:
        return []
    
    numbered_files.sort()
    gaps = []
    for i in range(1, max(numbered_files)):
        if i not in numbered_files:
            gaps.append(i)
    
    return gaps

def generate_temp_hash(file_path):
    """Generate a temporary hash name for duplicate files."""
    # Use file content hash + timestamp for uniqueness
    hasher = hashlib.md5()
    hasher.update(file_path.name.encode())
    hasher.update(str(time.time()).encode())
    return f"temp_{hasher.hexdigest()[:8]}"

def normalize_padding_in_tier(tier_name, tier_dir):
    """Convert any unpadded numbered files to 3-digit zero-padded format."""
    if not tier_dir.exists():
        return 0
    
    normalized_count = 0
    
    for file_path in tier_dir.iterdir():
        if (file_path.is_file() and 
            file_path.suffix.lower() in VALID_EXTENSIONS and
            file_path.name.lower() not in SAMPLE_FILES and
            file_path.stem.isdigit()):
            
            number = int(file_path.stem)
            # Check if it's already 3-digit padded
            if file_path.stem != f"{number:03d}":
                new_name = f"{number:03d}{file_path.suffix}"
                new_path = tier_dir / new_name
                
                if not new_path.exists():
                    logger.info(f"Normalizing padding: {file_path.name} -> {new_name}")
                    file_path.rename(new_path)
                    normalized_count += 1
                else:
                    logger.warning(f"Cannot normalize {file_path.name}: {new_name} already exists")
    
    return normalized_count

def resolve_duplicates_in_tier(tier_name, tier_dir):
    """Handle duplicate numbered files - keep newest, rename older to temp hash."""
    if not tier_dir.exists():
        return 0
    
    # Group files by their number
    numbered_groups = {}
    for file_path in tier_dir.iterdir():
        if (file_path.is_file() and 
            file_path.suffix.lower() in VALID_EXTENSIONS and
            file_path.name.lower() not in SAMPLE_FILES and
            file_path.stem.isdigit()):
            number = int(file_path.stem)
            if number not in numbered_groups:
                numbered_groups[number] = []
            numbered_groups[number].append(file_path)
    
    duplicates_resolved = 0
    
    # Handle groups with multiple files
    for number, files in numbered_groups.items():
        if len(files) > 1:
            logger.info(f"Found {len(files)} files with number {number:03d} in {tier_name}")
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Keep the newest, rename others to temp hash
            newest_file = files[0]
            logger.info(f"Keeping newest: {newest_file.name}")
            
            for old_file in files[1:]:
                temp_name = f"{generate_temp_hash(old_file)}{old_file.suffix}"
                temp_path = tier_dir / temp_name
                
                logger.info(f"Renaming duplicate {old_file.name} -> {temp_name}")
                old_file.rename(temp_path)
                duplicates_resolved += 1
    
    return duplicates_resolved

def get_temp_files(directory):
    """Get files with temp_ prefix that need sequential numbering."""
    if not directory.exists():
        return []
    
    temp_files = []
    for file_path in directory.iterdir():
        if (file_path.is_file() and 
            file_path.suffix.lower() in VALID_EXTENSIONS and
            file_path.name.startswith('temp_')):
            temp_files.append(file_path)
    
    # Sort by modification time (oldest first)
    return sorted(temp_files, key=lambda x: x.stat().st_mtime)

def rename_new_files_in_tier(tier_name, tier_dir):
    """Rename unnumbered files using sequential numbering from highest+1."""
    unnumbered_files = get_unnumbered_files(tier_dir)
    temp_files = get_temp_files(tier_dir)
    all_files_to_rename = unnumbered_files + temp_files
    
    if not all_files_to_rename:
        return 0
    
    logger.info(f"Found {len(unnumbered_files)} new files and {len(temp_files)} temp files in {tier_name} to rename")
    
    renamed_count = 0
    
    # Start numbering from highest existing number + 1
    next_number = get_highest_numbered_file(tier_dir) + 1
    
    # First, try to fill gaps with temp files (former duplicates)
    gaps = find_numbered_gaps(tier_dir)
    gap_index = 0
    
    for file_path in all_files_to_rename:
        target_number = None
        
        # For temp files (former duplicates), try to fill gaps first
        if file_path.name.startswith('temp_') and gap_index < len(gaps):
            target_number = gaps[gap_index]
            gap_index += 1
            logger.info(f"Filling gap {target_number:03d} with {file_path.name}")
        else:
            # Use sequential numbering for new files and remaining temp files
            target_number = next_number
            next_number += 1
        
        new_name = f"{target_number:03d}{file_path.suffix}"
        new_path = tier_dir / new_name
        
        # Safety check - should not happen with our logic
        if new_path.exists():
            logger.warning(f"Conflict detected: {new_name} already exists, using next available number")
            target_number = next_number
            next_number += 1
            new_name = f"{target_number:03d}{file_path.suffix}"
            new_path = tier_dir / new_name
        
        logger.info(f"Renaming {file_path.name} -> {new_name}")
        file_path.rename(new_path)
        renamed_count += 1
    
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

def run_migration():
    """Run incremental migration on bot startup with duplicate resolution."""
    logger.info("Starting media file migration check...")
    
    total_renamed = 0
    total_duplicates_resolved = 0
    total_normalized = 0
    
    # Process each tier directory
    for tier_name, tier_dir in TIER_DIRS.items():
        tier_dir.mkdir(exist_ok=True)  # Ensure directory exists
        
        # Step 1: Normalize padding (convert 10.gif -> 010.gif)
        normalized_count = normalize_padding_in_tier(tier_name, tier_dir)
        total_normalized += normalized_count
        
        # Step 2: Resolve duplicates (keep newest, temp rename older)
        duplicates_count = resolve_duplicates_in_tier(tier_name, tier_dir)
        total_duplicates_resolved += duplicates_count
        
        # Step 3: Sequential numbering for new files and gap-filling for temp files
        renamed_count = rename_new_files_in_tier(tier_name, tier_dir)
        total_renamed += renamed_count
    
    if total_normalized > 0:
        logger.info(f"Normalized padding on {total_normalized} files")
    
    if total_duplicates_resolved > 0:
        logger.info(f"Resolved {total_duplicates_resolved} duplicate files")
    
    if total_renamed > 0:
        logger.info(f"Migration complete: renamed {total_renamed} files")
    else:
        logger.info("No new files to rename")
    
    return total_renamed

if __name__ == "__main__":
    # For testing
    logging.basicConfig(level=logging.INFO)
    run_migration()
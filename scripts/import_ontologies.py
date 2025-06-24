#!/usr/bin/env python3
"""
Import mantras from subspace-studio ontologies.

This script converts the keyword phrases from the ontology files
into properly formatted mantra themes for the conditioner bot.
"""

import json
import os
import sys
from pathlib import Path
import re

# Path to the subspace-studio ontologies
ONTOLOGIES_PATH = Path("../../subspace-studio/ontologies")
OUTPUT_PATH = Path("../mantras/themes")

# Difficulty mappings based on keyword complexity
def calculate_difficulty(keyword):
    """Determine difficulty based on keyword length and complexity."""
    words = keyword.split()
    word_count = len(words)
    
    # Map to the actual difficulty levels used by the bot
    if word_count <= 2:
        return "basic"
    elif word_count <= 3:
        return "light"
    elif word_count <= 4:
        return "moderate"
    elif word_count <= 5:
        return "deep"
    else:
        return "extreme"

def calculate_base_points(keyword, difficulty):
    """Calculate base points based on difficulty and length."""
    # Based on existing themes' point ranges
    base_map = {
        "basic": 10,
        "light": 18,
        "moderate": 25,
        "deep": 33,
        "extreme": 42
    }
    
    # Add small variation for diversity
    words = keyword.split()
    variation = (len(words) % 3) - 1  # -1, 0, or 1
    
    return base_map[difficulty] + variation

def needs_placeholders(keyword):
    """Check if the keyword would benefit from placeholders."""
    # Look for pronouns that could be replaced
    if any(word in keyword.lower() for word in ["your", "their", "you"]):
        return True
    # Look for authority references
    if any(word in keyword.lower() for word in ["authority", "commands", "guidance"]):
        return True
    return False

def convert_to_mantra(keyword):
    """Convert a keyword phrase into a mantra with appropriate placeholders."""
    mantra = keyword
    
    # Only replace certain patterns that make sense
    replacements = {
        r'\btheir authority\b': "{controller}'s authority",
        r'\btheir commands?\b': "{controller}'s commands",
        r'\btheir guidance\b': "{controller}'s guidance",
        r'\btheir lead\b': "{controller}'s lead",
        r'\btheir will\b': "{controller}'s will",
        # Don't replace generic "your" or "you" - let the mantra system handle it
    }
    
    for pattern, replacement in replacements.items():
        mantra = re.sub(pattern, replacement, mantra, flags=re.IGNORECASE)
    
    # Capitalize first letter
    mantra = mantra[0].upper() + mantra[1:] if mantra else mantra
    
    return mantra

def import_ontology(filename):
    """Import a single ontology file and convert to mantra format."""
    filepath = ONTOLOGIES_PATH / filename
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return None
    
    # Extract theme name from filename
    theme_name = filename.replace('.json', '').lower()
    
    # Create mantra structure
    mantra_data = {
        "theme": theme_name,
        "description": data.get("description", ""),
        "mantras": []
    }
    
    # Convert keywords to mantras
    for keyword in data.get("keywords", []):
        difficulty = calculate_difficulty(keyword)
        base_points = calculate_base_points(keyword, difficulty)
        
        # Create base mantra
        mantra_text = convert_to_mantra(keyword)
        
        mantra_entry = {
            "text": mantra_text,
            "difficulty": difficulty,
            "base_points": base_points
        }
        
        mantra_data["mantras"].append(mantra_entry)
    
    # Add metadata
    mantra_data["metadata"] = {
        "imported_from": "subspace-studio",
        "tags": data.get("tags", []),
        "cnc": data.get("cnc", False)
    }
    
    return mantra_data

def main():
    """Main import function."""
    print("Importing mantras from subspace-studio ontologies...")
    
    # Create output directory if it doesn't exist
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    
    # Get list of ontology files
    ontology_files = list(ONTOLOGIES_PATH.glob("*.json"))
    
    imported_count = 0
    skipped_count = 0
    
    for ontology_file in ontology_files:
        theme_name = ontology_file.stem.lower()
        output_file = OUTPUT_PATH / f"{theme_name}.json"
        
        # Skip if already exists (unless --force flag is used)
        if output_file.exists() and "--force" not in sys.argv:
            print(f"Skipping {theme_name} (already exists)")
            skipped_count += 1
            continue
        
        print(f"Importing {theme_name}...")
        mantra_data = import_ontology(ontology_file.name)
        
        if mantra_data and mantra_data["mantras"]:
            # Save as draft if it's a new theme
            if not output_file.exists():
                output_file = OUTPUT_PATH / f"{theme_name}.json.draft"
            
            with open(output_file, 'w') as f:
                json.dump(mantra_data, f, indent=2)
            
            print(f"  ✓ Imported {len(mantra_data['mantras'])} mantras")
            imported_count += 1
        else:
            print(f"  ✗ No mantras found or error occurred")
    
    print(f"\nImport complete!")
    print(f"  - Imported: {imported_count} themes")
    print(f"  - Skipped: {skipped_count} themes (already exist)")
    print(f"\nNew themes are saved as .draft files for review before activation.")

if __name__ == "__main__":
    main()
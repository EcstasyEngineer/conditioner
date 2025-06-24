#!/usr/bin/env python3
"""
Review and list all available mantra themes.
Shows both active themes and draft themes.
"""

import json
from pathlib import Path
from collections import defaultdict

THEMES_PATH = Path("../mantras/themes")

def load_theme(filepath):
    """Load a theme file and return its data."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath.name}: {e}")
        return None

def main():
    """List all themes and their statistics."""
    active_themes = []
    draft_themes = []
    
    # Gather all theme files
    for theme_file in sorted(THEMES_PATH.glob("*.json*")):
        if theme_file.suffix == ".draft":
            draft_themes.append(theme_file)
        elif theme_file.suffix == ".json":
            active_themes.append(theme_file)
    
    print("="*80)
    print("MANTRA THEME INVENTORY")
    print("="*80)
    
    # Active themes
    print(f"\n## ACTIVE THEMES ({len(active_themes)} total)\n")
    difficulty_counts = defaultdict(int)
    
    for theme_file in active_themes:
        theme_data = load_theme(theme_file)
        if theme_data:
            theme_name = theme_data.get("theme", theme_file.stem)
            mantra_count = len(theme_data.get("mantras", []))
            
            # Count difficulties
            difficulties = defaultdict(int)
            for mantra in theme_data.get("mantras", []):
                difficulties[mantra.get("difficulty", "unknown")] += 1
            
            diff_str = ", ".join([f"{d}: {c}" for d, c in difficulties.items()])
            
            print(f"  • {theme_name:<20} - {mantra_count:3d} mantras ({diff_str})")
            
            # Add to totals
            for diff, count in difficulties.items():
                difficulty_counts[diff] += count
    
    print(f"\n  TOTAL ACTIVE MANTRAS: {sum(difficulty_counts.values())}")
    print(f"    Basic: {difficulty_counts.get('basic', 0)}")
    print(f"    Intermediate: {difficulty_counts.get('intermediate', 0)}")
    print(f"    Advanced: {difficulty_counts.get('advanced', 0)}")
    
    # Draft themes
    print(f"\n## DRAFT THEMES ({len(draft_themes)} total)\n")
    draft_mantras_total = 0
    
    for theme_file in draft_themes:
        theme_data = load_theme(theme_file)
        if theme_data:
            theme_name = theme_data.get("theme", theme_file.stem.replace('.json', ''))
            mantra_count = len(theme_data.get("mantras", []))
            draft_mantras_total += mantra_count
            
            # Check if imported
            imported_from = theme_data.get("metadata", {}).get("imported_from", "manual")
            
            print(f"  • {theme_name:<20} - {mantra_count:3d} mantras (source: {imported_from})")
    
    print(f"\n  TOTAL DRAFT MANTRAS: {draft_mantras_total}")
    
    # Summary
    print("\n" + "="*80)
    print("ACTIVATION INSTRUCTIONS")
    print("="*80)
    print("\nTo activate a draft theme, remove the .draft extension:")
    print("  mv mantras/themes/THEME_NAME.json.draft mantras/themes/THEME_NAME.json")
    print("\nTo activate all draft themes at once:")
    print("  for f in mantras/themes/*.json.draft; do mv \"$f\" \"${f%.draft}\"; done")
    print("\nMake sure to review the content before activation!")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Import mantras from subspace-studio format with deduplication and proper formatting.
Handles combinatorial explosion from subject/dominant variations.
"""
import json
import sys
from pathlib import Path
from collections import defaultdict
import re

def normalize_mantra_text(text, is_identity_theme=True):
    """Normalize mantra text for deduplication and convert to conditioner format."""
    # Replace dominants with {controller}
    text = text.replace("Master's", "{controller}'s")
    text = text.replace("Mistress's", "{controller}'s")
    text = text.replace("Master", "{controller}")
    text = text.replace("Mistress", "{controller}")
    
    # For identity themes, avoid third person
    if is_identity_theme:
        # Replace "Bambi" variations with first person or identity reference
        text = text.replace("Bambi's", "my")
        text = text.replace("Bambi is", "I am")
        text = text.replace("Bambi has", "I have")
        text = text.replace("Bambi does", "I do")
        text = text.replace("Bambi feels", "I feel")
        text = text.replace("Bambi", "this doll")
    
    return text

def create_dedup_key(mantra, is_identity_theme=True):
    """Create a key for deduplication that ignores subject/dominant variations."""
    text = mantra.get("line", "")
    
    # Normalize for comparison
    text = text.lower()
    text = re.sub(r"\bmaster'?s?\b", "[DOM]", text)
    text = re.sub(r"\bmistress'?s?\b", "[DOM]", text)
    
    if is_identity_theme:
        # Normalize subject variations
        text = re.sub(r"\bbambi'?s?\b", "[SUBJ]", text)
        text = re.sub(r"\bi\b", "[SUBJ]", text)
        text = re.sub(r"\bmy\b", "[SUBJ]", text)
        text = re.sub(r"\bme\b", "[SUBJ]", text)
    
    return text

def select_best_variant(variants, is_identity_theme=True):
    """Select the best variant from duplicates based on our criteria."""
    # Priority order:
    # 1. Has dominant reference (more dynamic)
    # 2. First person (subject=None) over third person
    # 3. Longer text (usually more complete)
    
    scored_variants = []
    for v in variants:
        score = 0
        text = v.get("line", "")
        
        # Bonus for dominant reference
        if v.get("dominant") is not None:
            score += 100
            
        # Bonus for first person (subject=None) in identity themes
        if is_identity_theme and v.get("subject") is None:
            score += 50
        elif not is_identity_theme and v.get("subject") is not None:
            score += 50
            
        # Small bonus for text length
        score += len(text) / 100
        
        scored_variants.append((score, v))
    
    # Return highest scoring variant
    scored_variants.sort(key=lambda x: x[0], reverse=True)
    return scored_variants[0][1]

def convert_difficulty(subspace_difficulty):
    """Convert subspace difficulty to conditioner format."""
    mapping = {
        "BASIC": "basic",
        "LIGHT": "light", 
        "MODERATE": "moderate",
        "DEEP": "deep",
        "EXTREME": "extreme"
    }
    return mapping.get(subspace_difficulty, "moderate")

def assign_base_points(difficulty):
    """Assign base points based on difficulty."""
    points_map = {
        "basic": 12,      # 10-15 range
        "light": 25,      # 20-30 range
        "moderate": 40,   # 35-45 range
        "deep": 70,       # 60-80 range
        "extreme": 110    # 100-120 range
    }
    return points_map.get(difficulty, 40)

def process_theme(input_file, theme_name, description, is_identity_theme=True):
    """Process a theme file and return deduplicated mantras."""
    with open(input_file, 'r') as f:
        mantras = json.load(f)
    
    # Group mantras by normalized key for deduplication
    grouped = defaultdict(list)
    for mantra in mantras:
        key = create_dedup_key(mantra, is_identity_theme)
        grouped[key].append(mantra)
    
    # Select best variant from each group
    processed_mantras = []
    for key, variants in grouped.items():
        best = select_best_variant(variants, is_identity_theme)
        
        # Convert to conditioner format
        difficulty = convert_difficulty(best.get("difficulty", "MODERATE"))
        processed_mantra = {
            "text": normalize_mantra_text(best.get("line", ""), is_identity_theme),
            "difficulty": difficulty,
            "base_points": assign_base_points(difficulty)
        }
        processed_mantras.append(processed_mantra)
    
    # Calculate statistics
    all_points = [m["base_points"] for m in processed_mantras]
    base_difficulty = sum(all_points) / len(all_points) if all_points else 0
    variance = sum((p - base_difficulty) ** 2 for p in all_points) / len(all_points) if all_points else 0
    
    # Create theme object
    theme = {
        "theme": theme_name,
        "description": description,
        "base_difficulty": round(base_difficulty, 1),
        "variance": round(variance, 1),
        "mantras": processed_mantras
    }
    
    return theme

def main():
    # Theme configurations
    themes_to_import = {
        "doll": {
            "file": "../../subspace-studio/hypnosis/mantras/Identity/Doll.json",
            "description": "Transform into a perfect, beautiful doll focused on appearance and obedience",
            "is_identity": True
        },
        "feminine": {
            "file": "../../subspace-studio/hypnosis/mantras/Personality/Feminine.json", 
            "description": "Embrace feminine energy, grace, and beauty in all aspects",
            "is_identity": True
        },
        "gaslighting": {
            "file": "../../subspace-studio/hypnosis/mantras/Ds/Gaslighting.json",
            "description": "Reality manipulation and mental confusion dynamics",
            "is_identity": False
        },
        "mindbreak": {
            "file": "../../subspace-studio/hypnosis/mantras/Hypnosis/Mindbreak.json",
            "description": "Complete mental surrender and cognitive dissolution", 
            "is_identity": True
        },
        "relaxation": {
            "file": "../../subspace-studio/hypnosis/mantras/Hypnosis/Relaxation.json",
            "description": "Deep relaxation, trance, and peaceful surrender",
            "is_identity": False
        },
        "slave": {
            "file": "../../subspace-studio/hypnosis/mantras/Identity/Slave.json",
            "description": "Total submission and ownership dynamics",
            "is_identity": True
        }
    }
    
    for theme_name, config in themes_to_import.items():
        print(f"Processing {theme_name}...")
        
        theme_data = process_theme(
            config["file"],
            theme_name,
            config["description"],
            config["is_identity"]
        )
        
        # Save to draft file
        output_file = f"../mantras/themes/{theme_name}.json.draft"
        with open(output_file, 'w') as f:
            json.dump(theme_data, f, indent=2)
        
        print(f"  Original mantras: {len(json.load(open(config['file'])))}")
        print(f"  Deduplicated mantras: {len(theme_data['mantras'])}")
        print(f"  Reduction: {100 - (len(theme_data['mantras']) / len(json.load(open(config['file']))) * 100):.1f}%")
        print(f"  Saved to: {output_file}")
        print()

if __name__ == "__main__":
    main()
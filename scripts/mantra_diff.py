#!/usr/bin/env python3
"""
Compare mantras between current and historical git versions.
Shows what was added, removed, and modified.

Usage:
    python3 scripts/mantra_diff.py mantras/brainwashing.json [git-ref]
    
    git-ref defaults to HEAD~10 or can be a commit hash, branch, or tag
"""

import json
import subprocess
import sys
from pathlib import Path


def get_git_file(filepath: str, ref: str) -> str | None:
    """Get file contents from a git ref."""
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{filepath}"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return None


def extract_mantras(json_content: str) -> dict[str, dict]:
    """Extract mantras as {text: full_mantra_obj} dict."""
    data = json.loads(json_content)
    return {m["text"]: m for m in data.get("mantras", [])}


def normalize_text(text: str) -> str:
    """Normalize mantra text for comparison (strip periods, lowercase)."""
    return text.rstrip(".").rstrip("—").strip().lower()


def find_similar(text: str, candidates: dict[str, dict], threshold: float = 0.8) -> str | None:
    """Find similar mantra text (for detecting revisions)."""
    norm_text = normalize_text(text)
    for candidate in candidates:
        norm_candidate = normalize_text(candidate)
        # Simple word overlap ratio
        words1 = set(norm_text.split())
        words2 = set(norm_candidate.split())
        if not words1 or not words2:
            continue
        overlap = len(words1 & words2) / max(len(words1), len(words2))
        if overlap >= threshold:
            return candidate
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/mantra_diff.py <theme.json> [git-ref]")
        print("Example: python3 scripts/mantra_diff.py mantras/brainwashing.json bc65835")
        sys.exit(1)
    
    filepath = sys.argv[1]
    ref = sys.argv[2] if len(sys.argv) > 2 else "HEAD~10"
    
    # Get current version
    current_path = Path(filepath)
    if not current_path.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)
    
    current_content = current_path.read_text()
    current_mantras = extract_mantras(current_content)
    
    # Get old version
    old_content = get_git_file(filepath, ref)
    if old_content is None:
        print(f"Error: Could not get {filepath} at ref {ref}")
        sys.exit(1)
    
    old_mantras = extract_mantras(old_content)
    
    # Set arithmetic
    current_texts = set(current_mantras.keys())
    old_texts = set(old_mantras.keys())
    
    added = current_texts - old_texts
    removed = old_texts - current_texts
    unchanged = current_texts & old_texts
    
    # Check for revisions (similar text that changed)
    revised = []
    truly_removed = []
    truly_added = list(added)
    
    for old_text in removed:
        similar = find_similar(old_text, {t: current_mantras[t] for t in added})
        if similar:
            revised.append((old_text, similar))
            truly_added.remove(similar)
        else:
            truly_removed.append(old_text)
    
    # Check for score changes
    score_changes = []
    for text in unchanged:
        old_pts = old_mantras[text].get("base_points", 0)
        new_pts = current_mantras[text].get("base_points", 0)
        if old_pts != new_pts:
            score_changes.append((text, old_pts, new_pts))
    
    # Output
    theme = json.loads(current_content).get("theme", "unknown")
    print(f"=" * 60)
    print(f"MANTRA DIFF: {theme.upper()}")
    print(f"Comparing: {ref} → HEAD")
    print(f"=" * 60)
    print()
    
    print(f"Old count: {len(old_mantras)}")
    print(f"New count: {len(current_mantras)}")
    print(f"Net change: {len(current_mantras) - len(old_mantras):+d}")
    print()
    
    if truly_removed:
        print(f"REMOVED ({len(truly_removed)}):")
        print("-" * 40)
        for text in sorted(truly_removed):
            pts = old_mantras[text].get("base_points", "?")
            print(f"  - [{pts}] {text}")
        print()
    
    if truly_added:
        print(f"ADDED ({len(truly_added)}):")
        print("-" * 40)
        for text in sorted(truly_added):
            pts = current_mantras[text].get("base_points", "?")
            print(f"  + [{pts}] {text}")
        print()
    
    if revised:
        print(f"REVISED ({len(revised)}):")
        print("-" * 40)
        for old_text, new_text in revised:
            old_pts = old_mantras[old_text].get("base_points", "?")
            new_pts = current_mantras[new_text].get("base_points", "?")
            print(f"  ~ [{old_pts}→{new_pts}]")
            print(f"    OLD: {old_text}")
            print(f"    NEW: {new_text}")
        print()
    
    if score_changes:
        print(f"RESCORED ({len(score_changes)}):")
        print("-" * 40)
        for text, old_pts, new_pts in sorted(score_changes, key=lambda x: x[2] - x[1], reverse=True):
            diff = new_pts - old_pts
            print(f"  [{old_pts}→{new_pts}] ({diff:+d}) {text}")
        print()
    
    # Summary
    unchanged_no_rescore = len(unchanged) - len(score_changes)
    print(f"SUMMARY:")
    print(f"  Removed:   {len(truly_removed)}")
    print(f"  Added:     {len(truly_added)}")
    print(f"  Revised:   {len(revised)}")
    print(f"  Rescored:  {len(score_changes)}")
    print(f"  Unchanged: {unchanged_no_rescore}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Generate blind test batches for Opus validation.

Reusable script for validating:
- Response messages (tier/subject accuracy, tone)
- Mantra texts (difficulty/theme accuracy, psychological impact)

Usage:
    python generate_blind_tests.py --type responses
    python generate_blind_tests.py --type mantras --theme obedience
    python generate_blind_tests.py --type mantras --all-themes
"""

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# PROMPT TEMPLATES - Edit these for different validation tasks
# ============================================================================

PROMPTS = {
    "responses": {
        "description": "Response message tier/subject validation",
        "context": """You are analyzing a response message from a conditioning/training system.

Response tiers (based on how quickly user responded):
- Tier 0 (Eager): <30s. Strong positive, enthusiastic.
- Tier 1 (Quick): 30s-2min. Good positive, solid praise.
- Tier 2 (Normal): 2min-30min. Acknowledgment, affirming.
- Tier 3 (Neutral): 30min+. Neutral acknowledgment, clinical.

Subject archetypes: pet, kitten, puppy, doll, drone, toy, puppet, slave, bimbo, slut.

Key psychological notes:
- Drone: ONLY subject where warmth is inappropriate. Clinical/technical language only.
- Bimbo: "empty head" language, gendered "good girl" praise, enthusiastic.
- Puppet: Strings/control imagery, guided motion.
- Pet family (pet/kitten/puppy): Warmth, affection, training.
- Slave: Service, duty, hierarchy.""",

        "task": """Analyze this message:
"{text}"

Respond with JSON:
{{
  "tier": <0-3>,
  "plausible_tiers": [<all tiers this could work for>],
  "subjects": [<all subjects this could work for>],
  "confidence": "high/medium/low",
  "quality": "keep/revise/remove",
  "quality_reasoning": "brief explanation of quality rating",
  "reasoning": "brief explanation of tier/subject choices"
}}

Quality criteria:
- keep: Natural, appropriate, good energy for tier
- revise: Right idea but awkward phrasing or slightly off energy
- remove: Cringe, inappropriate, or fundamentally doesn't work"""
    },

    "mantras": {
        "description": "Mantra text blind validation",
        "context": """You are analyzing mantras/affirmations from a conditioning/hypnosis system.

These mantras use placeholders:
- {subject}: The submissive's pet name (e.g., "toy", "puppet", "pet")
- {controller}: The dominant's title (e.g., "Master", "Goddess", "Owner")

Difficulty tiers (based on psychological intensity and internalization difficulty):
- basic (10-19 pts): Gentle introduction. Safe, deniable. "I'm just trying this."
- light (20-34 pts): Normalization. Growing comfort. "This is nice."
- moderate (35-59 pts): Identity integration. "This is who I am becoming."
- deep (60-99 pts): Core psychological rewrite. "This is who I am."
- extreme (100+ pts): Permanence and totality. "This is who I will always be."

Point scoring heuristics (additive from base 10):
- {controller} present: +15
- {subject} present: +5 (or +20 if both)
- Permanence language (forever, irreversible, permanent): +30
- Absolutism (nothing but, only exist to, completely): +15
- Identity statements (I am, defines me, my nature): +10
- Core/depth language (saturated, consumed, fundamental): +15
- Mechanism language (rewires, programs, installs): +10
- Sensory/visceral (aches, burns, melts, dissolves): +5
- Agency removal (cannot, impossible, unthinkable): +10

Themes (infer from content, may fit multiple):
- acceptance: Surrender, releasing resistance, peaceful compliance
- addiction: Craving, compulsion, escalating dependence
- amnesia: Memory dissolution, forgetting, mental fog
- suggestibility: Openness, absorption, receptivity to commands
- brainwashing: Systematic reprogramming, conditioning cycles
- obedience: Instant compliance, reflexive execution
- blank: Empty-mindedness, thoughtless receptivity
- puppet: External control, strings imagery, guided movement
- slave: Ownership, service, existence for another's benefit
- helplessness: Vulnerability, powerlessness, safety in surrender
- bimbo: Playful simplification, pretty-minded bliss
- devotion: Unwavering loyalty, dedicated service""",

        "task": """Analyze this mantra (you do NOT know its intended theme or difficulty):
"{text}"

Estimate what this mantra's score would be using the heuristics, then derive difficulty.

Respond with JSON:
{{
  "estimated_points": <number>,
  "point_breakdown": "brief breakdown of which markers you detected",
  "difficulty": "basic/light/moderate/deep/extreme",
  "themes": [<primary theme>, <secondary themes if applicable>],
  "psychological_impact": 1-5,
  "quality": "keep/revise/remove",
  "issues": ["list any problems: awkward phrasing, wrong intensity, tells-not-shows, etc."],
  "revision_suggestion": "if quality is 'revise', suggest improved text (or null)"
}}

Quality criteria:
- keep: Shows psychological experience (not just labels), natural phrasing, appropriate intensity
- revise: Right idea but has fixable issues
- remove: Fundamentally ineffective, cringe, or broken"""
    }
}


# ============================================================================
# DATA LOADERS
# ============================================================================

def load_response_messages():
    """Load response messages from MESSAGE_POOL."""
    from utils.response_messages import MESSAGE_POOL

    # Extract subject-specific messages (exclude "ALL" tagged ones for focused testing)
    messages = [
        {
            "msg_id": i,
            "text": msg["text"],
            "tier": msg["tier"],
            "subjects": msg["subjects"]
        }
        for i, msg in enumerate(MESSAGE_POOL)
        if "ALL" not in msg["subjects"]
    ]
    return messages


def load_mantras(theme=None, all_themes=False):
    """Load mantras from theme JSON files."""
    mantras_dir = Path(__file__).parent.parent / "mantras"
    messages = []
    msg_id = 0

    if all_themes:
        theme_files = list(mantras_dir.glob("*.json"))
    elif theme:
        theme_files = [mantras_dir / f"{theme}.json"]
    else:
        raise ValueError("Must specify --theme or --all-themes")

    for theme_file in theme_files:
        if not theme_file.exists():
            print(f"Warning: {theme_file} not found, skipping")
            continue

        with open(theme_file) as f:
            data = json.load(f)

        theme_name = data.get("theme", theme_file.stem)

        for mantra in data.get("mantras", []):
            messages.append({
                "msg_id": msg_id,
                "text": mantra["text"],
                "difficulty": mantra.get("difficulty", "unknown"),
                "theme": theme_name,
                "base_points": mantra.get("base_points", 0)
            })
            msg_id += 1

    return messages


# ============================================================================
# BATCH GENERATION
# ============================================================================

def generate_batches(messages, replicas=3, batch_size=15):
    """Generate randomized test batches."""
    # Replicate for reliability
    test_pool = messages * replicas
    random.shuffle(test_pool)

    # Split into batches
    batches = []
    for i in range(0, len(test_pool), batch_size):
        batch = test_pool[i:i+batch_size]
        batches.append({
            "batch_id": len(batches) + 1,
            "messages": batch
        })

    return batches


def verify_coverage(batches, messages, replicas):
    """Verify each message appears exactly N times."""
    msg_id_counts = {}
    for batch in batches:
        for msg in batch["messages"]:
            msg_id = msg["msg_id"]
            msg_id_counts[msg_id] = msg_id_counts.get(msg_id, 0) + 1

    errors = [msg_id for msg_id, count in msg_id_counts.items() if count != replicas]
    if errors:
        print(f"WARNING: Messages not appearing exactly {replicas}x: {errors}")
        return False
    return True


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate blind test batches for Opus validation")
    parser.add_argument("--type", choices=["responses", "mantras"], required=True,
                        help="Type of content to validate")
    parser.add_argument("--theme", help="Specific mantra theme to test")
    parser.add_argument("--all-themes", action="store_true", help="Test all mantra themes")
    parser.add_argument("--replicas", type=int, default=3,
                        help="Times each message is tested (default: 3)")
    parser.add_argument("--batch-size", type=int, default=15,
                        help="Messages per batch (default: 15)")
    parser.add_argument("--output", help="Output file (default: {type}_test_batches.json)")

    args = parser.parse_args()

    # Load data
    print(f"Loading {args.type}...")
    if args.type == "responses":
        messages = load_response_messages()
    else:
        messages = load_mantras(theme=args.theme, all_themes=args.all_themes)

    print(f"Loaded {len(messages)} messages")

    # Generate batches
    batches = generate_batches(messages, replicas=args.replicas, batch_size=args.batch_size)
    print(f"Created {len(batches)} batches of ~{args.batch_size} messages each")

    # Verify coverage
    if verify_coverage(batches, messages, args.replicas):
        print(f"✓ Verified: All messages appear exactly {args.replicas}x")

    # Get prompt template
    prompt = PROMPTS[args.type]

    # Build output
    output = {
        "metadata": {
            "type": args.type,
            "total_messages": len(messages),
            "total_tests": len(messages) * args.replicas,
            "replicas": args.replicas,
            "batch_size": args.batch_size
        },
        "prompt": {
            "description": prompt["description"],
            "context": prompt["context"],
            "task": prompt["task"]
        },
        "batches": batches
    }

    if args.type == "mantras":
        output["metadata"]["theme"] = args.theme or "all"

    # Save
    output_file = args.output or f"scripts/{args.type}_test_batches.json"
    output_path = Path(__file__).parent.parent / output_file
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved to: {output_path}")
    print(f"\nBatch distribution:")
    for batch in batches[:5]:
        print(f"  Batch {batch['batch_id']}: {len(batch['messages'])} messages")
    if len(batches) > 5:
        print(f"  ... and {len(batches) - 5} more batches")

    # Print example
    print(f"\nExample - Batch 1 (first 3 messages):")
    for msg in batches[0]["messages"][:3]:
        text_preview = msg['text'][:50] + "..." if len(msg['text']) > 50 else msg['text']
        if args.type == "responses":
            print(f"  [{msg['msg_id']}] T{msg['tier']}: \"{text_preview}\"")
        else:
            print(f"  [{msg['msg_id']}] {msg['difficulty']}: \"{text_preview}\"")

    print(f"\n--- PROMPT TEMPLATE ---")
    print(f"Context: {prompt['context'][:200]}...")
    print(f"\nTask template ready for Opus blind validation.")


if __name__ == "__main__":
    main()

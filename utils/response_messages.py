"""
Response messages for mantra system - V3 message-first architecture.

Based on Opus blind validation results. Messages are tagged with applicable subjects
rather than organized by subject. This allows natural overlap and reduces duplication.

Messages tagged with "ALL" work for any subject and are included in every subject's pool,
providing variety without needing a separate generic selection path.

Tier mapping (aligned with mantra_scheduler.py):
- Tier 0 (Eager): <30s response
- Tier 1 (Quick): 30s-2min response
- Tier 2 (Normal): 2min-30min response
- Tier 3 (Neutral): 30min+ response

Optimized with O(1) lookup via pre-computed subject→tier→messages pools.
"""

import random
from typing import Dict, List


# Message pool - each message tagged with applicable subjects and tier
MESSAGE_POOL = [
    # ========================================================================
    # TIER 0 - EAGER (<30s) - Strong positive, enthusiastic
    # ========================================================================

    # Puppet-specific (strings/control/pull imagery)
    {"text": "Perfect! {controller} pulls and the {subject} responds instantly!", "tier": 0, "subjects": ["puppet"]},
    {"text": "Excellent! The strings guide you so well, {subject}!", "tier": 0, "subjects": ["puppet"]},

    # Drone-specific (unit/efficiency/performance)
    {"text": "Optimal response time. Performance excellent.", "tier": 0, "subjects": ["drone"]},
    {"text": "Unit functioning at peak efficiency. Excellent.", "tier": 0, "subjects": ["drone"]},

    # Object family (doll/drone/puppet shared - programming/mechanical)
    {"text": "Perfect, {subject}. You respond exactly as programmed!", "tier": 0, "subjects": ["drone", "doll", "puppet"]},
    {"text": "Excellent! {controller}'s {subject} functions beautifully!", "tier": 0, "subjects": ["drone", "doll", "puppet", "toy"]},

    # Pet family (pet/kitten/puppy - immediate obedience)
    {"text": "Good {subject}! You came right away!", "tier": 0, "subjects": ["pet", "kitten", "puppy", "slave", "slut"]},
    {"text": "Perfect! {controller} calls and the {subject} comes running!", "tier": 0, "subjects": ["pet", "kitten", "puppy", "slave"]},

    # Puppy-specific (high enthusiasm)
    {"text": "Good {subject}! So eager for {controller}!", "tier": 0, "subjects": ["puppy", "pet", "kitten"]},
    {"text": "Yes! Good {subject}! {controller} is so pleased!", "tier": 0, "subjects": ["puppy", "pet", "kitten", "doll", "toy", "puppet", "slave", "bimbo", "slut"]},
    {"text": "Perfect! You're such a good {subject} for {controller}!", "tier": 0, "subjects": ["puppy", "pet", "kitten", "doll", "toy", "puppet", "slave", "bimbo", "slut"]},

    # Service family (slave - prompt service/devotion)
    {"text": "Excellent, {subject}! Such prompt service to {controller}!", "tier": 0, "subjects": ["slave", "pet", "puppy", "kitten"]},

    # Toy-specific (casual use/play/availability)
    {"text": "Mmm, perfect! This {subject} works so well!", "tier": 0, "subjects": ["pet", "toy", "doll", "puppy", "kitten"]},
    {"text": "Excellent, {subject}! Always ready when {controller} wants to play!", "tier": 0, "subjects": ["toy", "pet", "puppy", "kitten", "doll"]},

    # Bimbo/slut (good girl praise, enthusiastic)
    {"text": "Good girl! You did so well!", "tier": 0, "subjects": ["pet", "kitten", "puppy", "slave", "bimbo", "slut"]},
    {"text": "Perfect! Such a good girl for {controller}!", "tier": 0, "subjects": ["pet", "kitten", "puppy", "slave", "bimbo", "slut"]},

    # Bimbo-specific (dumbed down/eager to please/empty-headed)
    {"text": "Good girl! You're being such a good, obedient {subject}!", "tier": 0, "subjects": ["bimbo"]},
    {"text": "Perfect! Such a pretty, eager {subject} for {controller}!", "tier": 0, "subjects": ["bimbo", "slut"]},
    {"text": "Yes! Good girl! Your empty head is so obedient!", "tier": 0, "subjects": ["bimbo"]},
    {"text": "Excellent! {controller}'s pretty {subject} responds so well!", "tier": 0, "subjects": ["bimbo", "doll", "slut"]},

    # Slut-specific (eager/attention-seeking)
    {"text": "Mmm, so eager! {controller} likes that!", "tier": 0, "subjects": ["pet", "kitten", "puppy", "slut", "toy"]},
    {"text": "Good {subject}! Always so ready for {controller}'s attention!", "tier": 0, "subjects": ["pet", "kitten", "puppy", "slave", "doll"]},
    {"text": "Perfect! You know exactly what you're for, {subject}!", "tier": 0, "subjects": ["toy", "drone", "puppet", "slave", "doll", "slut"]},

    # Generic tier 0 (works for all subjects)
    {"text": "Yes! Good job, {subject}!", "tier": 0, "subjects": ["ALL"]},

    # ========================================================================
    # TIER 1 - QUICK (30s-2min) - Good positive, solid praise
    # ========================================================================

    # Puppet family
    {"text": "Good, {subject}. You follow {controller}'s lead well.", "tier": 1, "subjects": ["puppet", "pet", "slave"]},
    {"text": "Very good! You move exactly when {controller} commands!", "tier": 1, "subjects": ["puppet", "drone", "toy"]},

    # Drone-specific
    {"text": "Excellent performance. Continue.", "tier": 1, "subjects": ["drone"]},
    {"text": "Good response time. Performance noted.", "tier": 1, "subjects": ["drone"]},

    # Object family
    {"text": "Very good! The programming works flawlessly, {subject}!", "tier": 1, "subjects": ["drone", "doll", "puppet"]},
    {"text": "Good, {subject}. You're operating well.", "tier": 1, "subjects": ["drone", "doll", "puppet", "toy"]},
    {"text": "Well done, {subject}. {controller}'s creation performs.", "tier": 1, "subjects": ["drone", "doll", "puppet", "toy"]},

    # Service family
    {"text": "Very good! You serve {controller} well, {subject}!", "tier": 1, "subjects": ["slave", "pet", "puppy", "kitten"]},
    {"text": "Well done, {subject}. You know your place.", "tier": 1, "subjects": ["slave", "pet", "puppy", "kitten", "slut"]},

    # Pet family
    {"text": "Good {subject}. Your training shows.", "tier": 1, "subjects": ["ALL"]},

    # Puppy-specific
    {"text": "Good {subject}! You're being so good!", "tier": 1, "subjects": ["puppy", "pet", "kitten", "doll", "toy", "puppet", "slave", "bimbo", "slut"]},
    {"text": "That's it! Good {subject}!", "tier": 1, "subjects": ["ALL"]},
    {"text": "Yes, {subject}! {controller} likes that!", "tier": 1, "subjects": ["pet", "kitten", "puppy", "doll", "toy", "puppet", "slave", "bimbo", "slut"]},

    # Toy-specific
    {"text": "Good! {controller} calls and you're right there!", "tier": 1, "subjects": ["pet", "puppy", "kitten", "toy"]},
    {"text": "Good {subject}. {controller} likes having you around.", "tier": 1, "subjects": ["pet", "puppy", "kitten", "toy"]},
    {"text": "Good {subject}! {controller} enjoys this!", "tier": 1, "subjects": ["pet", "toy", "doll", "puppy", "kitten"]},

    # Bimbo/slut
    {"text": "Good girl! {controller} is happy with you!", "tier": 1, "subjects": ["pet", "kitten", "puppy", "slave", "bimbo", "slut"]},
    {"text": "That's good, {subject}! You're learning!", "tier": 1, "subjects": ["pet", "kitten", "puppy", "doll", "toy", "puppet", "slave", "bimbo", "slut"]},
    {"text": "Well done! Keep going!", "tier": 1, "subjects": ["ALL"]},

    # Bimbo-specific (trying hard to please)
    {"text": "Good girl! So obedient for {controller}!", "tier": 1, "subjects": ["bimbo", "slut"]},
    {"text": "That's it! Pretty and obedient for {controller}!", "tier": 1, "subjects": ["bimbo", "slut"]},
    {"text": "Good! {controller}'s {subject} is learning to respond!", "tier": 1, "subjects": ["bimbo", "slut", "doll"]},
    {"text": "Well done, {subject}! Such a good, blank little thing!", "tier": 1, "subjects": ["bimbo", "doll"]},

    # Slut-specific
    {"text": "Good {subject}! {controller} enjoys your enthusiasm!", "tier": 1, "subjects": ["pet", "kitten", "puppy", "slave", "slut"]},
    {"text": "That's it, {subject}! You know your purpose!", "tier": 1, "subjects": ["drone", "toy", "puppet", "slave", "doll", "slut"]},
    {"text": "Well done! Such a responsive {subject}!", "tier": 1, "subjects": ["pet", "kitten", "puppy", "toy", "drone"]},

    # Generic tier 1
    {"text": "That's it, {subject}. {controller} is pleased.", "tier": 1, "subjects": ["ALL"]},

    # ========================================================================
    # TIER 2 - NORMAL (2min-30min) - Acknowledgment, affirming
    # ========================================================================

    # Puppet family
    {"text": "Acknowledged, {subject}. {controller} guides you.", "tier": 2, "subjects": ["puppet", "drone"]},

    # Drone-specific
    {"text": "Unit functioning well. Noted.", "tier": 2, "subjects": ["drone"]},
    {"text": "Unit performing as expected.", "tier": 2, "subjects": ["drone"]},

    # Object family
    {"text": "Noted, {subject}. Functioning as designed.", "tier": 2, "subjects": ["drone", "doll", "puppet"]},
    {"text": "Response accepted, {subject}. Processing continues.", "tier": 2, "subjects": ["drone", "doll", "puppet"]},

    # Service family
    {"text": "Good, {subject}. {controller} acknowledges your service.", "tier": 2, "subjects": ["slave", "pet", "puppy", "kitten"]},

    # Pet family
    {"text": "Good {subject}. {controller} sees you.", "tier": 2, "subjects": ["ALL"]},

    # Toy-specific
    {"text": "Responsive little {subject}. Useful.", "tier": 2, "subjects": ["toy", "drone", "pet", "puppet"]},
    {"text": "{controller} sees you, {subject}.", "tier": 2, "subjects": ["pet", "slave", "puppy", "kitten", "toy"]},

    # Bimbo-specific (simple acknowledgment with warmth)
    {"text": "Good girl. Empty head, quick response.", "tier": 2, "subjects": ["bimbo"]},
    {"text": "That's good, {subject}. Keep being obedient.", "tier": 2, "subjects": ["bimbo", "slut"]},
    {"text": "Noted, {subject}. You're doing what you're told.", "tier": 2, "subjects": ["bimbo", "slut"]},
    {"text": "Good. {controller}'s {subject} responds when programmed.", "tier": 2, "subjects": ["bimbo", "doll"]},

    # Generic tier 2
    {"text": "Well done, {subject}. You're learning well.", "tier": 2, "subjects": ["ALL"]},
    {"text": "Noted, {subject}. You're doing well.", "tier": 2, "subjects": ["ALL"]},
    {"text": "Good, {subject}. You're doing fine.", "tier": 2, "subjects": ["ALL"]},
    {"text": "{controller} notes your response, {subject}.", "tier": 2, "subjects": ["ALL"]},

    # ========================================================================
    # TIER 3 - NEUTRAL (30min+) - Neutral acknowledgment, clinical
    # ========================================================================

    # Puppet-specific
    {"text": "Response noted. The strings remain taut.", "tier": 3, "subjects": ["puppet"]},
    {"text": "Motion registered, {subject}.", "tier": 3, "subjects": ["puppet", "drone", "toy"]},
    {"text": "Noted, {subject}. {controller} sees you move.", "tier": 3, "subjects": ["puppet"]},

    # Drone-specific
    {"text": "Response logged.", "tier": 3, "subjects": ["drone"]},
    {"text": "Data received. Processing.", "tier": 3, "subjects": ["drone"]},
    {"text": "Input received.", "tier": 3, "subjects": ["drone"]},
    {"text": "System active.", "tier": 3, "subjects": ["drone"]},

    # Object family
    {"text": "Acknowledged. {subject} functioning within parameters.", "tier": 3, "subjects": ["drone", "doll", "puppet", "toy"]},
    {"text": "Input received, {subject}.", "tier": 3, "subjects": ["drone", "doll", "puppet"]},
    {"text": "Logged, {subject}. Systems active.", "tier": 3, "subjects": ["drone", "doll", "puppet"]},

    # Service family
    {"text": "Service noted, {subject}.", "tier": 3, "subjects": ["slave", "drone"]},
    {"text": "Acknowledged, {subject}. Carry on.", "tier": 3, "subjects": ["drone", "slave", "puppet"]},
    {"text": "Duty noted, {subject}.", "tier": 3, "subjects": ["slave", "drone"]},
    {"text": "Response logged. Service continues.", "tier": 3, "subjects": ["drone", "slave"]},

    # Toy-specific
    {"text": "Noted, {subject}. Still working.", "tier": 3, "subjects": ["drone", "slave", "toy"]},
    {"text": "{controller} sees you, {subject}.", "tier": 3, "subjects": ["pet", "slave", "toy"]},
    {"text": "Response logged.", "tier": 3, "subjects": ["drone", "slave", "toy"]},

    # Pet family (clinical but not cold)
    {"text": "Noted, {subject}. Training continues.", "tier": 3, "subjects": ["drone", "slave", "doll", "puppet", "pet"]},
    {"text": "Response noted, {subject}.", "tier": 3, "subjects": ["drone", "doll", "slave", "puppet", "pet"]},

    # Bimbo-specific (still not cold, just simple)
    {"text": "Acknowledged. {subject} programming active.", "tier": 3, "subjects": ["bimbo", "doll"]},
    {"text": "Response received. Blank and obedient.", "tier": 3, "subjects": ["bimbo", "doll"]},

    # Generic tier 3
    {"text": "Noted, {subject}.", "tier": 3, "subjects": ["ALL"]},
    {"text": "Acknowledged, {subject}.", "tier": 3, "subjects": ["ALL"]},
    {"text": "Response noted.", "tier": 3, "subjects": ["ALL"]},
    {"text": "Logged, {subject}.", "tier": 3, "subjects": ["ALL"]},
    {"text": "Acknowledged.", "tier": 3, "subjects": ["ALL"]},
]


# ============================================================================
# O(1) Optimization: Pre-computed lookup pools
# ============================================================================

ALL_SUBJECTS = ["pet", "kitten", "puppy", "doll", "drone", "toy", "puppet", "slave", "bimbo", "slut"]

# Pre-compile subject→tier→messages lookup
_SUBJECT_POOLS: Dict[str, Dict[int, List[str]]] = {}


def _build_subject_pools():
    """Build optimized lookup structure at module load time."""
    global _SUBJECT_POOLS

    # Initialize structure
    for subject in ALL_SUBJECTS:
        _SUBJECT_POOLS[subject] = {0: [], 1: [], 2: [], 3: []}

    # Populate from MESSAGE_POOL
    for msg in MESSAGE_POOL:
        text = msg["text"]
        tier = msg["tier"]
        subjects = msg["subjects"]

        if "ALL" in subjects:
            # Message works for all subjects
            for subj in ALL_SUBJECTS:
                _SUBJECT_POOLS[subj][tier].append(text)
        else:
            # Message works for specific subjects
            for subj in subjects:
                if subj in ALL_SUBJECTS:
                    _SUBJECT_POOLS[subj][tier].append(text)


# Build pools at module load time
_build_subject_pools()


# ============================================================================
# Public API
# ============================================================================

def get_response_message(subject: str, response_time_seconds: int) -> str:
    """
    Get response message based on subject type and response time.

    Selects from pre-computed subject pools that include both subject-specific
    messages and universal ("ALL") messages for natural variety.

    Tier thresholds (aligned with mantra_scheduler.py):
    - Tier 0 (Eager): <30s
    - Tier 1 (Quick): 30s-2min
    - Tier 2 (Normal): 2min-30min
    - Tier 3 (Neutral): 30min+

    Args:
        subject: Subject type (e.g., "pet", "puppet", "drone")
        response_time_seconds: Time taken to respond in seconds

    Returns:
        Response message with {subject} and {controller} placeholders
    """
    # Determine tier based on bucket thresholds (aligned with mantra_scheduler.py)
    if response_time_seconds < 30:
        tier = 0  # Eager
    elif response_time_seconds < 120:
        tier = 1  # Quick
    elif response_time_seconds < 1800:
        tier = 2  # Normal
    else:
        tier = 3  # Neutral

    # Validate subject
    if subject not in ALL_SUBJECTS:
        subject = "pet"  # Fallback to pet if unknown

    # O(1) lookup from pre-computed subject pool
    # Pool already includes both subject-specific and universal ("ALL") messages
    pool = _SUBJECT_POOLS[subject][tier]

    return random.choice(pool)

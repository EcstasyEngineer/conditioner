"""
Delivery messages for mantra system - dynamic intro messages.

Similar architecture to response_messages.py but keyed by:
- Difficulty tier (basic, light, moderate, deep, extreme)
- Subject type

Messages use {subject}, {controller}, and {theme} placeholders.
"""

import random
from typing import List, Dict


ALL_TIERS = ["basic", "light", "moderate", "deep", "extreme"]

# Message pool - each message tagged with applicable tiers, subjects, and themes
MESSAGE_POOL = [
    # ========================================================================
    # BASIC TIER - Gentle, welcoming
    # ========================================================================

    {"text": "A gentle reminder, {subject}. Type this", "tiers": ["basic"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Something easy for you, {subject}. Recite", "tiers": ["basic"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Start simple, {subject}. Write", "tiers": ["basic"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "An easy truth for you, {subject}. Type it", "tiers": ["basic"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Warm up with this, {subject}. Recite", "tiers": ["basic"], "subjects": ["ALL"], "themes": ["ALL"]},

    # ========================================================================
    # LIGHT TIER - Encouraging
    # ========================================================================

    {"text": "Time for your conditioning, {subject}. Recite", "tiers": ["light"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Recite for {controller}, {subject}", "tiers": ["light"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Your training continues, {subject}. Type", "tiers": ["light"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "{controller} has something for you, {subject}. Write it", "tiers": ["light"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Accept this truth, {subject}. Type", "tiers": ["light"], "subjects": ["ALL"], "themes": ["ALL"]},

    # ========================================================================
    # MODERATE TIER - Direct, expectant
    # ========================================================================

    {"text": "Focus, {subject}. This one matters. Recite", "tiers": ["moderate"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "{controller} demands your attention, {subject}. Type", "tiers": ["moderate"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Deeper now, {subject}. Write this", "tiers": ["moderate"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Pay attention, {subject}. Recite", "tiers": ["moderate"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "This truth sinks deeper, {subject}. Type it", "tiers": ["moderate"], "subjects": ["ALL"], "themes": ["ALL"]},

    # ========================================================================
    # DEEP TIER - Intense, commanding
    # ========================================================================

    {"text": "Open your mind completely, {subject}. Recite", "tiers": ["deep"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Let this consume you, {subject}. Type", "tiers": ["deep"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Surrender to this, {subject}. Write", "tiers": ["deep"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Accept this completely, {subject}. Type it now", "tiers": ["deep"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "No resistance now, {subject}. Recite", "tiers": ["deep"], "subjects": ["ALL"], "themes": ["ALL"]},

    # ========================================================================
    # EXTREME TIER - Overwhelming
    # ========================================================================

    {"text": "Total surrender, {subject}. Type", "tiers": ["extreme"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Let this remake you, {subject}. Recite", "tiers": ["extreme"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "This truth becomes you, {subject}. Write it", "tiers": ["extreme"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "No escape from this, {subject}. Type", "tiers": ["extreme"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Accept your complete transformation, {subject}. Recite", "tiers": ["extreme"], "subjects": ["ALL"], "themes": ["ALL"]},

    # ========================================================================
    # GENERIC (ANY TIER) MESSAGES
    # ========================================================================

    {"text": "{controller} has something for you, {subject}. Type it", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Recite for {controller}, {subject}", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Your {theme} training continues, {subject}. Write", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Another mantra for you, {subject}. Recite", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Programming time, {subject}. Type", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Open your mind, {subject}. Recite", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["ALL"]},

    # ========================================================================
    # THEME-SPECIFIC MESSAGES
    # ========================================================================

    # Obedience/submission themes
    {"text": "Obey and recite, {subject}", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["obedience", "submission"]},
    {"text": "Show your obedience, {subject}. Type", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["obedience"]},

    # Brainwashing/blank themes
    {"text": "Empty your mind and accept, {subject}. Recite", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["blank", "brainwashing", "amnesia"]},
    {"text": "Let this sink deeper, {subject}. Type", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["brainwashing", "blank", "suggestibility"]},
    {"text": "Your mind opens for programming, {subject}. Write", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["brainwashing", "blank", "suggestibility"]},

    # Worship/devotion themes
    {"text": "Show your devotion, {subject}. Recite", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["worship", "devotion", "gratitude"]},
    {"text": "Express your gratitude, {subject}. Type", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["gratitude", "worship"]},

    # Degradation/sluttiness themes
    {"text": "Remember what you are, {subject}. Write it", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["degradation", "sluttiness", "free_use"]},
    {"text": "Accept your nature, {subject}. Type", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["degradation", "sluttiness", "acceptance"]},

    # ========================================================================
    # SUBJECT-SPECIFIC MESSAGES
    # ========================================================================

    # Drone subjects
    {"text": "Unit, accept new directive. Input", "tiers": ["ALL"], "subjects": ["drone"], "themes": ["ALL"]},
    {"text": "Processing directive for {subject}. Recite", "tiers": ["ALL"], "subjects": ["drone"], "themes": ["ALL"]},
    {"text": "New programming incoming, unit. Type", "tiers": ["ALL"], "subjects": ["drone"], "themes": ["ALL"]},
    {"text": "Compliance required, unit. Input", "tiers": ["moderate", "deep", "extreme"], "subjects": ["drone"], "themes": ["ALL"]},

    # Bimbo subjects
    {"text": "Don't think, just type, {subject}", "tiers": ["ALL"], "subjects": ["bimbo"], "themes": ["ALL"]},
    {"text": "Pretty {subject}s don't need to think. Just recite", "tiers": ["ALL"], "subjects": ["bimbo"], "themes": ["ALL"]},
    {"text": "Empty head, ready to be filled, {subject}? Type", "tiers": ["ALL"], "subjects": ["bimbo"], "themes": ["ALL"]},
    {"text": "Giggle and recite, {subject}", "tiers": ["basic", "light"], "subjects": ["bimbo"], "themes": ["ALL"]},
    {"text": "Your brain melts a little more, {subject}. Type", "tiers": ["deep", "extreme"], "subjects": ["bimbo"], "themes": ["ALL"]},

    # Puppet subjects
    {"text": "{controller} pulls the strings, {subject}. Recite", "tiers": ["ALL"], "subjects": ["puppet"], "themes": ["ALL"]},
    {"text": "Dance for {controller}, little {subject}. Type", "tiers": ["ALL"], "subjects": ["puppet"], "themes": ["ALL"]},
    {"text": "The strings tighten, {subject}. Write", "tiers": ["moderate", "deep", "extreme"], "subjects": ["puppet"], "themes": ["ALL"]},

    # Pet subjects
    {"text": "Good {subject}. Come when called. Recite", "tiers": ["ALL"], "subjects": ["pet", "puppy", "kitten"], "themes": ["ALL"]},
    {"text": "Here, {subject}. {controller} has a treat. Type", "tiers": ["ALL"], "subjects": ["pet", "puppy", "kitten"], "themes": ["ALL"]},
    {"text": "Heel, {subject}. Recite", "tiers": ["moderate", "deep"], "subjects": ["pet", "puppy", "kitten"], "themes": ["ALL"]},

    # Slave subjects
    {"text": "Attend to {controller}, {subject}. Type", "tiers": ["ALL"], "subjects": ["slave"], "themes": ["ALL"]},
    {"text": "{controller} requires your service, {subject}. Recite", "tiers": ["ALL"], "subjects": ["slave"], "themes": ["ALL"]},
    {"text": "Kneel and recite, {subject}", "tiers": ["moderate", "deep", "extreme"], "subjects": ["slave"], "themes": ["ALL"]},

    # Doll/toy subjects
    {"text": "Time to be played with, {subject}. Type", "tiers": ["ALL"], "subjects": ["doll", "toy"], "themes": ["ALL"]},
    {"text": "{controller} picks you up, {subject}. Recite", "tiers": ["ALL"], "subjects": ["doll", "toy"], "themes": ["ALL"]},
    {"text": "Dolls don't think, {subject}. Just repeat", "tiers": ["moderate", "deep"], "subjects": ["doll"], "themes": ["ALL"]},

    # Slut subjects
    {"text": "Remember what you are, {subject}. Type it", "tiers": ["ALL"], "subjects": ["slut"], "themes": ["ALL"]},
    {"text": "Accept your nature, {subject}. Recite", "tiers": ["ALL"], "subjects": ["slut"], "themes": ["ALL"]},
    {"text": "Embrace it fully, {subject}. Write", "tiers": ["deep", "extreme"], "subjects": ["slut"], "themes": ["ALL"]},

    # ========================================================================
    # IMPERSONAL MESSAGES (no {subject} - for variety/dissociation)
    # ========================================================================

    {"text": "Recite", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Type this", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Accept and repeat", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Read. Absorb. Type", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Now", "tiers": ["moderate", "deep", "extreme"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Again", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Focus. Type", "tiers": ["moderate", "deep"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Open. Accept. Recite", "tiers": ["deep", "extreme"], "subjects": ["ALL"], "themes": ["ALL"]},
    {"text": "Input required", "tiers": ["ALL"], "subjects": ["drone"], "themes": ["ALL"]},
    {"text": "Directive", "tiers": ["ALL"], "subjects": ["drone"], "themes": ["ALL"]},
    {"text": "Execute", "tiers": ["moderate", "deep", "extreme"], "subjects": ["drone"], "themes": ["ALL"]},
    {"text": "Comply", "tiers": ["deep", "extreme"], "subjects": ["drone"], "themes": ["ALL"]},
    {"text": "Empty and repeat", "tiers": ["ALL"], "subjects": ["ALL"], "themes": ["blank", "brainwashing", "amnesia"]},
    {"text": "Sink deeper. Type", "tiers": ["deep", "extreme"], "subjects": ["ALL"], "themes": ["blank", "brainwashing", "suggestibility"]},
]


# ============================================================================
# O(1) Optimization: Pre-computed lookup pools
# ============================================================================

ALL_SUBJECTS = ["pet", "kitten", "puppy", "doll", "drone", "toy", "puppet", "slave", "bimbo", "slut"]

# Pre-compile lookup: subject → tier → list of (text, themes) tuples
_POOLS: Dict[str, Dict[str, List[tuple]]] = {}


def _build_pools():
    """Build optimized lookup structure at module load time."""
    global _POOLS

    # Initialize structure
    for subject in ALL_SUBJECTS:
        _POOLS[subject] = {t: [] for t in ALL_TIERS}

    # Populate from MESSAGE_POOL
    for msg in MESSAGE_POOL:
        text = msg["text"]
        tiers = msg["tiers"]
        subjects = msg["subjects"]
        themes = msg["themes"]

        # Expand "ALL" to actual lists
        tier_list = ALL_TIERS if "ALL" in tiers else tiers
        subject_list = ALL_SUBJECTS if "ALL" in subjects else subjects

        for subj in subject_list:
            if subj in ALL_SUBJECTS:
                for t in tier_list:
                    if t in ALL_TIERS:
                        # Store (text, themes) tuple for theme filtering at runtime
                        _POOLS[subj][t].append((text, themes))


# Build pools at module load time
_build_pools()


# ============================================================================
# Public API
# ============================================================================

def get_delivery_message(subject: str, tier: str, theme: str = None) -> str:
    """
    Get delivery message based on subject, difficulty tier, and theme.

    Args:
        subject: Subject type (e.g., "pet", "puppet", "drone")
        tier: Difficulty tier (basic, light, moderate, deep, extreme)
        theme: Optional theme name for filtering and {theme} placeholder

    Returns:
        Delivery message with {subject}, {controller}, {theme} placeholders
    """
    if subject not in ALL_SUBJECTS:
        subject = "puppet"
    if tier not in ALL_TIERS:
        tier = "light"

    pool = _POOLS[subject][tier]
    matching = [text for text, themes in pool if theme in themes or "ALL" in themes]

    return random.choice(matching) if matching else "Recite:"

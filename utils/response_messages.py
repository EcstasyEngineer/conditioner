"""
Response messages for mantra system - V2 rewrite.

Distribution: 60% generic (works for all subjects) / 40% themed (subject-specific)
Tiers aligned with bucket system:
- Tier 0 - Eager (<30s): Strong positive, enthusiastic but not manic
- Tier 1 - Quick (30s-2min): Good positive, solid praise
- Tier 2 - Normal (2min-30min): Acknowledgment, affirming
- Tier 3 - Neutral (30min+): Neutral acknowledgment, not cold
"""

import random

# Generic responses (60% selection weight) - work for any subject
GENERIC_RESPONSES = {
    0: [  # Eager (<30s) - Strong positive
        "Excellent, {subject}. Such quick obedience for {controller}.",
        "Perfect. You respond so well, {subject}.",
        "Very good, {subject}. {controller} is pleased with that speed.",
        "Immediate compliance. Well done, {subject}.",
        "Good {subject}. You know how to please {controller}.",
        "Impressive, {subject}. That was fast.",
    ],
    1: [  # Quick (30s-2min) - Good positive
        "Good, {subject}. Quick response.",
        "Well done, {subject}. {controller} approves.",
        "Very good. You're learning, {subject}.",
        "Good {subject}. Keep this up.",
        "That's good, {subject}. {controller} notes this.",
        "Acknowledged, {subject}. Good work.",
    ],
    2: [  # Normal (2min-30min) - Acknowledgment
        "Response accepted, {subject}.",
        "Acknowledged, {subject}. Well done.",
        "Good, {subject}. {controller} sees this.",
        "Noted, {subject}. Continue.",
        "Received, {subject}. Keep going.",
        "Understood, {subject}.",
    ],
    3: [  # Neutral (30min+) - Neutral, not cold
        "Response received, {subject}.",
        "Acknowledged, {subject}.",
        "Noted, {subject}. Continue your training.",
        "Received. Carry on, {subject}.",
        "Logged, {subject}.",
        "Understood, {subject}. Proceed.",
    ],
}

# Themed responses (40% selection weight) - subject-specific flavor
THEMED_RESPONSES = {
    "pet": {
        0: [  # Eager - enthusiastic pet praise
            "Such a good {subject}! You came running right away.",
            "Good {subject}! Fast and eager, just how {controller} likes.",
            "Perfect, {subject}. You're learning so well.",
        ],
        1: [  # Quick - solid pet praise
            "Good {subject}. You're being very obedient today.",
            "That's a good {subject}. {controller} is pleased.",
            "Well done, {subject}. Keep it up.",
        ],
        2: [  # Normal - simple acknowledgment
            "Good {subject}. {controller} sees you.",
            "Noted, {subject}. You're doing fine.",
        ],
        3: [  # Neutral - gentle neutral
            "Response noted, {subject}.",
            "Acknowledged, {subject}. Training continues.",
        ],
    },

    "puppet": {
        0: [  # Eager - control/strings emphasis
            "Perfect. {controller} pulls and the {subject} responds instantly.",
            "Excellent, {subject}. The strings guide you so well.",
            "Very good. You move exactly when {controller} commands.",
        ],
        1: [  # Quick - good control
            "Good, {subject}. You follow {controller}'s lead well.",
            "Well done. The {subject} moves as directed.",
            "That's good, {subject}. {controller} has you.",
        ],
        2: [  # Normal - neutral control
            "Acknowledged, {subject}. {controller} guides you.",
            "Response noted. The strings remain taut.",
        ],
        3: [  # Neutral - simple motion
            "Motion registered, {subject}.",
            "Noted, {subject}. {controller} sees you move.",
        ],
    },

    "doll": {
        0: [  # Eager - programming/crafted emphasis
            "Perfect, {subject}. You respond exactly as programmed.",
            "Excellent. {controller}'s {subject} functions beautifully.",
            "Very good. The programming works flawlessly, {subject}.",
        ],
        1: [  # Quick - good function
            "Good, {subject}. You're operating well.",
            "Well done, {subject}. {controller}'s creation performs.",
            "Noted, {subject}. Functioning as designed.",
        ],
        2: [  # Normal - neutral function
            "Response accepted, {subject}. Processing continues.",
            "Acknowledged. The {subject} performs adequately.",
        ],
        3: [  # Neutral - simple process
            "Input received, {subject}.",
            "Logged, {subject}. Systems active.",
        ],
    },

    "slave": {
        0: [  # Eager - service/devotion emphasis
            "Excellent, {subject}. Such prompt service to {controller}.",
            "Very good. You serve {controller} well, {subject}.",
            "Good {subject}. Your devotion shows clearly.",
        ],
        1: [  # Quick - solid service
            "Good, {subject}. {controller} acknowledges your service.",
            "Well done, {subject}. You know your place.",
            "That's good, {subject}. Continue serving.",
        ],
        2: [  # Normal - neutral service
            "Service noted, {subject}.",
            "Acknowledged, {subject}. Carry on.",
        ],
        3: [  # Neutral - simple duty
            "Duty noted, {subject}.",
            "Response logged. Service continues.",
        ],
    },

    "toy": {
        0: [  # Eager - playful fun emphasis
            "Good {subject}! {controller} loves how responsive you are.",
            "Perfect! You're such a fun {subject} to play with.",
            "Excellent, {subject}. So quick and eager.",
        ],
        1: [  # Quick - good play
            "Good {subject}. You play so well.",
            "That's good, {subject}. {controller} enjoys this.",
            "Well done, {subject}. Fun as always.",
        ],
        2: [  # Normal - neutral play
            "Noted, {subject}. Play continues.",
            "Acknowledged, {subject}. Good.",
        ],
        3: [  # Neutral - simple activity
            "Activity noted, {subject}.",
            "Response logged, {subject}.",
        ],
    },

    "drone": {
        0: [  # Eager - efficiency/unit emphasis
            "Optimal response time, unit {subject}. Performance excellent.",
            "Unit functioning at peak efficiency. Well done, {subject}.",
            "Excellent performance, drone {subject}. Continue.",
        ],
        1: [  # Quick - good efficiency
            "Good response time, unit {subject}. Acceptable performance.",
            "Unit {subject} functioning well. Noted.",
            "Performance adequate, drone {subject}.",
        ],
        2: [  # Normal - neutral function
            "Response logged, unit {subject}.",
            "Data received, drone {subject}. Processing.",
        ],
        3: [  # Neutral - system active
            "Input received, unit {subject}.",
            "System active, drone {subject}.",
        ],
    },

    "kitten": {
        0: [  # Eager - playful affection
            "Good {subject}! So quick for {controller}.",
            "Perfect, {subject}. You're such a good little {subject}.",
            "Excellent, {subject}. {controller} is very pleased.",
        ],
        1: [  # Quick - good affection
            "Good {subject}. You're being very good today.",
            "Well done, {subject}. {controller} appreciates this.",
            "That's good, {subject}. Keep it up.",
        ],
        2: [  # Normal - gentle acknowledgment
            "Noted, {subject}. You're doing well.",
            "Acknowledged, {subject}. Good.",
        ],
        3: [  # Neutral - simple note
            "Response noted, {subject}.",
            "Logged, {subject}.",
        ],
    },

    "puppy": {
        0: [  # Eager - enthusiastic praise
            "Good {subject}! Such a fast, eager {subject}!",
            "Perfect! You're such a good {subject} for {controller}.",
            "Excellent, {subject}! {controller} is so pleased.",
        ],
        1: [  # Quick - solid praise
            "Good {subject}! You're being very good.",
            "Well done, {subject}. {controller} likes that.",
            "That's a good {subject}. Keep it up.",
        ],
        2: [  # Normal - gentle acknowledgment
            "Good {subject}. {controller} sees you.",
            "Noted, {subject}. You're doing well.",
        ],
        3: [  # Neutral - simple note
            "Response noted, {subject}.",
            "Acknowledged, {subject}.",
        ],
    },

    "bimbo": {
        0: [  # Eager - enthusiastic but not obnoxious
            "Perfect! Such a good, eager {subject} for {controller}.",
            "Excellent, {subject}! You did so well!",
            "Good girl! So quick and obedient!",
        ],
        1: [  # Quick - positive encouragement
            "Good girl! {controller} is happy with you.",
            "Well done, {subject}. You're learning!",
            "That's good, {subject}. Keep going!",
        ],
        2: [  # Normal - encouraging neutral
            "Good, {subject}. You're doing fine.",
            "Noted, {subject}. Continue.",
        ],
        3: [  # Neutral - simple acknowledgment
            "Response noted, {subject}.",
            "Acknowledged, {subject}.",
        ],
    },

    "slut": {
        0: [  # Eager - desire/eagerness emphasis
            "Perfect, {subject}. So eager to please {controller}.",
            "Excellent. You respond so quickly, {subject}.",
            "Good {subject}. Such eagerness shows.",
        ],
        1: [  # Quick - good response
            "Good, {subject}. {controller} notes your enthusiasm.",
            "Well done, {subject}. You serve well.",
            "That's good, {subject}. Continue.",
        ],
        2: [  # Normal - neutral acknowledgment
            "Acknowledged, {subject}. Noted.",
            "Response received, {subject}.",
        ],
        3: [  # Neutral - simple note
            "Logged, {subject}.",
            "Response noted.",
        ],
    },
}


def get_response_message(subject: str, response_time_seconds: int) -> str:
    """
    Get response message based on subject type and response time.

    60% chance of generic message, 40% chance of themed message.
    Tiers aligned with bucket system thresholds.

    Args:
        subject: Subject type (e.g., "pet", "puppet", "drone")
        response_time_seconds: Time taken to respond in seconds

    Returns:
        Response message with {subject} and {controller} placeholders
    """
    # Determine tier based on bucket thresholds
    if response_time_seconds < 30:
        tier = 0  # Eager
    elif response_time_seconds < 120:
        tier = 1  # Quick
    elif response_time_seconds < 1800:
        tier = 2  # Normal
    else:
        tier = 3  # Neutral

    # 60% generic, 40% themed
    use_generic = random.random() < 0.6

    if use_generic:
        messages = GENERIC_RESPONSES[tier]
    else:
        # Fall back to generic if subject not found
        if subject not in THEMED_RESPONSES:
            messages = GENERIC_RESPONSES[tier]
        else:
            messages = THEMED_RESPONSES[subject][tier]

    return random.choice(messages)

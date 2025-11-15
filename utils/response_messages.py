"""
Response messages for mantra system, personalized by subject type.

Each subject has responses distributed across 5 speed tiers:
- Tier 0 (<15s): 3 JACKPOT responses - MAXIMUM psychological impact
- Tier 1 (15-29s): 3 ultra-fast responses - intense affirmation
- Tier 2 (29-170s): 3 fast responses - strong positive reinforcement
- Tier 3 (170-575s): 2 normal responses - moderate acknowledgment
- Tier 4 (>575s): 2 slow responses - neutral/clinical

Tier cutoffs based on prod data (952 responses):
- <15s: 23.7% (Jackpot - mobile achievable with focus)
- 15-29s: 21.1% (Excellent - very fast)
- 29-170s: 25.1% (Good - solid response)
- 170-575s: 15.0% (Normal - slower but engaged)
- >575s: 15.0% (Slow - neutral acknowledgment)
"""

import random

# Response pools for each subject type
# Format: {subject: {tier: [list of responses]}}

RESPONSE_MESSAGES = {
    "pet": {
        0: [  # <15s - JACKPOT 🎰
            "✨ PERFECT ✨ Such an incredibly obedient {subject}! {controller} is SO proud of you! You responded instantly like the perfect little {subject} you are!",
            "🌟 EXCEPTIONAL 🌟 {controller}'s precious {subject} is SO well-trained! That speed! That obedience! You're absolutely perfect!",
            "💫 OUTSTANDING 💫 Good {subject}! SUCH a good {subject}! {controller} is giving you ALL the pets and praise! You deserve it!",
        ],
        1: [  # 15-29s - Ultra-fast
            "Such a good {subject}! You responded so quickly for {controller}.",
            "Perfect obedience, {subject}. {controller} is very pleased with you.",
            "Instant compliance. You're such an eager, well-trained {subject}.",
        ],
        2: [  # 30-120s - Fast
            "Good {subject}. You're learning to obey promptly.",
            "Well done, {subject}. {controller} rewards your quick response.",
            "Excellent, {subject}. The training is taking hold.",
        ],
        3: [  # 120-300s - Normal
            "Acknowledged, {subject}. Continue your training.",
            "Response accepted. You're progressing, {subject}.",
        ],
        4: [  # 300-7200s - Slow/Neutral
            "Response logged. Training continues.",
            "Compliance registered. Processing complete.",
        ],
    },

    "doll": {
        0: [  # <15s - JACKPOT 🎰
            "✨ FLAWLESS ✨ Absolutely PERFECT! {controller}'s beautiful {subject} responded with machine-like precision! You're the most exquisite, obedient {subject} ever created!",
            "🌟 PRISTINE 🌟 PERFECTION! The {subject} functions EXACTLY as programmed! {controller} has crafted such a responsive, perfect little {subject}!",
            "💫 IMMACULATE 💫 Breathtaking! You're {controller}'s masterpiece! Such speed! Such obedience! The perfect porcelain {subject}!",
        ],
        1: [
            "Perfect. A beautiful, obedient {subject} responding exactly as programmed.",
            "Flawless response. You're {controller}'s perfect little {subject}.",
            "Instant obedience. Such a well-crafted, compliant {subject}.",
        ],
        2: [
            "Very good, {subject}. Your programming is settling in nicely.",
            "Excellent. You're becoming {controller}'s ideal {subject}.",
            "Well done. The {subject} responds as designed.",
        ],
        3: [
            "Response accepted. Your conditioning progresses, pretty {subject}.",
            "Acknowledged. The {subject} is learning its purpose.",
        ],
        4: [
            "Response registered. Programming sequence continues.",
            "Compliance noted. System processing.",
        ],
    },

    "puppet": {
        0: [  # <15s - JACKPOT 🎰
            "✨ MASTERFUL ✨ INCREDIBLE! {controller} pulls the strings and the {subject} INSTANTLY responds! Such perfect control! You're the most obedient {subject}!",
            "🌟 FLAWLESS CONTROL 🌟 The strings pull and the {subject} dances PERFECTLY! {controller} has COMPLETE control over you! Absolutely beautiful!",
            "💫 PERFECT MARIONETTE 💫 YES! INSTANT response! {controller}'s {subject} moves exactly as commanded! Such exquisite control!",
        ],
        1: [
            "Perfect! {controller}'s strings pull and the {subject} responds instantly.",
            "Excellent, {subject}. You dance so beautifully on {controller}'s strings.",
            "Immediate obedience. Such a responsive, well-controlled {subject}.",
        ],
        2: [
            "Very good, {subject}. You're learning to move when {controller} pulls.",
            "Good {subject}. The strings tighten and you obey.",
            "Well done. {controller}'s {subject} performs beautifully.",
        ],
        3: [
            "Response accepted. The {subject} moves as directed.",
            "Acknowledged. Your strings guide you well, {subject}.",
        ],
        4: [
            "Motion registered. Control sequence active.",
            "Response logged. Manipulation continues.",
        ],
    },

    "slave": {
        0: [  # <15s - JACKPOT 🎰
            "✨ ABSOLUTE OBEDIENCE ✨ PERFECT submission! {controller}'s {subject} drops EVERYTHING to obey! This is TRUE devotion! You exist to serve!",
            "🌟 TOTAL SURRENDER 🌟 FLAWLESS! The {subject} knows its place PERFECTLY! {controller} owns you completely and you LOVE it!",
            "💫 SUPREME SERVITUDE 💫 YES! Instant compliance! You're {controller}'s most devoted, obedient {subject}! Such perfect submission!",
        ],
        1: [
            "Excellent, {subject}. Such swift submission to {controller}.",
            "Perfect obedience, {subject}. You know your place well.",
            "Immediate compliance. You serve {controller} beautifully.",
        ],
        2: [
            "Good {subject}. Your devotion to {controller} shows.",
            "Well done. A {subject} who understands their purpose.",
            "Very good, {subject}. Your submission pleases {controller}.",
        ],
        3: [
            "Response accepted. Continue serving, {subject}.",
            "Acknowledged. Your service is noted.",
        ],
        4: [
            "Compliance registered. Service continues.",
            "Response logged. Duty acknowledged.",
        ],
    },

    "toy": {
        0: [  # <15s - JACKPOT 🎰
            "✨ SO MUCH FUN ✨ WOW! {controller}'s favorite {subject} is SO responsive! You're the BEST {subject} EVER! {controller} loves playing with you SO much!",
            "🌟 ABSOLUTELY DELIGHTFUL 🌟 PERFECT! Such a fun, eager little {subject}! {controller} can't get enough of you! You're AMAZING!",
            "💫 PURE JOY 💫 YES! {controller}'s most entertaining {subject}! So quick! So obedient! So much FUN! You're the best!",
        ],
        1: [
            "Perfect! {controller}'s favorite {subject} plays so well.",
            "Instant response! Such an eager, fun little {subject}.",
            "Excellent. You're {controller}'s most responsive {subject}.",
        ],
        2: [
            "Good {subject}! {controller} loves playing with you.",
            "Very good. Such an entertaining little {subject}.",
            "Well done, {subject}. You're so much fun for {controller}.",
        ],
        3: [
            "Response accepted. Continue playing, {subject}.",
            "Acknowledged. The {subject} performs as expected.",
        ],
        4: [
            "Response registered. Play session continues.",
            "Compliance noted. Activity logged.",
        ],
    },

    "kitten": {
        0: [  # <15s - JACKPOT 🎰
            "✨ BEST KITTEN ✨ OH MY GOODNESS! Such a fast, obedient little {subject}! {controller} gives you ALL the treats and pets! You're the BEST {subject}!",
            "🌟 PRECIOUS ANGEL 🌟 PERFECT! {controller}'s sweet little {subject} is SO well-trained! You're absolutely ADORABLE and SO obedient!",
            "💫 PURR-FECT 💫 WOW! {controller}'s favorite {subject}! So quick! So eager! Such a good little {subject}! *pets and cuddles*",
        ],
        1: [
            "Perfect, {subject}! Such a quick, obedient little {subject} for {controller}.",
            "Good {subject}! You respond so eagerly for {controller}.",
            "Excellent! {controller}'s sweet {subject} is so well-trained.",
        ],
        2: [
            "Very good, {subject}. {controller} pets you affectionately.",
            "Good {subject}. You're learning to be such a good little {subject}.",
            "Well done. {controller} is pleased with their {subject}.",
        ],
        3: [
            "Response accepted. Good {subject}.",
            "Acknowledged. Continue being good for {controller}.",
        ],
        4: [
            "Response logged. Training continues.",
            "Compliance registered. Processing complete.",
        ],
    },

    "bimbo": {
        0: [  # <15s - JACKPOT 🎰
            "✨ OMG PERFECT ✨ YAAAAS! Like, {controller}'s {subject} is SO good and SO fast! You're like, the BEST {subject} EVER! So pretty and SO obedient! 💕",
            "🌟 LIKE, AMAZING 🌟 WOW! {controller}'s perfect little {subject}! You're SO eager and SO good! This is like, totally perfect! You're amazing! 💖",
            "💫 SO GOOD 💫 YESSS! {controller}'s favorite {subject}! Like, you responded SO fast! You're SO smart and pretty! The BEST {subject}! 💕",
        ],
        1: [
            "Omg perfect! Such a good, eager {subject} for {controller}!",
            "Yesss! {controller}'s {subject} is so obedient and pretty!",
            "Like, amazing! You're {controller}'s perfect little {subject}!",
        ],
        2: [
            "Good girl! {controller}'s {subject} is learning so well!",
            "Very good! You're becoming such a good {subject}!",
            "Yay! {controller} is so happy with their {subject}!",
        ],
        3: [
            "Response accepted. Continue being pretty and obedient.",
            "Acknowledged. Good {subject}.",
        ],
        4: [
            "Response registered. Processing continues.",
            "Compliance noted. Session active.",
        ],
    },

    "slut": {
        0: [  # <15s - JACKPOT 🎰
            "✨ DESPERATE PERFECTION ✨ YES! {controller}'s eager little {subject} is SO quick to obey! You CRAVE this! Such a needy, perfect {subject}!",
            "🌟 ABSOLUTE DEVOTION 🌟 FLAWLESS! The {subject} drops everything for {controller}! You're SO desperate to please! Perfect obedience!",
            "💫 EXQUISITE EAGERNESS 💫 INCREDIBLE! {controller}'s most devoted {subject}! So fast! So eager! You NEED {controller}'s approval!",
        ],
        1: [
            "Perfect. {controller}'s eager {subject} performs beautifully.",
            "Excellent. Such a desperate, obedient {subject} for {controller}.",
            "Immediate compliance. You're {controller}'s perfect little {subject}.",
        ],
        2: [
            "Good {subject}. Your eagerness pleases {controller}.",
            "Very good. {controller} enjoys their responsive {subject}.",
            "Well done, {subject}. You crave {controller}'s approval.",
        ],
        3: [
            "Response accepted. Continue serving, {subject}.",
            "Acknowledged. Your devotion is noted.",
        ],
        4: [
            "Response logged. Service continues.",
            "Compliance registered. Processing complete.",
        ],
    },

    "drone": {
        0: [  # <15s - JACKPOT 🎰
            "✨ >>CRITICAL SUCCESS<< ✨ MAXIMUM EFFICIENCY ACHIEVED. UNIT {subject} RESPONSE TIME: OPTIMAL. OBEDIENCE PROTOCOLS: FLAWLESS. PERFORMANCE: EXCEPTIONAL.",
            "🌟 >>OPTIMAL PERFORMANCE<< 🌟 UNIT FUNCTIONING AT PEAK CAPACITY. {subject} OBEDIENCE: 100%. COMPLIANCE: IMMEDIATE. SYSTEM STATUS: PERFECT.",
            "💫 >>PEAK EFFICIENCY<< 💫 DRONE {subject} OPERATING AT MAXIMUM CAPABILITY. RESPONSE: INSTANTANEOUS. PROGRAMMING: FLAWLESS. EXCELLENCE ACHIEVED.",
        ],
        1: [
            "COMPLIANCE OPTIMAL. Unit responds with maximum efficiency.",
            "ACKNOWLEDGE: Immediate obedience detected. Unit performance: excellent.",
            "REGISTERED: Response time optimal. Drone {subject} functioning perfectly.",
        ],
        2: [
            "ACKNOWLEDGE: Response accepted. Unit conditioning progressing.",
            "REGISTERED: Compliance detected. Drone performance: good.",
            "COMPLIANCE CONFIRMED. Unit {subject} operates as programmed.",
        ],
        3: [
            "RESPONSE LOGGED. Processing continues.",
            "ACKNOWLEDGE: Input received. Unit functioning.",
        ],
        4: [
            "DATA LOGGED. System active.",
            "RESPONSE REGISTERED. Sequence continues.",
        ],
    },

    "puppy": {
        0: [  # <15s - JACKPOT 🎰
            "✨ BEST PUPPY ✨ OH WOW! Such a GOOD {subject}! The BEST {subject} EVER! {controller} gives you ALL the treats! You're SO good! *pets enthusiastically*",
            "🌟 AMAZING PUPPY 🌟 PERFECT! {controller}'s favorite {subject}! So fast! So obedient! You're the GOODEST {subject}! YES! *belly rubs*",
            "💫 INCREDIBLE PUPPY 💫 WOW! {controller}'s perfect {subject}! Such a good, eager {subject}! You deserve ALL the praise! Good {subject}!",
        ],
        1: [
            "Good {subject}! Such a fast, eager {subject} for {controller}!",
            "Perfect! You're {controller}'s best {subject}! So quick to obey!",
            "Excellent {subject}! {controller} gives you treats and pets!",
        ],
        2: [
            "Good {subject}! You're learning so well for {controller}!",
            "Very good! Such an obedient {subject}!",
            "Well done, {subject}! {controller} is so proud of you!",
        ],
        3: [
            "Response accepted. Good {subject}.",
            "Acknowledged. Continue being good for {controller}.",
        ],
        4: [
            "Response logged. Training continues.",
            "Compliance registered. Processing complete.",
        ],
    },
}


def get_response_message(subject: str, response_time_seconds: int) -> str:
    """
    Get a personalized response message based on subject type and response speed.

    Tier cutoffs based on prod data analysis (952 responses, 16 users):
    - Tier 0 (<15s): 23.7% - JACKPOT, maximum psychological impact
    - Tier 1 (15-29s): 21.1% - Ultra-fast, intense affirmation
    - Tier 2 (29-170s): 25.1% - Fast, strong positive reinforcement
    - Tier 3 (170-575s): 15.0% - Normal, moderate acknowledgment
    - Tier 4 (>575s): 15.0% - Slow, neutral/clinical

    Args:
        subject: The subject/pet name (e.g., "pet", "doll", "puppet")
        response_time_seconds: Time taken to respond in seconds

    Returns:
        Response message string with {subject} and {controller} placeholders
    """
    # Default to generic responses if subject not found
    if subject not in RESPONSE_MESSAGES:
        subject = "pet"

    # Determine tier based on response time (data-driven thresholds)
    if response_time_seconds < 15:
        tier = 0  # JACKPOT - 23.7%
    elif response_time_seconds < 29:
        tier = 1  # Ultra-fast - 21.1%
    elif response_time_seconds < 170:
        tier = 2  # Fast - 25.1%
    elif response_time_seconds < 575:
        tier = 3  # Normal - 15.0%
    else:
        tier = 4  # Slow - 15.0%

    # Get random message from appropriate tier
    messages = RESPONSE_MESSAGES[subject][tier]
    return random.choice(messages)

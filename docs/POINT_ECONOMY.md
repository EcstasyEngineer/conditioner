# Point Economy Design

Reference document for balancing point rewards across all bot systems.

## Philosophy

Points represent **engagement value** — a combination of:
- Time invested
- Attention required
- Psychological weight of the activity
- Scarcity/exclusivity

Higher engagement activities should award more points per interaction, even if they take less clock time.

## System Reference

### Counter (Baseline)

**Rate**: 1 point per number
**Effort**: Rote, low engagement, mindless repetition
**Scarcity**: Unlimited — can grind indefinitely
**Engagement**: Lowest (just typing numbers)

**Earning potential**: ~1800 pts/hr at maximum grind (1 num/2 sec)

**Design intent**: Baseline "grinding" activity. High volume, low value per action. Rewards persistence and time investment, not psychological engagement.

### Audio Listening

**Rate**: 5 points per minute
**Effort**: Passive, immersive
**Scarcity**: Time-gated — must actually spend the time
**Engagement**: Medium (passive but sustained attention)

**Earning potential**: 300 pts/hr (fixed rate)

**Reference values**:
- 10 min file = 50 pts
- 30 min session = 150 pts
- 1 hour = 300 pts

**Design intent**: Rewards sustained immersion. You can't rush it — the time IS the engagement. Moderate points because passive.

### Gacha System

**Rate**: Variable, roughly doubles counter earnings when active
**Effort**: Luck-based bonus layer
**Scarcity**: Tied to other activities
**Engagement**: Dopamine/anticipation mechanic

**Design intent**: Multiplicative layer that makes grinding more exciting. Not a primary point source.

### Mantra System (Premium Engagement)

**Rate**: Variable based on difficulty tier
**Effort**: Active conditioning — read, internalize, reproduce
**Scarcity**: Limited attempts per day (frequency 0.33-6.0)
**Engagement**: HIGHEST — actively typing conditioning content

**Current earning potential** (at 3 mantras/day, mixed difficulty): ~150-300 pts/day

**Design intent**: Premium engagement activity. Scarcity + psychological weight = higher per-action value. You're not just spending time, you're actively participating in conditioning.

## Point Value Guidelines

### Per-Action Reference

| Action | Points | Notes |
|--------|--------|-------|
| Count 1 number | 1 pt | Baseline unit |
| 1 min audio | 5 pts | Equivalent to 5 counted numbers |
| Mantra | 20-200 pts | Based on tier (see [Tier Boundaries](#tier-boundaries)) |

### Daily Earning Benchmarks

**Casual user** (10 min engagement/day):
- Option A: Count to 300 (~10 min) = 300 pts
- Option B: 10 min audio = 50 pts
- Option C: 2 mantras (light avg) = 80-140 pts

**Active user** (30 min engagement/day):
- Counter grinding: ~900 pts
- Audio session: 150 pts
- 3-4 mantras: 200-400 pts

**Power user** (1+ hr/day, max frequency):
- Heavy counter: 1500+ pts
- Long audio: 300+ pts
- 6 mantras (max freq): 400-700 pts

## Mantra Point Calculation

### The Core Question

**Would typing this feel like a leap?**

A mantra that's easy to say = low points. A mantra that makes you pause, that feels like a confession or commitment = high points. The markers below are guidelines to help quantify this, but your judgment matters more than the math.

### Intensity Scoring

Base: 20 points

| Category | Examples | Points |
|----------|----------|--------|
| **Placeholders** | `{controller}` alone | +20 |
| | `{subject}` alone | +10 |
| | Both present | +30 |
| **Permanence** | forever, permanent, irreversible, eternal, will ever | +60 |
| **Ownership** | belongs to, owns, property, is {controller}'s | +30 |
| **Identity erasure** | who I was, everything I was, past erased, no longer me | +30 |
| **Vulnerability** | opens wide, exposes, lets in, defenseless | +30 |
| **Absolutism** | nothing but, only, completely, totally, every | +20 |
| **Mechanism** | rewires, programs, overwrites, erases, deleted, neurons | +20 |
| **Depth language** | core, saturated, consumed, soul, fundamental | +20 |
| **Agency removal** | cannot, impossible, unthinkable, no choice | +20 |
| **Comfort (negative)** | peaceful, gentle, soft, warm, safe | -15 |

These markers are examples, not exhaustive lists. Use judgment for synonyms and similar language.

### Calibration Examples

| Mantra | Why | Points |
|--------|-----|--------|
| "Commands drop straight into action" | Simple, no commitment | 20 |
| "I breathe in control, exhale resistance" | Meditative framing, feels like yoga | 20 |
| "{subject} softens into surrender" | Gentle, low stakes | 30 |
| "{controller}'s words bypass my thoughts entirely" | Controller + absolutism, but abstract | 60 |
| "My reflexes belong to {controller}" | Ownership is a real claim | 70 |
| "My subconscious opens wide for {controller}" | Vulnerability, intimate access | 70 |
| "{subject} is eternally receptive to {controller}" | Permanence changes everything | 110 |
| "Orders from {controller} overwrite every impulse permanently" | Stacked: mechanism + absolutism + permanence | 140 |

### Tier Boundaries

| Points | Tier | The Leap |
|--------|------|----------|
| 20-45 | basic | Easy to say. No real commitment. |
| 45-75 | light | Some weight. Getting comfortable. |
| 75-110 | moderate | Real claim. "This is becoming me." |
| 110-150 | deep | Hard to take back. Core change. |
| 150+ | extreme | Point of no return language. |

### When Math and Instinct Disagree

Trust instinct. If a mantra calculates to 60 but feels like 100 to type, it's 100. If it calculates to 120 but feels gentle, it's probably lower. The markers capture common patterns, not universal truth.

## Balancing Principles

1. **Engagement > Time**: Active conditioning beats passive grinding
2. **Scarcity premium**: Limited activities pay more per action
3. **Psychological weight**: Typing "I am nothing without {controller}" is worth more than typing "457"
4. **No single dominant strategy**: Each system has trade-offs

## Red Flags (Imbalance Indicators)

- Mantras feel "not worth it" compared to counting → Points too low
- Everyone just does audio, ignores mantras → Points or scarcity wrong
- Power users max out daily points in 10 minutes → Caps needed or rates too high
- New users feel they can never catch up → Consider diminishing returns or weekly resets

## Changelog

- 2025-12-05: Initial economy design document

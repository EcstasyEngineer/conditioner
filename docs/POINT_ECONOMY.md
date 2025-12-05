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

| Action | Points | Equivalent To |
|--------|--------|---------------|
| Count 1 number | 1 pt | Baseline unit |
| 1 min audio | 5 pts | 5 counted numbers |
| Basic mantra | 20-40 pts | 20-40 numbers, 4-8 min audio |
| Light mantra | 40-70 pts | 40-70 numbers, 8-14 min audio |
| Moderate mantra | 70-120 pts | 70-120 numbers, 14-24 min audio |
| Deep mantra | 120-180 pts | 120-180 numbers, 24-36 min audio |
| Extreme mantra | 180-250 pts | 180-250 numbers, 36-50 min audio |

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

### Intensity Scoring (Content-Based)

Base: 10 points

**Additive markers:**
- `{controller}` present: +15
- `{subject}` present: +5 (or +20 if both)
- Permanence language: +30
- Absolutism: +15
- Identity statements: +10
- Core/depth language: +15
- Mechanism language: +10
- Sensory/visceral: +5
- Agency removal: +10

### Scarcity Multiplier

Raw intensity score × **2.0** = final point value

This accounts for:
- Limited daily attempts
- Active engagement premium
- Psychological weight of typing conditioning content

### Tier Boundaries (After Multiplier)

| Tier | Intensity Score | Final Points | Difficulty Label |
|------|-----------------|--------------|------------------|
| 1 | 10-19 | 20-38 | basic |
| 2 | 20-34 | 40-68 | light |
| 3 | 35-59 | 70-118 | moderate |
| 4 | 60-89 | 120-178 | deep |
| 5 | 90+ | 180+ | extreme |

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
- 2025-12-05: Established 2.0x scarcity multiplier for mantras

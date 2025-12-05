# Mantra Refactor Continuation Prompt

Use this to continue #46 mantra quality refactor work.

## Context

We're refactoring mantra content quality for the conditioning Discord bot. Work started 2025-12-05.

**Completed:**
- `amnesia` theme — blind validated, replaced weak mantras
- `acceptance` theme — culled weak mantras, replaced with show-not-tell
- `suggestibility` theme — culled state labels, added sensory anchors
- `obedience` theme — culled generic "feels" patterns, added visceral language
- Point economy doc finalized with scoring heuristics

**Remaining themes:**
- addiction, brainwashing
- blank, puppet, slave, helplessness, bimbo, devotion

## Two-Phase Process

### Phase 1: Quality Cull (per theme)

Run blind validation to identify weak mantras. Use this prompt with Task agents:

```
You are evaluating mantras for a conditioning/hypnosis Discord bot. This is craft analysis, not roleplay.

For each mantra, evaluate:
1. **Shows vs tells**: Does it describe an experience or just label a state?
   - TELL: "I am obedient" (label)
   - SHOW: "Commands drop straight into action" (experience)

2. **Psychological movement**: Static state (1) to active process (5)
   - Static: "I am blank"
   - Movement: "Thoughts drift away before forming"

3. **Keep/Revise/Cut** recommendation

Mantras to evaluate:
{list mantras here}

Return a markdown table: | Mantra | Shows/Tells | Movement (1-5) | Verdict | Why |
```

**Quality red flags (auto-cut):**
- Therapeutic framing ("helps me", "my worries", self-help tone)
- Passive voice without subject ("memories are deleted")
- Pure state labels ("I am X" without mechanism)
- Generic verbs ("feels good", "is nice")

### Phase 2: Rescore Everything

After quality pass, rescore all mantras using the point economy.

**The core question: Would typing this feel like a leap?**

Use this prompt with Task agents:

```
Score these mantras for a hypnotic conditioning system.

**The core question:** Would typing this feel like a leap? A mantra that's easy to say = low points. A mantra that feels like a confession or commitment = high points.

## Scoring Guidelines

Base: 20 points

| Category | Examples | Points |
|----------|----------|--------|
| Placeholders | {controller} alone +20, {subject} alone +10, Both +30 |
| Permanence | forever, permanent, irreversible, eternal | +60 |
| Ownership | belongs to, owns, property | +30 |
| Identity erasure | who I was, everything I was, past erased | +30 |
| Vulnerability | opens wide, exposes, lets in, defenseless | +30 |
| Absolutism | nothing but, only, completely, every | +20 |
| Mechanism | rewires, programs, overwrites, erases, deleted | +20 |
| Depth language | core, saturated, consumed, soul | +20 |
| Agency removal | cannot, impossible, unthinkable | +20 |
| Comfort (negative) | peaceful, gentle, soft, warm | -15 |

**Tiers:** 20-40 basic, 40-70 light, 70-120 moderate, 120-180 deep, 180+ extreme

**Trust instinct over math.** If it calculates to 60 but feels like 100 to type, it's 100.

Mantras to score:
{list mantras here}

Return: | Mantra | Points | Tier | One-sentence justification |
```

## Key Documents

- `docs/POINT_ECONOMY.md` — Full scoring system, calibration examples, tier boundaries
- `docs/THEME_GUIDELINES.md` — Per-theme profiles, weak patterns to avoid

## Commit Message Template

```
Refactor {theme} mantras for quality and point accuracy

- Blind validated with Opus, culled {X} weak mantras
- Replaced with show-not-tell alternatives
- Rescored all mantras using point economy heuristics
- Distribution: {N} basic, {N} light, {N} moderate, {N} deep, {N} extreme

Part of #46
```

## Quick Checklist Per Theme

- [ ] Run quality cull (blind validation)
- [ ] Remove/replace weak mantras
- [ ] Rescore all mantras with new system
- [ ] Update JSON with new points and difficulty labels
- [ ] Verify distribution makes sense for theme
- [ ] Commit with template message

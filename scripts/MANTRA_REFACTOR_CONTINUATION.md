# Mantra Refactor Continuation Prompt

Use this to continue #46 mantra quality refactor work.

## Context

We're refactoring mantra content quality for the conditioning Discord bot. Work started 2025-12-05.

**Completed:**
- `amnesia` theme — blind validated, rescored (avg 90 pts)
- `acceptance` theme — culled weak mantras, rescored (avg 79 pts)
- `suggestibility` theme — culled state labels, rescored (avg 74 pts)
- `obedience` theme — culled generic "feels" patterns, rescored (avg 65 pts)
- `brainwashing` theme — culled hedged language, rescored (avg 101 pts)
- `addiction` theme — revised clinical jargon, rescored (avg 85 pts)
- `bimbo` theme — culled 1, revised "worries"→"thoughts", rescored (avg 70 pts)
- `focus` theme — culled 7 meditation-app labels, rescored (avg 63 pts)
- `devotion` theme — culled 3 hedged/self-help, rescored (avg 95 pts)
- `gratitude` theme — culled 7 therapy-speak, rescored (avg 89 pts)
- `worship` theme — culled 11 bare labels, rescored (avg 96 pts)
- `blank` theme — culled 4 hedged/clinical, rescored (avg 89 pts)
- `drone` theme — culled 8, removed duplicate identity statements, rescored (avg 93 pts)
- `puppet` theme — culled 2, rescored (avg 68 pts)
- `slave` theme — culled 19 redundant/self-help, rescored (avg 73 pts)
- `helplessness` theme — culled 8 comfort language, rescored (avg 63 pts)
- `free_use` theme — culled 5, rescored (avg 55 pts)
- Point economy doc finalized with scoring heuristics
- Removed `difficulty` field from all JSONs (now derived via `get_tier()`)
- Added `generation` profiles to all theme JSONs

**All themes complete!**

**Calibration note:** Many themes scored higher than expected targets due to inherent ownership/permanence language. Issue #50 intensity tiers may need revision based on actual scores.

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

**Quality red flags (likely cut):**
- Clinical self-help language ("worries", "anxiety", "healing", "growth", "self-improvement")
- Passive voice without clear agent ("memories are deleted" → "{controller} deletes my memories")
- Generic trait labels without theme anchor ("I am obedient" is weak, "I am {controller}'s maid" is fine)
- Hedged language ("starting to", "beginning to", "kind of")

**NOT red flags (sometimes miscategorized):**
- Dependence framing ("{controller} helps me think clearly" creates parasocial dependence - good)
- Simple language ("feels natural and good" is direct and valid)
- Theme-specific identity claims ("I am X" is fine when X is the theme's identity)
- Comfort/pleasure descriptions (the experience CAN be therapeutic without therapy language)
- Direct statements of state CAN work when they hit hard as confession/declaration

Mantras to evaluate:
{list mantras here}

Return a markdown table: | # | Mantra | Shows/Tells | Movement (1-5) | Verdict | Why |
```

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

Return: | # | Mantra | Points | Tier | One-sentence justification |
```

## Key Documents

- `docs/POINT_ECONOMY.md` — Full scoring system, calibration examples, tier boundaries
- `docs/THEME_GUIDELINES.md` — Universal rules, weak patterns, GPT-isms to avoid
- Each `mantras/*.json` — Theme-specific `generation` profiles with core, progression, good/bad examples

## Commit Message Template

```
Refactor {theme} mantras for quality and point accuracy

- Blind validated, culled {X} weak mantras
- Replaced/revised with show-not-tell alternatives
- Rescored all mantras using point economy heuristics
- Distribution: {N} mantras, avg {N} pts

Part of #46
```

## Quick Checklist Per Theme

- [ ] Run quality cull (blind validation)
- [ ] Remove/replace weak mantras
- [ ] Rescore all mantras with point economy
- [ ] Update JSON with new points
- [ ] Run `python3 scripts/theme_stats.py mantras/{theme}.json` to verify distribution
- [ ] Check avg matches expected intensity tier (see #50)

## Expected Intensity Tiers (from #50)

| Intensity | Themes | Target Avg |
|-----------|--------|------------|
| Hardcore | amnesia, brainwashing, slave, helplessness | 80-100+ |
| Heavy | puppet, addiction, drone | 70-90 |
| Medium | obedience, suggestibility, blank, free_use | 60-80 |
| Softer | acceptance, devotion, gratitude, worship | 50-70 |
| Lightest | bimbo, focus | 40-60 |

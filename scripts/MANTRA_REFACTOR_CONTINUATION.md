# Mantra Refactor Continuation Prompt

Use this to continue #46 mantra quality refactor work.

## Context

We're refactoring mantra content quality for the conditioning Discord bot. Work started 2025-12-05.

**Completed:**
- `amnesia` theme — full refactor with blind validation

**In Progress:**
- `acceptance` theme — running now

**Remaining high-priority themes (by usage):**
- addiction, suggestibility, brainwashing, obedience
- blank, puppet, slave, helplessness, bimbo, devotion

## Process Per Theme

1. **Generate blind test batches**: `python3 scripts/generate_blind_tests.py --type mantras --theme {theme} --replicas 1 --batch-size 10`

2. **Run blind validation** with parallel Task agents. Prompt template:

```
You are doing blind validation of mantras from a conditioning/hypnosis system.

Context:
- Placeholders: {subject} = submissive's pet name, {controller} = dominant's title
- Difficulty tiers: basic (20-38 pts), light (40-68), moderate (70-118), deep (120-178), extreme (180+)
- Point heuristics (intensity score, then ×2 for final points):
  - Base: 10
  - {controller} present: +15
  - {subject} present: +5 (or +20 if both)
  - Permanence (forever, irreversible, permanent): +30
  - Absolutism (nothing but, only exist to, completely): +15
  - Identity (I am, defines me, my nature): +10
  - Core/depth (saturated, consumed, fundamental): +15
  - Mechanism (rewires, programs, installs): +10
  - Sensory (aches, burns, melts, dissolves): +5
  - Agency removal (cannot, impossible, unthinkable): +10

Themes: acceptance, addiction, amnesia, suggestibility, brainwashing, obedience, blank, puppet, slave, helplessness, bimbo, devotion

For EACH mantra, respond with JSON:
{
  "text": "the mantra",
  "estimated_intensity": number (before 2x),
  "final_points": number (after 2x),
  "point_breakdown": "markers detected",
  "difficulty": "basic/light/moderate/deep/extreme",
  "themes": ["primary", "secondary"],
  "psychological_impact": 1-5,
  "quality": "keep/revise/remove",
  "issues": ["problems if any"],
  "revision_suggestion": "improved text if revise, else null"
}

Quality criteria:
- keep: Shows psychological experience, natural phrasing, appropriate intensity
- revise: Right idea but fixable issues (therapeutic language, passive voice, tells-not-shows)
- remove: Ineffective, cringe, or broken
```

3. **Analyze results**: Identify weak mantras (revise/remove), point mismatches, missing tiers

4. **Generate replacements** for weak mantras using Task agent with theme profile from `docs/THEME_GUIDELINES.md`

5. **Update theme JSON** with:
   - Replaced weak mantras
   - Recalculated points (intensity × 2)
   - Correct difficulty labels based on final points

## Key Documents

- `docs/THEME_GUIDELINES.md` — Per-theme profiles, scoring heuristic, quality criteria
- `docs/POINT_ECONOMY.md` — Why 2x multiplier, cross-system balance
- `docs/subject_psychological_profiles.md` — Subject archetypes (for response messages, not mantras)

## Point Economy Quick Reference

| System | Rate | Notes |
|--------|------|-------|
| Counter | 1 pt/number | Baseline, unlimited |
| Audio | 5 pt/minute | Time-gated |
| Mantras | 20-180+ pts | Scarce (1-6/day), premium engagement |

A 120-point deep mantra ≈ 120 counted numbers ≈ 24 min audio

## Quality Red Flags

- "Therapeutic" language (helps, worries, self-help tone)
- Passive voice ("memories are deleted" → "I delete memories")
- Tells-not-shows ("I am obedient" → "Commands drop straight into action")
- Missing personal anchor (no I/{subject}/{controller})
- Point inflation (extreme labels on moderate-intensity content)

## Commit Message Template

```
Refactor {theme} mantras for quality and point accuracy

- Blind validated {N} mantras with Opus
- Replaced {X} weak mantras (therapeutic/passive/flat)
- Recalculated points using heuristic × 2x multiplier
- Distribution: {N} basic, {N} light, {N} moderate, {N} deep, {N} extreme

Part of #46
```

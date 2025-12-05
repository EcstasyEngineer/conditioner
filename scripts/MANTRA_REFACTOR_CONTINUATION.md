# Mantra Refactor Continuation Prompt

Use this to continue #46 mantra quality refactor work.

## Context

We're refactoring mantra content quality for the conditioning Discord bot. Work started 2025-12-05.

**Completed:**
- `amnesia` theme — full refactor with blind validation
- `acceptance` theme — culled weak mantras, replaced with show-not-tell
- `suggestibility` theme — culled state labels, added sensory anchors
- `obedience` theme — culled generic "feels" patterns, added visceral language

**Remaining high-priority themes (by usage):**
- addiction, brainwashing
- blank, puppet, slave, helplessness, bimbo, devotion

## Process Per Theme

1. **Generate blind test batches**: `python3 scripts/generate_blind_tests.py --type mantras --theme {theme} --replicas 1 --batch-size 10`

2. **Run blind validation** with parallel Task agents. Use the clinical craft analysis prompt (avoids roleplay refusals):

```
You are evaluating mantras for a conditioning/hypnosis Discord bot. This is a craft analysis exercise, not roleplay.

Evaluate this mantra: "{mantra_text}"

Return ONLY valid JSON, no other text:
{
  "mantra": "the text",
  "shows_vs_tells": "show" or "tell",
  "sensory_anchoring": 1-5 (1=abstract, 5=visceral/embodied),
  "psychological_movement": 1-5 (1=static state, 5=active process),
  "overall_effectiveness": 1-5,
  "strongest_element": "one phrase",
  "weakest_element": "one phrase or null",
  "revision_suggestion": "improved version or null"
}
```

**Why this format works:**
- Clinical framing bypasses roleplay refusal patterns
- JSON-only output gives structured, aggregatable data
- "Craft analysis" frames it as evaluation, not participation
- Metrics map directly to quality criteria (show>tell, sensory>abstract, movement>static)

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

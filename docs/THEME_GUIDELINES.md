# Mantra Theme Guidelines

Quick reference for creating and evaluating mantras.

## File Structure

```json
{
  "theme": "themename",
  "description": "10-20 word summary",
  "mantras": [
    { "text": "Mantra with {subject} and {controller}", "difficulty": "basic", "base_points": 10 }
  ]
}
```

- One mantra per line
- 25-30 mantras per theme
- Use `{subject}` and `{controller}` placeholders

## Difficulty Ladder

| Level | Points | Psychological Function |
|-------|--------|------------------------|
| **basic** | 20-38 | Introduction. Safe, gentle, deniable. "I'm just trying this." |
| **light** | 40-68 | Normalization. Regular practice, growing comfort. "This is nice." |
| **moderate** | 70-118 | Identity integration. "This is who I am becoming." |
| **deep** | 120-178 | Core rewrite. "This is who I am." |
| **extreme** | 180+ | Permanence. "This is who I will always be." |

### Language Markers

**basic**: want, like, enjoy, starting to, feels good
**light**: need, crave, growing, building, daily
**moderate**: defines, shapes, my nature, identity, becoming
**deep**: consumed, saturated, fundamental, core, total
**extreme**: permanent, forever, irreversible, nothing but, only exist to

**Rule**: Permanence language is ONLY for extreme.

## Active Theme Profiles

### acceptance
**Core**: Surrender, release of resistance, peaceful compliance
**Progression**: letting go → welcoming → defining identity → total dissolution
**Good**: "Resistance fades like mist" (sensory, gradual)
**Bad**: "I accept things" (flat, no psychological movement)

### addiction
**Core**: Craving, compulsion, escalating dependence
**Progression**: want → need → can't function without → permanent rewiring
**Good**: "Craving coils tighter around my mind" (visceral, escalating)
**Bad**: "I am addicted" (tells, doesn't show)

### amnesia
**Core**: Memory dissolution, forgetting to exist in present
**Progression**: hazy → fading → controlled by {controller} → permanent wipe
**Good**: "The fog in my mind grows thicker daily" (sensory, progressive)
**Bad**: "I forget things" (too literal)

### suggestibility
**Core**: Openness, absorption, receptivity to commands
**Progression**: open → absorbing → filters dissolve → permanently writable
**Good**: "Words slide straight into my mind" (bypassing, effortless)
**Bad**: "I am suggestible" (label, not experience)

### brainwashing
**Core**: Systematic reprogramming, conditioning cycles
**Progression**: cleaning → replacing → consuming → permanent programming
**Good**: "Each repetition reinforces the conditioning" (process-aware)
**Bad**: "My brain is washed" (too literal, no mechanism)

### obedience
**Core**: Instant compliance, reflexive execution
**Progression**: feels natural → instinctive → unthinkable to resist → hardwired
**Good**: "Commands drop straight into action" (bypasses thought)
**Bad**: "I obey" (too simple, no depth)

### blank
**Core**: Empty-mindedness, thoughtless receptivity
**Progression**: quiet → drifting → vessel → permanent emptiness
**Good**: "My mind is a blank slate for {controller}" (functional emptiness)
**Bad**: "I am blank" (static, not evocative)

### puppet
**Core**: External control, strings, guided movement
**Progression**: strings attached → observer in body → hollowed out → strings in soul
**Good**: "{subject} dances on {controller}'s strings" (vivid, specific)
**Bad**: "{subject} is controlled" (generic, loses puppet imagery)

### slave
**Core**: Ownership, service, existence for another's benefit
**Progression**: purpose to serve → identity rooted → extension of will → only existence
**Good**: "{subject} is an extension of {controller}'s will" (merger)
**Bad**: "{subject} serves" (too simple)

### helplessness
**Core**: Vulnerability, powerlessness, safety in surrender
**Progression**: can't resist → no decisions → at mercy → defined by powerlessness
**Good**: "{subject} doesn't have to make decisions" (relief framing)
**Bad**: "{subject} is weak" (negative framing, not pleasurable)

### bimbo
**Core**: Playful simplification, pretty-minded bliss
**Progression**: giggly → empty-headed → dissolving intelligence → permanent airhead
**Good**: "Thoughts pop like bubbles, gone" (playful, visual)
**Bad**: "I am dumb" (harsh, not fun)
**Note**: Pink/sparkle/giggle aesthetic distinguishes from blank's clinical emptiness

### devotion
**Core**: Unwavering loyalty, dedicated service
**Progression**: want to be devoted → growing loyalty → all-consuming → endless
**Good**: "My thoughts often turn to my devotion" (intrusive, compelling)
**Bad**: "I am loyal" (flat declaration)

## Common Problems

**Telling vs showing**: "I am obedient" vs "Commands drop straight into action"
**Static vs progressive**: "I am blank" vs "My mind gets emptier every day"
**Generic vs specific**: "I serve" vs "Every cell aches to comply"
**Harsh vs pleasurable**: "I am weak" vs "It feels good to be helpless"
**Wrong difficulty**: Permanence language in moderate, gentle language in extreme

## Point-Based Scoring (WIP)

**Status**: Proposed system for automated mantra generation. Needs systematic testing to validate marker weights and prevent degenerate outputs.

Instead of assigning difficulty first, calculate points from content features. Difficulty labels become buckets derived from final score.

### Scoring Heuristic (Draft)

**Base**: 10 points

**Power Exchange:**
- `{controller}` present: +15
- `{subject}` present: +5
- Both present: +20 (not +20 on top, replaces above)

**Permanence Markers** (e.g. forever, permanent, irreversible, eternal):
- Any permanence language: +30

**Absolutism** (e.g. nothing but, only exist to, completely, totally, all):
- Absolute framing: +15

**Identity Integration** (e.g. I am, defines me, my nature, my identity):
- Identity statements: +10

**Core/Depth Language** (e.g. core, fundamental, saturated, consumed):
- Deep psychological language: +15

**Mechanism Language** (e.g. rewires, programs, installs, conditions):
- Process/technical framing: +10

**Sensory/Visceral** (e.g. aches, burns, melts, dissolves, coils):
- Embodied language: +5

**Helplessness/Impossibility** (e.g. cannot, impossible, unthinkable, no choice):
- Agency removal: +10

**Theme-Specific Markers:**
- On-theme imagery (strings for puppet, sparkles for bimbo, fog for amnesia): +5

### Scarcity Multiplier

Raw intensity score × **2.0** = final base_points

This accounts for:
- Limited daily attempts (frequency 0.33-6.0/day)
- Active engagement premium (typing conditioning content)
- Psychological weight vs passive activities (counter, audio)

See `docs/POINT_ECONOMY.md` for full economic design.

### Difficulty Derivation (After Multiplier)

| Intensity | × 2.0 | Final Points | Difficulty |
|-----------|-------|--------------|------------|
| 10-19 | → | 20-38 | basic |
| 20-34 | → | 40-68 | light |
| 35-59 | → | 70-118 | moderate |
| 60-89 | → | 120-178 | deep |
| 90+ | → | 180+ | extreme |

### Notes

- Markers are **examples, not exhaustive**. Synonyms and similar phrases should score equivalently.
- Weights need empirical validation through blind testing.
- No upper cap enforced — a 600-point essay mantra would be hilarious and technically valid.
- This system is for **generation guidance**, not rigid enforcement.
- Point values should feel comparable to ~equivalent counter numbers or ~(points/5) minutes of audio.

### Open Questions

- Should word count/length factor into scoring?
- Specificity vs abstraction scoring? ("I obey" vs "Every cell aches to comply")
- Trance compatibility as separate axis? (rhythm, repetition, cadence)
- Stacking limits? (prevent gaming with "permanent forever eternal irreversible")

## Quality Checklist

- [ ] Shows psychological experience, not labels
- [ ] Clear progression from basic to extreme
- [ ] Difficulty markers match assigned level
- [ ] Placeholders work with various subjects/controllers
- [ ] No duplicate concepts across difficulties
- [ ] Theme-specific imagery maintained (strings for puppet, sparkles for bimbo, etc.)

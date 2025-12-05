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

| Level | Psychological Function |
|-------|------------------------|
| **basic** | Introduction. Safe, gentle, deniable. "I'm just trying this." |
| **light** | Normalization. Regular practice, growing comfort. "This is nice." |
| **moderate** | Identity integration. "This is who I am becoming." |
| **deep** | Core rewrite. "This is who I am." |
| **extreme** | Permanence. "This is who I will always be." |

*Point values: See [POINT_ECONOMY.md](POINT_ECONOMY.md) for tier boundaries and calculation.*

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

## Weak Patterns to Avoid

### State Labels (Telling)
Declaring a state without showing the experience.

- ❌ "I am obedient" / "{subject} is blank"
- ❌ "My mind is empty" / "I feel submissive"
- ✅ "Commands drop straight into action" (shows obedience)
- ✅ "Thoughts drift away before forming" (shows blankness)

### Hedged Language
Uncommitted, tentative phrasing that undermines the mantra.

- ❌ "starting to", "beginning to", "kind of", "a little"
- ❌ "I think I might be...", "It seems like..."
- ✅ Direct statements: "The fog thickens" not "The fog is starting to thicken"

### Passive Voice
Subject receives action instead of experiencing it.

- ❌ "Memories are deleted", "Thoughts are removed"
- ❌ "{subject} is controlled by {controller}"
- ✅ "I forget", "{controller} deletes my memories"
- ✅ "{controller} controls {subject}" or "{subject} surrenders control"

### Therapeutic Framing
Self-help language that breaks the conditioning aesthetic.

- ❌ "helps me", "worries", "healing", "growth", "self-improvement"
- ❌ "{controller} helps me forget my worries"
- ✅ "I forget for {controller}" (service framing, not therapy)

### Generic Verbs
Vague action words without sensory or psychological specificity.

- ❌ "feels", "is", "has", "does" (as main verb without modifier)
- ❌ "It feels good to obey"
- ✅ "Obeying floods me with warmth" (specific sensation)
- ✅ "Obedience hums through my veins" (visceral, embodied)

### Static Descriptions
No sense of movement, progression, or change.

- ❌ "I am blank" (just a state)
- ✅ "My mind empties with each breath" (progressive)
- ✅ "Blankness spreads through my thoughts" (active)

## Common Problems (Summary)

**Telling vs showing**: "I am obedient" vs "Commands drop straight into action"
**Static vs progressive**: "I am blank" vs "My mind gets emptier every day"
**Generic vs specific**: "I serve" vs "Every cell aches to comply"
**Harsh vs pleasurable**: "I am weak" vs "It feels good to be helpless"
**Wrong difficulty**: Permanence language in moderate, gentle language in extreme

## Point Calculation

See [POINT_ECONOMY.md](POINT_ECONOMY.md) for the full scoring system, including:
- Intensity scoring heuristic (base + markers)
- Tier boundaries and difficulty derivation

## Quality Checklist

- [ ] Shows psychological experience, not labels
- [ ] Clear progression from basic to extreme
- [ ] Difficulty markers match assigned level
- [ ] Placeholders work with various subjects/controllers
- [ ] No duplicate concepts across difficulties
- [ ] Theme-specific imagery maintained (strings for puppet, sparkles for bimbo, etc.)

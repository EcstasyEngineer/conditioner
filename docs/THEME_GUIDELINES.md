# Mantra Theme Guidelines

Universal rules for creating and evaluating mantras. Theme-specific profiles live in each `mantras/*.json` file under the `generation` key.

## File Structure

```json
{
  "theme": "themename",
  "description": "Short display text for Discord UI (~60 chars)",
  "generation": {
    "good": ["Example mantra", "why it works"],
    "bad": ["Example mantra", "why it fails"],
    "notes": "Generation guidance (see below)"
  },
  "mantras": [
    { "text": "Mantra with {subject} and {controller}", "base_points": 50 }
  ]
}
```

### Generation Notes

The `notes` field guides LLM generation with theme-specific context. Include:

- **Headspace**: What psychological state does this theme evoke? What's the subjective experience?
- **Key imagery**: Specific metaphors or sensory language that define the theme
- **Distinguishing features**: What separates this from similar themes?
- **Voice rules**: Pronoun choices, tone, grammar quirks (e.g., drone's "its" and broken grammar)
- **What to avoid**: Language or framing that breaks the theme's feel
- **Content notes**: Intensity level, explicit content flags, gendered language

Not every theme needs all of these. Focus on what an LLM would need to generate mantras that *feel* right for this theme specifically.

- One mantra per entry, 25-30 mantras per theme
- Use `{subject}` and `{controller}` placeholders
- Points determine tier automatically (see POINT_ECONOMY.md)

## The Prime Directive

**Show the experience. Never label the state.**

The user is typing these words. They should feel something shift as they type, not recite a clinical diagnosis.

| Don't write | Write instead |
|-------------|---------------|
| "I am obedient" | "Commands drop straight into action" |
| "I am blank" | "Thoughts drift away before forming" |
| "I am suggestible" | "Words slide straight into my mind" |
| "I feel submissive" | "My shoulders drop when {controller} speaks" |

### Confessions Are Not Labels

Not all mantras describe an experience - some work because **typing them is the psychological act itself**. These are confessions, not labels.

| Flat label (reject) | Confession (valid) |
|---------------------|-------------------|
| "I am obedient" | "I surrender completely to {controller}" |
| "I am brainwashed" | "{subject} embraces {controller}'s brainwashing" |
| "{subject} is weak" | "I give my mind, body, and soul to {controller}" |

**The difference**: A label just describes a state. A confession is a declaration or commitment that feels like a leap to type. The "show don't tell" rule targets flat labels, not confessions that carry psychological weight.

**The test**: Would typing this feel like *saying something* or just *describing something*? Higher-point mantras should feel like more of a leap - something you wouldn't casually say or type.

## Tier Language (Psychological Function)

Point boundaries are defined in [POINT_ECONOMY.md](POINT_ECONOMY.md#tier-boundaries). Here's what each tier represents psychologically:

| Tier | Function | The Leap |
|------|----------|----------|
| basic | Introduction. Safe, deniable. | "I'm just trying this." |
| light | Normalization. Growing comfort. | "This is nice." |
| moderate | Identity integration. | "This is who I'm becoming." |
| deep | Core rewrite. | "This is who I am." |
| extreme | Permanence. Point of no return. | "This is who I will always be." |

### Language Markers by Tier

**basic**: want, like, enjoy, feels good, starting to notice
**light**: need, crave, growing, building, daily, harder to resist
**moderate**: defines, shapes, my nature, becoming, part of me
**deep**: consumed, saturated, fundamental, core, total, cannot
**extreme**: permanent, forever, irreversible, nothing but, only exist to

**Hard rule**: Permanence language ("forever", "permanent", "irreversible") is ONLY for extreme tier.

## Weak Patterns to Reject

### State Labels (Telling)
Declaring a state without showing the experience.

- ❌ "I am obedient" / "{subject} is blank" / "I feel submissive"
- ✅ "Commands drop straight into action" / "Thoughts drift away"

### Hedged Language
Uncommitted, tentative phrasing that undermines conviction.

- ❌ "starting to", "beginning to", "kind of", "a little", "I think I might"
- ✅ Direct: "The fog thickens" not "The fog is starting to thicken"

### Passive Voice Without Agent
Subject receives action from nowhere.

- ❌ "Memories are deleted" / "Thoughts are removed"
- ✅ "{controller} deletes my memories" / "I let thoughts go"

### Therapeutic Framing
Self-help language breaks the conditioning aesthetic.

- ❌ "helps me", "healing", "growth", "self-improvement", "worries", "anxiety"
- ✅ "I forget for {controller}" (service framing, not therapy)

### Generic Verbs
Vague action words without sensory or psychological specificity.

- ❌ "It feels good to obey" / "Submission is nice"
- ✅ "Obeying floods me with warmth" / "Obedience hums through my veins"

### Static Descriptions
No sense of movement, progression, or change.

- ❌ "I am blank" (just a state)
- ✅ "My mind empties with each breath" (progressive)
- ✅ "Blankness spreads through my thoughts" (active)

### GPT-isms to Avoid
Overused AI writing patterns that sound fake:

- ❌ "delve", "tapestry", "symphony of", "dance of", "embrace the"
- ❌ "journey", "beacon", "vessel of", "testament to"
- ❌ Unnecessary adjective stacking: "soft, gentle, warm, peaceful surrender"
- ❌ Purple prose: "The gossamer threads of consciousness dissolve into the ethereal void"
- ✅ Simple, direct, visceral: "My thoughts stop." / "I go quiet inside."

## Placeholders and Scoring

- `{subject}` - The user's chosen name/role (puppet, drone, pet, etc.)
- `{controller}` - The authority figure (Master, Mistress, Owner, etc.)

### Point Modifiers

| Element | Modifier | Rationale |
|---------|----------|-----------|
| First person only ("My", "I") | base | Direct ownership, minimal dissociation |
| Named self (`{subject}`) | +15 | Dissociation, role reinforcement |
| Controller reference (`{controller}`) | +20 | External authority, power dynamic |
| Both placeholders | +30 | Full dissociation + authority (not additive) |

### The Dual Voice Rule

**Write both versions** when a mantra concept works in both first person and named self:

| First Person (base) | Named Self (+15) |
|---------------------|------------------|
| "My mind is empty" | "{subject}'s mind is empty" |
| "I crave obedience" | "{subject} craves obedience" |
| "My thoughts belong to {controller}" | "{subject}'s thoughts belong to {controller}" |

This approach:
- Eliminates ambiguity about which voice to use
- Gives users variety (future: preference toggle)
- Provides clear scoring differentiation

**Exception - Drone theme**: Drone uses "it/its" pronouns and fragmented grammar as a core identity marker. Drone mantras should NOT have first-person variants.

### When NOT to duplicate

Some mantras only work in one voice:
- Pure confessions ("I surrender completely") - first person only
- Process descriptions ("The brainwashing deepens") - impersonal only
- Drone's mechanical voice ("{subject} awaits input") - named self only

## Voice Frames

Mantras use one of four voice frames, from most intimate to most detached:

| Frame | Pattern | Effect | Best For |
|-------|---------|--------|----------|
| **First Person** | "My mind...", "I crave..." | Direct ownership, confession | Identity claims, desires, commitments |
| **Named Self** | "{subject} obeys..." | Dissociation, role reinforcement | Actions, behaviors, observations |
| **Named Possessive** | "{subject}'s mind..." | Partial dissociation | Things being transformed/acted upon |
| **Process** | "The brainwashing..." | Maximum detachment, inevitability | Mechanisms, impersonal forces |

### Voice Frame Rules

**1. Don't mix frames** in the same mantra. Pick one and commit.
- ❌ "My mind drifts as {subject} surrenders"
- ✅ "My mind drifts" OR "{subject}'s mind drifts"

**2. First Person vs Named Self** (the key choice):
- **First person** = direct ownership, unmediated confession
  - "My purpose is to serve {controller}"
  - "I am nothing without {controller}"
- **Named Self** = dissociated, compartmentalized (the role speaks)
  - "{subject} obeys without hesitation" (observing behavior)
  - "{subject} is a slave" (identity claim, but the role says it)

Both can make identity claims. The difference: first person has no escape hatch, named self lets the pet name "be" the one confessing.

**3. Pronoun continuation** (when you need a pronoun after {subject}):
- **"their"** = gender-neutral, default for all themes
  - "{subject} feels the strings moving their body"
- Theme-specific pronoun rules live in each theme's `generation.notes`

**4. Process frame** is rare:
- Good for inevitable forces ("The brainwashing deepens")
- Most mantras should have a subject

## Quality Checklist

Before adding a mantra:

- [ ] Does it SHOW an experience rather than LABEL a state?
- [ ] Does the language match the point value's tier?
- [ ] Is there psychological movement (not static)?
- [ ] Does it avoid therapeutic/self-help framing?
- [ ] Is it free of GPT-isms and purple prose?
- [ ] Do placeholders work with various subject/controller names?
- [ ] Does it fit the theme's specific imagery? (strings for puppet, unit for drone, etc.)

## Point Calculation

See [POINT_ECONOMY.md](POINT_ECONOMY.md) for:
- Full scoring heuristic (base + intensity markers)
- Tier boundaries
- Calibration examples

## Adding a New Theme

1. Create `mantras/newtheme.json` with structure above
2. Write `generation` block with good/bad examples and any theme-specific notes
3. Write 25-30 mantras covering basic → extreme tiers
4. Run `scripts/theme_stats.py mantras/newtheme.json` to verify distribution
5. Have an agent blind-validate for quality using the checklist above

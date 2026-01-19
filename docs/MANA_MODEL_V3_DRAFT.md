# Mana Model v3 Draft

Incorporating GPT Pro feedback while preserving erotic hypnosis frame.

## Key Changes from v2

### 1. Split "empty" into two distinct states

**cognitive_quiet** (v2: empty)
- Low verbal thought, reduced inner monologue
- Grounded stillness, present but quiet
- Prerequisite for suggestion work

**dissociated** (new)
- Ego dissolution, "gone" feeling
- Time distortion, memory gaps
- The "blackout" reward state
- *Not* pathological in this context - it's a goal

This matters because:
- `blank` module → produces cognitive_quiet
- `bambi_blackout` → produces dissociated
- `bimbo`/`dumbdown` → require cognitive_quiet, produce dissociated + identity_flux

### 2. Rename "craving" to "momentum"

**momentum** (v2: craving)
- Desire to continue, approach motivation
- "More please" without the compulsion connotation
- Still fast decay (desire fades without reinforcement)

### 3. Add missing threat/avoidance variables

**safety** (new)
- Perceived safety, "this feels okay"
- Prerequisite for everything deep
- Puncture-prone (one bad cue drops it fast)
- Slow decay normally, instant collapse on violation

**reactance** (new, *inverse* - lower is better)
- Resistance to direction, "don't tell me what to do"
- Builds if content is too directive too fast
- Baseline varies by person
- Modules can *reduce* reactance (good) or trigger it (bad)

### 4. Reframe relational states

Keep the D/s framing (it's intentional for this use case) but acknowledge the underlying mechanics:

**receptive** - stays as-is (openness to input)

**submissive** - keep, but note it's built on safety + trust
- Can't build submission without safety first
- This is the "power differential accepted" state

**obedient** - keep, but note it requires low reactance
- Command-following readiness
- If reactance is high, obedience can't land

**devoted** - keep (emotional attachment)
- Slowest decay, but puncture-prone on betrayal
- The "worship" state

### 5. Split suggestible into components

**expectancy** (new, replaces part of suggestible)
- Belief that suggestions will work
- Context-dependent, not a fuel tank
- "I expect to go under" vs "this probably won't work"

**suggestible** - narrower definition
- Active acceptance of suggestions as true
- Requires expectancy + receptive + cognitive_quiet
- Gets *reinforced* by successful suggestions, not consumed

### 6. Add puncture mechanics

Some states don't just decay - they can collapse instantly:

| State | Decay | Puncture Risk |
|-------|-------|---------------|
| safety | very slow | HIGH - one bad cue |
| absorption | fast | HIGH - any jarring element |
| trust/devoted | very slow | MEDIUM - tone mismatch, boundary violation |
| cognitive_quiet | fast | MEDIUM - intrusive thoughts |
| dissociated | very fast | HIGH - any grounding stimulus |

This suggests modules should have `hazards` that can puncture states, not just `consumes`.

---

## Proposed v3 State Taxonomy

### METABOLICALLY EXPENSIVE (fast decay, 1.0-1.5/min)
```
absorption (1.5)     - attentional immersion, trance depth
dissociated (1.5)    - ego dissolution, "gone" state
aroused (1.5)        - physiological sexual activation
cognitive_quiet (1.0) - low verbal thought, mental stillness
```

### MOTIVATIONAL (medium decay, 0.5-0.8/min)
```
momentum (0.8)       - desire to continue (was: craving)
expectancy (0.5)     - belief suggestions will work
suggestible (0.5)    - active acceptance of suggestions
identity_flux (0.4)  - self-concept malleability
```

### RELATIONAL (slow decay, 0.2-0.3/min)
```
receptive (0.3)      - openness to input
obedient (0.3)       - command-following readiness
submissive (0.3)     - power differential accepted
devoted (0.2)        - emotional attachment/worship
safety (0.2)         - perceived safety (puncture-prone)
```

### INVERSE STATES (lower is better)
```
reactance (0.3 decay toward baseline)
  - resistance to direction
  - starts at personal baseline (varies)
  - modules can increase or decrease

tension (0.5 decay toward baseline)
  - somatic/muscular holding
  - relaxation modules decrease this
```

---

## Revised Consumption Model

Based on GPT feedback: most states shouldn't be consumed, they get reinforced.

### What gets consumed (true limited resources):
- **Novelty** - habituation reduces impact over session
- **Attentional bandwidth** - intense content uses cognitive resources
- **Reactance budget** - too directive too fast builds resistance

### What gets reinforced (not consumed):
- Safety, trust, rapport - successful modules strengthen these
- Suggestible - successful suggestions reinforce, not deplete
- Absorption - maintained by engaging content, not spent

### New consumption rules:
```json
"consumption_rules": {
  "requirement_cost_ratio": 0,  // No longer consume requirements

  "reinforcement": {
    // Successful module play reinforces these
    "safety": 0.1,      // +10% of production as bonus
    "suggestible": 0.15,
    "devoted": 0.1
  },

  "fatigue_per_module": {
    "attentional_bandwidth": 5,  // Each module costs some attention
    "novelty": 3                  // Habituation builds
  },

  "reactance_triggers": {
    "too_directive_too_fast": 10,  // If obedient < 20 and module requires obedient > 40
    "boundary_push": 15            // Specialization without foundation
  }
}
```

---

## Module Mapping Examples

### intro (opener)
```json
{
  "requires": {},
  "produces": {
    "absorption": 30,
    "receptive": 50,
    "safety": 40,
    "expectancy": 30
  },
  "reduces": {
    "reactance": 20,
    "tension": 30
  }
}
```

### blank (universal)
```json
{
  "requires": {
    "receptive": 20,
    "safety": 20
  },
  "produces": {
    "cognitive_quiet": 70,
    "absorption": 30,
    "receptive": 20
  },
  "reduces": {
    "tension": 40
  }
}
```

### bambi_blackout (utility)
```json
{
  "requires": {
    "suggestible": 25,
    "cognitive_quiet": 20
  },
  "produces": {
    "dissociated": 60,
    "absorption": 35
  },
  "hazards": {
    "grounding_cue": "dissociated"  // Any grounding sound punctures dissociation
  }
}
```

### bimbo (specialization)
```json
{
  "requires": {
    "suggestible": 35,
    "cognitive_quiet": 20,
    "safety": 30
  },
  "produces": {
    "identity_flux": 50,
    "dissociated": 30,
    "aroused": 25
  },
  "reduces": {
    "reactance": 10  // Surrendering identity reduces resistance
  }
}
```

### wakener (closer)
```json
{
  "requires": {},
  "produces": {
    "safety": 20  // Reaffirms safety on exit
  },
  "explicit_reduction": {
    "absorption": 80,
    "dissociated": 100,
    "cognitive_quiet": 60,
    "suggestible": 50
  },
  "increases": {
    "tension": 20  // Some grounding/alerting
  }
}
```

---

## Open Questions for v3

1. **Should safety be a hard gate?**
   - If safety < threshold, block ALL deep modules?
   - Or soft penalty to effectiveness?

2. **How to model puncture events?**
   - Probabilistic based on state level?
   - Or deterministic based on module content tags?

3. **Reactance baseline per user?**
   - Some people are naturally more resistant
   - Could be a user trait, not session state

4. **Is "expectancy" separate from "suggestible"?**
   - GPT suggests yes, but adds complexity
   - Could merge back if testing shows redundancy

5. **Novelty/habituation tracking?**
   - Per-module? Per-session? Per-user?
   - "You've heard this 10 times, reduced impact"

---

## Summary of Changes

| v2 | v3 | Rationale |
|----|----|----|
| empty | cognitive_quiet + dissociated | Split: quiet mind ≠ ego dissolution |
| craving | momentum | Less pathological framing |
| suggestible | expectancy + suggestible | Context vs active acceptance |
| (missing) | safety | Prerequisite for everything deep |
| (missing) | reactance | Resistance tracking |
| (missing) | tension | Somatic state |
| consumes 30% of requires | reinforcement model | States don't deplete on use |

This v3 is more complex but more psychologically grounded. Could implement as:
- **v2.5**: Just add safety + split empty, keep simple consumption
- **v3 full**: All changes including reinforcement model

Recommend v2.5 for near-term, v3 full as north star.

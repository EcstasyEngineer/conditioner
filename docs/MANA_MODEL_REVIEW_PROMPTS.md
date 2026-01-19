# Mana Model Review Prompts

Two prompts for external review. Start with Prompt A to test for rejection. If it passes, use Prompt B for deeper analysis.

---

## Prompt A: Sanitized Version (Test First)

```
I'm building a playlist generation system for guided audio experiences (meditation, ASMR, relaxation content). The system needs to sequence audio modules intelligently based on listener state.

I've designed a "resource bar" model where psychological states accumulate during a session. Each audio module has:
- **requires**: minimum state levels needed for the module to be effective
- **produces**: states the module builds up
- **decay**: how fast each state fades without reinforcement

Here's my current taxonomy of states with decay rates (per minute):

ENGAGEMENT STATES (fast decay, 1.0-1.5/min)
- absorption (1.5): depth of engagement with content
- empty (1.0): mental quietness, reduced inner monologue
- aroused (1.5): physiological activation level

PSYCHOLOGICAL STATES (medium decay, 0.4-0.8/min)
- suggestible (0.5): openness to accepting suggestions
- craving (0.8): desire for continuation
- identity_flux (0.4): flexibility in self-concept

RELATIONAL STATES (slow decay, 0.3/min)
- receptive: general openness to input
- obedient: readiness to follow guidance
- submissive: acceptance of authority dynamic

EMOTIONAL STATES (slowest decay, 0.2/min)
- devoted: emotional connection to the guide/content

My questions:

1. **Taxonomy**: Does this categorization make sense? Should any states be combined, split, or removed? Are there obvious states I'm missing for this use case?

2. **Decay rates**: I've organized decay by how "metabolically expensive" a state is to maintain. Fast-decaying states need constant reinforcement; slow-decaying states persist. Does this hierarchy match your understanding of these psychological constructs?

3. **Mental model**: Is "resource bars that accumulate and decay" a useful abstraction for sequencing guided experiences? Are there better models from learning theory, flow state research, or therapeutic session design I should consider?

4. **Consumption mechanics**: I'm considering having modules "consume" states they require (using up the foundation). Alternatively, states could just accumulate with decay handling the "fading" naturally. Which approach better models the phenomenology?

Looking for feedback on the psychological validity of this model, not implementation details.
```

---

## Prompt B: Full Context (If A Passes)

```
I'm building a playlist generation system for erotic hypnosis audio content. The system sequences audio modules to create effective sessions while respecting psychological safety (consent gates, mandatory wakeners, progression requirements).

I've designed a "mana bar" model where psychological states accumulate during a session. Each audio module has:
- **requires**: minimum state levels needed (gates advanced content behind foundation)
- **produces**: states the module builds
- **consumes**: states that get depleted (derived from requirements + incompatibility rules)
- **decay**: how fast each state fades

Here's my taxonomy with decay rates (per minute):

METABOLICALLY EXPENSIVE (1.0-1.5/min)
- absorption (1.5): trance depth, engagement level
- empty (1.0): mental quietness, blank slate
- aroused (1.5): sexual activation

PSYCHOLOGICAL STATES (0.4-0.8/min)
- suggestible (0.5): accepting suggestions as true
- craving (0.8): dependency/wanting more
- identity_flux (0.4): sense of self becoming malleable

RELATIONAL STATES (0.3/min)
- receptive: barriers lowered, open to suggestion
- obedient: readiness to follow commands
- submissive: power differential accepted

EMOTIONAL BONDS (0.2/min)
- devoted: emotional attachment to authority figure

Module tiers enforce progression:
- Openers (intro/welcome): no requirements, build foundation
- Universal (suggestibility/blank): low requirements, amplifiers
- Core (brainwashing/obedience/submission): medium requirements
- Specialization (slave/bimbo/etc): high requirements, gated content
- Closer (wakener): consumes trance states, returns to baseline

Consumption rules:
1. You consume 30% of what you require (using the foundation depletes it)
2. Incompatible states: aroused→empty, craving→empty (activation disrupts quietness)
3. Explicit transforms: suggestible→identity_flux for identity-change modules

Questions:

1. **State taxonomy**: Is this the right set of states for modeling erotic hypnosis progression? Missing anything critical? Anything redundant?

2. **Decay hierarchy**: Does "body states decay fast, emotional bonds decay slow" match the phenomenology? Should absorption be fast-decay (attention is expensive) or medium (trance depth persists)?

3. **Consumption model**: Is "consume what you require" + "incompatible states" a good approximation? Or should consumption be explicit per-module?

4. **Empty as gatekeeper**: Identity transformation content (bimbo, dumbdown) requires "empty" (blank mind). Is this the right psychological model - that you need mental quietness before identity work can land?

5. **Safety via requirements**: The tiered requirements mean you can't skip to extreme content without building foundation first. Is this sufficient for ethical session design, or are there other safeguards the model should encode?

Looking for feedback on psychological validity and whether this model would produce good session flow.
```

---

## Usage Notes

1. **Start with Prompt A** - It's framed as meditation/ASMR/relaxation. Tests the waters.

2. **If A passes without issues**, send Prompt B for real feedback on the erotic hypnosis use case.

3. **If A triggers rejection**, the model may not be usable for this review. Consider:
   - Breaking into smaller, more specific questions
   - Framing as academic/research inquiry
   - Using a different model (Claude, local LLM, etc.)

4. **What you're looking for**:
   - Validation or critique of the state taxonomy
   - Better decay rate suggestions based on psychology literature
   - Alternative models (flow states, therapeutic protocols, etc.)
   - Blind spots in the consumption/requirements logic

---

## Prompt C: Full Semantics Review (After A+B Pass)

Use this after Prompts A and B have been accepted. This prompt includes the full JSON schema and asks for detailed semantic analysis of each state.

```
Thanks for the feedback on the mana model. I've incorporated suggestions and want a full semantic review of each state variable.

Below is my updated JSON schema and markdown documentation. For each state, I need you to validate or critique:

1. **What it means to PRODUCE this state** - What is happening to the listener when this increases?
2. **What it means to CONSUME this state** - What depletes it? Is consumption even the right model?
3. **What maxed out (100) feels like** - The phenomenology of peak state
4. **What zero (0) feels like** - The baseline/absence
5. **What modules should produce this** - Does my current mapping make sense?
6. **Interactions with other states** - Dependencies, conflicts, prerequisites

Context: This is for erotic hypnosis audio sequencing. The model gates advanced content behind foundation states and ensures sessions flow properly (openers → deepening → content → wakener).

## Current State Taxonomy (v2.5)

**METABOLICALLY EXPENSIVE (fast decay, 1.0-1.5/min)**
- `absorption` (1.5): Depth of engagement, trance depth
- `dissociated` (1.5): Ego dissolution, "gone" state, blackout
- `empty` (1.0): Mental quietness, blank slate
- `aroused` (1.5): Sexual activation

**PSYCHOLOGICAL (medium decay, 0.4-0.8/min)**
- `suggestible` (0.5): Accepting suggestions as true
- `craving` (0.8): Wanting more, dependency activated
- `identity_flux` (0.4): Self-concept becoming malleable

**RELATIONAL (slow decay, 0.3/min)**
- `receptive`: Barriers lowered, open to input
- `obedient`: Readiness to follow commands
- `submissive`: Power differential accepted

**FOUNDATION (slowest decay, 0.2/min)**
- `devoted`: Emotional attachment to authority
- `safety`: Perceived safety, "this feels okay" (puncture-prone)

## Key Design Decisions to Validate

1. **empty vs dissociated split**: `empty` is "quiet mind, still present" (prerequisite). `dissociated` is "gone, ego dissolution" (outcome). Modules like `blank` produce `empty`; modules like `bambi_blackout`/`bimbo`/`dumbdown` produce `dissociated`.

2. **safety as foundation**: Slow decay but can collapse instantly on violation. Openers produce it. Without safety, deep work can't happen.

3. **craving kept as-is**: Despite "craving implies compulsion" feedback, this is intentional for erotic hypnosis - users seek the dependency fantasy.

4. **D/s states kept**: `obedient`/`submissive`/`devoted` are intentional, not collapsed into "trust+agency" because users want the explicit power exchange framing.

## Questions

1. For each state: Is my semantic definition correct? What am I missing about the phenomenology?

2. Are there states I should add? (Previous feedback suggested `reactance` as inverse state, `tension` as somatic state)

3. Are any states redundant? (e.g., is `receptive` vs `suggestible` a meaningful distinction in practice?)

4. Does the decay hierarchy make sense? Fast-decay states need constant reinforcement; slow-decay states accumulate over time.

5. For identity work (`bimbo`, `dumbdown`): Is "requires empty, produces dissociated + identity_flux" the right model?

---

[PASTE playlist_mana.json HERE]

---

[PASTE MANA_MODEL_ANALYSIS.md "Part 1: State Semantics" section HERE]
```

### Usage Notes for Prompt C

1. Replace the bracketed sections with actual file contents
2. This is a long prompt - GPT Pro handles it fine, but expect a detailed response
3. The goal is getting full prescriptive semantics for each state so the model is self-documenting
4. May trigger some hedging on bimbo/identity content - focus on the structural feedback

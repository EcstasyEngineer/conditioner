# Playlist Stat Model

Reference documentation for the stat-based playlist generation system.

## Overview

The playlist generator uses a **stat model** to sequence audio modules. Each module declares:
- `minimum`: Stats needed for the module to be effective (optional)
- `maximum`: Stat ceilings above which the module is inappropriate (optional, rare)
- `modifies`: How the module changes stats (positive = increase, negative = decrease)

### Generator Algorithm

1. Start with all stats at 0
2. Pick an opener (required first module)
3. Loop until target duration reached:
   - Apply decay for previous module's duration (before checking requirements)
   - Filter modules where current stats >= `minimum` requirements
   - Filter modules where current stats <= `maximum` constraints
   - Select randomly from valid modules
   - Apply `modifies` using logarithmic scaling (see below)
4. End with a closer (required last module)

### Stat Scaling

**Production (logarithmic)**: Harder to max out. Diminishing returns as you approach 100.

```
new_stat = stat + amount * (1 - stat/100)
```

Example: If `absorption` is 60 and module adds +30:
- Linear would give: 60 + 30 = 90
- Logarithmic gives: 60 + 30 * (1 - 0.6) = 60 + 12 = 72

**Decay (linear)**: Stats fall at a constant rate per minute.

```
new_stat = max(0, stat - decay_per_minute * minutes)
```

This creates **"hard to build, easy to lose"** dynamics - matching how psychological states actually work. Deep trance takes effort to achieve but surfaces quickly when disrupted.

**Clamping**: All stats are clamped to [0, 100].

### Stat Behavior Types

| Type | Behavior | Examples |
|------|----------|----------|
| **Mana** | Resource to build and spend. | `absorption`, `receptive`, `suggestible`, `trust` |
| **Strain** | Accumulates with work. High = saturation. | `identity_flux` |
| **Depth** | Can oscillate. Resource-like and strain-like. | `dissociated`, `empty` |

These types are conceptual - the generator uses the same formulas for all stats. Stickiness is controlled by decay rate: slow-decay stats (0.2-0.3/min) are naturally persistent.

---

## The 12 Stats

| Stat | Decay/min | Type | What it measures |
|------|-----------|------|------------------|
| `absorption` | 1.5 | Mana | Trance depth, attentional capture |
| `dissociated` | 1.5 | Depth | Ego dissolution, "gone" state |
| `aroused` | 1.5 | Mana | Sexual activation |
| `empty` | 1.0 | Depth | Mental quietness |
| `anticipation` | 0.8 | Mana | Wanting more |
| `suggestible` | 0.5 | Mana | Accepting suggestions as true |
| `identity_flux` | 0.4 | Strain | Accumulated identity work |
| `receptive` | 0.3 | Mana | Openness, barriers lowered |
| `obedient` | 0.3 | Mana | Command-following readiness |
| `submissive` | 0.3 | Mana | Power differential accepted |
| `devoted` | 0.2 | Mana | Emotional attachment |
| `trust` | 0.2 | Mana | Perceived safety and rapport |

All stats range 0-100, start at 0, and decay toward 0 over time.

### Decay Categories

```
FAST DECAY (1.0-1.5/min) - expensive to maintain
├── aroused (1.5)
├── absorption (1.5)
├── dissociated (1.5)
└── empty (1.0)

MEDIUM DECAY (0.4-0.8/min)
├── anticipation (0.8)
├── suggestible (0.5)
└── identity_flux (0.4)

SLOW DECAY (0.2-0.3/min) - persistent, sticky
├── receptive (0.3)
├── obedient (0.3)
├── submissive (0.3)
├── devoted (0.2)
└── trust (0.2)
```

---

## Stat Semantics

What each stat means at its extremes.

### absorption
| At 0 | At 100 |
|------|--------|
| Fully present, analytical, clock-watching | Completely absorbed, time distortion, "I was gone" |

### receptive
| At 0 | At 100 |
|------|--------|
| Skeptical, guarded, "prove it to me" | No critical filter, "whatever you say" |

### suggestible
| At 0 | At 100 |
|------|--------|
| Suggestions don't stick, slides off | Statements become facts upon hearing |

### empty
| At 0 | At 100 |
|------|--------|
| Normal busy mind, thoughts competing | No thoughts at all, "I can't think" |

### dissociated
| At 0 | At 100 |
|------|--------|
| Normal self-awareness, clear identity | Complete ego dissolution, memory gaps |

### obedient
| At 0 | At 100 |
|------|--------|
| Commands are suggestions, "make me" | Commands execute without consideration |

### submissive
| At 0 | At 100 |
|------|--------|
| Equal footing, no power dynamic | Complete surrender, "I am yours" |

### devoted
| At 0 | At 100 |
|------|--------|
| No emotional investment, "just audio" | Worship-level attachment, will do anything |

### anticipation
| At 0 | At 100 |
|------|--------|
| Take it or leave it, easy to stop | Strong pull, "don't stop" energy |

### aroused
| At 0 | At 100 |
|------|--------|
| No sexual component | Highly activated, hard to focus on other content |

### trust
| At 0 | At 100 |
|------|--------|
| Guarded, unsafe, may exit | Complete safety, will follow anywhere |

### identity_flux
| At 0 | At 100 |
|------|--------|
| Solid self-concept, "I know who I am" | Complete identity saturation, mind needs to settle |

---

## Module Schema

### Required Fields

```json
{
  "tier": "opener|universal|core|specialization|utility|closer",
  "duration_s": 300,
  "modifies": { "stat": delta },
  "description": "What the module does"
}
```

### Optional Fields

```json
{
  "minimum": { "stat": min_value },
  "maximum": { "stat": max_value }
}
```

### Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `tier` | Yes | Module category for sequencing |
| `duration_s` | Yes | Length in seconds |
| `modifies` | Yes | Stat deltas. Positive = increase, negative = decrease. |
| `description` | Yes | Human-readable summary |
| `minimum` | No | Stat floors. Module invalid if not met. |
| `maximum` | No | Stat ceilings. Module invalid if exceeded. Rare. |

### Tiers

| Tier | Purpose |
|------|---------|
| opener | Start session, build foundation |
| universal | Amplifiers, deepeners |
| core | Main content themes |
| specialization | Advanced/niche content |
| utility | Bridges, consent gates, transitions |
| closer | End session, return to baseline |

---

## Examples

### Opener (no minimum)

```json
{
  "tier": "opener",
  "duration_s": 300,
  "modifies": {
    "absorption": 30,
    "receptive": 50,
    "suggestible": 20,
    "trust": 40
  },
  "description": "Session opener. Establishes consent, begins relaxation."
}
```

### Core module (with minimum)

```json
{
  "tier": "core",
  "duration_s": 470,
  "minimum": { "receptive": 30, "suggestible": 20 },
  "modifies": {
    "absorption": 25,
    "obedient": 60,
    "submissive": 30
  },
  "description": "Command following. Builds compliance patterns."
}
```

### Module with negative modifies

```json
{
  "tier": "universal",
  "duration_s": 570,
  "minimum": { "receptive": 20 },
  "modifies": {
    "absorption": 30,
    "empty": 70,
    "receptive": 20,
    "suggestible": 30,
    "anticipation": -10
  },
  "description": "Mental clearing. Thoughts emptied, clean slate."
}
```

### Closer (brings stats down)

```json
{
  "tier": "closer",
  "duration_s": 300,
  "modifies": {
    "absorption": -80,
    "suggestible": -50,
    "empty": -60,
    "dissociated": -100,
    "receptive": -40,
    "identity_flux": -50,
    "trust": 20
  },
  "description": "Session closer. Safe return to awareness."
}
```

### Module with maximum (rare)

```json
{
  "tier": "utility",
  "duration_s": 180,
  "maximum": { "absorption": 30 },
  "modifies": {
    "receptive": 40,
    "trust": 30
  },
  "description": "Early calibration. Needs listener still alert."
}
```

---

## Tagging Guide

When adding stat metadata to audio files.

### What does this module DO?

| If the module... | It likely modifies... |
|------------------|----------------------|
| Deepens trance, focuses attention | `absorption: +25` |
| Lowers defenses, builds rapport | `receptive: +30` |
| Makes suggestions feel true | `suggestible: +40` |
| Quiets the mind, stops thoughts | `empty: +50` |
| Creates ego dissolution, "gone" feeling | `dissociated: +40` |
| Builds command-following reflexes | `obedient: +50` |
| Establishes power differential | `submissive: +40` |
| Creates emotional attachment | `devoted: +30` |
| Builds wanting, "more please" | `anticipation: +50` |
| Sexually activates | `aroused: +40` |
| Does identity transformation | `identity_flux: +40` |
| Establishes safety | `trust: +30` |
| Brings listener back up | `absorption: -60`, `dissociated: -80` |

### What minimums does this module need?

| If the module... | It likely needs... |
|------------------|-------------------|
| Uses direct suggestions | `suggestible: 20` |
| Assumes trance depth | `absorption: 25` |
| Needs mental quiet | `empty: 20` |
| Assumes power dynamic | `submissive: 25` |
| Needs compliance patterns | `obedient: 20` |
| Builds on arousal | `aroused: 20` |
| Assumes emotional connection | `devoted: 20` |

---

## Session Rules

```json
{
  "required_opener": ["intro", "welcome"],
  "required_closer": ["wakener"],
  "intermission_module": "bambi_intermission",
  "target_duration_minutes": 30,
  "min_tracks": 3,
  "max_tracks": 6
}
```

- Sessions must start with an opener and end with a closer
- `intermission_module` is played between sessions when user remains in voice channel
- Generator selects randomly from valid modules at each step

---

## Orchestration Heuristics

Guidance for quality playlists. Not enforced by the generator, but good to know when tagging:

- **High dissociation reduces retention**: Suggestion-heavy modules are less effective when `dissociated > 70`
- **Stickiness combo**: `devoted` + `anticipation` together creates strong session-to-session engagement
- **Arousal compliance is brittle**: `aroused` can spike `obedient` temporarily, but the effect is fragile
- **Relational stats fatigue**: `obedient`, `submissive`, `devoted` have diminishing returns from overuse
- **Identity saturation**: High `identity_flux` means the mind needs to settle before more identity work

---

## Future Considerations

### User Profile Integration

User preferences could inform:
- Initial stat baselines (returning vs new listener)
- Preferred content themes
- Session length preferences

See issue #70.

### Additional Mechanics (Deferred)

- **Novelty/habituation**: Same module twice has diminishing returns
- **Arc shaping**: Session intensity curves
- **Inter-session memory**: Stats that persist between sessions

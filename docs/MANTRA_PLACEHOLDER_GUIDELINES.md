# Mantra Placeholder Usage Guidelines

## Executive Summary

This document analyzes the usage of `{subject}` and `{controller}` placeholders across mantra themes and provides best practices for psychological effectiveness in hypnotic conditioning content.

## JSON Schema Reference

### Complete Mantra Theme Schema

```json
{
  "theme": "string",           // Required: Theme identifier (lowercase, no spaces)
  "description": "string",     // Required: Theme description shown in /mantra list_themes
  "base_difficulty": number,   // Required: Average of all base_points (calculated)
  "variance": number,          // Required: Statistical variance of base_points
  "mantras": [                 // Required: Array of mantra objects
    {
      "text": "string",        // Required: Mantra text with optional {subject} and {controller} placeholders
      "difficulty": "string",  // Required: One of: "basic", "light", "moderate", "deep", "extreme"
      "base_points": number    // Required: Point value based on difficulty tier
    }
  ]
}
```

### Difficulty Tiers and Point Ranges

| Difficulty | Base Points Range | Description |
|------------|------------------|-------------|
| basic | 10-15 | Simple affirmations, entry-level content |
| light | 20-30 | Slightly suggestive, building concepts |
| moderate | 35-45 | Clear D/s dynamics, moderate intensity |
| deep | 60-80 | Strong conditioning, advanced concepts |
| extreme | 100-120 | Intense content, complete submission |

### Placeholder System

The bot supports exactly two placeholders:
- `{subject}` - Replaced with user's chosen pet name (e.g., "toy", "pet", "slave")
- `{controller}` - Replaced with user's chosen dominant title (e.g., "Master", "Mistress", "Goddess")

**IMPORTANT**: Use `{controller}` not `{dominant}`. All themes have been standardized to use `{controller}`.

### How the Bot Uses Theme Data

1. **Theme Loading** (`load_themes()`)
   - Loads all `*.json` files from `/mantras/themes/`
   - Stores themes in memory indexed by theme name
   - Validates JSON structure on load

2. **Theme Display** (`/mantra list_themes`)
   - Shows `description` field from each theme JSON
   - Displays count of mantras available
   - Sorted alphabetically by theme name

3. **Mantra Selection**
   - Randomly selects from user's active themes
   - Weights selection toward moderate difficulty
   - Filters by difficulty based on user performance

4. **Text Processing** (`format_mantra()`)
   ```python
   formatted = mantra_text.format(
       subject=subject,      # User's pet name
       controller=controller # User's dominant title
   )
   ```
   - Replaces `{subject}` with user's pet name
   - Replaces `{controller}` with user's dominant title
   - Capitalizes first letter of result

5. **Point Calculation**
   - Uses `base_points` from the selected mantra
   - Applies difficulty multiplier (currently only for extreme: 0.8x)
   - Adds speed bonus (up to +30 points)
   - Adds streak bonus (up to +100 points)
   - Applies public channel multiplier (2.5x if applicable)

### Important Implementation Notes

- **Case Sensitivity**: Theme names must be lowercase in JSON
- **No Spaces**: Theme names cannot contain spaces
- **File Naming**: `themename.json` (no .draft extension for active themes)
- **Required Fields**: All fields in schema are required
- **Placeholder Format**: Must use Python string format syntax: `{subject}` not `${subject}` or `{{subject}}`

## Current State Analysis

### Placeholder Usage Statistics

| Theme | {subject} | {controller} | Identity-Heavy Rating |
|-------|-----------|--------------|---------------------|
| acceptance | 12 | 15 | Moderate |
| addiction | 10 | 15 | High |
| bimbo | 9 | 13 | Very High |
| brainwashing | 9 | 15 | Very High |
| drone | 0 | 8 | Extremely High |
| obedience | 9 | 16 | High |
| suggestibility | 9 | 15 | Moderate |

### Key Findings

1. **Third-Person Distance Problem**: Using `{subject}` in identity transformation themes creates psychological distance that undermines internalization.

2. **Identity-Heavy Themes**: Themes focused on identity transformation (drone, bimbo, brainwashing) should minimize or eliminate `{subject}` usage.

3. **Successful Pattern**: The drone theme correctly avoids `{subject}` entirely, using "this unit/drone" instead.

## Classification System

### Identity-Heavy Themes
Themes that fundamentally alter or replace the user's sense of self.

**Extremely High**
- Complete dehumanization or non-human identity
- Examples: drone, robot, object, furniture

**Very High**
- Major personality transformation
- Examples: bimbo, slave, doll, pet

**High**
- Strong behavioral identity shifts
- Examples: addiction, worship, servant

**Moderate**
- Mental state changes without core identity shift
- Examples: acceptance, suggestibility, focus

**Low**
- Skill or behavior focused
- Examples: productivity, fitness, self-care

## Best Practice Guidelines

### For Identity-Heavy Themes (High to Extremely High)

**DON'T USE {subject}:**
```
❌ "{subject} is becoming a perfect drone"
❌ "{subject} has no thoughts anymore"
```

**DO USE:**
```
✓ "I am becoming a perfect drone"
✓ "This drone has no thoughts anymore"
✓ "You are just a unit now"
✓ "My mind belongs to {controller}"
```

### For Moderate to Low Identity Themes

**{subject} CAN BE EFFECTIVE:**
```
✓ "{subject} feels so relaxed"
✓ "Good girls like {subject} always focus"
✓ "{subject} accepts {controller}'s guidance"
```

### Universal Guidelines

1. **Always use {controller} for dominant references** - standardized across all themes
2. **First-person creates strongest internalization** - "I am..." > "You are..." > "{subject} is..."
3. **Identity self-reference reinforces transformation** - "This bimbo thinks..." instead of "{subject} thinks..."

## Psychological Rationale

### Why {subject} Undermines Identity Themes

1. **Third-Person Dissociation**: "Toy is becoming a drone" creates observer perspective
2. **Maintains Separation**: Preserves distinction between current self and target identity
3. **Reduces Immersion**: Breaks the hypnotic flow by referencing external identity

### When {subject} Enhances Experience

1. **Reinforces Chosen Pet Name**: In non-identity contexts
2. **Creates Positive Association**: "Good {subject}" patterns
3. **Maintains Relationship Dynamic**: Shows possession without identity change

## Recommendations for Existing Themes

### Immediate Actions

1. **Revise bimbo.json**: Replace `{subject}` with first-person or "this bimbo"
2. **Review brainwashing.json**: Reduce `{subject}` usage in identity-altering mantras
3. **Update addiction.json**: Consider reducing `{subject}` in extreme difficulties

### Theme-Specific Recommendations

**acceptance.json** - Current usage is appropriate (Moderate identity)

**addiction.json** - Consider reducing `{subject}` in extreme difficulties

**bimbo.json** - Major revision needed:
- Replace "{subject} is getting giggly" → "I'm getting so giggly"
- Replace "{subject} is too pretty to think" → "This bimbo is too pretty to think"

**brainwashing.json** - Moderate revision needed for extreme mantras

**drone.json** - Excellent identity handling, properly uses {controller}

**obedience.json** - Current usage acceptable, minor tweaks for extreme

**suggestibility.json** - Current usage is appropriate

## Guidelines for Future Themes

### High Identity Themes to Avoid {subject}
- doll, puppet, toy
- slave, property, object  
- pet variants (kitten, puppy, cow)
- mindless, blank, empty
- slut, whore, fucktoy

### Themes Where {subject} Works Well
- relaxation, focus, meditation
- pleasure, arousal, sensitivity
- trust, safety, comfort
- learning, intelligence, creativity
- service, devotion (when not identity-based)

## Implementation Checklist

When creating or reviewing a theme:

1. **Classify Identity Level** (Extremely High → Low)
2. **For High+ Identity Themes:**
   - [ ] Remove or minimize {subject}
   - [ ] Use first-person or identity self-reference
   - [ ] Ensure {controller} is used for authority
3. **For Moderate/Low Identity Themes:**
   - [ ] {subject} can be used appropriately
   - [ ] Balance with first-person for variety
4. **All Themes:**
   - [ ] Consistent placeholder usage throughout
   - [ ] Progressive intensity matches language choices
   - [ ] Extreme difficulties handle identity appropriately

## Examples of Proper Usage

### Extremely High Identity (drone)
```
Basic: "Systems activating"
Light: "This unit obeys"
Moderate: "Drone programming overrides human thoughts"
Deep: "I am nothing but {controller}'s drone"
Extreme: "Humanity deleted, only drone remains"
```

### Very High Identity (bimbo)
```
Basic: "Thinking is hard"
Light: "Giggles come so easily"
Moderate: "This bimbo loves being dumb"
Deep: "My mind is pink and empty"
Extreme: "I exist only as {controller}'s perfect bimbo"
```

### Moderate Identity (acceptance)
```
Basic: "{subject} feels open"
Light: "I accept what comes"
Moderate: "{subject} surrenders to {controller}"
Deep: "Complete acceptance fills me"
Extreme: "I have no will but {controller}'s"
```

## Conclusion

The effectiveness of hypnotic mantras depends heavily on proper pronoun usage. Identity transformation themes must minimize psychological distance by avoiding third-person references to the subject. This creates deeper internalization and more effective conditioning experiences while maintaining user safety through consensual framework.

---

*Version 1.0 - Created June 2024*
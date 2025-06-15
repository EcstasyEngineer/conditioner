# Mantras System Documentation

## Overview
The mantras system provides themed hypnotic affirmations that users can "capture" for points. Each theme contains mantras at various difficulty levels with corresponding point values.

## Theme File Format
Each theme is a JSON file in the `themes/` directory with the following structure:

```json
{
  "theme": "theme_name",
  "description": "Description of the theme",
  "mantras": [
    {
      "text": "The mantra text with {pet_name} and {dominant_title} variables",
      "difficulty": "basic|light|moderate|deep|extreme",
      "base_points": 10-120
    }
  ]
}
```

## Difficulty Tiers
- **basic**: 10-15 points - Simple, comfortable affirmations
- **light**: 20-30 points - Slightly suggestive content
- **moderate**: 35-50 points - Clear D/s dynamics
- **deep**: 60-80 points - Strong conditioning statements
- **extreme**: 90-120 points - Most intense content (gated)

## Template Variables
- `{pet_name}`: User's chosen pet name (e.g., "puppy", "kitten", "pet")
- `{dominant_title}`: User's chosen dominant title ("Master" or "Mistress")

## Adding New Themes
1. Create a new JSON file in `themes/` directory
2. Follow the format above with at least 3 mantras per difficulty tier
3. Test that all template variables are used correctly
4. Consider progression - easier mantras should build toward harder ones

## Current Themes
- **suggestibility**: Foundation theme for openness and receptivity
- **acceptance**: Foundation theme for surrender and letting go

## Planned Themes
- **obedience**: Following commands and instructions
- **addiction**: Craving and compulsion loops
- **brainwashing**: Mental reprogramming themes
- **mindbreak**: Total mental surrender (extreme, gated)
- **bimbo**: Playful identity transformation
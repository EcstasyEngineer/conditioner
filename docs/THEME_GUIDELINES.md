# Mantra Theme Development Guide

This guide provides best practices for creating new mantra themes. Following these guidelines ensures quality and consistency.

## 1. Theme File Structure

All themes are JSON files in the `/mantras/` directory. Active themes are named `themename.json`, while drafts should be named `themename.json.draft` to prevent them from being loaded.

For readability, each mantra object should be on a single line. See `mantras/acceptance.json` for a reference implementation.

```json
{
  "theme": "theme_name",
  "description": "Brief, 10-20 word summary of the theme's focus.",
  "mantras": [
    { "text": "Mantra text with {subject} and {controller} variables.", "difficulty": "basic", "base_points": 10 },
    { "text": "Another mantra text example.", "difficulty": "basic", "base_points": 12 }
  ]
}
```

### Requirements & Distribution
- **Theme Name**: A lowercase, single-word identifier.
- **Template Variables**: All mantras must use `{subject}` and `{controller}` for user-specific names.
- **Mantra Count**: Each theme should have 25-30 mantras. The distribution across difficulties can vary to fit the theme's focus (e.g., a theme like 'brainwashing' may have more 'deep' and 'extreme' mantras).
- **Formatting**: Each mantra object must be on a single line to improve readability.

### Difficulty & Point Values
Each difficulty has a specific point range and standardized values to ensure balance.

| Difficulty | Description | Point Values |
|---|---|---|
| **Basic** | Introduction to the concept. Establishes a gentle foundation. <br> - `"I obey without question"` <br> - `"Thinking is hard, smiling is easy"` <br> - `"I accept and surrender"` | `10-15` |
| **Light** | Acceptance and normalization. The theme becomes a positive and normal part of the user's mindset. <br> - `"Resistance fades like mist"` <br> - `"Obedience is instinctive now"` <br> - `"Every word echoes as truth"` | `20-30` |
| **Moderate** | Integration and identification. The user begins to identify with the theme on a personal level. <br> - `"Surrender defines my identity"` <br> - `"My comfort zone is obedience"` <br> - `"{controller}'s brainwashing defines me"` | `35-45` |
| **Deep** | Core identity modification. The theme becomes a fundamental part of the user's being, overriding previous beliefs. <br> - `"My thoughts are no longer my own"` <br> - `"{controller} owns my decision-making"` <br> - `"Compliance saturates every nerve"` | `60-80` |
| **Extreme** | Total and permanent transformation. The theme is an irreversible, absolute reality. <br> - `"The brainwashing is permanent and irreversible"` <br> - `"I exist only to carry out orders"` <br> - `"All resistance deleted—forever obedient"` | `100-120` |

## 2. Content & Language Guidelines

### Gender Neutrality
All mantras **must** be gender-neutral. The `{controller}` variable can represent any gender, and the text must flow naturally. Do not use gendered pronouns outside of the template variables.

- **Good**: `"{controller} owns {subject}'s thoughts."`
- **Bad**: `"She owns {subject}'s thoughts."`

### Language Patterns
- **Use**: First-person (`I am...`), third-person (`{subject} becomes...`), present/progressive tense (`is`, `becoming`), and declarative statements.
- **Avoid**: Questions, uncertainty (`maybe`, `might`), past tense, and negative framing.

### Intensity Markers by Difficulty
Use specific language to mark the intensity of each difficulty level.

| Difficulty | Language Style | Keywords |
|---|---|---|
| **Basic** | Gentle introduction | `enjoy`, `like`, `feel`, `want`, `starting to` |
| **Light** | Growth and regularity | `growing`, `building`, `daily`, `often`, `need`, `crave` |
| **Moderate** | Identity and control | `I am`, `becoming my nature`, `controls`, `defines`, `shapes` |
| **Deep** | Core change, near-completion | `consumed`, `saturated`, `to my core`, `fundamental`, `nearly total` |
| **Extreme**| Permanence and absolutes | `forever`, `permanently`, `irreversibly`, `nothing but`, `only exist to` |

**Key Rule**: Permanence language (`forever`, `irreversibly`) and absolute statements (`nothing but`, `only exist to`) are reserved **exclusively** for the **Extreme** difficulty.

## 3. Writing & Quality Assurance

### Writing Process
1.  **Define Theme**: Summarize the core concept in 3-5 words and list 10-15 related keywords.
2.  **Map Difficulty**: Write one example mantra for each difficulty level to establish a clear progression.
3.  **Vary Mantras**: For each level, vary the perspective (I/my vs. {subject}), focus (mental/emotional), and scope (specific to general).
4.  **Test Flow**: Check that each mantra reads naturally with different `{subject}` (e.g., puppet, kitten) and `{controller}` (e.g., Master, Mistress) values.

### Quality Checklist
Before finalizing a theme, ensure it meets these standards:
- [ ] 25-30 total mantras.
- [ ] An appropriate distribution of difficulties per the .
- [ ] Correct template variables (`{subject}`, `{controller}`).
- [ ] All text is gender-neutral.
- [ ] Clear, consistent progression from Basic to Extreme.
- [ ] Adheres to standardized point values.
- [ ] No duplicate concepts.
- [ ] Tested with various subject/controller combinations.

### Testing Recommendations
- Have others review for typos, flow, and intensity.
- Use blind comparison tests to verify difficulty ordering.
- Ensure intensity markers match their assigned difficulty.
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

## 4. Quality Assessment Methodology

When performing systematic QA analysis of mantra themes, use the following comprehensive scoring framework:

### QA Scoring Criteria

**Scoring Weight Distribution:**
- **Hypnotic Effectiveness (30%)**: Progressive conditioning strength, psychological impact, trance compatibility
- **Content Quality (25%)**: Writing quality, mantra variety, clear progression, grammar and flow
- **Technical Implementation (25%)**: File structure compliance, consistent formatting, balanced point progression
- **Thematic Coherence (20%)**: Mantras align with theme concept, unified user experience

### Scoring Scale
- **Excellent (90-100)**: Ready for immediate activation, gold standard quality
- **Good (75-89)**: High quality, minor improvements recommended
- **Adequate (60-74)**: Functional but needs enhancement for optimal effectiveness
- **Needs Work (40-59)**: Significant improvements required before activation
- **Poor (0-39)**: Major overhaul or retirement recommended

### Assessment Categories

**Hypnotic Effectiveness Evaluation:**
- Does the theme create a clear psychological progression?
- Are mantras designed to bypass critical thinking?
- Does the difficulty progression enhance conditioning over time?
- Are the mantras compatible with trance states and repetitive conditioning?

**Content Quality Evaluation:**
- Are mantras well-written with proper grammar and flow?
- Is there sufficient variety to prevent monotony?
- Do mantras read naturally with different subject/controller combinations?
- Is the language appropriate for the target difficulty level?

**Technical Implementation Evaluation:**
- Does the file follow standard JSON structure (no "intensity", "base_difficulty", etc.)?
- Are mantras formatted as one per line for readability?
- Do point values follow the standardized progression (10-15, 20-30, 35-45, 60-80, 100-120)?
- Are all required properties present and correctly named?

**Thematic Coherence Evaluation:**
- Do all mantras support the central theme concept?
- Is the user experience unified and immersive?
- Does the theme description accurately represent the content?
- Are there conflicting or off-theme mantras that dilute the experience?

### Quality Assurance Process
1. **Initial Assessment**: Score each category individually on 0-100 scale
2. **Weighted Calculation**: Apply percentage weights to determine overall score
3. **Issue Documentation**: Note specific problems and improvement opportunities
4. **Recommendations**: Provide actionable feedback for enhancement
5. **Activation Readiness**: Determine if theme is ready for user deployment

### Common Quality Issues
- **Repetitive Content**: Multiple mantras with identical structure or meaning
- **Inconsistent Difficulty**: Mantras placed in wrong difficulty categories
- **Poor Progression**: No clear escalation from basic to extreme
- **Technical Debt**: Non-standard file structure or property naming
- **Thematic Drift**: Mantras that don't align with the core theme concept

This methodology ensures consistent, objective evaluation of all mantra themes and provides clear guidance for systematic improvement.
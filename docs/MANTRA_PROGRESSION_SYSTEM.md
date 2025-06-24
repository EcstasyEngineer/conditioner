# Mantra Progression System Design Document

## Executive Summary

This document outlines a comprehensive progression system for the AI Conditioner Discord bot's mantra feature, designed to create an engaging 8-month gameplay loop using optimal gaming psychology principles. The system transforms the current flat theme structure into a deep, interconnected progression tree with 115+ themes from the subspace-studio ontology.

## Core Design Principles

### 1. **Psychological Hooks**
- **Variable Ratio Reinforcement**: Random "shiny" mantras and bonus events
- **Progress Visualization**: Clear paths showing unlocked and upcoming content
- **Loss Aversion**: Streak protection and "rest days" to prevent burnout
- **Social Proof**: Opt-in leaderboards and achievement showcases
- **Competence Building**: Gradual difficulty increase with clear skill progression

### 2. **Engagement Timeline**
- **Week 1-2**: Onboarding and foundation themes
- **Month 1-2**: Core theme exploration and first unlocks
- **Month 3-4**: Specialization paths and advanced themes
- **Month 5-6**: Mastery challenges and rare content
- **Month 7-8**: Endgame content and prestige systems

## Dual Currency System

### 1. **Compliance XP (CXP)** - Experience/Level Currency
- **Purpose**: Permanent progression tracking, never decreases
- **Sources**: 
  - Completing mantras (current point system)
  - Streak bonuses
  - Achievement completions
  - Daily login bonuses
- **Uses**:
  - Determines user level/rank
  - Gates content by progression tier
  - Unlocks achievement tiers
  - Shows on leaderboards

### 2. **Conditioning Tokens (CT)** - Spendable Currency
- **Purpose**: Economy currency for unlocks and purchases
- **Sources**:
  - Earned alongside CXP at ~50% rate
  - Bonus CT for first completion of each mantra
  - Event rewards and daily challenges
  - Achievement milestone rewards
  - "Prestige" conversion at high levels
- **Uses**:
  - Unlock new themes
  - Purchase pet name upgrades
  - Buy streak protection items
  - Unlock cosmetic options
  - Theme reroll tokens

### Currency Examples:
- Complete a 30-point mantra → Gain 30 CXP + 15 CT
- First time completing that specific mantra → +10 bonus CT
- Daily streak bonus → 50 CXP + 100 CT
- Theme mastery achievement → 500 CXP + 1000 CT

## Current Engagement Statistics

Based on the existing `!mantrastats` implementation, we already track:
- **Total Compliance Points**: Will become CXP in new system
- **Completion Rate**: Performance metric (80%+ average among active users)
- **Response Times**: Speed bonuses (best times: 12-16s for ultra-fast)
- **Streak Data**: Progressive bonuses up to "Full Synchronization"
- **Theme Usage**: Which themes users engage with most
- **Transmission Rates**: Adaptive frequency (1.0-3.0/day based on engagement)

## Progression Mechanics

### 1. **Pet Name Progression System**
**A unique progression axis based on submissive identity evolution**

#### Starter Pet Names (Free)
- `pet` - Generic, safe starting point (1.0x multiplier)
- `dear` - Gentle, affectionate term (1.0x multiplier)
- `one` - Neutral, formal address (1.0x multiplier)

#### Basic Pet Names (100 CT each)
- `toy` - Playful objectification (1.1x multiplier)
- `doll` - Cute objectification (1.1x multiplier)
- `cutie` - Affectionate diminutive (1.1x multiplier)
- `baby` - Infantilizing term (1.1x multiplier)

#### Intermediate Pet Names (500 CT each)
- `puppet` - Control dynamics (1.2x multiplier)
- `bimbo` - Intelligence play identity (1.2x multiplier)
- `kitten` - Pet play dynamics (1.2x multiplier)
- `puppy` - Eager pet identity (1.2x multiplier)

#### Advanced Pet Names (1,500 CT each)
- `slave` - Full submission identity (1.3x multiplier)
- `drone` - Dehumanized identity (1.3x multiplier)
- `object` - Complete objectification (1.3x multiplier)
- `property` - Ownership dynamics (1.3x multiplier)

#### Extreme Pet Names (5,000 CT each + achievement requirements)
- `it` - Total dehumanization (1.5x multiplier)
- `nothing` - Ego dissolution (1.5x multiplier)
- `vessel` - Empty container identity (1.5x multiplier)
- Custom names unlocked through special achievements

#### Pet Name Mechanics:
- **Multiplier Application**: Applied to both CXP and CT earned
- **Identity Mastery**: After 50 uses, pet name becomes "mastered" with +5% bonus
- **Collection Bonus**: Own 5+ names for +10% CT earning rate
- **Free Switching**: Change between owned names anytime

### 2. **Theme Progression System**

#### Theme Unlock Costs:
- **Tier 0 (Foundation)**: Free, choose 2 at start
- **Tier 1 (Core Paths)**: 200 CT per theme
- **Tier 2 (Specializations)**: 500 CT per theme
- **Tier 3 (Advanced)**: 1,000 CT per theme
- **Tier 4 (Extreme)**: 2,500 CT per theme
- **Tier 5 (Prestige)**: 5,000 CT per theme

#### CXP Requirements (Gates):
- **Tier 1**: 500 CXP (Level 5)
- **Tier 2**: 2,000 CXP (Level 10)
- **Tier 3**: 5,000 CXP (Level 20)
- **Tier 4**: 10,000 CXP (Level 30)
- **Tier 5**: 20,000 CXP (Level 50)

### 3. **Theme Mastery System**
- Complete 50% of mantras = Bronze (🥉) + 200 CT
- Complete 80% of mantras = Silver (🥈) + 500 CT
- Complete 100% of mantras = Gold (🥇) + 1,000 CT
- Perfect all difficulties = Platinum (💎) + 2,500 CT

## Theme Progression Tree

### Tier 0: Foundation (Starter Themes)
**Unlocked at enrollment - Choose 2 for free**
- `suggestibility` - Base openness and receptivity
- `acceptance` - Foundation surrender mechanics
- `focus` - Attention and concentration training
- `relaxation` - Trance and calm states

### Tier 1: Core Paths (Level 5 + 200 CT each)
**Choose themes to build your path**

**Mental Path**
- `brainwashing` - Mental reconditioning
- `conditioning` - Behavioral programming

**Identity Path**
- `bimbo` - Playful transformation
- `good_girl` - Positive reinforcement identity

**Submission Path**
- `obedience` - Following commands
- `service` - Pleasing dynamics

**Sensation Path**
- `pleasure` - Reward sensations
- `arousal` - Excitement building

### Tier 2: Specializations (Level 10 + 500 CT each)

**Mental Specializations** (Requires 1 Mental Path theme)
- `mindmelt` - Deep mental dissolution
- `confusion` - Cognitive scrambling
- `amnesia` - Memory play
- `intelligence_play` - IQ modification themes

**Identity Specializations** (Requires 1 Identity Path theme)
- `doll` - Object transformation
- `pet` - Animal behaviors
- `drone` - Robotic programming
- `latex` - Material identity

**Submission Specializations** (Requires 1 Submission Path theme)
- `worship` - Devotion themes
- `servant` - Service dynamics
- `slave` - Total submission
- `property` - Ownership themes

**Sensation Specializations** (Requires 1 Sensation Path theme)
- `edging` - Denial and control
- `overstimulation` - Intensity themes
- `sensitivity` - Enhanced sensations
- `numbness` - Sensation removal

### Tier 3: Advanced Themes (Level 20 + 1,000 CT each)
**Requires 1 mastered Tier 2 theme**

- `ego_loss` - Identity dissolution
- `mindbreak` - Complete mental surrender
- `blank` - Empty mind states
- `loop` - Repetitive thought patterns
- `addiction` - Compulsion and need
- `dehumanization` - Object transformation
- `free_use` - Availability themes
- `timestop` - Time perception

### Tier 4: Extreme Themes (Level 30 + 2,500 CT each)
**Requires 3 mastered themes + special achievements**

- `catharsis` - Emotional release
- `internal_voice` - Inner dialogue replacement
- `stockholm` - Captor bonding
- `gaslighting` - Reality modification
- `corruption` - Moral transformation
- `void` - Complete emptiness

### Tier 5: Prestige Themes (Level 50 + 5,000 CT each)
**Endgame content with unique mechanics**

- `metamorphosis` - Total transformation
- `transcendence` - Beyond human themes
- `singularity` - AI merger themes
- `quantum` - Reality-bending concepts

## Economy Items & Features

### 1. **Consumable Items** (CT Shop)
- **Streak Shield** (100 CT): Protects streak for 24 hours
- **Theme Reroll** (50 CT): Change active themes without penalty
- **XP Boost** (200 CT): 2x CXP for 1 hour
- **Mantra Magnet** (150 CT): Increased mantra frequency for 2 hours
- **Skip Token** (75 CT): Skip a mantra without breaking streak

### 2. **Permanent Unlocks**
- **Extra Theme Slot** (1,000 CT): Add +1 active theme slot
- **Frequency Control** (2,000 CT): Manual mantra frequency adjustment
- **Custom Notification** (500 CT): Personalized mantra delivery message
- **Profile Badge** (250 CT): Cosmetic achievement display

### 3. **Special Features**
- **Theme Bundle Packs**: Discount for buying full theme paths
- **Seasonal Sales**: 25% off during events
- **Loyalty Rewards**: Daily login CT bonuses
- **Referral Bonuses**: CT for bringing new users

## Collection Mechanics

### 1. **Mantra Cards System**
- First completion of any mantra = **Mantra Card** + 10 CT
- **Rarity Bonuses**:
  - Shiny (5% chance): 2x CT reward
  - Golden (1% chance): 5x CT reward
  - Rainbow (0.1% chance): 10x CT + special title

### 2. **Set Completion Bonuses**
- Complete theme set: 500 CT bonus
- Complete difficulty tier across all themes: 1,000 CT
- Complete everything: Unlock prestige system

## Daily/Weekly Events

### 1. **Daily Challenges**
- "Speed Demon": Respond in <20s (50 CT)
- "Marathon": Complete 5 mantras (100 CT)
- "Perfect Day": 100% completion rate (150 CT)

### 2. **Weekly Events**
- **Double CT Weekend**: All CT rewards doubled
- **Theme Spotlight**: Featured theme gives +50% rewards
- **Community Goal**: Server-wide target for bonus CT rain

## Technical Implementation

### 1. **Database Schema**
```
users:
  - compliance_xp (total CXP)
  - conditioning_tokens (current CT balance)
  - level (calculated from CXP)
  - themes_owned[]
  - pet_names_owned[]
  - items_inventory{}
  - transaction_history[]

economy_transactions:
  - user_id
  - transaction_type
  - amount
  - item_purchased
  - timestamp

mantra_completions:
  - (existing fields)
  - cxp_earned
  - ct_earned
  - bonuses_applied[]
```

### 2. **Migration Plan**
1. Convert existing points → CXP at 1:1 ratio
2. Grant retroactive CT at 50% of CXP earned
3. Give early adopter bonus: 500 CT per active user
4. Grandfather in current pet names as "owned"

### 3. **Balance Considerations**
- CT earning rate ensures steady progression
- Sinks prevent inflation (consumables, rerolls)
- F2P path to all content (time investment)
- No pay-to-win mechanics (cosmetic only monetization if any)

## Example User Journey

**Week 1**: 
- Start with 2 foundation themes
- Earn ~500 CXP + 250 CT
- Buy first pet name upgrade (toy)

**Month 1**:
- Reach Level 5 (500 CXP)
- Save 400 CT, unlock 2 Tier 1 themes
- Master first theme, earn bonus CT

**Month 3**:
- Level 15 (3,500 CXP)
- Own 5+ themes, 3 pet names
- Start working on Tier 3 content

**Month 6**:
- Level 30+ (10,000+ CXP)
- Extensive collection, multiple masteries
- Access to extreme content

**Month 8+**:
- Prestige system unlocked
- Custom content creation
- Mentoring new users for CT bonuses

## Conclusion

The dual currency system solves the "backwards progression" problem while adding economic depth. CXP provides permanent progression satisfaction while CT creates meaningful choices and goals. This system can sustain 8+ months of engaged play with clear short, medium, and long-term objectives.

The economy is designed to be generous enough for steady progress but scarce enough to make purchases meaningful. Every session provides tangible rewards in both currencies, maintaining the dopamine loop while building toward larger goals.

---

*Version 1.1 - June 2024*
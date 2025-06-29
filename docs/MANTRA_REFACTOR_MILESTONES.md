# Mantra Refactor Implementation Timeline

## Overview
Aggressive refactor focused on enabling new features: tech trees, forced delays, mini-games, events.

## Week 1: Foundation & Quick Wins

### Day 1-2: Basic Structure
- [ ] Create `mantras/` directory structure
- [ ] Split commands into `commands/user.py` and `commands/admin.py`
- [ ] Extract delivery loop to `core/delivery.py`
- [ ] Move views to `views/` with callback pattern
- [ ] Fix circular imports
- [ ] **Success**: Bot runs with new structure, no functional changes

### Day 3-4: State Machine Foundation
- [ ] Implement basic `MantraStateMachine` class
- [ ] Create `UserMantraState` model
- [ ] Replace `active_challenges` dict with state manager
- [ ] Add state persistence to config
- [ ] **Success**: Timeout duplicate logging fixed, states persist

### Day 5-7: Core Abstractions
- [ ] Create `GameMode` base class
- [ ] Wrap current system in `ClassicMode`
- [ ] Extract scheduling logic to `core/scheduler.py`
- [ ] Create `ContentManager` for theme loading
- [ ] **Success**: Ready for new features

## Week 2: Progression & Features

### Day 8-9: Progression Engine
- [ ] Create dual currency model (XP/CT)
- [ ] Implement `ProgressionEngine` 
- [ ] Add level calculation
- [ ] Create migration for existing points → XP
- [ ] **Success**: Users have levels, XP visible in `/mantra status`

### Day 10-11: Tech Tree Foundation
- [ ] Implement theme prerequisites
- [ ] Create unlock checking
- [ ] Add `/mantra tree` command (text version)
- [ ] Build theme shop with CT spending
- [ ] **Success**: Users can unlock new themes

### Day 12-14: Feature System
- [ ] Create `Feature` base class
- [ ] Implement `ForcedDelayFeature`
- [ ] Add feature registration system
- [ ] Hook features into response flow
- [ ] **Success**: Forced delays working for power users

## Week 3: Advanced Features

### Day 15-16: Event System
- [ ] Create `EventManager`
- [ ] Implement holiday content loading
- [ ] Add date-based activation
- [ ] Create first test event
- [ ] **Success**: Special mantras on specific dates

### Day 17-18: Session Game Mode
- [ ] Create `SessionMode` skeleton
- [ ] Implement session state tracking
- [ ] Add basic session flow
- [ ] Create session-specific views
- [ ] **Success**: Basic DM mini-game working

### Day 19-21: Polish & Testing
- [ ] Performance testing with state system
- [ ] Fix any state persistence issues
- [ ] Ensure backward compatibility
- [ ] Update all commands to use new systems
- [ ] **Success**: Everything stable

## Critical Path Items

**Must Have for New Features:**
1. State machine (for delays & sessions)
2. Progression engine (for tech tree)
3. Game mode abstraction (for mini-games)
4. Feature system (for pluggable mechanics)

**Can Defer:**
- Visual tech tree (text version first)
- Complex achievements
- Collaborative modes
- Advanced session mechanics

## Risk Mitigation

**Incremental Deployment:**
- Each week's work can deploy independently
- Old mantras.py kept as backup
- Feature flags for new systems
- Gradual user migration

**Testing Strategy:**
- Dev bot for initial testing
- Volunteer beta testers
- Canary deployment (10% → 50% → 100%)
- Monitor error rates closely

## Success Metrics

### Week 1 Success
- No increase in errors
- Commands respond <100ms
- State persists correctly
- Duplicate logging eliminated

### Week 2 Success  
- XP/levels calculating correctly
- Users can unlock themes
- Forced delays trigger properly
- No performance degradation

### Week 3 Success
- Events activate on schedule
- Sessions maintain state
- All features interoperate
- Ready for future expansion

## Long-term Benefits

**Immediate wins:**
- Fix timeout duplicate logging
- Enable forced delays
- Support tech tree

**Future enablement:**
- Holiday events easy to add
- New game modes plug in
- Complex flows supportable
- Multiple devs can contribute

## Communication Plan

**Week 1:** "Fixing some internal structure, no visible changes"
**Week 2:** "Adding progression system! Check your level with `/mantra status`"
**Week 3:** "New features rolling out - mini-games and special events!"

This aggressive timeline delivers value quickly while building foundation for all planned features.
# Mantra System Migration Plan

## Overview
Aggressive refactor to support tech trees, forced delays, mini-games, and events.

## Current Issues
- 1056-line monolith mixing everything
- No state management for complex flows
- Can't support planned features cleanly
- Circular import hacks from previous "chop and drop"

## Target Architecture
```
mantras/
├── commands/         # All slash/text commands
├── core/            # Delivery engine and state
├── features/        # Pluggable features
├── game_modes/      # Different interaction patterns
├── models/          # Data structures
├── views/           # Discord UI components
└── utils/           # Pure helper functions
```

## Phase 1: Foundation Split (Day 1-2)

### 1. Create Structure
```bash
mkdir -p cogs/dynamic/mantras/{commands,core,features,game_modes,models,views,utils}
touch cogs/dynamic/mantras/__init__.py
```

### 2. Split Commands
```python
# commands/user.py - User slash commands
- /mantra enroll
- /mantra status  
- /mantra settings
- /mantra modules
- /mantra disable

# commands/admin.py - Admin commands
- !mantrastats
- !mantrareset
- Admin-only slash commands

# commands/progression.py (new, empty for now)
- /mantra tree
- /mantra level
- /mantra shop
```

### 3. Extract Core Engine
```python
# core/delivery.py
- deliver_mantras task loop
- send_mantra_to_user()
- handle_mantra_response()

# core/scheduler.py  
- calculate_next_delivery()
- adjust_frequency()
- check_online_status()
```

### 4. Move Views (Fix Circular Imports)
```python
# views/theme_selector.py
class ThemeSelectView:
    def __init__(self, save_callback):
        self.save_callback = save_callback
    
    async def save_themes(self, themes):
        await self.save_callback(themes)

# views/mantra_views.py
- MantraRequestView (with timeout callback)
- MantraResponseView
- MantraDisableOfferView
```

## Phase 2: State Machine (Day 3-4)

### 1. Create State System
```python
# core/state_machine.py
class MantraFlow:
    states = {
        "idle": {"next": ["pending", "maintenance"]},
        "pending": {"next": ["delayed", "awaiting", "timeout"]},
        "delayed": {"next": ["awaiting", "timeout"]},
        "awaiting": {"next": ["completed", "timeout"]},
        "completed": {"next": ["idle"]}
    }
```

### 2. Replace Implicit State
```python
# Before: Scattered flags
if user_id in self.active_challenges:
    if "timeout_count" in config:
        if config["last_timeout"] > cutoff:

# After: Clear state
state = await StateManager.get_user_state(user_id)
if state.current == MantraState.PENDING:
    await state.transition("timeout")
```

### 3. Add State Persistence
```python
# models/user_state.py
@dataclass
class UserMantraState:
    current_state: str
    entered_at: datetime
    context: dict  # Stores challenge, delays, etc
    history: list  # State transitions
```

## Phase 3: Feature Modules (Week 2)

### 1. Forced Delay Feature
```python
# features/forced_delay.py
class ForcedDelay:
    def should_trigger(self, user_state) -> bool
    def get_delay_params(self) -> DelayConfig
    def apply_delay(self, flow: MantraFlow)
```

### 2. Progression System
```python
# core/progression.py
class ProgressionEngine:
    def award_xp(self, encounter)
    def calculate_level(self, total_xp)
    def check_unlocks(self, new_level)
    
# features/tech_tree.py
class TechTree:
    def get_available_nodes(self, user_progress)
    def can_unlock(self, node, user_state)
    def unlock_node(self, node, user_state)
```

### 3. Content Loading
```python
# core/content_loader.py
class ContentManager:
    def load_base_themes(self)
    def load_event_content(self, event_name)
    def get_available_content(self, user_state)
```

## Phase 4: Game Modes (Week 3)

### 1. Abstract Game Mode
```python
# game_modes/base.py
class GameMode(ABC):
    @abstractmethod
    async def start_encounter(self, user, content)
    
    @abstractmethod
    async def handle_timeout(self, user, context)
```

### 2. Refactor Current System
```python
# game_modes/classic.py
class ClassicMantraMode(GameMode):
    # Current implementation moved here
```

### 3. Prepare for New Modes
```python
# game_modes/sessions.py (skeleton)
class SessionMode(GameMode):
    # For mini-game sessions
    
# game_modes/collaborative.py (skeleton)  
class CollaborativeMode(GameMode):
    # For group mantras
```

## Migration Checklist

### Before Starting
- [ ] Full backup of current bot
- [ ] Test environment ready
- [ ] Document current command behavior

### Phase 1 Verification
- [ ] All commands still work
- [ ] No import errors
- [ ] Delivery task runs
- [ ] Views respond correctly

### Phase 2 Verification  
- [ ] State transitions work
- [ ] States persist across restarts
- [ ] Timeout handling improved
- [ ] No duplicate logging

### Phase 3 Verification
- [ ] Features can be toggled
- [ ] XP/progression calculating
- [ ] Content loads dynamically
- [ ] No performance regression

### Phase 4 Verification
- [ ] Classic mode identical to current
- [ ] New modes can be added
- [ ] Clean separation of concerns
- [ ] Ready for new features

## Rollback Plan

Each phase can be rolled back independently:
1. Keep old mantras.py as backup
2. Single import switch in `__init__.py`
3. Test each phase before proceeding
4. Full rollback takes < 5 minutes

## Success Metrics

- **Code Quality**: No file > 400 lines
- **Feature Velocity**: New features in hours, not days
- **Bug Reduction**: State bugs eliminated
- **Performance**: No degradation
- **Maintainability**: Clear where everything lives
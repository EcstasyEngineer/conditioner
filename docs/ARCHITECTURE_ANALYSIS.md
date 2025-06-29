# Aggressive Refactoring Plan for Future Features

## Vision
Transform the mantra system from a monolithic cog into a modular, event-driven architecture that supports complex features like progression systems, mini-games, and dynamic content.

## Upcoming Features That Need Support
- **Mantra Tech Tree** with dual currencies (CXP/CT)
- **Forced Integration Delays** with state management
- **Interactive DM Mini-Games** with sessions
- **Holiday Events** and special content
- **Progression Systems** with achievements
- **Advanced UI** (paginated selections, visual trees)

## Aggressive New Architecture

### Core Domain Split
```
cogs/dynamic/mantras/
├── __init__.py              # Cog registration only
├── commands/
│   ├── __init__.py
│   ├── user.py              # User-facing commands
│   ├── admin.py             # Admin commands
│   ├── progression.py       # New: /mantra tree, level, shop
│   └── minigames.py         # New: Interactive session commands
├── core/
│   ├── __init__.py
│   ├── delivery.py          # Mantra delivery engine
│   ├── state_machine.py     # New: FSM for complex flows
│   ├── progression.py       # New: XP/currency/unlock logic
│   ├── scheduler.py         # Timing and frequency logic
│   └── content_loader.py    # Dynamic theme/event loading
├── features/
│   ├── __init__.py
│   ├── forced_delay.py      # Delay mechanics
│   ├── tech_tree.py         # Tree logic and prerequisites
│   ├── achievements.py      # Achievement tracking
│   └── events.py            # Holiday/special events
├── game_modes/
│   ├── __init__.py
│   ├── classic.py           # Current mantra system
│   ├── sessions.py          # New: DM mini-game sessions
│   └── collaborative.py     # Future: Group mantras
├── models/
│   ├── __init__.py
│   ├── user_state.py        # User progression/state
│   ├── mantra_content.py    # Mantra data structures
│   └── session_state.py     # Game session states
├── views/
│   ├── __init__.py
│   ├── theme_selector.py    # Paginated theme UI
│   ├── tree_display.py      # Visual progression tree
│   ├── shop_interface.py    # CT spending UI
│   └── session_views.py     # Mini-game interactions
└── utils/
    ├── __init__.py
    ├── calculations.py      # Points, XP, multipliers
    ├── validators.py        # Config/state validation
    └── formatters.py        # Text formatting helpers
```

### Key Architectural Changes

#### 1. **State Machine Core**
Replace implicit state with explicit FSM:
```python
class MantraState:
    IDLE = "idle"
    PENDING = "pending"
    DELAYED = "delayed"
    AWAITING = "awaiting"
    COMPLETED = "completed"
    TIMEOUT = "timeout"

class UserMantraFlow:
    def __init__(self, user_id):
        self.state = MantraState.IDLE
        self.context = {}  # Stores flow data
        
    async def transition(self, event):
        # Handle state transitions
        pass
```

#### 2. **Event-Driven Content**
Support dynamic content loading:
```python
class ContentManager:
    def load_theme(self, theme_name):
        # Load from JSON or events/
        pass
        
    def get_holiday_content(self, date):
        # Return special event mantras
        pass
        
    def get_progression_content(self, user_level):
        # Return level-appropriate content
        pass
```

#### 3. **Progression Engine**
Separate progression from delivery:
```python
class ProgressionEngine:
    def calculate_xp(self, encounter):
        # XP calculation logic
        pass
        
    def check_unlocks(self, user_state):
        # Return newly unlocked content
        pass
        
    def get_tech_tree_state(self, user):
        # Return tree visualization data
        pass
```

#### 4. **Game Mode Abstraction**
Support different interaction patterns:
```python
class GameMode(ABC):
    @abstractmethod
    async def start_encounter(self, user):
        pass
        
    @abstractmethod  
    async def handle_response(self, user, response):
        pass

class ClassicMode(GameMode):
    # Current mantra system
    
class SessionMode(GameMode):
    # Mini-game sessions with stakes
```

### Migration Strategy

#### Phase 1: Foundation (Weekend 1)
1. Create directory structure
2. Split current mantras.py by function:
   - Commands → `commands/user.py`
   - Admin → `commands/admin.py`
   - Delivery → `core/delivery.py`
   - Views → `views/`
3. Fix circular imports with proper interfaces

#### Phase 2: State Management (Weekend 2)
1. Implement basic state machine
2. Convert implicit states to FSM
3. Add state persistence
4. Test with forced delay feature

#### Phase 3: Progression System (Week 3)
1. Add progression engine
2. Implement dual currency
3. Create tech tree logic
4. Build shop commands

#### Phase 4: Dynamic Content (Week 4)
1. Create content loader
2. Move mantras to structured format
3. Add event system hooks
4. Test holiday content

#### Phase 5: Advanced Features (Ongoing)
1. Mini-game sessions
2. Achievement system
3. Collaborative modes
4. Advanced visualizations

### Benefits of Aggressive Refactor

1. **Feature Velocity**: New features plug in cleanly
2. **State Clarity**: No more implicit state bugs
3. **Content Flexibility**: Easy to add events/themes
4. **Testing**: Each component testable in isolation
5. **Collaboration**: Multiple devs can work on different features

### What This Enables

✅ **Tech Tree**: Progression engine handles prerequisites  
✅ **Forced Delays**: State machine manages delay states  
✅ **Mini-Games**: Game modes support different interactions  
✅ **Events**: Content loader handles special content  
✅ **Complex UIs**: Views separated from logic  
✅ **Future Features**: Clean extension points  

### Example: Adding Holiday Event

```python
# features/events.py
class ValentinesEvent(HolidayEvent):
    def get_special_mantras(self):
        return load_json("events/valentines/mantras.json")
    
    def get_multipliers(self):
        return {"romance": 2.0, "devotion": 1.5}

# Just register it, everything else works
EventManager.register(ValentinesEvent())
```

### Example: Adding Forced Delay

```python
# features/forced_delay.py
class ForcedDelayTrigger:
    def should_delay(self, user_state):
        return (user_state.streak >= 10 or 
                user_state.recent_speed_avg < 20)
    
    def get_delay_duration(self):
        return random.choices([2, 5, 10], weights=[70, 25, 5])

# Integrates with state machine automatically
```

## Why This Architecture?

The current "chop and drop" approach just moved code around. This architecture:
- **Separates concerns properly**: UI, game logic, progression, content
- **Supports complex features**: State machines, events, progression
- **Scales with ambition**: Add game modes without touching core
- **Maintains simplicity**: Each file still does one thing well
- **Enables the roadmap**: Every planned feature has a clear home

This isn't over-engineering - it's building the foundation for the features you already want to add.
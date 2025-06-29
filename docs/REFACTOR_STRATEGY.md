# Mantra System Refactor Strategy

## 1. Overview

This document outlines the strategy for refactoring the mantra system. The current implementation is a single, large cog that mixes commands, UI, state management, and core logic, making it difficult to maintain and extend.

The primary goals of this refactor are:
- **Simplicity & Clarity**: Each part of the system should have a single, well-defined responsibility.
- **State Management**: Introduce an explicit state machine to robustly handle complex user interaction flows, such as forced delays or multi-step encounters.
- **Extensibility**: Create a foundation that makes it easy to add new features (like mini-games, tech trees, and events) without rewriting core logic.
- **Developer Experience**: Make the codebase easy for anyone to understand and contribute to.

## 2. Core Problems to Solve

- **Monolithic Cog**: `cogs/dynamic/mantras.py` is over 1000 lines and handles everything, leading to tight coupling.
- **Implicit State**: User state is tracked in scattered dictionaries (`active_challenges`, `user_streaks`) and config files. This is fragile and cannot support features that require a clear sequence of states (e.g., `PENDING` -> `DELAYED` -> `AWAITING_RESPONSE`).
- **Mixed Concerns**: Utility files (`utils/mantras.py`, `utils/ui.py`) mix pure functions with stateful logic and UI code with business logic, causing circular dependencies and making code hard to test.

## 3. Target Architecture

We will adopt a modular, feature-based architecture within a new `cogs/dynamic/mantras/` directory.

```
cogs/dynamic/mantras/
├── __init__.py      # Cog setup file
├── commands/        # Slash commands (user, admin)
├── core/            # Core logic (delivery, scheduling, state machine)
├── features/        # Pluggable features (e.g., Forced Delays)
├── game_modes/      # Different interaction patterns (e.g., Classic, Session)
├── models/          # Data structures (e.g., UserState, Encounter)
├── views/           # Discord UI components (Views, Modals)
└── utils/           # Pure, stateless helper functions
```

## 4. Key Concepts

### a. The State Machine

This is the most critical part of the refactor. We will move from implicit flags to an explicit state machine.

**Before:**
```python
# Scattered checks
if user_id in self.active_challenges:
    #...
if "timeout_count" in config:
    #...
```

**After:**
A central state manager will handle a user's progression through a mantra encounter.

```python
# models/state.py
from enum import Enum

class MantraState(Enum):
    IDLE = "idle"
    PENDING_ENCOUNTER = "pending_encounter"
    AWAITING_RESPONSE = "awaiting_response"
    IN_DELAY = "in_delay"
    TIMEOUT = "timeout"

@dataclass
class UserState:
    user_id: int
    current_state: MantraState = MantraState.IDLE
    context: dict = field(default_factory=dict) # For mantra text, sent_at, etc.
    # ... other state data
```

```python
# core/state_manager.py
class StateManager:
    async def get_user_state(self, user_id: int) -> UserState:
        # ... logic to load state from persistence
        pass

    async def transition_to(self, user_id: int, new_state: MantraState, context: dict = None):
        # ... logic to update and save state
        pass
```
This model allows us to easily implement the desired "forced delay" feature by creating an `IN_DELAY` state and preventing transitions until a timer has passed.

### b. Decoupled Commands and Views

- **Commands (`/commands`)**: Command files will *only* define the command structure and its inputs. The execution logic will be delegated to the core systems. They should not contain any business logic.
- **Views (`/views`)**: Views will *only* define the UI components and their callbacks. Callbacks will trigger functions in the core systems, passing along necessary data. They should not contain business logic like point calculations or state transitions.

**Example: A View with Callbacks**
```python
# views/mantra_response.py
class MantraResponseView(discord.ui.View):
    def __init__(self, encounter_id: str, on_submit_callback: callable):
        super().__init__()
        self.on_submit_callback = on_submit_callback

    @discord.ui.button(label="Submit", style=discord.ButtonStyle.primary)
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Logic to open a modal to get user input
        # ...
        # On modal submit:
        await self.on_submit_callback(encounter_id, user_response)
        # The view's job is done. The core system handles the rest.
```

### c. Pluggable Features

Features like "Forced Delays" or "Streaks" will be implemented as self-contained modules. The core delivery loop will invoke them at specific hook points (e.g., `on_response_received`, `before_sending_mantra`).

```python
# features/forced_delay.py
class ForcedDelayFeature:
    def should_apply(self, user_state: UserState, response_time_seconds: int) -> bool:
        # ... logic to determine if a delay is needed
        return user_state.streak > 10 and response_time_seconds < 15

    async def apply(self, state_manager: StateManager, user_id: int):
        # ... logic to transition the user to the IN_DELAY state
        await state_manager.transition_to(user_id, MantraState.IN_DELAY, context={"delay_seconds": 120})
```

## 5. Migration Strategy

The refactor will be executed incrementally:
1.  **Build the Skeleton**: Create the new directory structure and files.
2.  **Implement the State Machine**: Build the `StateManager` and `UserState` model. This is the foundational piece.
3.  **Migrate Core Logic**: Move the mantra delivery loop, scheduling, and response handling into `core/delivery.py` and `core/scheduler.py`, integrating the new state machine.
4.  **Migrate Commands & Views**: Move slash commands into `commands/` and UI components into `views/`, stripping them of business logic and connecting them to the core systems via callbacks or direct function calls.
5.  **Migrate Utilities**: Move pure functions from `utils/mantras.py` to `cogs/dynamic/mantras/utils.py`. Deprecate the old utils file.
6.  **Decommission the Monolith**: Once all logic is migrated, the old `cogs/dynamic/mantras.py` will be replaced by a small cog file that simply loads the new components.

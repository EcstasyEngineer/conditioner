# Discord Bot Architecture Analysis

## Executive Summary

The codebase has a solid foundation with good separation in some areas (utils pattern, config system) but suffers from classic MVC violations where Views handle business logic and Controllers (cogs) are doing too much. The recent issue with duplicate timeout logging is a direct symptom of this architectural problem.

## Current Architecture Pattern

```
User Input → Cog (Controller + Business Logic) → Utils (Pure Logic) → Data (JSONL/Config)
                ↓
              UI Views (View + Business Logic + State Management)
```

## What's Working Well ✅

### 1. Utils Layer
- Clean, pure functions with no Discord dependencies
- Good examples: `points.py`, `encounters.py`
- Easy to test and reuse

### 2. Configuration System
- Thread-safe, well-isolated
- Clear scope separation
- No coupling to Discord

### 3. Data Persistence
- JSONL encounter logging is clean
- Config files are well-organized
- Clear read/write patterns

## Major Issues 🚨

### 1. Views Doing Business Logic
```python
# BAD: UI View handling business logic
class MantraRequestView:
    async def on_timeout(self):
        # This should NOT be here:
        config = get_user_mantra_config(...)
        result = adjust_user_frequency(config, success=False)
        schedule_next_encounter(config, self.themes)
        save_user_mantra_config(...)
```

### 2. Circular Dependencies
- Views import utils inside methods to avoid circular imports
- Sign of poor layer separation

### 3. Monolithic Cogs
- `mantras.py`: 1057 lines mixing commands, tasks, admin, business logic
- Should be split into focused components

### 4. State Management Chaos
- UI views managing persistent state
- Business state mixed with UI state
- No clear state ownership

## Recommended Architecture

```
User Input → Command Handler (thin) → Service Layer → Repository/Utils → Data
                    ↓                      ↓
                UI Factory ← View Models ←
                    ↓
                Pure Views (no logic)
```

## Immediate Fixes

### 1. Extract Business Logic from Views
```python
# GOOD: Service handles logic, View just displays
class MantraService:
    def handle_timeout(self, user_id: int) -> TimeoutResult:
        # All business logic here
        return TimeoutResult(embed=..., next_view=...)

class MantraRequestView:
    async def on_timeout(self):
        result = self.service.handle_timeout(self.user.id)
        await self._message.edit(embed=result.embed, view=result.next_view)
```

### 2. Split Large Cogs
- `mantras_commands.py` - User commands only
- `mantras_admin.py` - Admin commands
- `mantras_tasks.py` - Background tasks
- `mantras_service.py` - Business logic

### 3. Introduce View Models
```python
@dataclass
class MantraStatusViewModel:
    subject: str
    controller: str
    themes: List[str]
    total_points: int
    # ... other display data
```

### 4. Create Proper Service Layer
```python
class MantraService:
    def __init__(self, config_manager, encounter_repo):
        self.config = config_manager
        self.encounters = encounter_repo
    
    def enroll_user(self, user_id: int, ...) -> EnrollmentResult:
        # Orchestrate the enrollment process
    
    def process_response(self, user_id: int, ...) -> ResponseResult:
        # Handle mantra response logic
```

## Benefits of Refactoring

1. **Testability**: Can test business logic without Discord
2. **Maintainability**: Clear responsibilities, easier to modify
3. **Reusability**: Services can be used by multiple cogs
4. **Debugging**: Errors isolated to appropriate layers
5. **No More Duplicate Logging**: Clear ownership of operations

## Migration Path

1. **Phase 1**: Extract business logic from views (1-2 days)
2. **Phase 2**: Create service layer for mantras (2-3 days)
3. **Phase 3**: Split monolithic cogs (1-2 days)
4. **Phase 4**: Introduce view models (1 day)
5. **Phase 5**: Apply pattern to other cogs (ongoing)

## Examples of Current Violations

### UI Components Doing Business Logic
- `MantraRequestView.on_timeout()` contains extensive business logic:
  - Config management
  - Frequency adjustment calculations
  - State transitions
  - Streak updates

### Mixed Responsibilities in Cogs
- `mantras.py` cog is 1057 lines combining:
  - Discord command handling
  - Business logic orchestration
  - UI view creation
  - Background task management
  - Direct config manipulation

### UI Views Managing State
- Views like `MantraDisableOfferView` directly modify user configuration
- Should only handle UI interactions and delegate state changes

### Business Logic in UI Creation
- `create_mantra_success_embed()` contains logic for determining when to show tips
- Random chance calculations (33%) embedded in UI code

## Conclusion

The timeout duplicate logging bug is a perfect example of why this refactoring matters - the view shouldn't have been logging encounters at all. With proper separation, this bug would have been impossible.
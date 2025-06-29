# Mantra System Refactor Plan

This document tracks the tasks required to complete the mantra system refactor.

## Phase 1: Foundation & Core Systems (Week 1)

The goal of this phase is to build the new structure and migrate the absolute core logic without breaking existing functionality.

### Day 1-2: Project Scaffolding
- [x] Create new directory structure under `cogs/dynamic/mantras/`.
- [x] Create `__init__.py` to mark it as a package.
- [x] Create `REFACTOR_STRATEGY.md` and `REFACTOR_PLAN.md`.
- [ ] Create empty files for the main components (e.g., `core/delivery.py`, `models/state.py`, `commands/user.py`).
- [ ] Delete old planning documents (`MANTRA_MIGRATION_PLAN.md`, `MANTRA_REFACTOR_MILESTONES.md`, `MANTRA_REFACTOR_EXAMPLES.md`).

### Day 3-4: State Machine Implementation
- [ ] **Model:** Implement `UserState` and `MantraState` enum in `models/state.py`.
- [ ] **Persistence:** Create a `StateManager` in `core/state.py` responsible for loading/saving `UserState` objects (e.g., to/from the existing JSON configs).
- [ ] **Integration:** Replace the `self.active_challenges` dictionary in the old cog with calls to the new `StateManager`. The goal is to have the state machine shadow the old system first.

### Day 5-7: Core Logic Migration
- [ ] **Scheduler:** Move `schedule_next_encounter` and related time calculation logic from `utils/mantras.py` into `cogs/dynamic/mantras/core/scheduler.py`.
- [ ] **Delivery Loop:** Move the `mantra_delivery` task loop from `cogs/dynamic/mantras.py` into `cogs/dynamic/mantras/core/delivery.py`.
- [ ] **Response Handling:** Move the core logic for handling a user's mantra response into `core/delivery.py`. This includes checking the match, calculating points, and updating streaks.
- [ ] **Connect:** The new delivery loop should use the new scheduler and state manager.

**Success Criteria for Phase 1:**
- The bot runs without errors using the new structure.
- Mantras are delivered on schedule.
- User responses are processed correctly.
- User state (streaks, timeouts) is persisted across restarts via the new `StateManager`.
- The old `cogs/dynamic/mantras.py` is smaller, delegating core work to the new `core` modules.

## Phase 2: Commands, Views, and Features (Week 2)

The goal of this phase is to decouple the UI and command layers and implement the first new feature using the new architecture.

### Day 8-10: Decouple Commands & Views
- [ ] **Commands:** Move all `/mantra` slash command definitions from the main cog into `commands/user.py` and `commands/admin.py`.
- [ ] **Command Logic:** Ensure command functions are thin wrappers that call the core systems (e.g., `core.delivery.start_enrollment(user)`).
- [ ] **Views:** Move `ThemeSelectView`, `MantraRequestView`, etc., from `utils/ui.py` and `cogs/dynamic/mantras.py` into `views/`.
- [ ] **Callbacks:** Refactor views to use callbacks to communicate with the core systems, removing all business logic from the view classes.

### Day 11-12: Migrate Utilities
- [ ] **Pure Functions:** Identify and move stateless functions (`format_mantra_text`, `check_mantra_match`, `calculate_speed_bonus`) from `utils/mantras.py` to `cogs/dynamic/mantras/utils/text.py` (or similar).
- [ ] **Content Loading:** Move theme loading logic into `core/content_loader.py`.
- [ ] **Cleanup:** Update all imports to point to the new locations. Deprecate `utils/mantras.py`.

### Day 13-14: Implement Forced Delay Feature
- [ ] **Feature Class:** Create `features/forced_delay.py` with a class that contains the logic for when and how to apply a delay.
- [ ] **State:** Add the `IN_DELAY` state to the `MantraState` enum.
- [ ] **Integration:** Hook the `ForcedDelayFeature` into the response handling logic in `core/delivery.py`. When the feature is triggered, it should use the `StateManager` to transition the user to the `IN_DELAY` state.
- [ ] **Delivery Check:** The `mantra_delivery` loop must check for the `IN_DELAY` state and not send a new mantra until the delay has passed.

**Success Criteria for Phase 2:**
- All slash commands work as before.
- All UI views and modals work as before.
- The old `utils/mantras.py` and `utils/ui.py` are no longer used by the mantra system.
- The "Forced Delay" feature works as specified: users who respond too quickly are put into a temporary cooldown state.

## Phase 3: Cleanup & Finalization (Week 3)

- [ ] **New Cog:** Create the final `cogs/dynamic/mantras.py` which will be very lightweight. It will be responsible for initializing the `StateManager`, loading the commands from the `commands/` directory, and starting the core task loops.
- [ ] **Remove Old Code:** Delete the original `cogs/dynamic/mantras.py` (or rename it to `_old.py` temporarily).
- [ ] **Documentation:** Add docstrings and comments to the new modules explaining their roles.
- [ ] **Final Review:** Review the entire new system for clarity, consistency, and performance.

**Success Criteria for Phase 3:**
- The refactor is complete.
- The codebase is significantly easier to navigate and understand.
- The system is robust and ready for future feature development.

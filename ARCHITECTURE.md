# Project architecture and module layering

Goal: keep cogs thin (Discord I/O only). Put domain logic in `features/`. Let `core/` host shared infrastructure and types.

- cogs/
  - Discord glue code: commands, slash commands, listeners, tasks.
  - No business logic or file formats; call into `features/*` for behavior.
- features/
  - App/domain logic. Stateless or explicit state passed in. Strongly typed.
  - Examples: mantras scheduling/matching, points math, encounter logging.
  - Prefer to avoid importing Discord types directly. Accept "user-like" inputs via shared types from `core/types.py`.
- core/
  - Bot infrastructure: config system, error handling, permissions, startup wiring, shared types.
  - `core/types.py` defines `UserLike` and related Protocols used across `features/` and `cogs/`.

Import rules (one-way):
- cogs -> features, core
- features -> core (infra, shared types). Avoid Discord imports to keep features reusable and fast to import.
- core -> should not depend on cogs/features

Data/layout:
- configs/ — per-user and guild JSON configs via core.config
- logs/encounters — JSONL event streams read by features.encounters
- mantras/ — theme JSON packs loaded by cogs.dynamic.mantras

Discord types in features?
- Default: keep features Discord-agnostic. This keeps imports fast and encourages clean layering.
- If you need Discord-specific typing, use `typing.TYPE_CHECKING` or Protocols in `core/types.py` to preserve runtime decoupling.

Shared typing
- `core/types.py` exposes:
  - `HasId` Protocol (id: int)
  - `UserLike = Union[int, HasId]` — accepted by config and features APIs.
  - This matches `core.config.Config._resolve_config_id`, which accepts either an int ID or any object with an `id`.

Testing notes:
- Keep features importable without Discord.
- Unit-test with both plain ints and small stubs implementing `id: int`.

Presenters vs. domain logic
- Keep presentation (Embeds, views) in cogs. `features/` should return data, not Discord objects.
- Example: mantra stats presenter lives in `cogs/dynamic/mantra_stats.py`; underlying calculations live in `features/mantras.py`.

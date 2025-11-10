# Normalization Action Plan

Scope: foundation parity for core helpers/config without cross-linking code or issues.

## Goals
- Core permission helpers: single normalized API
  - get_superadmins(config) always returns list[int]
  - is_superadmin(config, user_id) and is_superadmin(ctx)
  - is_admin(config, ctx) and is_admin(ctx)
- Config parity: treat ctx=None as global; consistent guild/user/global resolution.
- Error logging: keep existing approach for now; track upgrade separately.
- Dev/Admin cogs: align names and UX across repos where appropriate.
- Scripts/tests: minimal unit tests for normalization.

## Completed (this commit set)
- Core utils normalized with dual-call signatures and list coercion.
- Config `_resolve_config_id`: `ctx=None` treated as global.
- Added basic unit test for superadmin/admin normalization.

## Pending / TODO
- Error logging upgrade (tracked in this repo’s issue #40):
  - Per-guild error channel with global fallback
  - on_app_command_error coverage; loop exception handler for background tasks
  - Rate-limit by (context, type, message[:100], scope)
  - Unit tests: channel resolution + rate limiter
- Dev/Admin cogs: reconcile command names/aliases and UX
- CI guard (optional): check for drift in foundation files
- Docs refresh after upgrades

## Rollout
- Keep changes in this dev repo first; promote to main once verified in your environment.

## Quick Tests
- `python3 -m unittest -q tests.test_utils_superadmin`

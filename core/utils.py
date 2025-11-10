"""Shared helper utilities for permission checks and config access.

Normalization goals:
- Always store global "superadmins" as a list of ints.
- Provide backward-compatible helpers usable as either:
  - is_superadmin(config, user_id)
  - is_superadmin(ctx)
  - is_admin(config, ctx)
  - is_admin(ctx)
"""
from typing import List, Union, Any


def _normalize_superadmins_list(config) -> List[int]:
    superadmins = config.get(None, "superadmins", scope="global") or []
    changed = False
    if not isinstance(superadmins, list):
        superadmins = [superadmins]
        changed = True
    norm = []
    for item in superadmins:
        try:
            norm.append(int(item))
        except Exception:
            continue
    if changed or norm != superadmins:
        config.set(None, "superadmins", norm, scope="global")
    return norm


def get_superadmins(config) -> List[int]:
    return _normalize_superadmins_list(config)


def is_superadmin(config_or_ctx: Any, user_id: Union[int, None] = None) -> bool:
    if user_id is None:
        ctx = config_or_ctx
        config = getattr(getattr(ctx, "bot", None), "config", None)
        if config is None:
            return False
        return ctx.author.id in get_superadmins(config)
    else:
        config = config_or_ctx
        return int(user_id) in get_superadmins(config)


def is_admin(config_or_ctx: Any, maybe_ctx: Any = None) -> bool:
    if maybe_ctx is None:
        ctx = config_or_ctx
        config = getattr(getattr(ctx, "bot", None), "config", None)
        if config is None:
            return False
    else:
        config = config_or_ctx
        ctx = maybe_ctx

    if is_superadmin(config, ctx.author.id):
        return True
    if ctx.guild is None:
        return False
    admins = config.get(ctx, "admins", [])
    if ctx.author.id in (admins or []):
        return True
    if getattr(ctx.author.guild_permissions, "administrator", False):
        return True
    if ctx.author == getattr(ctx.guild, "owner", None):
        return True
    return False

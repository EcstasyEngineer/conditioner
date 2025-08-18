from typing import Tuple, Protocol, runtime_checkable, Union
from core.config import Config

"""
Points management utilities (moved from utils.points).
"""

# Strong typing for user-like inputs without importing discord.
# Accept either an int (Discord user ID) or any object with an `id: int` attribute
# e.g., discord.Member, discord.User, or a lightweight stub in tests.
@runtime_checkable
class HasId(Protocol):
    id: int

UserLike = Union[int, HasId]

def get_points(config: Config, user: UserLike) -> int:
    """Return a user's current point total from the config storage."""
    return config.get_user(user, 'points', 0)


def add_points(config: Config, user: UserLike, amount: int) -> int:
    """Add points (can be negative). Returns the new clamped total."""
    current = get_points(config, user)
    new_total = max(0, current + amount)
    config.set_user(user, 'points', new_total)
    return new_total


def set_points(config: Config, user: UserLike, amount: int) -> int:
    """Set points to a specific non-negative amount and return it."""
    new_total = max(0, amount)
    config.set_user(user, 'points', new_total)
    return new_total


def transfer_points(config: Config, from_user: UserLike, to_user: UserLike, amount: int) -> Tuple[int, int]:
    """Transfer points; returns (from_new_total, to_new_total)."""
    from_current = get_points(config, from_user)
    if from_current < amount:
        raise ValueError(f"Insufficient points: has {from_current}, needs {amount}")
    from_new = add_points(config, from_user, -amount)
    to_new = add_points(config, to_user, amount)
    return from_new, to_new


# Tokens (second currency)

def get_tokens(config: Config, user: UserLike) -> int:
    """Return a user's token total."""
    return config.get_user(user, 'tokens', 0)


def add_tokens(config: Config, user: UserLike, amount: int) -> int:
    current = get_tokens(config, user)
    new_total = max(0, current + amount)
    config.set_user(user, 'tokens', new_total)
    return new_total


def set_tokens(config: Config, user: UserLike, amount: int) -> int:
    new_total = max(0, amount)
    config.set_user(user, 'tokens', new_total)
    return new_total


def spend_tokens(config: Config, user: UserLike, amount: int) -> int:
    if amount < 0:
        raise ValueError("Amount to spend must be non-negative")
    current = get_tokens(config, user)
    if current < amount:
        raise ValueError(f"Insufficient tokens: has {current}, needs {amount}")
    new_total = current - amount
    config.set_user(user, 'tokens', new_total)
    return new_total

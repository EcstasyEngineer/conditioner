"""
Points management utilities.

Centralized functions for handling user points across all cogs.
No more inter-cog dependencies or "get points cog" nonsense.
"""

def get_points(bot, user) -> int:
    """
    Get a user's current point total.
    
    Args:
        bot: The Discord bot instance with config system
        user: Discord user object
        
    Returns:
        int: Current point total (0 if not set)
    """
    return bot.config.get_user(user, 'points', 0)


def add_points(bot, user, amount: int) -> int:
    """
    Add points to a user's total.
    
    Args:
        bot: The Discord bot instance with config system
        user: Discord user object
        amount: Points to add (can be negative to subtract)
        
    Returns:
        int: New point total after addition
    """
    current = get_points(bot, user)
    new_total = max(0, current + amount)
    bot.config.set_user(user, 'points', new_total)
    return new_total


def set_points(bot, user, amount: int) -> int:
    """
    Set a user's points to a specific amount.
    
    Args:
        bot: The Discord bot instance with config system
        user: Discord user object
        amount: Points to set (minimum 0)
        
    Returns:
        int: New point total (same as amount, but clamped to 0+)
    """
    new_total = max(0, amount)
    bot.config.set_user(user, 'points', new_total)
    return new_total


def transfer_points(bot, from_user, to_user, amount: int) -> tuple[int, int]:
    """
    Transfer points from one user to another.
    
    Args:
        bot: The Discord bot instance with config system
        from_user: Discord user object (sender)
        to_user: Discord user object (receiver)
        amount: Points to transfer
        
    Returns:
        tuple[int, int]: (from_user_new_total, to_user_new_total)
        
    Raises:
        ValueError: If from_user doesn't have enough points
    """
    from_current = get_points(bot, from_user)
    
    if from_current < amount:
        raise ValueError(f"Insufficient points: has {from_current}, needs {amount}")
    
    from_new = add_points(bot, from_user, -amount)
    to_new = add_points(bot, to_user, amount)
    
    return from_new, to_new
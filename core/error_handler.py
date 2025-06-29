"""
Simple error logging utility for Discord channel integration.
"""

import discord
import traceback
from datetime import datetime, timedelta
from typing import Optional, Dict


# Simple rate limiting storage
_error_timestamps: Dict[str, datetime] = {}
_rate_limit_minutes = 5


def _should_send_error(error_key: str) -> bool:
    """Check if error should be sent based on rate limiting."""
    now = datetime.now()
    
    if error_key not in _error_timestamps:
        _error_timestamps[error_key] = now
        return True
    
    last_sent = _error_timestamps[error_key]
    if now - last_sent >= timedelta(minutes=_rate_limit_minutes):
        _error_timestamps[error_key] = now
        return True
    
    return False


def _create_error_key(error: Exception, context: str) -> str:
    """Generate a unique key for error rate limiting."""
    error_type = type(error).__name__
    error_msg = str(error)[:100]  # First 100 chars
    return f"{context}:{error_type}:{error_msg}"


async def log_error_to_discord(bot, error: Exception, context: str, extra_info: str = ""):
    """
    Log error to Discord channel with rate limiting.
    
    Args:
        bot: The Discord bot instance
        error: The exception that occurred
        context: Context where error occurred (e.g., "command_help", "event_on_message")
        extra_info: Additional context information
    """
    # Get error channel from config
    if not hasattr(bot, 'config'):
        return
    
    error_channel_id = bot.config.get_global("error_channel_id")
    if not error_channel_id:
        return  # No channel configured
    
    # Check rate limiting
    error_key = _create_error_key(error, context)
    if not _should_send_error(error_key):
        return  # Rate limited
    
    # Get the channel
    channel = bot.get_channel(error_channel_id)
    if not channel:
        return  # Channel not found
    
    # Create embed
    embed = discord.Embed(
        title="🚨 System Error Detected",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="Error Type",
        value=f"`{type(error).__name__}`",
        inline=True
    )
    
    embed.add_field(
        name="Context",
        value=f"`{context}`",
        inline=True
    )
    
    # Error message (truncated if too long)
    error_msg = str(error)
    if len(error_msg) > 1000:
        error_msg = error_msg[:1000] + "..."
    
    embed.add_field(
        name="Error Message",
        value=f"```{error_msg}```",
        inline=False
    )
    
    # Extra info if provided
    if extra_info:
        if len(extra_info) > 1000:
            extra_info = extra_info[:1000] + "..."
        embed.add_field(
            name="Additional Info",
            value=f"```{extra_info}```",
            inline=False
        )
    
    # Traceback (limited length)
    tb = traceback.format_exc()
    if len(tb) > 1000:
        tb = "..." + tb[-1000:]  # Last 1000 chars
    
    embed.add_field(
        name="Traceback",
        value=f"```python\n{tb}\n```",
        inline=False
    )
    
    embed.set_footer(text="Error Logging System")
    
    # Send to channel
    try:
        await channel.send(embed=embed)
    except Exception:
        # If we can't send to Discord, at least it's still in the regular logs
        pass
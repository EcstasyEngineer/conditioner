"""
Generic delivery utilities for DMs, media files, and auto-deletion.

Shared functionality that can be used by multiple cogs for sending
content via DM, handling media files, and managing auto-deletion.
"""

import discord
import asyncio
import random
import os
from pathlib import Path
from typing import Optional, List, Union


class DeliveryTracker:
    """Track messages for auto-deletion and other delivery features."""
    
    def __init__(self):
        self.tracked_messages = {}  # {message_id: {"delete_at": datetime, "metadata": dict}}
    
    def track_message(self, message_id: int, metadata: dict):
        """Track a message for future operations."""
        self.tracked_messages[message_id] = metadata
    
    def untrack_message(self, message_id: int):
        """Stop tracking a message."""
        self.tracked_messages.pop(message_id, None)
    
    def get_tracked_message(self, message_id: int) -> Optional[dict]:
        """Get tracking data for a message."""
        return self.tracked_messages.get(message_id)


async def send_dm_with_media(
    user: discord.User, 
    content: str, 
    media_path: Optional[Path] = None,
    embed: Optional[discord.Embed] = None
) -> Optional[discord.Message]:
    """
    Send a DM to a user with optional media attachment.
    
    Args:
        user: Discord user to send DM to
        content: Text content of the message
        media_path: Optional path to media file to attach
        embed: Optional embed to include
        
    Returns:
        discord.Message: The sent message, or None if failed
    """
    try:
        if media_path and media_path.exists():
            # Handle different file types
            if media_path.suffix.lower() == '.txt':
                # Read and send link content
                try:
                    with open(media_path, 'r') as f:
                        link_content = f.read().strip()
                    
                    # Send link content instead of file
                    message = await user.send(f"{content}\n\n{link_content}", embed=embed)
                    return message
                except Exception as e:
                    print(f"Error reading link file {media_path}: {e}")
                    # Fall back to sending without media
                    message = await user.send(content, embed=embed)
                    return message
            else:
                # Send as file attachment
                with open(media_path, 'rb') as f:
                    file = discord.File(f, filename=media_path.name)
                    message = await user.send(content, file=file, embed=embed)
                    return message
        else:
            # Send without media
            message = await user.send(content, embed=embed)
            return message
            
    except discord.Forbidden:
        print(f"Cannot send DM to user {user.id} - DMs disabled")
        return None
    except Exception as e:
        print(f"Error sending DM to user {user.id}: {e}")
        return None


def select_random_media_file(directory_path: Union[str, Path]) -> Optional[Path]:
    """
    Select a random media file from a directory.
    
    Args:
        directory_path: Path to directory containing media files
        
    Returns:
        Path: Random file path, or None if no valid files found
    """
    directory = Path(directory_path)
    
    if not directory.exists():
        return None
    
    # Valid media extensions
    valid_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.mp3', '.mp4', '.txt', '.webm')
    
    # Find all valid files (excluding sample files)
    valid_files = [
        f for f in directory.glob('*') 
        if f.suffix.lower() in valid_extensions 
        and 'sample' not in f.name.lower()
    ]
    
    if not valid_files:
        return None
    
    return random.choice(valid_files)


async def schedule_auto_delete(message: discord.Message, delay_seconds: int) -> bool:
    """
    Schedule a message for automatic deletion after a delay.
    
    Args:
        message: Discord message to delete
        delay_seconds: Seconds to wait before deletion
        
    Returns:
        bool: True if deletion was scheduled successfully
    """
    try:
        await asyncio.sleep(delay_seconds)
        await message.delete()
        return True
    except discord.NotFound:
        # Message already deleted
        return True
    except discord.Forbidden:
        # No permission to delete
        print(f"No permission to delete message {message.id}")
        return False
    except Exception as e:
        print(f"Error auto-deleting message {message.id}: {e}")
        return False


def get_file_count_in_directory(directory_path: Union[str, Path]) -> int:
    """
    Count valid media files in a directory.
    
    Args:
        directory_path: Path to directory
        
    Returns:
        int: Number of valid media files
    """
    directory = Path(directory_path)
    
    if not directory.exists():
        return 0
    
    valid_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.mp3', '.mp4', '.txt', '.webm')
    
    valid_files = [
        f for f in directory.glob('*') 
        if f.suffix.lower() in valid_extensions 
        and 'sample' not in f.name.lower()
    ]
    
    return len(valid_files)


def load_file_counts_from_json(json_path: Union[str, Path] = 'media_file_counts.json') -> dict:
    """
    Load file counts from JSON file with fallback to directory scanning.
    
    Args:
        json_path: Path to JSON file containing file counts
        
    Returns:
        dict: File counts by category/tier
    """
    import json
    
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Fallback: count files directly from common tier structure
        tier_paths = {
            "common": "media/common/",
            "uncommon": "media/uncommon/", 
            "rare": "media/rare/",
            "epic": "media/epic/",
        }
        
        counts = {}
        for tier, path in tier_paths.items():
            counts[tier] = get_file_count_in_directory(path)
        
        return counts


async def send_dm_with_auto_delete(
    user: discord.User,
    content: str,
    delete_after_seconds: int,
    media_path: Optional[Path] = None,
    embed: Optional[discord.Embed] = None
) -> Optional[discord.Message]:
    """
    Send a DM with automatic deletion after a specified time.
    
    Args:
        user: Discord user to send DM to
        content: Message content
        delete_after_seconds: Seconds before auto-deletion
        media_path: Optional media file to attach
        embed: Optional embed to include
        
    Returns:
        discord.Message: The sent message, or None if failed
    """
    message = await send_dm_with_media(user, content, media_path, embed)
    
    if message and delete_after_seconds > 0:
        # Schedule deletion in background
        asyncio.create_task(schedule_auto_delete(message, delete_after_seconds))
    
    return message
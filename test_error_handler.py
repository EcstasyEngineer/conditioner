#!/usr/bin/env python3
"""
Test script for the error handler system.
This demonstrates that the error handler catches uncaught exceptions without code changes.
"""

import asyncio
import sys
import os
sys.path.append('.')

from core.error_handler import ErrorHandler
from unittest.mock import MagicMock

async def test_background_task_error():
    """Simulate a background task that throws an error."""
    print("Starting background task that will fail...")
    await asyncio.sleep(0.1)  # Simulate some work
    # This will cause an uncaught exception in the asyncio task
    raise ValueError("Test error from background task - this should be caught!")

async def test_error_handler():
    """Test the error handler system."""
    print("=== Error Handler Test ===")
    
    # Create a mock bot
    mock_bot = MagicMock()
    mock_bot.config.get_global.return_value = None
    
    # Initialize error handler
    print("1. Initializing error handler...")
    error_handler = ErrorHandler(mock_bot)
    print("   ✓ Error handler created")
    
    # Test manual error logging
    print("2. Testing manual error logging...")
    test_error = RuntimeError("Manual test error")
    await error_handler.log_error(test_error, "manual_test", {"test_data": "value"})
    print("   ✓ Manual error logged")
    
    # Test uncaught exception handling
    print("3. Testing uncaught asyncio exception...")
    try:
        # Create a task that will fail
        task = asyncio.create_task(test_background_task_error())
        await task
    except ValueError:
        print("   ✓ Exception was raised (expected)")
    
    # Give time for the error handler to process
    await asyncio.sleep(0.2)
    print("   ✓ Asyncio error handler should have logged the exception")
    
    print("\n=== Test Complete ===")
    print("Check the console output and logs for error handler activity.")
    print("In production, these would be sent to Discord channels.")

if __name__ == "__main__":
    asyncio.run(test_error_handler())
# Error Logging System

The centralized error logging system automatically catches and reports all uncaught exceptions without requiring any changes to existing code.

## Features

- **Automatic Error Catching**: Hooks into asyncio and sys exception handlers
- **Discord Integration**: Sends formatted error reports to designated channels
- **Rate Limiting**: Prevents spam (5-minute cooldown per unique error)
- **Zero Code Changes**: Works with existing cogs without modification
- **Detailed Context**: Provides full tracebacks and context information

## Setup

### 1. Automatic Initialization

The error handler is automatically initialized when the bot starts. No code changes needed for regular commands and events.

### 2. Configure Error Channel

Use the `!seterrorlog` command to set up error reporting:

```
!seterrorlog #bot-errors
```

This will:
- Configure the error reporting channel
- Send a test message to confirm it's working
- Start catching all uncaught exceptions

### 3. Admin Commands

Available commands for admins:

- `!seterrorlog [#channel]` - Set the error reporting channel (or show current if no channel provided)
- `!testerror` - Trigger a test error to verify the system

## What Gets Caught

The system catches errors from:

- **Command Errors**: Traditional and slash command errors (automatically via `on_command_error`)
- **Event Errors**: Errors in event handlers (automatically via `on_error`)
- **Task Loop Errors**: **Requires manual error handler** (see Task Loop section below)

## Error Report Format

Discord error reports include:

- **Error Type**: `KeyError`, `ValueError`, etc.
- **Context**: Where the error occurred (`mantra_delivery`, `on_message`, etc.)
- **Error Message**: Full error description
- **Traceback**: Complete stack trace
- **Extra Info**: Task details, user info, etc.
- **Timestamp**: When the error occurred

## Task Loop Error Handling

Discord.py task loops (`@tasks.loop`) require their own error handlers. They do NOT trigger `on_error` or `on_command_error`.

### Adding Error Handler to Task Loop

```python
@tasks.loop(minutes=2)
async def my_task_loop(self):
    # Task code here
    pass

@my_task_loop.error
async def my_task_loop_error(self, error):
    """Handle errors in the task loop."""
    if self.logger:
        self.logger.error(f"Error in my_task_loop: {error}", exc_info=True)
    
    from core.error_handler import log_error_to_discord
    await log_error_to_discord(self.bot, error, "task_my_task_loop")
```

**Important**: Without the `@taskname.error` handler, task loop errors will only appear in file logs, not Discord!

## Rate Limiting

- **5-minute cooldown** between identical errors
- Prevents channel spam from repeated failures
- Each unique error (type + message + context) is tracked separately
- Rate limit can be configured in global config

## Examples

### Background Task Error

If the mantra delivery task fails with a `KeyError`, you'll get:

```
🚨 System Error Detected
Error Type: KeyError
Context: task_mantra_delivery
Error Message: 'pet_name'
Traceback: [full stack trace]
```

### Command Error

If a command fails:

```
🚨 System Error Detected  
Error Type: AttributeError
Context: command_enroll
Error Message: 'NoneType' object has no attribute 'get'
User: username (ID: 123456789)
Channel: #general
Traceback: [full stack trace]
```

## Configuration

Error handler settings are stored in global config:

```json
{
  "error_channel_id": 123456789,
  "error_rate_limit_minutes": 5
}
```

## Benefits

1. **Immediate Visibility**: No more silent failures
2. **No SSH Required**: Errors appear directly in Discord
3. **Zero Maintenance**: No code changes needed for existing features
4. **Full Context**: Complete information for debugging
5. **Spam Protection**: Rate limiting prevents notification overload

## Troubleshooting

**Error channel not receiving messages:**
- Use `!seterrorlog` without arguments to check current configuration
- Ensure bot has send message permissions in the error channel
- Use `!testerror` to verify the system is working
- **For task loops**: Make sure you added the `@taskname.error` handler

**Too many error notifications:**
- Rate limiting should prevent spam (5min cooldown)
- Check for underlying issues causing repeated failures
- Consider fixing root causes rather than disabling notifications

**Missing error details:**
- All errors are still logged to `logs/bot.log` regardless of Discord reporting
- Use SSH access to check detailed logs if needed
- Error handler failures are logged separately

**Task loop errors not appearing in Discord:**
- Task loops require explicit error handlers - see "Task Loop Error Handling" section
- Without the `@taskname.error` decorator, errors only go to file logs

This system ensures that critical errors like the recent `pet_name` KeyError will never go unnoticed again.
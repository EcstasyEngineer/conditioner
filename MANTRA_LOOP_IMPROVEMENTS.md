# Mantra Loop Improvement Suggestions

## Current Issues

1. **Loop runs every 5 minutes** - This means if someone goes idle at minute 1, they might still get a mantra at minute 5
2. **Consecutive checks are too close together** - 2 seconds isn't enough for status propagation
3. **No memory between loops** - Each 5-minute cycle has no knowledge of previous status

## Proposed Solutions

### Option 1: Longer Check Intervals
- Keep 5-minute loop
- Increase check interval to 30-60 seconds
- Do 3-4 checks over 2-3 minutes
- Downside: Delays mantra delivery significantly

### Option 2: Status History Tracking (Recommended)
- Keep 5-minute loop  
- Track user status history in memory (not saved to JSON)
- Structure:
  ```python
  self.user_status_history = {
      user_id: {
          "history": [(timestamp, status), ...],  # Last 30 minutes
          "last_active": timestamp,
          "consecutive_active_checks": 0
      }
  }
  ```
- Only send mantras if user has been active for 2-3 consecutive 5-minute checks
- This gives 10-15 minutes of "proven" activity before sending

### Option 3: Hybrid Approach
- Quick check (current 3×2s) for immediate status
- If online, check history for sustained activity
- Require 2+ consecutive loops of online/dnd status
- Reset counter if idle/offline detected

### Option 4: Event-Based Tracking
- Listen to `on_presence_update` events
- Track when users change status in real-time
- Only send mantras if they've been online/dnd for 10+ minutes
- Most accurate but more complex

## Recommended Implementation

Use Option 2 or 3:
- Minimal code changes
- Prevents 3 AM mantras from brief online blips
- Uses existing 5-minute loop efficiently
- No need to save status history to disk
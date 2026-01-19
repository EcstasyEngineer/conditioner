# Voice-Boosted Mantras Specification

## Overview

When users spend time in the ambient voice channel (brainwashing loop), the system will opportunistically trigger mantra interactions during their session. This creates tighter integration between passive audio conditioning and active mantra reinforcement.

## Goals

1. Deliver mantras while users are in a receptive trance state
2. Support both enrolled users (full mantra) and non-enrolled users (passive affirmation)
3. Avoid spamming users with pending mantras
4. Prevent learning algorithm pollution from artificial triggers
5. Apply points nerf to voice-boosted mantras (25% of normal)

## Architecture

### Data Flow

```
player.py (listening_reward_loop, 1 min)
    │
    ├── Checks: user in ambient channel, not deafened, enrolled, no pending mantra
    ├── Checks: join_time > 5 min ago, next_delivery > 3 min away
    │
    └── Writes to user config JSON:
            voice_boost_requested: true
            next_delivery: now + random(30, 120) seconds

mantras.py (mantra_delivery loop, 30 sec)
    │
    ├── Sees next_delivery is past, delivers mantra
    ├── On delivery: copies voice_boost_requested to delivered_mantra
    │
    └── On response (handle_mantra_response):
            If delivered_mantra.voice_boosted:
                - Apply 25% points multiplier
                - Skip learning algorithm updates (distribution + frequency)
            Else:
                - Normal processing
```

### Config Fields

**User config (`user_{id}.json`) - mantra_system object:**

```json
{
  "voice_boost_requested": false,  // Set by player.py, cleared on delivery
  "delivered_mantra": {
    "text": "...",
    "theme": "...",
    "voice_boosted": false  // Copied from voice_boost_requested on delivery
  }
}
```

## Implementation Details

### player.py Changes

Add to `listening_reward_loop` (runs every 1 minute):

```python
# After adding points, check for mantra boost opportunity
config = self.bot.config.get_user(member, 'mantra_system', {})

# Skip if not enrolled
if not config.get("enrolled"):
    # TODO: Future - send passive affirmation to non-enrolled users
    continue

# Skip if mantra already pending (sent is not None)
if config.get("sent") is not None:
    continue

# Configurable delays
VOICE_BOOST_MIN_DELAY = 30      # X: minimum seconds before mantra fires
VOICE_BOOST_MAX_DELAY = 240     # Y: maximum seconds (4 min)
VOICE_BOOST_THRESHOLD = 300     # 5 min in channel before boosting starts

# Skip if next_delivery already within max delay window (already boosted or about to fire)
next_delivery_str = config.get("next_delivery")
if next_delivery_str:
    next_delivery = datetime.fromisoformat(next_delivery_str)
    if next_delivery <= datetime.now() + timedelta(seconds=VOICE_BOOST_MAX_DELAY):
        continue

# Check join duration (need 5+ min in channel)
join_time = self._get_join_time(member)  # Need to track this
if join_time is None or (datetime.now() - join_time).total_seconds() < VOICE_BOOST_THRESHOLD:
    continue

# Boost: set next_delivery to soon and flag it
delay_seconds = random.randint(VOICE_BOOST_MIN_DELAY, VOICE_BOOST_MAX_DELAY)
config["next_delivery"] = (datetime.now() + timedelta(seconds=delay_seconds)).isoformat()
config["voice_boost_requested"] = True
self.bot.config.set_user(member, 'mantra_system', config)
```

**Join time tracking (in-memory, not persisted):**

```python
def __init__(self, bot):
    self._voice_join_times = {}  # {user_id: datetime}

@commands.Cog.listener()
async def on_voice_state_update(self, member, before, after):
    ambient_id = self.bot.config.get(member.guild.id, "ambient_channel_id")

    # Joined ambient channel
    if after.channel and after.channel.id == ambient_id:
        if not before.channel or before.channel.id != ambient_id:
            self._voice_join_times[member.id] = datetime.now()

    # Left ambient channel
    if before.channel and before.channel.id == ambient_id:
        if not after.channel or after.channel.id != ambient_id:
            self._voice_join_times.pop(member.id, None)
```

### mantra_service.py Changes

**In `deliver_mantra()`:**

```python
# When saving delivered_mantra, include voice_boosted flag
config["delivered_mantra"] = mantra.copy()
config["delivered_mantra"]["voice_boosted"] = config.pop("voice_boost_requested", False)
```

**In `handle_mantra_response()`:**

```python
# Check if this was a voice-boosted mantra
voice_boosted = config.get("delivered_mantra", {}).get("voice_boosted", False)

if voice_boosted:
    # Apply 25% points multiplier
    base_points = int(base_points * 0.25)
    speed_bonus = int(speed_bonus * 0.25)
    public_bonus = int(public_bonus * 0.25)

    # Skip learning algorithm updates
    # (Don't update availability_distribution or frequency)
else:
    # Normal learning updates
    # ... existing learner.record() and frequency adjustment code ...
```

## Edge Cases

### User leaves voice before mantra fires
- Mantra still fires (next_delivery is set)
- They respond whenever they see it
- Learning is still skipped (voice_boosted flag is on the delivered mantra)
- This is acceptable - they were in trance when we queued it

### User has voice_boost_requested but bot restarts
- Flag persists in config
- Next delivery will be voice_boosted
- Acceptable behavior

### Multiple voice sessions same day
- Each session can trigger boosts independently
- Learning skip prevents distribution pollution

### User completes mantra, still in voice
- After completion, sent = None, next_delivery = future (normal schedule)
- Next loop iteration: sees next_delivery far away, boosts again
- Correct behavior - they get another one

## Points Calculation

**Normal mantra (example):**
- Base: 100 pts
- Speed bonus: 30 pts
- Public bonus: 0 pts
- Total: 130 pts

**Voice-boosted mantra (same example):**
- Base: 25 pts (100 * 0.25)
- Speed bonus: 7 pts (30 * 0.25)
- Public bonus: 0 pts
- Total: 32 pts

## Future Extensions

### Passive Affirmations (non-enrolled users)

Could send periodic affirmations to non-enrolled users in voice:
- No response required
- No points
- Serves as engagement funnel to mantra enrollment
- Different message pool (lighter, more general)

### Tuning the Delays

The cooldown between boosts is implicitly `rand(X, Y)` where:
- `VOICE_BOOST_MIN_DELAY` (X) = 30 seconds
- `VOICE_BOOST_MAX_DELAY` (Y) = 240 seconds (4 min)

Adjust these based on user feedback. Shorter = more intense session. Longer = more breathing room.

## Testing

1. Join ambient channel, wait 5+ min, verify mantra arrives within ~2 min
2. Complete mantra, verify 25% points awarded
3. Verify availability_distribution unchanged after voice-boosted completion
4. Verify frequency unchanged after voice-boosted completion
5. Leave channel before mantra fires, verify it still delivers
6. Complete pending mantra while back in voice, verify another boost triggers

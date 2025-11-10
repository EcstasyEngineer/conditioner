# Mantra System V2 - Design Document

## State Machine (Simplified)

### Two-Timestamp Approach

No explicit state variable needed. State is implicit from timestamps:

```python
config = {
    "next_delivery": "2025-11-11T14:00:00",  # When to send next
    "sent": null,  # When current was sent (null = not sent yet)
    "consecutive_failures": 0
}
```

**State interpretation:**
- `sent == null` → Waiting to send at `next_delivery`
- `sent != null && now < next_delivery` → Awaiting user response
- `sent != null && now >= next_delivery` → Timeout/missed

### State Transitions

**On delivery loop (every 5 min):**
```python
if config['sent'] is None:
    # Not sent yet
    if now >= config['next_delivery']:
        # Time to send!
        await send_mantra(user)
        config['sent'] = now
        config['next_delivery'] = schedule_next(user)  # Immediately schedule next
else:
    # Already sent, waiting for response
    if now >= config['next_delivery']:
        # Hit next delivery time = timeout
        config['consecutive_failures'] += 1
        config['sent'] = None
        log_encounter(user, completed=False, expired=True)

        if config['consecutive_failures'] >= 5:
            config['enrolled'] = False  # Auto-disable
```

**On user response:**
```python
# Success!
config['consecutive_failures'] = 0
config['sent'] = None  # Clear sent timestamp
log_encounter(user, completed=True, response_time=...)
award_points(...)
# next_delivery already scheduled, no change needed
```

**Key insight:** `next_delivery` serves as BOTH the target send time AND the deadline. No separate deadline field needed.

---

## Scheduling Algorithm: Probability Distribution Integration

### Concept

Build a probability distribution of user availability (continuous or discrete). To schedule next encounter, "walk forward" until we've accumulated enough probability mass.

### Building the Distribution

**Historical Analysis:**
```python
def build_availability_distribution(user_id):
    """Build probability distribution from historical encounters."""
    encounters = load_encounters(user_id)

    # Option A: Discrete buckets (hour or 30min)
    hour_success = defaultdict(lambda: {'completed': 0, 'total': 0})

    for enc in encounters:
        dt = datetime.fromisoformat(enc['timestamp'])
        hour = dt.hour  # Or use (hour * 2 + minute // 30) for 30min buckets
        hour_success[hour]['total'] += 1
        if enc.get('completed'):
            hour_success[hour]['completed'] += 1

    # Calculate probabilities (with smoothing for sparse data)
    probabilities = {}
    for hour in range(24):
        stats = hour_success[hour]
        if stats['total'] >= 3:
            probabilities[hour] = stats['completed'] / stats['total']
        else:
            probabilities[hour] = 0.5  # Neutral default

    # Option B: Continuous (polynomial/gaussian fit)
    # Could fit a mixture of gaussians to the success data
    # For now, discrete is simpler and works

    return probabilities  # dict: hour -> probability (0-1)
```

**Weekday/Weekend Consideration:**
```python
def build_availability_distribution(user_id):
    """Build separate distributions for weekday vs weekend."""

    weekday_probs = build_distribution_for_days(user_id, [0,1,2,3,4])  # Mon-Fri
    weekend_probs = build_distribution_for_days(user_id, [5,6])  # Sat-Sun

    return {
        'weekday': weekday_probs,
        'weekend': weekend_probs
    }
```

### Scheduling via Integration

**Core idea:** Instead of fixed intervals, accumulate probability mass.

```python
def schedule_next(user_id):
    """Schedule next encounter by integrating probability distribution."""

    config = get_config(user_id)
    distribution = build_availability_distribution(user_id)

    # Determine if next day is weekday or weekend
    next_day = datetime.now() + timedelta(days=1)
    is_weekend = next_day.weekday() >= 5
    probs = distribution['weekend' if is_weekend else 'weekday']

    # Calculate "area under curve" needed
    # This replaces the TCP speedup - higher frequency = less area needed
    frequency = config.get('frequency', 1.0)  # encounters per day
    target_mass = 1.0 / frequency  # e.g., 2/day = 0.5 mass needed

    # Walk forward in time, accumulating probability
    current_time = datetime.now()
    accumulated_mass = 0.0

    for hours_ahead in range(1, 168):  # Check up to 7 days ahead
        check_time = current_time + timedelta(hours=hours_ahead)
        hour = check_time.hour

        # Get probability for this hour
        prob = probs.get(hour, 0.5)

        # Accumulate mass (1 hour * probability)
        accumulated_mass += prob

        # Have we reached target?
        if accumulated_mass >= target_mass:
            return check_time.replace(minute=0, second=0)

    # Fallback: 24 hours from now
    return current_time + timedelta(hours=24)
```

**Example walkthrough:**

User has distribution:
- Hour 9: 0.3
- Hour 14: 0.5
- Hour 16: 0.4
- Hour 2-6: 0.1 (night)

User frequency: 2.0 encounters/day → target_mass = 0.5

Starting at hour 7:
- Hour 8: prob=0.2, accumulated=0.2
- Hour 9: prob=0.3, accumulated=0.5 ✓ **Schedule for 9AM**

This naturally **squeezes away** from low-probability times (night).

---

## TCP Speedup (Revised)

Instead of multiplying frequency:
```python
# Old approach (bad):
new_freq = current_freq * 1.1

# New approach (good):
# Frequency affects target_mass in schedule_next()
# Higher frequency = smaller target_mass = schedules sooner
# Lower frequency = larger target_mass = schedules later
```

On success with fast response:
```python
if response_time < 120:
    config['frequency'] = min(6.0, config['frequency'] * 1.1)
```

On timeout:
```python
config['frequency'] = max(0.33, config['frequency'] * 0.9)
```

This preserves TCP-style acceleration but applies it via the scheduling algorithm.

---

## Implementation Checklist

### Phase 1: State Machine (2 days)
- [ ] Add `next_delivery` and `sent` to user config
- [ ] Remove `current_encounter` state machine
- [ ] Update delivery loop to use two-timestamp logic
- [ ] Test reload safety

### Phase 2: Probability Scheduling (3 days)
- [ ] Implement `build_availability_distribution()`
- [ ] Add weekday/weekend split
- [ ] Implement `schedule_next()` with integration
- [ ] Test with historical data

### Phase 3: Refinements (2 days)
- [ ] Tune minimum sample sizes
- [ ] Add smoothing for sparse data
- [ ] Consider 30min buckets vs hour buckets
- [ ] Test edge cases (new users, always-offline, etc.)

### Phase 4: UI Refactor (3 days)
- [ ] Extract services layer
- [ ] Move logic out of views
- [ ] Fix broken buttons
- [ ] Add favorites button

---

## Open Questions

1. **Bucket granularity:** Hour vs 30min? (Start with hour, refine later)
2. **Smoothing:** How to handle hours with 0-2 samples? (Use global default or neighbor averaging)
3. **Continuous vs discrete:** Polynomial fit worth the complexity? (No, discrete is fine)
4. **Frequency bounds:** Keep 0.33-6.0 range? (Yes, proven safe)
5. **Auto-disable threshold:** Keep 5 consecutive failures? (Yes)

---

## Migration Path

1. Deploy state machine change (backwards compatible, just changes storage)
2. Run both old scheduler + new scheduler in parallel for 1 week (log both, send using old)
3. Compare results, tune parameters
4. Switch to new scheduler
5. UI refactor can happen independently

---

## Data Analysis Results

From 1,213 historical encounters across 11 users:

**Per-User Insights:**
- Natural pacing: 11h - 140h (highly variable)
- Active hours: Completely personalized
- Example patterns:
  - User A: Morning (7-10AM), 100% completion
  - User B: Night owl (8PM-midnight), 100% completion
  - User C: Afternoon only (2-5PM), 88% completion

**Aggregate:**
- Most common active hours: 9AM, 2PM, 4PM, 5PM (but NOT universal)
- Day of week: No significant pattern (75-80% across all days)
- High performers: Consistent in their specific hours
- Low performers: Scattered across all hours

**Key Takeaway:** One-size-fits-all scheduling won't work. Per-user learning is essential.

---

## Example Config Schema

```json
{
  "enrolled": true,
  "themes": ["acceptance", "suggestibility"],
  "frequency": 2.0,

  "next_delivery": "2025-11-11T14:00:00",
  "sent": null,
  "consecutive_failures": 0,

  "current_mantra": {
    "text": "I accept complete reprogramming",
    "theme": "acceptance",
    "difficulty": "extreme",
    "base_points": 90
  },

  "favorites": {
    "I am completely programmable": 2.0
  },

  "learned_distribution": {
    "weekday": {
      "9": 0.3,
      "14": 0.5,
      "16": 0.4
    },
    "weekend": {
      "10": 0.4,
      "16": 0.6,
      "20": 0.3
    }
  }
}
```

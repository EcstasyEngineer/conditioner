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

### Learning the Distribution: Prediction Error Algorithm

**Core Concept:** Learn from surprise. Large updates when prediction is wrong, small updates when it's right.

**Implementation:**
```python
class AvailabilityLearner:
    def __init__(self):
        # Hour buckets (24 per day)
        self.distribution = [0.5 for _ in range(24)]
        self.learning_rate = 0.20
        self.floor = 0.1  # Prevent death spiral
        self.ceil = 1.0

    def hour_of_day(self, dt: datetime) -> int:
        """Get hour bucket (0-23) from datetime."""
        return dt.hour

    def update(self, dt: datetime, success: bool):
        """Update based on prediction error (Elo-style)."""
        hour = self.hour_of_day(dt)
        actual = 1.0 if success else 0.0
        expected = self.distribution[hour]

        # Prediction error
        error = actual - expected
        delta = self.learning_rate * error

        new_value = self.distribution[hour] + delta
        clamped_value = max(self.floor, min(self.ceil, new_value))

        # Round to 3 decimals to keep config files clean
        self.distribution[hour] = round(clamped_value, 3)

    def get_prob(self, dt: datetime) -> float:
        """Get probability for a given datetime."""
        hour = self.hour_of_day(dt)
        return self.distribution[hour]

    def get_distribution(self):
        return self.distribution
```

**Why This Works:**

**High surprise = large update:**
- Success at prob 0.1: `delta = 0.20 * (1.0 - 0.1) = +0.18` (big boost!)
- Failure at prob 0.9: `delta = 0.20 * (0.0 - 0.9) = -0.18` (big penalty!)

**Low surprise = small update:**
- Success at prob 0.9: `delta = 0.20 * (1.0 - 0.9) = +0.02` (tiny boost)
- Failure at prob 0.1: `delta = 0.20 * (0.0 - 0.1) = -0.02` (tiny penalty)

**Natural anti-collapse:** Can't reach 0.0 (asymptotic approach), plus safety floor at 0.1

**Why no gaussian smoothing:**
- Prediction error algorithm's self-dampening is sufficient for 24 buckets
- Adding gaussian neighbors dilutes the learning signal
- Simpler implementation (just 10 lines of core logic)

**Tested Performance (960 total test runs):**
- **1hr buckets, lr=0.20, no gaussian**: MAE 0.0878 (WINNER)
  - Most stable: σ=0.0186
  - Best across all 4 test archetypes
- **15min buckets + gaussian**: MAE 0.0968 (10% worse, too sparse)
- **30min buckets + gaussian**: MAE 0.1100 (20% worse)
- 53% better than baseline additive learning
- 11% better than multiplicative learning
- 26% better recovery from pattern changes

### Scheduling via Integration

**Core idea:** Instead of fixed intervals, accumulate probability mass.

```python
def schedule_next(user_id):
    """Schedule next encounter by integrating probability distribution."""

    config = get_config(user_id)
    learner = get_learner(user_id)  # Persistent learner instance
    distribution = learner.get_distribution()

    # Calculate "area under curve" needed
    # Higher frequency = less area needed = schedules sooner
    frequency = config.get('frequency', 1.0)  # encounters per day
    target_mass = 1.0 / frequency  # e.g., 2/day = 0.5 mass needed

    # Walk forward in time, accumulating probability
    current_time = datetime.now()
    accumulated_mass = 0.0

    for hours_ahead in range(1, 168):  # Check up to 7 days ahead
        check_time = current_time + timedelta(hours=hours_ahead)
        hour = check_time.hour

        # Get probability for this hour
        prob = distribution.get(hour, 0.5)

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

### Phase 2: Prediction Error Learning (2 days)
- [ ] Implement `AvailabilityLearner` class with prediction error updates
- [ ] Store learner state in user config (distribution dict)
- [ ] Update on each encounter (success or failure)
- [ ] Persist distribution to config after updates

### Phase 3: Probability Integration Scheduling (2 days)
- [ ] Implement `schedule_next()` with probability integration
- [ ] Use learner's distribution for scheduling
- [ ] Test "squeeze away" behavior (avoids dead zones)
- [ ] Test with historical data

### Phase 4: Refinements (2 days)
- [ ] Test edge cases (new users, pattern changes, always-offline)
- [ ] Verify floor prevents death spiral
- [ ] Test TCP frequency acceleration integration
- [ ] Monitor convergence over time

### Phase 5: UI Refactor (3 days)
- [ ] Extract services layer
- [ ] Move logic out of views
- [ ] Fix broken buttons
- [ ] Add favorites button

---

## Resolved Design Questions

Based on comprehensive testing with simulated and real user data:

1. **Learning algorithm:** ✓ Prediction error (Elo-style) - 53% better than baseline
2. **Learning rate:** ✓ 0.20 optimal (tested 0.10-0.30 across 720 runs)
3. **Gaussian smoothing:** ✗ Not needed - dilutes signal, prediction error self-dampens
4. **Floor/ceiling:** ✓ [0.1, 1.0] prevents death spiral
5. **Weekday/weekend split:** ✗ Single 24-hour distribution works fine
6. **Bucket granularity:** ✓ Hour buckets (24 per day) - best stability and final accuracy
7. **Minute interpolation:** ✗ Worse performance (65% worse MAE)
8. **Multi-hour expiration windows:** ✗ Dilutes signal (48% worse MAE)
9. **Success-only learning:** ✗ Throws away valuable data (147% worse MAE)
10. **Decay toward baseline:** ✗ Prevents convergence
11. **Frequency bounds:** ✓ Keep 0.33-6.0 range
12. **Auto-disable threshold:** ✓ Keep 5 consecutive failures

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

## Testing Results

**Simulation with synthetic users (300 encounters):**
- Prediction error learning: MAE 0.069
- Proportional updates: MAE 0.078 (11% worse)
- Additive with floor: MAE 0.089 (29% worse)
- Additive baseline: MAE 0.137 (98% worse)

**Real user data (9 users, 43-281 encounters):**
- Single-hour bidirectional: MAE 0.101 (best)
- Multi-hour windows: MAE 0.160 (58% worse)
- Success-only: MAE 0.249 (147% worse)

**Pattern change recovery (morning→night transition):**
- Prediction error @ 30 encounters: MAE 0.277
- Proportional @ 30 encounters: MAE 0.375 (35% worse)

**Convergence speed:**
- 60% learned after 15-20 encounters
- Final accuracy achieved by 200-300 encounters

**Comprehensive bucket size + learning rate sweep (960 total runs):**

*Multi-seed stability test (20 seeds × 4 archetypes × 3 configs = 240 runs):*
- **1hr lr=0.20 no-gauss: MAE 0.0878** ✓ WINNER
  - Std dev: 0.0186 (most stable)
  - Range: [0.0474, 0.1306]
  - Best on all 4 archetypes
- 15min lr=0.25 gauss-w4: MAE 0.0968 (10% worse, too sparse)
- 30min lr=0.30 gauss-w3: MAE 0.1100 (20% worse)

*Learning rate sweep for 1hr no-gaussian (20 seeds × 4 archetypes × 9 LRs = 720 runs):*
- lr=0.20: MAE 0.0878 ✓ OPTIMAL
- lr=0.17: MAE 0.0885 (0.8% worse)
- lr=0.22: MAE 0.0888 (1.1% worse)
- lr=0.15: MAE 0.0913 (4.0% worse)
- lr=0.25: MAE 0.0915 (4.2% worse)
- lr=0.10: MAE 0.1170 (25% worse, too slow)
- lr=0.30: MAE 0.0973 (10% worse, too aggressive)

**Key insights:**
- Hour buckets best for long-term accuracy (200+ encounters)
- Smaller buckets (15min, 30min) learn faster early but worse final accuracy
- Gaussian smoothing dilutes learning signal for 24 buckets
- Sweet spot for lr is 0.17-0.22, with 0.20 at peak

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

  "availability_distribution": [
    0.15, 0.12, 0.10, 0.10, 0.10, 0.10, 0.10, 0.45, 0.73, 0.88, 0.65, 0.42,
    0.35, 0.32, 0.92, 0.78, 0.65, 0.58, 0.82, 0.71, 0.62, 0.55, 0.48, 0.25
  ]
}
```

**Note:** Distribution is an array of 24 floats (index 0 = midnight-1am, 1 = 1am-2am, etc.). Starts at 0.5 for all hours, updates via prediction error learning on each encounter. Values are automatically rounded to 3 decimals to keep config files clean (e.g., 0.732 instead of 0.73234567).

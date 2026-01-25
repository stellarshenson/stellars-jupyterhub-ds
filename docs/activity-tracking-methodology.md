# Activity Tracking Methodology Research

## Current Implementation

Our current approach uses **exponential decay scoring**:
- Samples collected every 10 minutes (configurable)
- Each sample marked active/inactive based on `last_activity` within threshold
- Score calculated as weighted ratio: `weighted_active / weighted_total`
- Weight formula: `weight = exp(-λ × age_hours)` where `λ = ln(2) / half_life`
- Default half-life: 72 hours / 3 days (activity from 3 days ago worth 50%)

### Why 72-hour Half-life?

The decay applies to **wall-clock time**, not working time. Users work only a fraction of each 24-hour period, creating a mismatch between configured (calendar) half-life and effective (working hours) half-life.

#### Configured vs Effective Half-life

**The difference is NOT about sampling** - sampling just measures activity at discrete intervals.

The difference comes from:
1. **Decay is CONTINUOUS** - applies to calendar time 24/7
2. **Work is SPARSE** - only happens during work hours
3. **Decay during BREAKS** - overnight/weekend decay continues with no new work

Example with 72h configured half-life and 8h/day work:

| Event | Calendar Age | Weight | Work Added |
|:------|-------------:|-------:|:----------:|
| Day 0: Work 9am-5pm | 0h | 1.000 | +8h |
| Day 0: Sleep overnight | 16h | 0.857 | -- |
| Day 1: Work 9am-5pm | 24h | 0.794 | +8h |
| Day 1: Sleep overnight | 40h | 0.680 | -- |
| Day 2: Work 9am-5pm | 48h | 0.630 | +8h |
| Day 2: Sleep overnight | 64h | 0.540 | -- |
| Day 3: Work 9am-5pm | 72h | 0.500 | +8h |

At 72h calendar age, weight = 0.500 (half-life by definition). But only 24 work hours occurred in those 72 calendar hours. Each overnight break (16h) causes ~15% decay with no new work added.

#### Effective Half-life Table

The following table shows **effective half-life in working hours** for different work patterns and configured half-lives. Simulation: 7 days, 10-minute sampling intervals.

| Work Pattern | Configured 24h | Configured 48h | Configured 72h |
|:------------:|:--------------:|:--------------:|:--------------:|
| 12h/day | 12.0h | 21.3h | 26.8h |
| 10h/day | 10.0h | 17.8h | 22.3h |
| 8h/day | 8.0h | 14.3h | 18.0h |
| 6h/day | 6.0h | 10.8h | 13.5h |
| 4h/day | 4.0h | 7.2h | 9.0h |
| 2h/day | 2.0h | 3.7h | 4.5h |

#### Key Insights

With a 72-hour configured half-life:
- **8h/day worker**: effective half-life is 18 working hours (~2.25 work days)
- **4h/day worker**: effective half-life is 9 working hours (~2.25 work days)
- **Consistent ~2.25 work days** at the 50% point regardless of daily work hours
- Overnight breaks don't aggressively penalize scores
- A 24-hour configured half-life gives exactly 1 work day effective half-life

## Industry Approaches

### 1. Exponential Moving Average (EMA) / Time-Decay Systems

**How it works:**
- Recent events weighted more heavily than older ones
- Decay factor (α) determines how quickly old data loses relevance
- Example: α=0.5 per day means yesterday's activity worth 50%, two days ago worth 25%

**Half-life parameterization:**
- More intuitive than raw decay factor
- "Activity has a 24-hour half-life" is clearer than "α=0.5"
- Our implementation already uses this approach

**Pros:**
- Memory-efficient (no need to store all historical data)
- Naturally handles irregular sampling intervals
- Smooths out noise/outliers

**Cons:**
- Older activity never fully disappears (asymptotic to zero)
- May not match user intuition of "weekly activity"

**Reference:** [Exponential Moving Averages at Scale](https://odsc.com/blog/exponential-moving-averages-at-scale-building-smart-time-decay-systems/)

---

### 2. Time-Window Activity Percentage (Hubstaff approach)

**How it works:**
- Fixed time window (e.g., 10 minutes)
- Count active seconds / total seconds = activity %
- Aggregate over day/week as average of windows

**Hubstaff's formula:**
```
Active seconds / 600 = activity rate % (per 10-min segment)
```

**Key insight from Hubstaff:**
> "Depending on someone's job and daily tasks, activity rates will vary widely. People with 75% scores and those with 25% scores can often times both be working productively."

**Typical benchmarks:**
- Data entry/development: 60-80% keyboard/mouse activity
- Research/meetings: 30-50% activity
- 100% is unrealistic for any role

**Pros:**
- Simple to understand
- Direct mapping to "how active was I today"

**Cons:**
- Doesn't capture quality of work
- Penalizes reading, thinking, meetings

**Reference:** [Hubstaff Activity Calculation](https://support.hubstaff.com/how-are-activity-levels-calculated/)

---

### 3. Productivity Categorization (RescueTime approach)

**How it works:**
- Applications/websites pre-categorized by productivity score (-2 to +2)
- Time spent in each category weighted and summed
- Daily productivity score = weighted sum / total time

**Categories:**
- Very Productive (+2): IDE, documentation
- Productive (+1): Email, spreadsheets
- Neutral (0): Uncategorized
- Distracting (-1): News sites
- Very Distracting (-2): Social media, games

**Pros:**
- Captures quality of activity, not just presence
- Customizable per user/role

**Cons:**
- Requires app categorization (complex to implement)
- Subjective classification
- Not applicable to JupyterLab (all activity is "productive")

**Reference:** [RescueTime Methodology](https://www.rescuetime.com/)

---

### 4. GitHub Contribution Graph (Threshold-based intensity)

**How it works:**
- Count contributions per day (commits, PRs, issues)
- Map counts to 4-5 intensity levels
- Levels based on percentiles of user's own activity

**Typical thresholds:**
```javascript
// Example from implementations
thresholds: [0, 10, 20, 30]  // contributions per day
colors: ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39']
```

**Key insight:**
- Relative to user's own history (not absolute)
- Someone with 5 commits/day max sees different scale than 50 commits/day

**Pros:**
- Visual, intuitive
- Adapts to user's activity patterns

**Cons:**
- Binary daily view (no intra-day granularity)
- Doesn't show decay/trend

---

### 5. Daily Target Approach (8h = 100%)

**How it works:**
- Define expected activity hours per day (e.g., 8h)
- Actual active hours / expected hours = daily score
- Cap at 100% or allow overtime bonus

**Formula:**
```
Daily score = min(1.0, active_hours / 8.0) × 100
Weekly score = avg(daily_scores)
```

**Pros:**
- Maps directly to work expectations
- Easy to explain to users

**Cons:**
- Assumes consistent work schedule
- Doesn't account for part-time, weekends
- JupyterHub users may have variable schedules

---

## Recommendations for JupyterHub Activity Monitor

### Option A: Keep Current (EMA with decay)

Our current implementation is actually well-designed for the use case:

| Aspect | Current Implementation |
|--------|------------------------|
| Sampling | Every 10 min (configurable) |
| Active threshold | 60 min since last_activity |
| Decay | 72-hour (3-day) half-life |
| Score range | 0-100% |
| Visualization | 5-segment bar with color coding |

**Suggested improvements:**
1. Add tooltip showing actual score percentage
2. Document what the score represents

### Option B: Hybrid Daily + Decay

Combine daily activity percentage with decay:

```python
# Daily activity: hours active today / 8 hours (capped at 100%)
daily_score = min(1.0, active_hours_today / 8.0)

# Apply decay to historical daily scores
weekly_score = sum(daily_score[i] * exp(-λ * i) for i in range(7)) / 7
```

**Benefits:**
- More intuitive "8h = full day" concept
- Still decays older activity

### Option C: Simplified Presence-Based

For JupyterLab, activity mostly means "server running + recent kernel activity":

| Status | Points/day |
|--------|------------|
| Offline | 0 |
| Online, idle > 1h | 0.25 |
| Online, idle 15m-1h | 0.5 |
| Online, active < 15m | 1.0 |

Weekly score = sum of daily points / 7

---

## Decision Points

1. **What does "100% activity" mean for JupyterHub users?**
   - Option: Active during all sampled periods in retention window
   - Option: 8 hours of activity per day
   - Option: Relative to user's own historical average

2. **How fast should old activity decay?**
   - Current: 72-hour / 3-day half-life (balanced decay)
   - Alternative: 24-hour half-life (aggressive decay)
   - Alternative: 7-day half-life (weekly trend)

3. **Should weekends count differently?**
   - Current: All days weighted equally
   - Alternative: Exclude weekends from expected activity

---

## Sources

- [Exponential Moving Averages at Scale (ODSC)](https://odsc.com/blog/exponential-moving-averages-at-scale-building-smart-time-decay-systems/)
- [Exponential Smoothing (Wikipedia)](https://en.wikipedia.org/wiki/Exponential_smoothing)
- [Hubstaff Activity Calculation](https://support.hubstaff.com/how-are-activity-levels-calculated/)
- [How Time is Calculated in Hubstaff](https://support.hubstaff.com/how-is-time-tracked-and-calculated-in-hubstaff/)
- [RescueTime](https://www.rescuetime.com/)
- [EWMA Formula (Corporate Finance Institute)](https://corporatefinanceinstitute.com/resources/career-map/sell-side/capital-markets/exponentially-weighted-moving-average-ewma/)
- [Developer Productivity Metrics (Axify)](https://axify.io/blog/developer-productivity-metrics)

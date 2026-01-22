# Activity Tracking Methodology Research

## Current Implementation

Our current approach uses **exponential decay scoring**:
- Samples collected every 10 minutes (configurable)
- Each sample marked active/inactive based on `last_activity` within threshold
- Score calculated as weighted ratio: `weighted_active / weighted_total`
- Weight formula: `weight = exp(-λ × age_hours)` where `λ = ln(2) / half_life`
- Default half-life: 24 hours (activity from yesterday worth 50%)

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
| Decay | 24-hour half-life |
| Score range | 0-100% |
| Visualization | 5-segment bar with color coding |

**Suggested improvements:**
1. Add tooltip showing actual score percentage
2. Consider longer half-life (48-72h) for less frequent users
3. Document what the score represents

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
   - Current: 24-hour half-life (aggressive decay)
   - Alternative: 72-hour half-life (more stable)
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

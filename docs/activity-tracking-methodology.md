# JupyterHub Activity Monitoring Methodology

This document describes the activity monitoring system implemented in stellars-jupyterhub-ds.

## Overview

The Activity Monitor provides administrators with real-time visibility into user engagement and resource consumption across all JupyterLab containers. It combines instantaneous metrics (CPU, memory, status) with historical activity scoring using exponential decay.

**Access**: Admin-only page at `/activity`

## Data Collection

### Activity Sampling

The system samples user activity at regular intervals, recording whether each user was active during that period.

| Parameter | Environment Variable | Default | Description |
|-----------|---------------------|---------|-------------|
| Sample interval | `JUPYTERHUB_ACTIVITYMON_SAMPLE_INTERVAL` | 600s (10 min) | Time between activity samples |
| Inactive threshold | `JUPYTERHUB_ACTIVITYMON_INACTIVE_AFTER` | 60 min | Minutes since last activity to mark inactive |
| Retention period | `JUPYTERHUB_ACTIVITYMON_RETENTION_DAYS` | 7 days | How long samples are stored |

Each sample records:
- Username
- Timestamp
- Active flag (true if `last_activity` within inactive threshold)

Samples are stored in SQLite database (`/data/activity_samples.db`) and persist across hub restarts.

### Resource Metrics

Real-time metrics collected via Docker API:

| Metric | Update Interval | Source |
|--------|-----------------|--------|
| CPU % | 10s | Docker stats API |
| Memory MB | 10s | Docker stats API |
| Volume sizes | 1h | Docker volume inspect |
| Server status | 10s | JupyterHub spawner state |

Volume breakdown shows per-volume sizes (home, workspace, cache) in tooltip.

## Activity Score Calculation

### Exponential Decay Formula

Activity score uses weighted ratio of active samples, where recent samples count more than older ones:

```
score = (Σ weighted_active) / (Σ weighted_total) × 100

weight = exp(-λ × age_hours)
λ = ln(2) / half_life_hours
```

With a 72-hour half-life:
- Samples from 3 days ago have 50% weight
- Samples from 6 days ago have 25% weight
- Samples from 9 days ago have 12.5% weight

### Normalization

Raw scores represent percentage of sampled time that the user was active. Since users don't work 24/7, this is normalized against expected work hours:

```
normalized_score = raw_score / (target_hours / 24)
```

| Parameter | Environment Variable | Default | Description |
|-----------|---------------------|---------|-------------|
| Target hours | `JUPYTERHUB_ACTIVITYMON_TARGET_HOURS` | 8h | Expected work hours per day for 100% score |
| Half-life | `JUPYTERHUB_ACTIVITYMON_HALF_LIFE` | 72h | Decay half-life in hours |

Example: User active 8h/day has raw score ~33% (8/24). With 8h target: `33% / 0.333 = 100%`.

### Minimum Data Requirement

Activity percentage is shown in tooltip only after 24 hours of data collection. Before that, tooltip displays "Not enough data (Nh of 24h collected)" to prevent misleading scores from incomplete data.

Minimum samples required: `86400 / sample_interval` (144 samples at 10-minute intervals)

## Wall-Clock vs Working Time

The decay applies continuously to calendar time, but users only work a fraction of each day. This creates a difference between configured half-life and effective half-life.

### Why It Matters

| Event | Calendar Age | Weight | Impact |
|:------|-------------:|-------:|:-------|
| Day 0: Work 9am-5pm | 0h | 1.000 | +8h active |
| Day 0: Sleep overnight | 16h | 0.857 | Decay, no new work |
| Day 1: Work 9am-5pm | 24h | 0.794 | +8h active |
| Day 1: Sleep overnight | 40h | 0.680 | Decay, no new work |
| Day 2: Work 9am-5pm | 48h | 0.630 | +8h active |
| Day 3: Start of day | 72h | 0.500 | Half-life point |

Each overnight break causes ~15% decay with no new activity to offset it.

### Effective Half-life Table

Effective half-life in working hours for different work patterns:

| Work Pattern | Configured 24h | Configured 48h | Configured 72h |
|:------------:|:--------------:|:--------------:|:--------------:|
| 12h/day | 12.0h | 21.3h | 26.8h |
| 10h/day | 10.0h | 17.8h | 22.3h |
| 8h/day | 8.0h | 14.3h | 18.0h |
| 6h/day | 6.0h | 10.8h | 13.5h |
| 4h/day | 4.0h | 7.2h | 9.0h |
| 2h/day | 2.0h | 3.7h | 4.5h |

With 72-hour configured half-life, an 8h/day worker has 18 working hours (~2.25 work days) effective half-life. This prevents overnight breaks from aggressively penalizing scores.

## User Interface

### Status Indicator

Three-state indicator based on server and activity status:

| Color | Status | Condition |
|-------|--------|-----------|
| Green | Active | Server running AND activity within inactive threshold |
| Yellow | Inactive | Server running BUT no recent activity |
| Red | Offline | Server not running |

### Activity Bar

5-segment bar visualization with color coding:

| Segments Lit | Color | Meaning |
|--------------|-------|---------|
| 4-5 | Green | High activity (80-100%) |
| 2-3 | Yellow | Medium activity (40-79%) |
| 1 | Red | Low activity (1-39%) |
| 0 | Empty | No activity (0%) |

Bar is capped at 100% (5 segments). Tooltip shows actual percentage, including values over 100% for users exceeding target hours.

### Table Columns

| Column | Description | Sortable |
|--------|-------------|----------|
| User | JupyterHub username | Yes |
| Auth | Authorization status (checkmark=authorized, X=not authorized) | Yes |
| Status | 3-state indicator (green=active, yellow=idle, red=offline) | Yes |
| CPU | Current CPU usage % | Yes |
| Memory | Current memory in MB/GB | Yes |
| Volumes | Total volume size (tooltip: per-volume breakdown) | Yes |
| Time Left | Remaining session time (if idle culler enabled) | Yes |
| Last Active | Relative time since last activity | Yes |
| Activity | Normalized activity score bar | Yes |

All column headers have tooltips explaining their meaning.

Default sort: Status descending (active users first), then username ascending.

## API Endpoints

### GET /api/activity

Returns JSON array of all users with activity data:

```json
{
  "users": [
    {
      "username": "konrad",
      "is_authorized": true,
      "server_active": true,
      "recently_active": true,
      "cpu_percent": 12.5,
      "memory_mb": 1234,
      "memory_percent": 15.2,
      "volume_size_mb": 2048,
      "volume_breakdown": {"home": 512, "workspace": 1400, "cache": 136},
      "time_remaining_seconds": 85500,
      "activity_score": 33.2,
      "sample_count": 288,
      "last_activity": "2026-01-25T10:30:00Z"
    }
  ],
  "timestamp": "2026-01-25T11:00:00Z"
}
```

### POST /api/activity/reset

Clears all activity samples. Admin only. Returns confirmation message.

## Configuration Reference

All environment variables with defaults:

```bash
# Sampling
JUPYTERHUB_ACTIVITYMON_SAMPLE_INTERVAL=600      # seconds between samples
JUPYTERHUB_ACTIVITYMON_RETENTION_DAYS=7         # days to keep samples
JUPYTERHUB_ACTIVITYMON_INACTIVE_AFTER=60        # minutes until inactive

# Scoring
JUPYTERHUB_ACTIVITYMON_HALF_LIFE=72             # decay half-life in hours
JUPYTERHUB_ACTIVITYMON_TARGET_HOURS=8           # target hours for 100%

# UI refresh
JUPYTERHUB_ACTIVITYMON_RESOURCES_UPDATE_INTERVAL=10    # seconds
JUPYTERHUB_ACTIVITYMON_VOLUMES_UPDATE_INTERVAL=3600    # seconds
```

## Implementation Files

| File | Purpose |
|------|---------|
| `services/jupyterhub/conf/bin/custom_handlers.py` | API handlers, sampling logic, score calculation |
| `services/jupyterhub/html_templates_enhanced/activity.html` | Admin UI template |
| `config/jupyterhub_config.py` | Handler registration, template vars |
| `services/jupyterhub/conf/settings_dictionary.yml` | Settings page definitions |

## Database Schema

SQLite database at `/data/activity_samples.db`:

```sql
CREATE TABLE activity_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    is_active INTEGER NOT NULL,
    UNIQUE(username, timestamp)
);

CREATE INDEX idx_activity_username ON activity_samples(username);
CREATE INDEX idx_activity_timestamp ON activity_samples(timestamp);
```

## Design Rationale

### Why Exponential Decay?

- Memory-efficient (no need to store weighted aggregates)
- Naturally handles irregular work schedules
- Smooths noise from sporadic activity
- Configurable half-life adapts to different use cases

### Why 72-hour Half-life?

- Provides ~2.25 work days effective half-life for 8h/day workers
- Doesn't aggressively penalize weekends or breaks
- Balances recency with stability
- Shorter half-life (24h) would over-penalize normal day boundaries

### Why Normalization?

- Raw 33% score for 8h/day worker is confusing
- Normalized 100% matches user expectation of "full work day"
- Allows scores > 100% for overtime visibility
- Configurable target hours adapts to different work patterns

### Why 24h Minimum Data?

- Prevents misleading scores from partial data
- Single work session would show artificially high/low score
- Full day of data gives representative sample
- Clear feedback to users about data collection progress

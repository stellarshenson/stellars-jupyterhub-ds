# Acceptance Criteria - activity scoring (target-hours normalisation + honest hours)

The activity score is the user's recent active time measured against a daily target (`JUPYTERHUB_ACTIVITYMON_TARGET_HOURS`, default 8h), not against the 24h clock. Samples are taken 24/7, so the decay-weighted active fraction is the share of the day active; the score normalises that against the target and caps at 100. A separate honest hours figure (`activity_hours`, real avg active hours/day, uncapped) drives the meter tooltip.

## Root cause (under-reporting: Natalia 33%)

- [x] **Identified** - `monitor.get_score` returned the raw decay-weighted active fraction (active / all 24/7 samples), so an 8h/day user maxed at 8/24 = 33%
  - log: 2026-06-17 root-caused; `monitor.py:get_score`
- [x] **Regression source** - the original `activity.html` normalised client-side (`normalized = activity_score / (targetHours/24)`, i.e. 33/0.333 ≈ 100); the React portal dropped that step and showed the raw 33%
  - log: 2026-06-17 confirmed against git `HEAD:services/jupyterhub/html_templates_enhanced/activity.html:74-76,231-235`
- [x] **Unused setting** - `JUPYTERHUB_ACTIVITYMON_TARGET_HOURS` was documented and passed to templates but never referenced by the scorer
  - log: 2026-06-17 now wired into `ActivityMonitor`

## Fix

- [x] **Normalise in the backend** - `get_score` returns `min(100, round((active_fraction*24 / target_hours) * 100))` so every consumer (portal, log buckets) agrees; the normalisation lives once, in the scorer
  - log: 2026-06-17 `monitor.py:get_score` via `_weighted_active_fraction`
- [x] **8h/day -> 100** - a user active the target hours scores 100, not 33
  - log: 2026-06-17 `test_eight_hours_a_day_scores_100_not_33`
- [x] **Proportional below target** - ~4h/day scores ~50
  - log: 2026-06-17 `test_half_target_scores_about_50`
- [x] **target_hours config** - read from env (1-24, default 8), echoed in the config log line
  - log: 2026-06-17 `test_target_hours_default`, `test_target_hours_env`
- [x] **Capped meter, honest tooltip** - the 0-100 score caps at 100 (old client was uncapped, could show 150%); the real uncapped hours live in `activity_hours` for the tooltip
  - log: 2026-06-17 `get_avg_active_hours` added
- [x] **Edge: no samples** - `get_score` returns `(None, 0)`, `get_avg_active_hours` returns `None`
  - log: 2026-06-17 `test_avg_active_hours_none_without_samples`
- [x] **Existing behaviour preserved** - all-active -> 100, all-inactive -> 0, recent-active-dominates still holds
  - log: 2026-06-17 prior tests green

## Honest hours tooltip (was: reword to avg hours over 3 days)

- [x] **Real hours exposed** - `/activity` returns `activity_hours` per user (decay-weighted avg active hours/day, uncapped), from `calculate_avg_active_hours`
  - log: 2026-06-17 `handlers/activity.py`, `helpers.calculate_avg_active_hours`
- [x] **Tooltip wording** - the meter tooltip reads "Active on average Nh/day over the last 3 days" (3 days = the 72h half-life window); falls back to "N% of the daily activity target" when hours are absent
  - log: 2026-06-17 `meters.activityTitle`, threaded to hero + servers table + drawer
- [x] **No fabrication** - hours come from real samples; never derived from a percentage
  - log: 2026-06-17 derived in the backend from the sample table
- [ ] **Runtime: heavy users read high** - on the live hub a full-time user shows ~100% with a truthful Nh/day tooltip
  - log: 2026-06-17 backend + frontend + tests done; on-screen confirm pends operator rebuild

## API

- `GET /api/activity` -> each user gains `activity_hours: number | null` alongside `activity_score`
- Env `JUPYTERHUB_ACTIVITYMON_TARGET_HOURS` (1-24, default 8) - daily active hours that count as a 100% score

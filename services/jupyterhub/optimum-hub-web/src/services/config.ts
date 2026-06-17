/* Platform thresholds and quotas - the same values the hub enforces, used by the
 * adapters to flag over-limit cells and by the Settings / Lab Container pages. */

export const THRESHOLDS = {
  memPerUserPct: 25, // JUPYTERHUB_LAB_MEMORY_MAX_USAGE_FRACTION (0.25)
  containerExtraSpaceGB: 10, // JUPYTERHUB_LAB_CONTAINER_MAX_EXTRA_SPACE_GB
  volumeTotalGB: 50, // JUPYTERHUB_LAB_VOLUME_MAX_TOTAL_SIZE_GB
  timeLeftWarnMin: 60, // UI: time-left turns amber below this
}

export const IDLE_CULLER = {
  timeoutH: 4,
  activityTargetH: 8,
  maxExtensionH: 12,
}

// UI animation timings (milliseconds) - tunable here without touching the
// components or CSS. The TTL extend value drives both the JS hold timer and the
// CSS bar-fill/glow (threaded to global.css via the `--oh-ttl-anim` variable).
export const ANIMATION = {
  ttlExtendMs: 3000, // TTL extend: bar fills to the new limit over this duration
}

// Mock-mode display fixtures only. Live mode never reads jupyterhubVersion or
// baseUrl from here - it fetches the real version from GET /hub/api/info
// (liveSource.getHubInfo) and the real settings from the settings handler.
export const PLATFORM = {
  version: '1.0.0',
  jupyterhubVersion: '5.5.0',
  admin: 'admin',
  baseUrl: '/jupyterhub',
  timezone: 'Europe/Warsaw',
  labImage: 'stellars/stellars-jupyterlab-ds:latest',
}

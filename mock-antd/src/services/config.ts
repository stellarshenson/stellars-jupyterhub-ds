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

export const PLATFORM = {
  version: '1.0.0',
  jupyterhubVersion: '3.3.6',
  admin: 'admin',
  baseUrl: '/jupyterhub',
  timezone: 'Europe/Warsaw',
  labImage: 'stellars/stellars-jupyterlab-ds:latest',
}

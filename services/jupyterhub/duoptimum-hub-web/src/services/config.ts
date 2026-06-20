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

// Resource-bar (CPU / memory) fill-colour rule, in percent. Fixed bands, NOT a
// blend through the accent (blending warning with the blue accent muddied it into
// a dim brown): normal accent below `warnPct`, full (normal) warning at/above
// `warnPct`, full danger at/above `dangerPct`; only the warn..danger span blends
// (warm warning -> red). Drives meters.barColor for every CPU/memory bar (host
// status, server hero, servers table). Stated as a rule on /design-language.
export const BAR_COLOR = {
  warnPct: 70, // at or above (and below danger): full warning (amber)
  dangerPct: 90, // at or above: full danger (red)
}

// Servers-list CPU/MEM counter COLOUR by the server's usage as a % of its ASSIGNED
// quota. The counter VALUE is host-relative (CPU = total cores-used %, MEM = GB);
// the COLOUR is quota-relative. Tune the bands here. Drives serverMetrics.quotaColor
// and serverMetrics.quotaCrossing (the tooltip "(over warning threshold)" clause).
export const QUOTA_COLOR = {
  warnPct: 75, // at or above (and below danger): warning (amber)
  dangerPct: 100, // at or above: danger (red) - the assigned quota is reached/exceeded
}

// TTL bar/readout COLOUR by fraction of base left (the reverse of the resource
// bars). Blue (info) above `warnFrac`; full (normal) warning at/below `warnFrac`;
// dim red at/below `dangerFrac` (a low timer is the normal end state, not an
// alarm); only the warn..danger span blends (warm warning -> dim red). Banked
// (frac > 1) = blue. Visual only. Drives meters.ttlTone.
export const TTL_COLOR = {
  warnFrac: 0.30, // at or below this fraction of base left: full warning (amber)
  dangerFrac: 0.10, // at or below: full dim-red
}

// Servers-list column-header explanatory tooltips (CPU/MEM), shared by the Servers
// page table and the Home servers widget so the host-relative figures are not
// misread (the cell shows total CPU across cores / absolute GB, not % of assigned).
export const SERVERS_COL_HELP = {
  cpu: 'Total CPU used across cores - 100% = one core (e.g. 1300% = ~13 cores)',
  mem: 'Memory used, in GB',
}

// UI animation timings (milliseconds) - tunable here without touching the
// components or CSS. The TTL extend value drives the rAF bar-fill + count-up
// hold timer; the glow ramp is threaded to global.css via `--doh-ttl-glow`.
export const ANIMATION = {
  ttlExtendMs: 3000, // TTL extend: bar grows (rAF) from current fill to the new limit over this duration
  ttlGlowMs: 100, // TTL extend: glow/blur RAMP duration (each of ramp-on and ramp-off); the glow holds at 50% in between for the whole fill, never a pulse (threaded to CSS via --doh-ttl-glow)
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

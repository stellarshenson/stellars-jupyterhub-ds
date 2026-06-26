/* Pure mapping from a 0-100 activity value to the 5-segment meter's lit-bar count and
 * tone. Extracted (no React) so it is unit-testable in isolation. */

// Lit-bar count for a 0-100 value. EXACTLY zero activity lights ZERO bars (empty meter);
// any positive value lights at least one (and at most five). null is handled by the caller
// (rendered as a dash), never passed here.
export function litBars(value: number): number {
  if (value <= 0) return 0
  return Math.min(5, Math.max(1, Math.round(value / 20)))
}

// Tone class driven by the lit-bar count: 0 bars = none (empty), 1 = pale red (low),
// 2-3 = orange (idle), 4-5 = green (default, no class).
export function meterTone(lit: number): string {
  return lit <= 0 ? '' : lit <= 1 ? 'low' : lit <= 3 ? 'idle' : ''
}

/* Per-GPU stripe colours - the design system's fixed 10-hue IDENTITY palette.
 *
 * The striped per-GPU meter draws a diagonal stripe over a `var(--color-accent)`
 * fill. Each device's stripe colour is its IDENTITY: a fixed colour bound to the
 * device index, so a given GPU keeps the same hue no matter how many devices are
 * present. (The prior implementation computed an evenly-spaced hue rotation by live
 * count, which shifted every device's colour whenever the inventory changed and
 * could stray into warm "warning" reds.) The palette is 10 curated HSL triples
 * spread across the wheel, hand-tuned on hue + value to read mutually distinct and
 * to avoid alarm hues; past 10 devices the colours cycle and the meter marks the
 * wrapped rows. Pure + framework-free so it is unit-testable. Mirrors the canonical
 * artifact docs/design-system/Design Language.dc.html. */

// 10 fixed identity hues, [h, s%, l%]: cyan, orange, green, violet, neutral gray,
// magenta, green-2, blue, amber, teal. Curated to stay distinct and never alarm-red.
const GPU_STRIPES: ReadonlyArray<readonly [number, number, number]> = [
  [197, 95, 32], [26, 95, 42], [140, 80, 32], [262, 90, 44], [212, 10, 47],
  [322, 90, 42], [95, 85, 38], [225, 95, 42], [45, 95, 40], [170, 90, 31],
]

// number of fixed identity colours; devices at index >= this reuse a colour (cycle)
export const GPU_STRIPE_COUNT = GPU_STRIPES.length

/** Stripe colour for GPU `index` - a fixed identity hue from the 10-entry palette,
 * selected by `index % 10` so each device keeps its colour as the inventory changes.
 * Returns an `hsl(...)` string. Devices past 10 reuse a colour; the meter appends a
 * cycle marker to those labels (see GpuMeter). */
export function gpuStripeColor(index: number): string {
  const i = ((index % GPU_STRIPE_COUNT) + GPU_STRIPE_COUNT) % GPU_STRIPE_COUNT
  const [h, s, l] = GPU_STRIPES[i]
  return `hsl(${h}, ${s}%, ${l}%)`
}

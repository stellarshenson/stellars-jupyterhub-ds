/* Per-GPU stripe colours computed to CONTRAST with the bar's base accent fill.
 *
 * The striped per-GPU meter draws a diagonal stripe over a `var(--color-accent)`
 * fill; for the stripe to read it must stand out from that base. Rather than
 * hardcode tints (which drift out of contrast when the theme accent changes), we
 * compute each stripe: rotate the hue per device so each GPU reads distinct, then
 * pick the stripe lightness on the side AWAY from the base's luminance and push it
 * until the WCAG contrast ratio of the actually-rendered (alpha-composited) stripe
 * clears a target. So the colours vary per GPU but every one stays inside the
 * contrast budget against the base. Pure + framework-free so it is unit-testable. */

interface RGB { r: number; g: number; b: number }

function hexToRgb(hex: string): RGB {
  const h = hex.replace('#', '')
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h
  const n = parseInt(full, 16)
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 }
}

// WCAG relative luminance (0 = black, 1 = white)
function relLuminance({ r, g, b }: RGB): number {
  const lin = (c: number) => {
    const s = c / 255
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
  }
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
}

// WCAG contrast ratio between two relative luminances (1 = identical, 21 = max)
function contrastRatio(l1: number, l2: number): number {
  const hi = Math.max(l1, l2)
  const lo = Math.min(l1, l2)
  return (hi + 0.05) / (lo + 0.05)
}

function hslToRgb(h: number, s: number, l: number): RGB {
  const c = (1 - Math.abs(2 * l - 1)) * s
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1))
  const m = l - c / 2
  let r = 0, g = 0, b = 0
  if (h < 60) { r = c; g = x } else if (h < 120) { r = x; g = c }
  else if (h < 180) { g = c; b = x } else if (h < 240) { g = x; b = c }
  else if (h < 300) { r = x; b = c } else { r = c; b = x }
  return { r: Math.round((r + m) * 255), g: Math.round((g + m) * 255), b: Math.round((b + m) * 255) }
}

function rgbToHue({ r, g, b }: RGB): number {
  const rn = r / 255, gn = g / 255, bn = b / 255
  const max = Math.max(rn, gn, bn), min = Math.min(rn, gn, bn), d = max - min
  if (d === 0) return 0
  let h: number
  if (max === rn) h = ((gn - bn) / d) % 6
  else if (max === gn) h = (bn - rn) / d + 2
  else h = (rn - gn) / d + 4
  h *= 60
  return h < 0 ? h + 360 : h
}

// alpha-composite a foreground over a background (so contrast is measured against
// what is actually painted, not the solid stripe colour)
function over(fg: RGB, bg: RGB, alpha: number): RGB {
  return {
    r: Math.round(fg.r * alpha + bg.r * (1 - alpha)),
    g: Math.round(fg.g * alpha + bg.g * (1 - alpha)),
    b: Math.round(fg.b * alpha + bg.b * (1 - alpha)),
  }
}

// graphical-object contrast: visible against the accent without being harsh
export const STRIPE_TARGET_CONTRAST = 2.6
const STRIPE_ALPHA = 0.9
const STRIPE_SAT = 0.85

/** Stripe colour for GPU `index` of `count`, contrasting with the `baseHex` accent
 * fill. Hue is rotated evenly across the devices (offset off the base hue so the
 * first stripe is already distinct); lightness starts on the high-contrast side of
 * the base luminance and is pushed outward until the composited stripe clears
 * STRIPE_TARGET_CONTRAST. Returns an `rgba(...)` string. */
export function gpuStripeColor(baseHex: string, index: number, count: number): string {
  const base = hexToRgb(baseHex)
  const baseLum = relLuminance(base)
  const span = count > 0 ? count : 1
  // evenly spaced hues around the wheel, offset off the accent's own hue
  const hue = (rgbToHue(base) + 40 + (index * 360) / span) % 360
  // contrast of this hue at the painted (composited) lightness l, vs the base
  const contrastAt = (l: number) => contrastRatio(relLuminance(over(hslToRgb(hue, STRIPE_SAT, l), base, STRIPE_ALPHA)), baseLum)
  // pick the direction that can reach MORE contrast: a dark stripe beats a light
  // one on a bright/mid base (e.g. bright cyan -> ~9:1 dark vs ~2:1 light), and
  // vice-versa on a dark base. Then step from mid-lightness (most saturated) only
  // until the target is met, so the stripe stays as vivid/distinct as possible.
  const goDarker = contrastAt(0.1) >= contrastAt(0.9)
  let l = 0.5
  for (let i = 0; i < 14; i++) {
    if (contrastAt(l) >= STRIPE_TARGET_CONTRAST) break
    l = goDarker ? Math.max(0.05, l - 0.04) : Math.min(0.97, l + 0.04)
  }
  const { r, g, b } = hslToRgb(hue, STRIPE_SAT, l)
  return `rgba(${r}, ${g}, ${b}, ${STRIPE_ALPHA})`
}

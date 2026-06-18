/* Environment-stage badge: a small outlined rectangle in the header showing the
 * deployment stage, coloured per stage. Driven by JUPYTERHUB_BRANDING_STAGE ->
 * window.jhdata.stage; empty/unset renders nothing. Unknown text falls back to
 * neutral grey. Colours use the design-language named palette (--oh-*); "blue" is
 * the accent/cyan per the design theme. */

const STAGE_TONE: Record<string, string> = {
  DEV: 'var(--oh-green)',
  TST: 'var(--oh-cyan)',
  STG: 'var(--oh-orange)',
  PRD: 'var(--oh-red)',
}

export function StageBadge() {
  const raw = (typeof window !== 'undefined' ? window.jhdata?.stage : '')?.trim()
  if (!raw) return null
  const tone = STAGE_TONE[raw.toUpperCase()] ?? 'var(--oh-gray)'
  return (
    <span className="oh-stage-badge" style={{ color: tone }} title={`Environment: ${raw}`}>
      {raw}
    </span>
  )
}

/* Scope-filter pills - colour by state, double as counts, lit (accent ring) when
 * active. Drives a list's visible scope. The default scope is never "everything". */
export type ScopeTone = 'ok' | 'warn' | 'grey' | 'accent' | 'danger'

// tone -> doh-pill colour class; exported so other pills (e.g. the Events Type
// column) colour-match the legend instead of re-deriving it
export const TONE_CLASS: Record<ScopeTone, string> = {
  ok: 'running',
  warn: 'idle',
  grey: 'stopped',
  accent: 'accent',
  danger: 'error',
}

export interface Scope {
  key: string
  label: string
  count?: number
  tone: ScopeTone
}

export function ScopeFilterPills({ scopes, value, onChange }: { scopes: Scope[]; value: string; onChange: (k: string) => void }) {
  return (
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
      {scopes.map((s) => (
        <span
          key={s.key}
          className={`doh-pill doh-scope ${TONE_CLASS[s.tone]}${value === s.key ? ' active' : ''}`}
          onClick={() => onChange(s.key)}
        >
          <span className="doh-dot" />
          {s.label}
          {s.count != null && ` ${s.count.toLocaleString()}`}
        </span>
      ))}
    </div>
  )
}

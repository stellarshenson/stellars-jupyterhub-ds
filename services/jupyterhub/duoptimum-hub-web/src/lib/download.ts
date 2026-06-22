/* Client-side file downloads - the real "Export" / "Report" actions. A pure
 * browser save (Blob + object URL), no backend: the data is already in hand, so
 * it saves whatever the source holds. Used by the groups export and the fleet
 * activity report. */

function triggerDownload(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

/** Save `data` as a pretty-printed .json file. */
export function downloadJson(filename: string, data: unknown): void {
  triggerDownload(filename, new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
}

const csvCell = (v: string | number | null | undefined): string => {
  const s = v == null ? '' : String(v)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

/** Save a CSV from a header row + body rows (RFC-4180 quoting). */
export function downloadCsv(filename: string, header: string[], rows: Array<Array<string | number | null | undefined>>): void {
  const lines = [header, ...rows].map((r) => r.map(csvCell).join(','))
  triggerDownload(filename, new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' }))
}

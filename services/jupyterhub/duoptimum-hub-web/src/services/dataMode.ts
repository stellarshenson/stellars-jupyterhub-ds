/* Data mode: `live` (readonly GETs to the hub; auth rides the session cookie) is
 * the default for every build and `npm run dev`. `mock` (fixtures, no hub) is
 * opt-in via VITE_DATA_MODE=mock and exists ONLY to back the Playwright suite
 * (`npm run dev:mock` / `--mode mock`); it never runs in production. */
export type DataMode = 'mock' | 'live'

export function dataMode(): DataMode {
  return import.meta.env.VITE_DATA_MODE === 'mock' ? 'mock' : 'live'
}

export function isMock(): boolean {
  return dataMode() === 'mock'
}

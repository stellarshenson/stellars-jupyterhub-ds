/* Data mode: `mock` (fixtures, runs with no hub - the default) or `live`
 * (readonly GETs to the hub through the dev proxy; auth rides the session cookie). */
export type DataMode = 'mock' | 'live'

export function dataMode(): DataMode {
  return import.meta.env.VITE_DATA_MODE === 'live' ? 'live' : 'mock'
}

export function isMock(): boolean {
  return dataMode() === 'mock'
}

/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Data mode: 'mock' (fixtures, default) or 'live' (real hub reads/writes). */
  readonly VITE_DATA_MODE?: 'mock' | 'live'
  /** Hub deploy prefix for API calls: '' for base_url=/, '/jupyterhub' for the path mount. */
  readonly VITE_HUB_BASE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

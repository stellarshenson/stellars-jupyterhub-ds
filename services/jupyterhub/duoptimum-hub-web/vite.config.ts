import { readFileSync } from 'node:fs'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// Stamp the build with the package version so the UI always shows the current
// release (kept in lockstep with the platform via `make increment_version`).
const pkgVersion = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf-8')).version

// Build fingerprint: compressed UTC datetime (yymmdd.hhmm) + a short hash of the
// full timestamp, recomputed on every `vite build` (so every docker image build
// that runs it). Surfaced only as a tooltip on the version line, never permanent.
const _bd = new Date()
const _p = (n: number) => String(n).padStart(2, '0')
const _stamp = `${String(_bd.getUTCFullYear()).slice(2)}${_p(_bd.getUTCMonth() + 1)}${_p(_bd.getUTCDate())}.${_p(_bd.getUTCHours())}${_p(_bd.getUTCMinutes())}`
const _iso = _bd.toISOString()
let _h = 5381
for (let i = 0; i < _iso.length; i++) _h = ((_h * 33) ^ _iso.charCodeAt(i)) >>> 0
const buildId = `${_stamp}-${_h.toString(36).slice(0, 4)}`

// Duoptimum Hub web.
// - base: when the hub serves the SPA at a sub-path, set VITE_BASE (the hub
//   build uses /hub/portal/ via .env.hub). This drives both asset URLs and the
//   react-router basename (src/router.tsx reads import.meta.env.BASE_URL).
// - manifest: the hub-served PortalHandler reads dist/.vite/manifest.json to
//   find the hashed entry JS/CSS for the shell template.
// - proxy: in `live` data mode the app issues same-origin GETs to the hub REST
//   API. Dev proxies /jupyterhub/hub/api to the real hub origin; cookies are
//   forwarded (auth rides the hub session cookie - no API token needed).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const hubOrigin = env.VITE_HUB_ORIGIN || 'https://localhost'
  return {
    base: env.VITE_BASE || '/',
    plugins: [react()],
    define: {
      __APP_VERSION__: JSON.stringify(pkgVersion),
      __BUILD_ID__: JSON.stringify(buildId),
    },
    build: {
      manifest: true,
    },
    server: {
      port: 5180,
      proxy: {
        '/jupyterhub/hub/api': {
          target: hubOrigin,
          changeOrigin: true,
          secure: false,
          cookieDomainRewrite: '',
        },
      },
    },
  }
})

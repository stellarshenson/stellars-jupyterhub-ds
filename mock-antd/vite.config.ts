import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// Optimum Hub mock-antd.
// - base: when served behind the hub at a sub-path, set VITE_BASE (e.g. /jupyterhub/portal/)
// - proxy: in `live` data mode the app issues same-origin GETs to the hub REST API.
//   Dev proxies /jupyterhub (and /hub) to the real hub origin; cookies are forwarded
//   (auth token rides in the hub session cookie - no API token needed).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const hubOrigin = env.VITE_HUB_ORIGIN || 'https://localhost'
  return {
    base: env.VITE_BASE || '/',
    plugins: [react()],
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

import { defineConfig, devices } from '@playwright/test'

// Smoke + screenshot tests render the UI with no hub, so they run against the
// MOCK dev server - start it with `make dev-mock` (npm run dev:mock).
export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  fullyParallel: false,
  reporter: 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5180',
    headless: true,
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})

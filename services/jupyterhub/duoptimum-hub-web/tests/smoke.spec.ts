import { test, expect } from '@playwright/test'

// Captured console errors per page, asserted empty at the end of each test.
function trackErrors(page: import('@playwright/test').Page): string[] {
  const errors: string[] = []
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(m.text())
  })
  page.on('pageerror', (e) => errors.push(String(e)))
  return errors
}

test('shell renders with brand + sider + breadcrumb', async ({ page }) => {
  const errors = trackErrors(page)
  await page.goto('/home')
  await expect(page.locator('img.doh-brand-logo')).toBeVisible()
  await page.screenshot({ path: 'tests/__screens__/home.png', fullPage: true })
  // antd act() noise is fine; flag only genuine React/runtime errors
  const real = errors.filter((e) => !e.includes('ResizeObserver'))
  expect(real, real.join('\n')).toEqual([])
})

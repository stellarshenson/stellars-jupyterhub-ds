import { test } from '@playwright/test'

const PAGES: Array<[string, string]> = [
  ['home', '/home'],
  ['servers', '/servers'],
  ['users', '/users'],
  ['groups', '/groups'],
  ['user-config', '/users/alice'],
  ['group-config', '/groups/gpu'],
  ['new-user', '/users/new'],
  ['lab-container', '/lab-container'],
  ['events', '/events'],
  ['notifications', '/notifications'],
  ['settings', '/settings'],
  ['settings-reference', '/settings/reference'],
  ['tokens', '/tokens'],
  ['design-system', '/design-system'],
]

test('capture pages - dark', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('optimum-hub-theme', 'dark'))
  for (const [name, path] of PAGES) {
    await page.goto(path)
    await page.waitForTimeout(700)
    await page.screenshot({ path: `tests/__screens__/${name}-dark.png`, fullPage: true })
  }
})

test('capture user home + design - light', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('optimum-hub-theme', 'light')
    localStorage.setItem('optimum-hub-role', 'user')
  })
  await page.goto('/home')
  await page.waitForTimeout(700)
  await page.screenshot({ path: 'tests/__screens__/home-user-light.png', fullPage: true })
})

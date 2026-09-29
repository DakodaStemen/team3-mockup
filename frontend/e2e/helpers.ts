import { expect, type Page } from '@playwright/test'

/** The landing page's "Explore with sample data" leads to the dashboard the other specs test. */
export async function openDashboard(page: Page) {
  await page.goto('/')
  await page.getByRole('button', { name: 'Explore with sample data' }).click()
  await expect(page.locator('.stat', { hasText: 'Graduation' })).toBeVisible()
}

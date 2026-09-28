import { expect, test, type Page } from '@playwright/test'

// Mirrors the demo walkthrough: Alex's baseline, then one what-if at a time.
const stat = (page: Page, label: string) => page.locator('.stat', { hasText: label }).locator('span').last()

async function whatIf(page: Page, event: string, term: string, course?: string) {
  await page.getByLabel('Event').selectOption(event)
  await page.getByLabel(event === 'Add Summer' ? 'Summer term' : 'Term').selectOption(term)
  if (course) await page.getByLabel('Course').selectOption(course)
  await page.getByRole('button', { name: 'Run what-if' }).click()
  await expect(page.getByTestId('whatif')).toBeVisible()
}

test.beforeEach(async ({ page }) => {
  await page.goto('/')
  await expect(stat(page, 'Graduation')).toHaveText('Spring 2030')
})

test('fail CSE 2020 delays graduation and shows where courses moved', async ({ page }) => {
  await whatIf(page, 'Fail', 'Spring 2027', 'CSE 2020')
  await expect(stat(page, 'Graduation')).toHaveText('Spring 2030 → Fall 2030')
  await expect(page.getByTestId('terms').getByText('was Spring 2027')).toBeVisible()
  await page.getByRole('button', { name: 'Discard' }).click()
  await expect(stat(page, 'Graduation')).toHaveText('Spring 2030')
})

test('failing MATH 2210 costs a full year', async ({ page }) => {
  await whatIf(page, 'Fail', 'Fall 2026', 'MATH 2210')
  await expect(stat(page, 'Graduation')).toHaveText('Spring 2030 → Spring 2031')
})

test('pass keeps the course in its term and marks nothing affected', async ({ page }) => {
  await whatIf(page, 'Pass', 'Fall 2026', 'CSE 2010')
  await expect(page.getByTestId('whatif')).toContainText('no course moved')
  await expect(page.getByTestId('terms').getByText('(affected)')).toHaveCount(0)
  await expect(page.getByTestId('terms').locator('.term').first()).toContainText('CSE 2010 ✓')
})

test('add summer leaves graduation unchanged', async ({ page }) => {
  await whatIf(page, 'Add Summer', 'Summer 2027')
  await expect(stat(page, 'Graduation')).toHaveText('Spring 2030 → Spring 2030')
})

test('keep a what-if, then undo it', async ({ page }) => {
  await whatIf(page, 'Change Unit Load', 'Fall 2026')  // default 12 units
  await expect(stat(page, 'Graduation')).toHaveText('Spring 2030 → Fall 2031')
  await page.getByRole('button', { name: 'Keep this plan' }).click()
  await expect(stat(page, 'Graduation')).toHaveText('Fall 2031')
  await page.getByRole('button', { name: 'Undo last' }).click()
  await expect(stat(page, 'Graduation')).toHaveText('Spring 2030')
})

test('clicking a course loads it into the what-if form', async ({ page }) => {
  await page.getByTestId('terms').getByRole('button', { name: /^PHYS 2510 / }).click()
  await expect(page.getByLabel('Term')).toHaveValue('Spring 2028')
  await expect(page.getByLabel('Course')).toHaveValue('PHYS 2510')
})

test('base unit cap and student switch replan', async ({ page }) => {
  await page.getByLabel('Unit cap').selectOption('18')
  await expect(stat(page, 'Unit cap')).toHaveText('18')
  await page.getByLabel('Student').selectOption('morgan')
  await expect(stat(page, 'Graduation')).toHaveText('Fall 2027')
})

test('plain-language question gets a guardrail decision', async ({ page }) => {
  await page.getByRole('button', { name: 'Ask' }).click()
  await expect(page.getByTestId('guard')).toBeVisible({ timeout: 20_000 })  // escalated without Ollama
})

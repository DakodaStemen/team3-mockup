import { expect, test, type Page } from '@playwright/test'
import { openDashboard } from './helpers'

// Mirrors the demo walkthrough: Alex's baseline, then one what-if at a time.
const stat = (page: Page, label: string) => page.locator('.stat', { hasText: label }).locator('span').last()

async function whatIf(page: Page, event: string, term: string, course?: string) {
  await page.getByRole('radio', { name: event, exact: true }).click()
  await page.getByLabel(event === 'Add Summer' ? 'Summer term' : event === 'Add Winter' ? 'Winter term' : 'Term').selectOption(term)
  if (course) await page.getByLabel('Course').selectOption(course)
  await page.getByRole('button', { name: 'Run what-if' }).click()
  await expect(page.getByTestId('whatif')).toBeVisible()
}

test.beforeEach(async ({ page }) => {
  await openDashboard(page)
  await expect(stat(page, 'Graduation')).toHaveText('Spring 2030')
})

test('fail CSE 2020 delays graduation and shows where courses moved', async ({ page }) => {
  await whatIf(page, 'Fail', 'Spring 2027', 'CSE 2020')
  await expect(stat(page, 'Graduation')).toHaveText('Spring 2030 → Fall 2030')
  await expect(page.getByTestId('terms').getByText('was Spring 2027')).toBeVisible()
  await page.getByRole('button', { name: 'Discard' }).click()
  await expect(stat(page, 'Graduation')).toHaveText('Spring 2030')
})

test('a summer retake wins back the term a failed course cost', async ({ page }) => {
  await whatIf(page, 'Fail', 'Spring 2027', 'CSE 2020')
  await expect(page.getByTestId('whatif')).toContainText('Catch up with Summer 2027')
  await page.getByRole('button', { name: 'Preview catch-up plan' }).click()
  await expect(stat(page, 'Graduation')).toHaveText('Spring 2030 → Spring 2030')
  await expect(page.getByTestId('terms').getByText('Summer 2027', { exact: false }).first()).toBeVisible()
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

test('add winter inserts a January term between Fall and Spring', async ({ page }) => {
  await whatIf(page, 'Add Winter', 'Winter 2028')
  await expect(stat(page, 'Graduation')).toHaveText('Spring 2030 → Spring 2030')  // once-a-year courses set the pace
  const terms = page.getByTestId('terms').locator('.term h3')
  await expect(terms.nth(2)).toContainText('Fall 2027')
  await expect(terms.nth(3)).toContainText('Winter 2028')
  await expect(terms.nth(4)).toContainText('Spring 2028')
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
  await expect(page.getByLabel('Unit cap')).toHaveValue('18')
  await page.getByLabel('Student').selectOption('morgan')
  await expect(stat(page, 'Graduation')).toHaveText('Fall 2027')
})

test('a student with history sees completed terms, grades, and retakes before the plan', async ({ page }) => {
  await page.getByLabel('Student').selectOption('jordan')
  const past = page.getByTestId('terms').locator('.term.past')
  await expect(past).toHaveCount(2)
  await expect(past.first()).toContainText('Fall 2026')
  await expect(past.first()).toContainText('Completed')
  await expect(past.first()).toContainText('CSE 2010 D')
  await expect(page.getByTestId('terms').locator('.term:not(.past)').first()).toContainText('Fall 2027')
})

test('uploading the sample transcript builds a plan from it', async ({ page }) => {
  await page.getByRole('button', { name: 'or try a sample' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'Read Sample transcript' })).toContainText('5 terms')
  await expect(page.getByText('Not in the B.S. CS catalog, so not counted: BIOL 1000.')).toBeVisible()
  await expect(page.getByTestId('terms').locator('.term.past')).toHaveCount(5)
  await expect(page.getByTestId('terms').locator('.term:not(.past)').first()).toContainText('Spring 2027')
})

test('electives are labeled and risky courses are flagged', async ({ page }) => {
  await expect(page.getByTestId('terms').locator('.kind.k-elective').first()).toBeVisible()
  await expect(page.getByText('Protect these')).toBeVisible()
  await expect(page.getByTestId('terms').locator('.risk').first()).toBeVisible()
})

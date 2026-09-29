import { expect, test, type Page } from '@playwright/test'

// Edge cases found in the frontend sweep: stale form state, request races, error rendering, console noise.
const stat = (page: Page, label: string) => page.locator('.stat', { hasText: label }).locator('span').last()
const alert = (page: Page) => page.getByRole('alert')

test.beforeEach(async ({ page }) => {
  await page.goto('/')
  await expect(stat(page, 'Graduation')).toHaveText('Spring 2030')
})

test('after keeping a what-if, the form never points at a course that moved away', async ({ page }) => {
  await page.getByLabel('Term').selectOption('Spring 2027')
  await page.getByLabel('Course').selectOption('CSE 2020')
  await page.getByRole('button', { name: 'Run what-if' }).click()
  await page.getByRole('button', { name: 'Keep this plan' }).click()
  // CSE 2020 left Spring 2027; the form must show (and send) a course that is really there.
  await expect(page.getByLabel('Course')).not.toHaveValue('CSE 2020')
  await page.getByRole('button', { name: 'Run what-if' }).click()
  await expect(page.getByTestId('whatif')).toBeVisible()
  await expect(alert(page)).toHaveCount(0)
})

test('undo to a shorter plan keeps the selected term valid', async ({ page }) => {
  await page.getByLabel('Event').selectOption('Change Unit Load')
  await page.getByLabel('New unit load').selectOption('12')
  await page.getByRole('button', { name: 'Run what-if' }).click()
  await page.getByRole('button', { name: 'Keep this plan' }).click()
  await page.getByLabel('Term').selectOption('Fall 2031')  // only exists in the 12-unit plan
  await page.getByRole('button', { name: 'Undo last' }).click()
  await page.getByRole('button', { name: 'Run what-if' }).click()
  await expect(page.getByTestId('whatif')).toBeVisible()
  await expect(alert(page)).toHaveCount(0)
})

test('switching student with Add Summer selected offers the new plan\'s summers', async ({ page }) => {
  await page.getByLabel('Event').selectOption('Add Summer')
  await page.getByLabel('Student').selectOption('morgan')
  await expect(stat(page, 'Graduation')).toHaveText('Fall 2027')
  await expect(page.getByLabel('Summer term')).toHaveValue(/^Summer \d{4}$/)
  await page.getByRole('button', { name: 'Run what-if' }).click()
  await expect(page.getByTestId('whatif')).toBeVisible()
  await expect(alert(page)).toHaveCount(0)
})

test('a slow plan response for the previous student never overwrites the current one', async ({ page }) => {
  await page.route('**/api/plan', async route => {
    const body = route.request().postDataJSON()
    if (body.student_id === 'jordan') await new Promise(r => setTimeout(r, 1500))
    await route.continue()
  })
  await page.getByLabel('Student').selectOption('jordan')
  await page.getByLabel('Student').selectOption('morgan')
  await expect(stat(page, 'Graduation')).toHaveText('Fall 2027')
  await page.waitForTimeout(2000)  // jordan's late response arrives now
  await expect(stat(page, 'Graduation')).toHaveText('Fall 2027')
})

test('a what-if answered after switching student is dropped', async ({ page }) => {
  await page.route('**/api/scenario', async route => { await new Promise(r => setTimeout(r, 1500)); await route.continue() })
  await page.getByRole('button', { name: 'Run what-if' }).click()
  await page.getByLabel('Student').selectOption('morgan')
  await expect(stat(page, 'Graduation')).toHaveText('Fall 2027')
  await page.waitForTimeout(2000)
  await expect(page.getByTestId('whatif')).toHaveCount(0)
})

test('validation errors render as readable text', async ({ page }) => {
  await page.route('**/api/scenario', route => route.fulfill({
    status: 422, contentType: 'application/json',
    body: JSON.stringify({ detail: [{ loc: ['body', 'event', 'unit_load'], msg: 'Input should be less than or equal to 21', type: 'less_than_equal' }] }),
  }))
  await page.getByRole('button', { name: 'Run what-if' }).click()
  await expect(alert(page)).toContainText('event.unit_load: Input should be less than or equal to 21')
  await expect(alert(page)).not.toContainText('{')
  await page.route('**/api/scenario', route => route.fulfill({
    status: 422, contentType: 'application/json',
    body: JSON.stringify({ detail: [{ loc: ['body', 'plan', 'terms', 0, 'courses'], msg: 'List should have at most 12 items' }, { loc: ['body'], msg: 'second' }] }),
  }))
  await page.getByRole('button', { name: 'Run what-if' }).click()
  await expect(alert(page)).toHaveText(/0\.courses: List should have at most 12 items \(\+1 more\)/)
  await page.route('**/api/scenario', route => route.fulfill({ status: 413, contentType: 'application/json', body: '{"detail": null}' }))
  await page.getByRole('button', { name: 'Run what-if' }).click()
  await expect(alert(page)).toContainText('too large')
})

test('backend down gives a clear message', async ({ page }) => {
  await page.route('**/api/scenario', route => route.fulfill({ status: 502, contentType: 'text/plain', body: 'Bad Gateway' }))
  await page.getByRole('button', { name: 'Run what-if' }).click()
  await expect(alert(page)).toContainText('planner API')
  await page.route('**/api/scenario', route => route.abort())
  await page.getByRole('button', { name: 'Run what-if' }).click()
  await expect(alert(page)).toContainText('planner API')
})

for (const scheme of ['light', 'dark'] as const) {
  test(`a full walkthrough logs no console errors in ${scheme} mode`, async ({ page }) => {
    const errors: string[] = []
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()) })
    page.on('pageerror', e => errors.push(String(e)))
    await page.emulateMedia({ colorScheme: scheme })
    if (scheme === 'dark') await page.addInitScript(() => localStorage.setItem('adpp-theme', 'dark'))  // the app is light unless toggled
    await page.goto('/')
    await expect(stat(page, 'Graduation')).toHaveText('Spring 2030')
    for (const ev of ['Fail', 'Pass', 'Add Summer', 'Change Unit Load']) {
      await page.getByLabel('Event').selectOption(ev)
      await page.getByRole('button', { name: 'Run what-if' }).click()
      await expect(page.getByTestId('whatif')).toBeVisible()
      await page.getByRole('button', { name: 'Keep this plan' }).click()
    }
    await page.getByRole('button', { name: 'Reset to baseline' }).click()
    await expect(stat(page, 'Graduation')).toHaveText('Spring 2030')
    await page.getByLabel('Student').selectOption('sam')
    await expect(page.getByTestId('terms')).toBeVisible()
    expect(errors).toEqual([])
  })
}

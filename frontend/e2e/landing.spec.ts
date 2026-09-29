import { expect, test } from '@playwright/test'
import { readFileSync } from 'node:fs'

// The first thing anyone sees: upload a transcript, or explore with sample data.
test('the landing page offers an upload and sample data', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('landing')).toBeVisible()
  await expect(page.getByText('Upload your transcript')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Explore with sample data' })).toBeVisible()
  await expect(page.locator('.stats')).toHaveCount(0)
})

test('sample data opens the dashboard, and the logo returns to the landing page', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Explore with sample data' }).click()
  await expect(page.locator('.stat', { hasText: 'Graduation' }).locator('span').last()).toHaveText('Spring 2030')
  await page.getByRole('button', { name: /Degree Pathway Planner/ }).click()
  await expect(page.getByTestId('landing')).toBeVisible()
})

test('the sample transcript goes straight to a plan built from it', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Try the sample transcript instead' }).click()
  await expect(page.getByTestId('terms').locator('.term.past')).toHaveCount(5)
})

test('a PDF transcript is read and planned', async ({ page, context }) => {
  // Print the synthetic transcript to a real PDF with the browser, then upload that.
  const sample = readFileSync('../backend/data/sample_transcript.txt', 'utf8')
  const printer = await context.newPage()
  await printer.setContent(`<pre style="font:12px monospace">${sample.replace(/&/g, '&amp;').replace(/</g, '&lt;')}</pre>`)
  const pdf = await printer.pdf({ format: 'Letter' })
  await printer.close()
  await page.goto('/')
  await page.locator('input[type=file]').setInputFiles({ name: 'transcript.pdf', mimeType: 'application/pdf', buffer: pdf })
  await expect(page.getByRole('status').filter({ hasText: 'Read transcript.pdf' })).toContainText('5 terms')
  await expect(page.getByTestId('terms').locator('.term.past')).toHaveCount(5)
})

test('an unreadable file shows a plain error on the landing page', async ({ page }) => {
  await page.goto('/')
  await page.locator('input[type=file]').setInputFiles({ name: 'notes.txt', mimeType: 'text/plain', buffer: Buffer.from('hello there') })
  await expect(page.getByRole('alert')).toContainText('no CSUSB terms or courses found')
  await expect(page.getByTestId('landing')).toBeVisible()
})

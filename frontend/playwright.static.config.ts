import { defineConfig } from '@playwright/test'

// The GitHub Pages build (no backend; the API runs in the browser under Pyodide) must pass the same walkthrough.
// The engine downloads Pyodide from the jsDelivr CDN, so this needs network access.
export default defineConfig({
  testDir: 'e2e',
  testMatch: ['demo.spec.ts', 'landing.spec.ts'],
  expect: { timeout: 60_000 },  // each test starts a fresh engine: Pyodide and its packages download on a cold cache
  timeout: 120_000,
  use: { baseURL: 'http://localhost:4173' },
  webServer: {
    command: 'VITE_STATIC=1 npm run build && npx vite preview --port 4173 --strictPort',
    url: 'http://localhost:4173',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})

import { defineConfig } from '@playwright/test'

// End-to-end tests drive the real app: FastAPI backend plus the Vite dev server.
export default defineConfig({
  testDir: 'e2e',
  timeout: process.env.CI ? 60_000 : 30_000,  // CI renders the WebGL graph in software, so pages are slower
  use: { baseURL: 'http://localhost:5173' },
  webServer: [
    { command: 'uv run uvicorn planner.api:app --port 8000', cwd: '../backend', url: 'http://localhost:8000/health', reuseExistingServer: !process.env.CI },
    { command: 'npm run dev -- --port 5173 --strictPort', url: 'http://localhost:5173', reuseExistingServer: !process.env.CI },
  ],
})

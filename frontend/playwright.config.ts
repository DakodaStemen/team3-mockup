import { defineConfig } from '@playwright/test'

// End-to-end tests drive the real app: FastAPI backend plus the Vite dev server.
export default defineConfig({
  testDir: 'e2e',
  timeout: 30_000,
  use: { baseURL: 'http://localhost:5173' },
  webServer: [
    { command: 'uv run uvicorn planner.api:app --port 8000', cwd: '../backend', url: 'http://localhost:8000/health', reuseExistingServer: true },
    { command: 'npm run dev -- --port 5173 --strictPort', url: 'http://localhost:5173', reuseExistingServer: true },
  ],
})

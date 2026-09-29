import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// VITE_STATIC=1 builds the GitHub Pages demo, where the API runs in the browser (src/backend.ts).
// VITE_BASE is the Pages path, e.g. /team3-mockup/.
export default defineConfig({
  base: process.env.VITE_BASE ?? '/',
  plugins: [react()],
  worker: { format: 'es' },
  optimizeDeps: { exclude: ['pyodide'] },
  server: { proxy: { '/api': { target: 'http://localhost:8000', rewrite: (p) => p.replace(/^\/api/, '') } } },
})

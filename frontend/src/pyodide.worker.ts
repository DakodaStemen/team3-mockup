// Runs the planner (FastAPI + networkx + the engine) under Pyodide, entirely in the browser.
// public/planner.zip is built by backend/scripts/pages_bundle.py; FastAPI and pydantic come from Pyodide's own packages.
import { loadPyodide, version } from 'pyodide'

const BASE = import.meta.env.BASE_URL

async function boot() {
  const py = await loadPyodide({ indexURL: `https://cdn.jsdelivr.net/pyodide/v${version}/full/` })
  const [, zip] = await Promise.all([py.loadPackage(['fastapi', 'pydantic']), fetch(`${BASE}planner.zip`).then(r => {
    if (!r.ok) throw new Error('planner.zip is missing from this build')
    return r.arrayBuffer()
  })])
  py.unpackArchive(zip, 'zip', { extractDir: '/app' })
  py.runPython("import sys; sys.path.insert(0, '/app')")
  py.runPython('from planner.browser import handle')
  return py
}

const ready = boot()
ready.then(() => postMessage({ ready: true }), () => {})

type Request = { id: number; method: string; path: string; query: string; body: ArrayBuffer; type: string }

// Requests run one at a time, like a single-worker server.
let queue: Promise<unknown> = ready.catch(() => {})

self.onmessage = ({ data }: MessageEvent<Request>) => {
  queue = queue.then(async () => {
    try {
      const py = await ready
      py.globals.set('req', { method: data.method, path: data.path, query: data.query, body: new Uint8Array(data.body), type: data.type })
      const out = await py.runPythonAsync(
        'r = req.to_py()\nawait handle(r["method"], r["path"], r["query"], bytes(r["body"]), r["type"])')
      postMessage({ id: data.id, ...JSON.parse(out) })
    } catch (e) {
      postMessage({ id: data.id, error: e instanceof Error ? e.message : String(e) })
    }
  })
}

// The planner API. Locally, `/api` is FastAPI (proxied by Vite). In the static GitHub Pages build
// (VITE_STATIC=1) there is no server: the same FastAPI app runs in a Web Worker under Pyodide.
export const STATIC = import.meta.env.VITE_STATIC === '1'

type Reply = { status: number; type: string; body: string }

let worker: Worker | undefined
let nextId = 0
const pending = new Map<number, { resolve: (r: Reply) => void; reject: (e: Error) => void }>()
const readyListeners = new Set<() => void>()
let isReady = false

function start(): Worker {
  if (worker) return worker
  worker = new Worker(new URL('./pyodide.worker.ts', import.meta.url), { type: 'module' })
  worker.onmessage = ({ data }) => {
    if (data.ready) { isReady = true; readyListeners.forEach(f => f()); return }
    const p = pending.get(data.id)
    if (!p) return
    pending.delete(data.id)
    if (data.error) p.reject(new Error(data.error)); else p.resolve(data)
  }
  worker.onerror = () => {
    pending.forEach(p => p.reject(new Error("The in-browser planner engine failed to start.")))
    pending.clear()
  }
  return worker
}

/** Starts loading the engine and calls back when it is ready (immediately if it already is). */
export function whenEngineReady(cb: () => void) {
  if (!STATIC) return
  start()
  if (isReady) cb(); else readyListeners.add(cb)
}

/** `fetch` for `/api/...` paths, answered by the worker in the static build. */
export async function apiFetch(url: string, init?: RequestInit): Promise<Response> {
  if (!STATIC) return fetch(url, init)
  const [path, query = ''] = url.replace(/^\/api/, '').split('?')
  const body = init?.body
  let bytes = new ArrayBuffer(0), type = new Headers(init?.headers).get('content-type') ?? ''
  if (typeof body === 'string') bytes = new TextEncoder().encode(body).buffer as ArrayBuffer
  else if (body instanceof Blob) { bytes = await body.arrayBuffer(); type ||= body.type }
  const w = start()
  const reply = await new Promise<Reply>((resolve, reject) => {
    const id = nextId++
    pending.set(id, { resolve, reject })
    w.postMessage({ id, method: init?.method ?? 'GET', path, query, body: bytes, type }, [bytes])
  })
  return new Response(reply.body, { status: reply.status, headers: { 'content-type': reply.type } })
}

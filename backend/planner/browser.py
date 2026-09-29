"""Run the FastAPI app inside the browser (Pyodide) for the static GitHub Pages demo.

The frontend's `/api` calls are posted to a Web Worker, which calls `handle()`. It drives the same ASGI app the
server runs, so validation, limits, and error bodies are identical to `uvicorn planner.api:app`.
"""
import json

import fastapi.dependencies.utils
import fastapi.routing
import starlette.concurrency

from .api import app


async def _inline(func, *args, **kwargs):
    """The browser has no threads, so plain `def` endpoints run inline instead of in anyio's worker pool."""
    return func(*args, **kwargs)


for module in (starlette.concurrency, fastapi.routing, fastapi.dependencies.utils):
    module.run_in_threadpool = _inline


async def handle(method: str, path: str, query: str = "", body: bytes = b"", content_type: str = "") -> str:
    """Return a JSON string: {"status": int, "type": content-type, "body": str}."""
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method, "scheme": "http",
        "path": path, "raw_path": path.encode(), "query_string": query.encode(), "root_path": "",
        "headers": [
            (b"content-length", str(len(body)).encode()), (b"host", b"localhost"),
            (b"content-type", (content_type or "application/octet-stream").encode()),
        ],
        "server": ("localhost", 80), "client": ("127.0.0.1", 0),
    }
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    out = {"status": 500, "type": "text/plain", "chunks": []}

    async def send(message):
        if message["type"] == "http.response.start":
            out["status"] = message["status"]
            headers = {k.decode().lower(): v.decode() for k, v in message["headers"]}
            out["type"] = headers.get("content-type", "application/json")
        elif message["type"] == "http.response.body":
            out["chunks"].append(message.get("body", b""))

    await app(scope, receive, send)
    return json.dumps({"status": out["status"], "type": out["type"], "body": b"".join(out["chunks"]).decode("utf8")})

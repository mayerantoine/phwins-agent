"""FastAPI API for the PH WINS Q&A agent.

The UI lives in `frontend/` (Vite + React + TypeScript). In development, run
the Vite dev server (`cd frontend && npm run dev`) — it proxies `/ask` here.
In production, run `npm run build` first; this server then serves
`frontend/dist` as static files at `/`.

Run against the local tool-use loop (default):
    python web.py                     # or:  uvicorn web:app --reload

Run against the Managed Agents runtime:
    python web.py --managed           # or:  PHWINS_BACKEND=managed uvicorn web:app --reload
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from phwins import ask, ask_managed


BACKEND = os.environ.get("PHWINS_BACKEND", "local").lower()
_ask = ask_managed if BACKEND == "managed" else ask

app = FastAPI(title=f"PH WINS 2024 Q&A ({BACKEND})")


class AskRequest(BaseModel):
    question: str


@app.post("/ask")
def ask_endpoint(req: AskRequest) -> dict:
    return _ask(req.question)


@app.get("/backend")
def backend() -> dict:
    return {"backend": BACKEND}


DIST = Path(__file__).parent / "frontend" / "dist"

if DIST.exists():
    # Production: serve the built React app at the root.
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="frontend")
else:
    # Dev fallback: guide the user to run Vite or build.
    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return (
            "<!doctype html><html><body style='font-family:system-ui;padding:2rem;"
            "max-width:640px;margin:auto;line-height:1.5;color:#1f1d1a;background:#faf8f5'>"
            "<h1>PH WINS Q&amp;A API</h1>"
            "<p>The frontend has not been built yet. You have two options:</p>"
            "<ol>"
            "<li><strong>Dev</strong>: <code>cd frontend &amp;&amp; npm install &amp;&amp; "
            "npm run dev</code>, then open <a href='http://127.0.0.1:5173'>"
            "http://127.0.0.1:5173</a>.</li>"
            "<li><strong>Prod</strong>: <code>cd frontend &amp;&amp; npm run build</code>, "
            "then refresh this page.</li>"
            "</ol>"
            "<p>The <code>POST /ask</code> endpoint is live regardless.</p>"
            "</body></html>"
        )


if __name__ == "__main__":
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="Run the PH WINS web API.")
    parser.add_argument("--managed", action="store_true", help="Use the Managed Agents runtime.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload.")
    args = parser.parse_args()

    if args.managed:
        os.environ["PHWINS_BACKEND"] = "managed"

    uvicorn.run(
        "web:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        env_file=None,
    )

"""Single-file FastAPI web UI.

Run against the local tool-use loop (default):
    python web.py                     # or:  uvicorn web:app --reload

Run against the Managed Agents runtime:
    python web.py --managed           # or:  PHWINS_BACKEND=managed uvicorn web:app --reload

Exposes POST `/ask` which calls the same `phwins.ask()` / `ask_managed()`
the CLI uses. No build step, no framework — vanilla fetch and a bit of CSS.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
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


INDEX_HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>PH WINS 2024 Q&A</title>
  <style>
    body { font-family: -apple-system, system-ui, sans-serif; max-width: 780px;
           margin: 2rem auto; padding: 0 1rem; color: #222; line-height: 1.5; }
    h1 { font-size: 1.4rem; margin-bottom: .25rem; }
    p.tagline { color: #666; margin-top: 0; }
    form { display: flex; gap: .5rem; margin: 1.5rem 0; }
    input[type=text] { flex: 1; padding: .6rem .8rem; font-size: 1rem;
                       border: 1px solid #ccc; border-radius: 4px; }
    button { padding: .6rem 1.2rem; font-size: 1rem; border: 0;
             background: #2b6cb0; color: white; border-radius: 4px; cursor: pointer; }
    button:disabled { background: #999; cursor: wait; }
    .card { border: 1px solid #ddd; border-radius: 6px; padding: 1rem 1.2rem;
            margin-top: 1rem; background: #fafafa; }
    .card h3 { margin: 0 0 .5rem; font-size: .85rem; text-transform: uppercase;
               color: #666; letter-spacing: .05em; }
    .direct { font-size: 1.1rem; }
    .full, .reasoning, .synthesis { white-space: pre-wrap; }
    details { margin-top: 1rem; }
    summary { cursor: pointer; color: #2b6cb0; }
    .sources { color: #666; font-size: .85rem; margin-top: 1rem; }
    .error { color: #c00; }
  </style>
</head>
<body>
  <h1>PH WINS 2024 workforce Q&A</h1>
  <p class="tagline">Ask a plain-English question about the U.S. public health workforce.</p>

  <form id="askForm">
    <input type="text" id="question" placeholder="e.g. What percent of workers are experiencing burnout?" required>
    <button id="askBtn" type="submit">Ask</button>
  </form>

  <div id="output"></div>

  <script>
    const form = document.getElementById('askForm');
    const btn = document.getElementById('askBtn');
    const out = document.getElementById('output');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const question = document.getElementById('question').value.trim();
      if (!question) return;
      btn.disabled = true; btn.textContent = 'Thinking…';
      out.innerHTML = '';
      try {
        const r = await fetch('/ask', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({question}),
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json();
        render(data);
      } catch (err) {
        out.innerHTML = `<div class="card error">Error: ${err.message}</div>`;
      } finally {
        btn.disabled = false; btn.textContent = 'Ask';
      }
    });

    function render(d) {
      const parts = [];
      if (d.direct_answer) {
        parts.push(`<div class="card"><h3>Answer</h3><div class="direct">${escape(d.direct_answer)}</div></div>`);
      }
      if (d.synthesis) {
        parts.push(`<div class="card"><h3>Synthesis</h3><div class="synthesis">${escape(d.synthesis)}</div></div>`);
      }
      if (d.full_answer) {
        parts.push(`<details><summary>Full answer (with 95% CIs)</summary><div class="card full">${escape(d.full_answer)}</div></details>`);
      }
      if (d.reasoning) {
        parts.push(`<details><summary>Reasoning</summary><div class="card reasoning">${escape(d.reasoning)}</div></details>`);
      }
      const s = d.sources || {};
      const topics = (s.topics || []).join(', ');
      parts.push(`<div class="sources">Source: PH WINS ${s.survey_year || ''} (${s.source_file || ''})${topics ? ' — topics: ' + topics : ''}</div>`);
      out.innerHTML = parts.join('');
    }

    function escape(s) {
      return String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
    }
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


if __name__ == "__main__":
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="Run the PH WINS web UI.")
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

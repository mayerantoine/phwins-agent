# phwins-agent

A tutorial-friendly agent that answers plain-English questions about the U.S. public health workforce using the **PH WINS 2024** survey (de Beaumont Foundation / ASTHO).

## Setup

```bash
uv sync
cp .env.example .env   # add ANTHROPIC_API_KEY
```

## Run

**CLI (local tool-use loop):**
```bash
python cli.py "What percent of workers are experiencing burnout?"
python cli.py                                # REPL
```

**CLI (Managed Agents runtime):**
```bash
python -m phwins.setup_managed               # one-time provision
python cli.py --managed "..."
```

**Web UI (dev — Vite dev server, hot reload):**

Terminal 1 — API:
```bash
uv run python web.py --reload                # local backend (default)
uv run python web.py --managed --reload      # Managed Agents backend
```

Terminal 2 — frontend:
```bash
cd frontend
npm install                                  # first time only
npm run dev
# open http://localhost:5173
```

Vite proxies `/ask` to `http://127.0.0.1:8000`, so both dev servers work together.

**Web UI (prod — single server, static build):**
```bash
cd frontend && npm run build && cd ..
uv run python web.py
# open http://localhost:8000  (serves frontend/dist)
```

The chosen backend appears in the FastAPI title and at `GET /backend`. You can also set it via env var for use with plain uvicorn:
```bash
PHWINS_BACKEND=managed uv run uvicorn web:app --reload
```

## Code tour (read in this order)

The `phwins/` package is organized as a four-chapter walkthrough:

| # | File | What it teaches |
|---|---|---|
| 1 | [`phwins/data.py`](phwins/data.py) | The data + the grounded lookup tool. `data_lookup()` is a plain function; the model calls it via a tool schema. |
| 2 | [`phwins/prompts.py`](phwins/prompts.py) | Everything we tell Claude: system prompt, structured-output schema, tool definitions. |
| 3 | [`phwins/agent.py`](phwins/agent.py) | The local tool-use loop. Two phases: unconstrained tool-use, then one constrained call for the final JSON. |
| 3b | [`phwins/managed.py`](phwins/managed.py) | Same behavior on the Managed Agents runtime. Diff against `agent.py` to see what changes (only the transport). |
| 4a | [`cli.py`](cli.py) | Thin CLI wrapper. `--managed` picks the backend. |
| 4b | [`web.py`](web.py) | FastAPI JSON API. Reuses `phwins.ask()` directly and serves `frontend/dist` in prod. |
| 4c | [`frontend/`](frontend) | React + Vite + TypeScript UI. See `frontend/src/App.tsx` for the component tree. |

## Data

| File | Description |
|---|---|
| `data/phwins_2024.json` | Normalized estimates: `topics → subtopics → estimates` |
| `data/DownloadAll__2024_202607032025.xlsx` | Raw source export |
| `data/questions.md` | Evaluation question set |

Each estimate carries `value_pct`, `lci`/`uci` (95% CI), `subpopulation`, and a `suppressed` flag. Scope: national, 2024, state/local/tribal governmental public health workforce.

8 topics: Demographics, Workforce Characteristics, Engagement & Satisfaction, Staying & Leaving, Workplace Well-being, Training, Flexibility & Benefits, Community Engagement.

## Stack

- Python 3.12, uv
- `anthropic>=0.116.0`, `python-dotenv`, `fastapi`, `uvicorn`
- Frontend: React 18, TypeScript, Vite, CSS Modules (no CSS framework)
- Model: `claude-opus-4-7` with adaptive thinking and prompt caching on the taxonomy

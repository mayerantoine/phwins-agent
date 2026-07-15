# phwins-agent

An agent that answers natural-language questions about the U.S. public health workforce using the **PH WINS 2024** survey (Public Health Workforce Interests and Needs Survey, de Beaumont / ASTHO).

## Goal

Given a workforce question in plain English (e.g., "What percent of workers are experiencing burnout?"), the agent looks up the relevant estimate(s) in the PH WINS 2024 dataset and returns a grounded answer with the value, confidence interval, and source context.

## Data

Everything lives in `data/`:

- **`phwins_2024.json`** — normalized dataset. Structure:
  ```
  topics[] → subtopics[] → estimates[]
  ```
  Each estimate has `subpopulation`, `filters`, `value_pct`, `lci`/`uci` (95% CI), and a `suppressed` flag.

  8 topics cover: Demographics, Workforce Characteristics, Engagement & Satisfaction, Staying & Leaving, Workplace Well-being (incl. burnout), Training, Flexibility & Benefits, Community Engagement.

- **`DownloadAll__2024_202607032025.xlsx`** — the raw source export the JSON was built from.

- **`questions.md`** — the evaluation set. Two query types:
  1. **Single-lookup** — resolves to one `topic → subtopic → filter` pull.
  2. **Multi-pull synthesis** — combines 2+ subtopics and narrates the connection.

Survey scope is **national, 2024**. Filters (agency type, tenure, age, etc.) live on individual estimates.

## Architecture

Package `phwins/` is a four-chapter walkthrough:
- `phwins/data.py` — `data_lookup()` + `build_taxonomy()`. The grounded tool.
- `phwins/prompts.py` — `SYSTEM_PROMPT`, `ANSWER_SCHEMA`, tool schemas.
- `phwins/agent.py` — `ask()`: two-phase local tool-use loop (unconstrained → structured JSON via `ANSWER_SCHEMA`).
- `phwins/managed.py` — `ask_managed()`: same behavior on the Managed Agents runtime.
- `phwins/setup_managed.py` — one-time agent + environment provisioning.
- `phwins/formatting.py` — shared answer formatter (used by CLI and web).

Entry points:
- `cli.py` — one-shot / REPL CLI. `--managed` switches to the cloud backend.
- `web.py` — single-file FastAPI app + vanilla-JS UI. Run with `uvicorn web:app --reload`.

Model: `claude-opus-4-7` with adaptive thinking and prompt caching on the taxonomy. Tools: `data_lookup` (local JSON) and `synthesize` (second model call for narrative paragraphs on 3+ finding questions).

## Stack

Python 3.12, uv. Dependencies: `anthropic>=0.116.0`, `python-dotenv`, `fastapi`, `uvicorn`. Requires `ANTHROPIC_API_KEY` in `.env`.

# phwins-agent

Answers natural-language questions about the U.S. public health workforce using the **PH WINS 2024** survey (de Beaumont Foundation / ASTHO).

## What it does

Ask a question in plain English. The agent looks up estimates in the PH WINS 2024 dataset and returns a grounded answer with values, 95% confidence intervals, and source context. For multi-topic questions, it synthesizes a narrative paragraph in the de Beaumont / ASTHO reporting voice.

## Setup

```bash
uv sync
cp .env.example .env   # add your ANTHROPIC_API_KEY
```

## Usage

**One-shot:**
```bash
python cli.py "What percent of workers are experiencing burnout?"
```

**REPL:**
```bash
python cli.py
> What share of the workforce plans to leave within a year?
> exit
```

## Data

| File | Description |
|---|---|
| `data/phwins_2024.json` | Normalized estimates: `topics → subtopics → estimates` |
| `data/DownloadAll__2024_202607032025.xlsx` | Raw source export |
| `data/questions.md` | Evaluation question set |

Each estimate includes `value_pct`, `lci`/`uci` (95% CI), `subpopulation`, and a `suppressed` flag. Survey scope: national, 2024, state/local/tribal governmental public health workforce.

8 topics: Demographics, Workforce Characteristics, Engagement & Satisfaction, Staying & Leaving, Workplace Well-being, Training, Flexibility & Benefits, Community Engagement.

## Architecture

- `main.py` — `ask()` function: two-phase Claude loop (tool-use + structured JSON output)
- `cli.py` — CLI wrapper with one-shot and REPL modes
- Model: `claude-opus-4-7` with adaptive thinking and prompt caching on the taxonomy
- Tools exposed to the model: `data_lookup` (local JSON lookup) and `synthesize` (narrative paragraph via a second model call)

## Stack

- Python 3.12, uv
- `anthropic>=0.116.0`, `python-dotenv`

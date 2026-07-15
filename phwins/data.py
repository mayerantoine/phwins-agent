"""PH WINS 2024 data access — the grounded tool the agent calls.

Chapter 1 of the tutorial: how the local JSON is shaped, how we look up
estimates by (topic, subtopic, subpopulation), and how we derive the
taxonomy the model sees in its system prompt.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


DEFAULT_DATA_PATH = Path(__file__).parent.parent / "data" / "phwins_2024.json"


@lru_cache(maxsize=8)
def _load(data_path: str) -> dict:
    with open(data_path, "r") as f:
        return json.load(f)


def _subtopic_name(s: dict) -> str:
    """Duplicate subtopic names exist as detailed + combined views; suffix the combined one."""
    estimates = s["estimates"]
    if estimates and all(e.get("combined_view") for e in estimates):
        return f"{s['measure_name']} (combined)"
    return s["measure_name"]


def _pick(query: str, items: list, key) -> list:
    """Case-insensitive exact match first; fall back to substring match."""
    q = query.lower()
    exact = [i for i in items if key(i).lower() == q]
    return exact or [i for i in items if q in key(i).lower()]


def data_lookup(
    topic: str,
    subtopic: str,
    subpopulation: str | None = None,
    *,
    data_path: str | Path = DEFAULT_DATA_PATH,
) -> list[dict]:
    """Look up PH WINS 2024 estimates by (topic, subtopic, subpopulation).

    Each level matches case-insensitively: exact first, substring fallback.
    Returns [] when nothing matches.
    """
    dataset = _load(str(Path(data_path)))

    results: list[dict] = []
    for t in _pick(topic, dataset["topics"], lambda t: t["topic_name"]):
        for s in _pick(subtopic, t["subtopics"], _subtopic_name):
            estimates = s["estimates"]
            if subpopulation:
                estimates = _pick(subpopulation, estimates, lambda e: e["subpopulation"])
            for e in estimates:
                results.append(
                    {
                        "year": dataset["survey_year"],
                        "topic": t["topic_name"],
                        "subtopic": _subtopic_name(s),
                        "subpopulation": e["subpopulation"],
                        "value_pct": e["value_pct"],
                        "lci": e.get("lci"),
                        "uci": e.get("uci"),
                        "suppressed": e.get("suppressed"),
                        "combined_view": e.get("combined_view"),
                        "n": e.get("n"),
                    }
                )
    return results


def build_taxonomy(data_path: str | Path = DEFAULT_DATA_PATH) -> dict:
    d = _load(str(Path(data_path)))
    return {
        "survey_year": d["survey_year"],
        "geography": d["geography"],
        "estimate_fields": [
            "subpopulation", "filters", "value_pct", "lci", "uci",
            "suppressed", "combined_view", "n",
        ],
        "topics": [
            {
                "topic_name": t["topic_name"],
                "subtopics": [
                    {
                        "measure_name": _subtopic_name(s),
                        "subpopulations": [e["subpopulation"] for e in s["estimates"]],
                    }
                    for s in t["subtopics"]
                ],
            }
            for t in d["topics"]
        ],
    }


def format_taxonomy_prompt(taxonomy: dict) -> str:
    """Render the taxonomy as the indented tree the model sees in its system prompt."""
    lines = [
        f"Survey year: {taxonomy['survey_year']}    Geography: {taxonomy['geography']}",
        f"Estimate fields on each returned row: {', '.join(taxonomy['estimate_fields'])}",
        "",
        "Topics -> Subtopics -> Subpopulations:",
    ]
    for t in taxonomy["topics"]:
        lines.append(f"- {t['topic_name']}")
        for s in t["subtopics"]:
            lines.append(f"    * {s['measure_name']}")
            for sp in s["subpopulations"]:
                lines.append(f"        - {sp}")
    return "\n".join(lines)

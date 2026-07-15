"""Hydrate a bar-chart payload from an LLM chart_hint + the ground-truth tool_trace.

Chapter 4 of the tutorial. The LLM picks *which* subtopic to visualize (via
`chart_hint` in the final structured answer); the bar values themselves come
from the rows `data_lookup` actually returned this turn. That split keeps the
numbers grounded even though the model chose the framing.
"""

from __future__ import annotations

from pathlib import Path

from .data import DEFAULT_DATA_PATH, data_lookup

MAX_BARS = 5


def _matches(row: dict, topic: str, subtopic: str) -> bool:
    return (
        row["topic"].lower() == topic.lower()
        and row["subtopic"].lower() == subtopic.lower()
    )


def build_chart(
    hint: dict | None,
    tool_trace: list[dict],
    *,
    survey_year: str,
    source_file: str,
    data_path=DEFAULT_DATA_PATH,
) -> dict | None:
    """Turn a chart_hint + trace into the frontend chart payload, or None.

    Returns None when: hint is null/empty, the named subtopic wasn't actually
    looked up this turn, or every row for it is suppressed.
    """
    if not hint:
        return None

    topic = hint.get("topic")
    subtopic = hint.get("subtopic")
    if not topic or not subtopic:
        return None

    # The subtopic must have been looked up this turn (grounding gate).
    if not any(_matches(r, topic, subtopic) for r in tool_trace):
        return None

    # Pull the full subtopic distribution so the chart shows context, even if
    # the model only looked up one subpopulation. Values still come from data,
    # never from the LLM.
    rows = [r for r in data_lookup(topic, subtopic, data_path=data_path) if not r.get("suppressed")]
    seen: set[str] = set()
    unique: list[dict] = []
    for r in rows:
        key = r["subpopulation"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    if not unique:
        return None

    sort = hint.get("sort", "value_desc")
    if sort == "value_desc":
        unique.sort(key=lambda r: r["value_pct"], reverse=True)

    highlight = hint.get("highlight_subpopulation")

    if len(unique) > MAX_BARS:
        kept = unique[:MAX_BARS]
        rest = unique[MAX_BARS:]
        # If the highlighted bar is outside the top-N, swap it in for the smallest kept bar.
        if highlight and not any(r["subpopulation"] == highlight for r in kept):
            hi_row = next((r for r in rest if r["subpopulation"] == highlight), None)
            if hi_row is not None:
                smallest_idx = min(range(len(kept)), key=lambda i: kept[i]["value_pct"])
                displaced = kept[smallest_idx]
                kept[smallest_idx] = hi_row
                rest = [r for r in rest if r["subpopulation"] != highlight] + [displaced]
        other_sum = sum(r["value_pct"] for r in rest)
        bars = [
            {
                "label": r["subpopulation"],
                "value_pct": r["value_pct"],
                "lci": r.get("lci"),
                "uci": r.get("uci"),
                "is_highlight": highlight is not None and r["subpopulation"] == highlight,
                "is_group": False,
            }
            for r in kept
        ]
        bars.append(
            {
                "label": f"Other ({len(rest)} more)",
                "value_pct": round(other_sum, 1),
                "lci": None,
                "uci": None,
                "is_highlight": False,
                "is_group": True,
            }
        )
    else:
        bars = [
            {
                "label": r["subpopulation"],
                "value_pct": r["value_pct"],
                "lci": r.get("lci"),
                "uci": r.get("uci"),
                "is_highlight": highlight is not None and r["subpopulation"] == highlight,
                "is_group": False,
            }
            for r in unique
        ]

    return {
        "title": subtopic,
        "subtitle": topic,
        "caption": hint.get("caption", ""),
        "highlight": highlight,
        "bars": bars,
        "source": {
            "topic": topic,
            "subtopic": subtopic,
            "survey_year": survey_year,
            "source_file": Path(source_file).name,
        },
    }

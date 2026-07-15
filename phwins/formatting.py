"""Shared formatting for CLI and web UI — turns an answer dict into
a human-readable string with a source footer."""


def format_answer(result: dict) -> str:
    synthesis = (result.get("synthesis") or "").strip()
    answer = synthesis if synthesis else (result.get("direct_answer") or "").strip()

    sources = result.get("sources") or {}
    year = sources.get("survey_year", "")
    source_file = sources.get("source_file", "")
    topics = sources.get("topics") or []
    topics_str = ", ".join(topics) if topics else ""

    source_line = f"Source: PH WINS {year} ({source_file})"
    if topics_str:
        source_line += f" — topics: {topics_str}"

    return f"{answer}\n\n{source_line}"

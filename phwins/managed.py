"""ask_managed(): same behavior as agent.ask(), but running on the
Anthropic Managed Agents runtime (agent + environment live in the cloud;
we only handle custom-tool callbacks).

Chapter 3b of the tutorial. Diff against `agent.py` to see the delta.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from .agent import build_sources, parse_answer_json, synthesize
from .chart import build_chart
from .data import DEFAULT_DATA_PATH, build_taxonomy, data_lookup


MODEL = "claude-opus-4-7"
MAX_EVENTS = 500


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} not set (check .env)")
    return value


def _handle_tool_call(
    client: "anthropic.Anthropic",
    name: str,
    tool_input: dict,
    data_path: str | Path,
) -> tuple[str, bool, list[dict]]:
    """Execute a custom tool call. Returns (result_text, is_error, rows_for_trace)."""
    try:
        if name == "data_lookup":
            rows = data_lookup(
                topic=tool_input["topic"],
                subtopic=tool_input["subtopic"],
                subpopulation=tool_input.get("subpopulation"),
                data_path=data_path,
            )
            return json.dumps(rows), False, rows
        if name == "synthesize":
            paragraph = synthesize(
                client,
                question=tool_input["question"],
                angle=tool_input["angle"],
                findings=tool_input["findings"],
                model=MODEL,
            )
            return paragraph, False, []
        return json.dumps({"error": f"unknown tool: {name}"}), True, []
    except Exception as e:
        return json.dumps({"error": str(e)}), True, []


def open_session(
    client: "anthropic.Anthropic | None" = None,
) -> tuple["anthropic.Anthropic", str]:
    """Open a Managed Agents session. Returns (client, session_id)."""
    load_dotenv()
    _require_env("ANTHROPIC_API_KEY")
    agent_id = _require_env("PHWINS_AGENT_ID")
    env_id = _require_env("PHWINS_ENV_ID")

    if client is None:
        client = anthropic.Anthropic()
    session = client.beta.sessions.create(agent=agent_id, environment_id=env_id)
    return client, session.id


def close_session(client: "anthropic.Anthropic", session_id: str) -> None:
    """Archive the session. Best-effort — swallow errors."""
    try:
        client.beta.sessions.archive(session_id)
    except Exception:
        pass


def ask_managed(
    question: str,
    *,
    session_id: str | None = None,
    client: "anthropic.Anthropic | None" = None,
    data_path: str | Path = DEFAULT_DATA_PATH,
) -> dict:
    """Answer a PH WINS question via the Managed Agent runtime.

    If session_id is provided, reuse it (caller owns lifecycle). Otherwise open
    a fresh session and archive it on exit.

    Returns the same dict shape as agent.ask(): direct_answer, full_answer,
    synthesis, reasoning, sources.
    """
    owns_session = session_id is None
    if owns_session:
        client, session_id = open_session(client)
    elif client is None:
        load_dotenv()
        _require_env("ANTHROPIC_API_KEY")
        client = anthropic.Anthropic()

    tool_trace: list[dict] = []
    final_text_parts: list[str] = []

    try:
        with client.beta.sessions.events.stream(session_id=session_id) as stream:
            client.beta.sessions.events.send(
                session_id=session_id,
                events=[
                    {"type": "user.message", "content": [{"type": "text", "text": question}]}
                ],
            )

            events_seen = 0
            for event in stream:
                events_seen += 1
                if events_seen > MAX_EVENTS:
                    raise RuntimeError(f"session exceeded {MAX_EVENTS} events without completing")

                etype = event.type

                if etype == "agent.custom_tool_use":
                    result_text, is_error, rows = _handle_tool_call(
                        client, event.name, event.input or {}, data_path
                    )
                    tool_trace.extend(rows)
                    client.beta.sessions.events.send(
                        session_id=session_id,
                        events=[
                            {
                                "type": "user.custom_tool_result",
                                "custom_tool_use_id": event.id,
                                "content": [{"type": "text", "text": result_text}],
                                "is_error": is_error,
                            }
                        ],
                    )
                    continue

                if etype == "agent.message":
                    for block in event.content or []:
                        if getattr(block, "type", None) == "text":
                            final_text_parts.append(block.text)
                    continue

                if etype == "session.status_terminated":
                    break

                if etype == "session.status_idle":
                    stop_reason = getattr(event, "stop_reason", None)
                    if stop_reason and getattr(stop_reason, "type", None) == "requires_action":
                        continue
                    break
    finally:
        if owns_session:
            close_session(client, session_id)

    text = "".join(final_text_parts).strip()
    parsed = parse_answer_json(text)

    taxonomy = build_taxonomy(data_path=data_path)
    parsed["sources"] = build_sources(tool_trace, taxonomy, data_path)
    parsed["chart"] = build_chart(
        parsed.pop("chart_hint", None),
        tool_trace,
        survey_year=taxonomy["survey_year"],
        source_file=str(data_path),
        data_path=data_path,
    )
    return parsed

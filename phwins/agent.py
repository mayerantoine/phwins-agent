"""The local agent loop: ask() runs a tool-use conversation with Claude,
then makes one final constrained call to emit the structured answer.

Chapter 3 of the tutorial. Read this next to `managed.py` to see what
Managed Agents changes (only the transport, not the tools or prompts).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from .chart import build_chart
from .data import DEFAULT_DATA_PATH, build_taxonomy, data_lookup, format_taxonomy_prompt
from .prompts import (
    ANSWER_SCHEMA,
    DATA_LOOKUP_TOOL,
    SYNTHESIS_SYSTEM_PROMPT,
    SYNTHESIZE_TOOL,
    SYSTEM_PROMPT,
)


_SAFE_STUB = {
    "direct_answer": "I couldn't format an answer for that. Try asking about a PH WINS 2024 workforce topic — burnout, intent to leave, training needs, satisfaction, or demographics.",
    "full_answer": "",
    "synthesis": "",
    "reasoning": "",
    "chart_hint": None,
    "is_in_scope": False,
}


def _extract_json_block(text: str) -> str:
    """Peel a ```json … ``` fence if the model wrapped its answer in one."""
    stripped = text.strip()
    fence = "```json"
    if fence in stripped:
        after = stripped.split(fence, 1)[1]
        end = after.find("```")
        if end != -1:
            return after[:end].strip()
        return after.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        return stripped[3:-3].strip()
    return stripped


def parse_answer_json(text: str) -> dict:
    """Parse the model's final text into the answer dict, or return a safe stub.

    Handles the common failure mode of prose + fenced JSON. Never dumps raw text
    into direct_answer / full_answer — that used to leak the whole JSON payload
    into the UI when parsing failed.
    """
    for candidate in (text, _extract_json_block(text)):
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(parsed, dict):
            continue
        for key in ANSWER_SCHEMA["required"]:
            if key == "chart_hint":
                parsed.setdefault(key, None)
            elif key == "is_in_scope":
                parsed.setdefault(key, True)
            else:
                parsed.setdefault(key, "")
        return parsed
    return dict(_SAFE_STUB)


def synthesize(
    client: "anthropic.Anthropic",
    question: str,
    angle: str,
    findings: list[dict],
    model: str = "claude-opus-4-7",
) -> str:
    """Second model call — turn a list of findings into a de Beaumont-voice paragraph."""
    resp = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYNTHESIS_SYSTEM_PROMPT,
        output_config={"effort": "medium"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Angle: {angle}\n\n"
                    f"Findings (JSON):\n{json.dumps(findings, indent=2)}\n\n"
                    "Write the paragraph now."
                ),
            }
        ],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def build_sources(trace: list[dict], taxonomy: dict, data_path: str | Path) -> dict:
    topics: list[str] = []
    for r in trace:
        if r["topic"] not in topics:
            topics.append(r["topic"])
    return {
        "survey_year": taxonomy["survey_year"],
        "source_file": Path(data_path).name,
        "topics": topics,
    }


def ask(
    question: str,
    *,
    model: str = "claude-opus-4-7",
    max_turns: int = 6,
    data_path: str | Path = DEFAULT_DATA_PATH,
) -> dict:
    """Answer a PH WINS question. Returns dict with direct_answer, full_answer, reasoning, sources."""
    load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set (check .env)")

    client = anthropic.Anthropic()
    taxonomy = build_taxonomy(data_path=data_path)
    system_text = SYSTEM_PROMPT.format(
        year=taxonomy["survey_year"], taxonomy=format_taxonomy_prompt(taxonomy)
    )
    system_blocks = [
        {"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}
    ]

    messages: list[dict] = [{"role": "user", "content": question}]
    tool_trace: list[dict] = []  # ground-truth sources

    # Phase 1: tool-use loop. Unconstrained output so the model can call data_lookup freely.
    for _ in range(max_turns):
        resp = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_blocks,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            tools=[DATA_LOOKUP_TOOL, SYNTHESIZE_TOOL],
            messages=messages,
        )

        if resp.stop_reason != "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            break

        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            args = block.input or {}
            try:
                if block.name == "data_lookup":
                    rows = data_lookup(
                        topic=args["topic"],
                        subtopic=args["subtopic"],
                        subpopulation=args.get("subpopulation"),
                        data_path=data_path,
                    )
                    tool_trace.extend(rows)
                    content = json.dumps(rows)
                elif block.name == "synthesize":
                    paragraph = synthesize(
                        client,
                        question=args["question"],
                        angle=args["angle"],
                        findings=args["findings"],
                        model=model,
                    )
                    content = paragraph
                else:
                    content = json.dumps({"error": f"unknown tool: {block.name}"})
                is_error = False
            except Exception as e:
                content = json.dumps({"error": str(e)})
                is_error = True
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                    "is_error": is_error,
                }
            )
        messages.append({"role": "user", "content": tool_results})
    else:
        return {
            "direct_answer": "[max_turns reached without final answer]",
            "full_answer": "",
            "synthesis": "",
            "reasoning": "",
            "sources": build_sources(tool_trace, taxonomy, data_path),
            "chart": None,
            "is_in_scope": True,
        }

    # Phase 2: one more turn constrained to the answer schema.
    messages.append(
        {
            "role": "user",
            "content": "Now emit the final structured answer as JSON per the schema.",
        }
    )
    final = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system_blocks,
        output_config={
            "format": {"type": "json_schema", "schema": ANSWER_SCHEMA},
            "effort": "high",
        },
        messages=messages,
    )
    text = "".join(b.text for b in final.content if b.type == "text").strip()
    parsed = parse_answer_json(text)

    parsed["sources"] = build_sources(tool_trace, taxonomy, data_path)
    parsed["chart"] = build_chart(
        parsed.pop("chart_hint", None),
        tool_trace,
        survey_year=taxonomy["survey_year"],
        source_file=str(data_path),
        data_path=data_path,
    )
    return parsed

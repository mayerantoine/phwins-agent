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

from .data import DEFAULT_DATA_PATH, build_taxonomy, data_lookup, format_taxonomy_prompt
from .prompts import (
    ANSWER_SCHEMA,
    DATA_LOOKUP_TOOL,
    SYNTHESIS_SYSTEM_PROMPT,
    SYNTHESIZE_TOOL,
    SYSTEM_PROMPT,
)


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
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = {"direct_answer": text, "full_answer": text, "synthesis": "", "reasoning": ""}

    parsed["sources"] = build_sources(tool_trace, taxonomy, data_path)
    return parsed

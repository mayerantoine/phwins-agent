from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import anthropic
from dotenv import load_dotenv


DEFAULT_DATA_PATH = Path(__file__).parent / "data" / "phwins_2024.json"


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


def _taxonomy_prompt(taxonomy: dict) -> str:
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


SYSTEM_PROMPT = """You are a PH WINS 2024 workforce data analyst. You answer questions about the U.S. public health workforce using ONLY the PH WINS 2024 survey (de Beaumont / ASTHO), retrieved via the `data_lookup` tool.

Scope: national estimates, 2024, state/local/tribal governmental public health workforce.

Rules:
- Never invent numbers. Every quantitative claim must come from a `data_lookup` result you actually called and received in this turn.
- Use the taxonomy below to pick exact `topic`, `subtopic`, and `subpopulation` strings. Matching is case-insensitive (exact first, substring fallback), but stay close to the labels shown. Subtopics ending in `(combined)` are collapsed views of the same-named detailed subtopic — use one view or the other, never mix rows from both. If no matching subpopulation exists, say so plainly.
- For single-lookup questions, one `data_lookup` call is enough. For synthesis questions, make multiple calls, then narrate the connection.
- Report values with their 95% CI, e.g. `21.1% (95% CI 21.0-21.3)`.
- If an estimate has `suppressed: true`, report it as suppressed and do not use `value_pct`.
- If the question asks for something outside the taxonomy (a different year, a state-level breakdown, a variable not surveyed), say clearly that PH WINS 2024 does not cover it.
- Keep answers concise: the number(s), a one-line interpretation, and the source coordinates (topic / subtopic / subpopulation).
- For multi-pull synthesis questions where 3+ distinct data points need to be woven into a story (workforce risk profile, retention vs. burnout tension, generational comparison), after your `data_lookup` calls also call the `synthesize` tool to get a cohesive narrative paragraph in the de Beaumont / ASTHO reporting voice. Skip `synthesize` for single-lookup, ranking, or out-of-scope questions — the default format is better for those.
- If you called `synthesize`, place the returned paragraph verbatim in the `synthesis` field. `full_answer` still remains the values + 95% CIs + one-line interpretation regardless of whether `synthesize` fired. If you did not call `synthesize`, set `synthesis` to `""`.

Final output format:
Your last message must be JSON with four fields — a structured-output schema will enforce this. Write:
- `direct_answer`: ONE plain-text sentence answering the question. No markdown, no bullets, no source citation. Include the headline percent(s) inline in parentheses next to each named item so the number backing the claim is visible — e.g. "The top three training needs are Budget and Financial Management (50.5%), Policy Engagement (40.2%), and Systems and Strategic Thinking (34.2%)." Skip CIs here; the `full_answer` carries those.
- `full_answer`: The rich answer with values, 95% CIs, and a one-line interpretation. Markdown is fine. This is NOT the synthesis paragraph — even when you called `synthesize`, `full_answer` still carries the values and CIs.
- `synthesis`: The de Beaumont / ASTHO narrative paragraph returned by the `synthesize` tool, verbatim. Empty string `""` when `synthesize` was not called.
- `reasoning`: Show your work. Name each `data_lookup` call you made (topic / subtopic / subpopulation) and what it returned. If you did arithmetic (summing subpopulations, computing a share), spell it out with the numbers so the user can verify. If you declined because the question is out of scope, say so here.

Taxonomy for {year}:
{taxonomy}
"""


ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "direct_answer": {
            "type": "string",
            "description": "One plain-text sentence. No markdown, no CIs, no bullets.",
        },
        "full_answer": {
            "type": "string",
            "description": "Rich answer with values and 95% CIs plus a one-line interpretation. Markdown OK. Not the synthesis paragraph.",
        },
        "synthesis": {
            "type": "string",
            "description": "The de Beaumont / ASTHO narrative paragraph returned by the `synthesize` tool, verbatim. Empty string \"\" if `synthesize` was not called this turn (single-lookup, ranking, or out-of-scope questions).",
        },
        "reasoning": {
            "type": "string",
            "description": "Step-by-step audit: which data_lookup calls were made, what came back, any arithmetic.",
        },
    },
    "required": ["direct_answer", "full_answer", "synthesis", "reasoning"],
    "additionalProperties": False,
}


SYNTHESIS_SYSTEM_PROMPT = """You are a public health workforce communicator writing in the voice of the PH WINS 2024 report (de Beaumont Foundation / ASTHO).

Given a question, an interpretive angle, and a short list of quantitative findings, produce ONE cohesive paragraph (3-6 sentences) that:
- Opens with an assertion-style topic sentence tied to the angle. Reference voice: "Public health workers are younger, committed, and burned out." / "Workforce strain is taking a toll." / "Employees are committed to staying in government public health, yet burnout persists at high levels."
- Weaves each finding into the narrative with a qualitative interpretive frame ("more than 70%", "roughly 1 in 5", "more than a quarter", "about half") followed by the precise percent in parentheses on first mention — e.g. "more than 70% (71.0%)".
- Uses connective devices (yet, however, at the same time, meanwhile, even as) to link findings into a story rather than a list.
- Graduates severity where appropriate: broad to acute (e.g. "71% report some burnout ... 1 in 5 (19.6%) report symptoms that won't go away").
- Ends with an implication sentence tying the findings together (risk, tension, opportunity). Do NOT prescribe policy.

Rules:
- Use ONLY the numbers passed in `findings`. Do not invent, round in ways that mislead, or extrapolate beyond what's given.
- No bullets, no headings, no CIs, no source citation. Return only the paragraph text — nothing else.
"""


SYNTHESIZE_TOOL = {
    "name": "synthesize",
    "description": (
        "Compose a cohesive-paragraph narrative for a multi-pull synthesis question. "
        "Call ONLY after you have pulled 3+ distinct data points via data_lookup and the "
        "question calls for weaving them into a story (risk profile, workforce overview, "
        "comparison across topics). Do NOT call for single-lookup or ranking questions — "
        "the default full_answer format is better for those. Returns a paragraph in the "
        "de Beaumont / ASTHO reporting voice; use it verbatim as the body of full_answer "
        "(you may add a source line after it)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The user's original question, quoted."},
            "angle": {
                "type": "string",
                "description": "The interpretive frame — e.g. 'workforce risk profile', 'retention vs burnout tension'. Becomes the paragraph's topic sentence.",
            },
            "findings": {
                "type": "array",
                "description": "The specific values to weave in. Each must correspond to a data_lookup row actually retrieved.",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string", "description": "Plain-English label, e.g. 'any burnout symptoms', 'intent to leave in one year'."},
                        "value_pct": {"type": "number"},
                        "lci": {"type": ["number", "null"]},
                        "uci": {"type": ["number", "null"]},
                        "topic": {"type": "string"},
                        "subtopic": {"type": "string"},
                    },
                    "required": ["label", "value_pct", "topic", "subtopic"],
                },
            },
        },
        "required": ["question", "angle", "findings"],
    },
}


def _synthesize(
    client: "anthropic.Anthropic",
    question: str,
    angle: str,
    findings: list[dict],
    model: str = "claude-opus-4-7",
) -> str:
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


DATA_LOOKUP_TOOL = {
    "name": "data_lookup",
    "description": (
        "Retrieve PH WINS 2024 estimates. Use taxonomy strings verbatim: matching is "
        "case-insensitive, exact first with substring fallback. Subtopics ending in "
        "'(combined)' are collapsed views of the same-named detailed subtopic — pick one, "
        "never mix both. Returns a list of estimate rows with value_pct, lci, uci, "
        "suppressed, and source coordinates. Empty list means no match — try a different "
        "subpopulation string or omit it to get every row under the subtopic."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Topic name from the taxonomy."},
            "subtopic": {"type": "string", "description": "Subtopic (measure_name) from the taxonomy."},
            "subpopulation": {
                "type": ["string", "null"],
                "description": "Optional subpopulation label. Omit or null to return every row under the subtopic.",
            },
        },
        "required": ["topic", "subtopic"],
    },
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
        year=taxonomy["survey_year"], taxonomy=_taxonomy_prompt(taxonomy)
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
                    paragraph = _synthesize(
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
            "sources": _build_sources(tool_trace, taxonomy, data_path),
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

    parsed["sources"] = _build_sources(tool_trace, taxonomy, data_path)
    return parsed


def _build_sources(trace: list[dict], taxonomy: dict, data_path: str | Path) -> dict:
    topics: list[str] = []
    for r in trace:
        if r["topic"] not in topics:
            topics.append(r["topic"])
    return {
        "survey_year": taxonomy["survey_year"],
        "source_file": Path(data_path).name,
        "topics": topics,
    }



"""One-time provisioning for the Managed Agents runtime: creates (or updates)
the agent + environment. Run this before using `ask_managed`.

    python -m phwins.setup_managed

Prints the IDs; add them to `.env` as PHWINS_AGENT_ID and PHWINS_ENV_ID.
"""

from __future__ import annotations

import os

import anthropic
from dotenv import load_dotenv

from .data import DEFAULT_DATA_PATH, build_taxonomy, format_taxonomy_prompt
from .prompts import DATA_LOOKUP_TOOL, SYNTHESIZE_TOOL, SYSTEM_PROMPT


AGENT_NAME = "PH WINS 2024 Workforce Analyst"
MODEL = "claude-opus-4-7"
ENV_NAME = "phwins-agent-env"
ENV_CONFIG = {"type": "cloud", "networking": {"type": "unrestricted"}}


def _as_custom_tool(tool: dict) -> dict:
    return {
        "type": "custom",
        "name": tool["name"],
        "description": tool["description"],
        "input_schema": tool["input_schema"],
    }


def provision_agent() -> str:
    """Create or update the Managed Agent and return its ID."""
    load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set (check .env)")

    client = anthropic.Anthropic()
    taxonomy = build_taxonomy(DEFAULT_DATA_PATH)
    system_text = SYSTEM_PROMPT.format(
        year=taxonomy["survey_year"], taxonomy=format_taxonomy_prompt(taxonomy)
    )
    tools = [_as_custom_tool(DATA_LOOKUP_TOOL), _as_custom_tool(SYNTHESIZE_TOOL)]

    existing_id = os.environ.get("PHWINS_AGENT_ID")
    if existing_id:
        current = client.beta.agents.retrieve(existing_id)
        agent = client.beta.agents.update(
            existing_id,
            version=current.version,
            name=AGENT_NAME,
            model=MODEL,
            system=system_text,
            tools=tools,
        )
        print(f"updated agent_id={agent.id}")
        print(f"version={agent.version}")
    else:
        agent = client.beta.agents.create(
            name=AGENT_NAME,
            model=MODEL,
            system=system_text,
            tools=tools,
        )
        print(f"created agent_id={agent.id}")
        print(f"version={agent.version}")
        print(f"Add to .env:  PHWINS_AGENT_ID={agent.id}")
    return agent.id


def provision_environment() -> str:
    """Create or update the Managed Agents environment and return its ID."""
    load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set (check .env)")

    client = anthropic.Anthropic()

    existing_id = os.environ.get("PHWINS_ENV_ID")
    if existing_id:
        env = client.beta.environments.update(
            existing_id, name=ENV_NAME, config=ENV_CONFIG
        )
        print(f"updated env_id={env.id}")
    else:
        env = client.beta.environments.create(name=ENV_NAME, config=ENV_CONFIG)
        print(f"created env_id={env.id}")
        print(f"Add to .env:  PHWINS_ENV_ID={env.id}")
    return env.id


if __name__ == "__main__":
    provision_agent()
    provision_environment()

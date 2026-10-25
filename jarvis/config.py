"""Central configuration. Secrets come only from the environment / .env (never from code)."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

ROOT = Path(__file__).resolve().parent.parent
if load_dotenv:
    load_dotenv(ROOT / ".env", override=False)

DATA_DIR = ROOT / "data" / "worlds"
RUNTIME_DIR = ROOT / "runtime"
UI_DIR = ROOT / "ui"

CLOSE_PERIOD = "2026-09"          # the month Jarvis closes
LOCKED_THROUGH = "2026-08"        # periods <= this are locked
ENTITY = "Afterglow Labs, Inc."


def env(name: str, default: str | None = None) -> str | None:
    val = os.environ.get(name)
    return val if val not in (None, "") else default


def world_seed() -> int:
    return int(env("WORLD_SEED", "2026"))


# --- Elastic -------------------------------------------------------------
ELASTIC_URL = env("ELASTIC_URL")
ELASTIC_API_KEY = env("ELASTIC_API_KEY")          # master key: bootstrap scripts ONLY
ELASTIC_PREFIX = env("ELASTIC_INDEX_PREFIX", "jarvis")

# per-role keys (minted by `python -m jarvis.search.mint_keys`)
ROLE_KEYS = {
    "ai_agent": env("JARVIS_PREPARER_KEY"),
    "ai_reviewer": env("JARVIS_REVIEWER_KEY"),
    "gateway": env("GATEWAY_KEY"),
    "human_controller": env("CONTROLLER_KEY"),
}

# --- LLM -----------------------------------------------------------------
# NB: we deliberately do NOT inherit ANTHROPIC_BASE_URL from the shell, so a
# dev harness's proxy setting can't silently redirect the agent.
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
ANTHROPIC_URL = env("JARVIS_ANTHROPIC_URL", "https://api.anthropic.com")
MODEL_REASONING = env("JARVIS_MODEL_REASONING", "claude-3-5-sonnet-20241022")
MODEL_FAST = env("JARVIS_MODEL_FAST", "claude-3-5-haiku-20241022")

SEC_USER_AGENT = env("SEC_USER_AGENT", "JarvisERP research contact@example.com")

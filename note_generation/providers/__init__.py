"""Provider adapters. Every adapter exposes the same function:

    generate(system: str, user: str, model_cfg: dict, gen_cfg: dict) -> GenerationResult

and raises TransientError (retry) or PermanentError (log and move on). Adapters never
fall back to another model, never retry on their own (SDK retries are switched off so
the runner logs every attempt), and never change the prompt.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field

API_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GEMINI_API_KEY",
    "mock": None,
}

PLACEHOLDER_PREFIXES = ("your-", "todo", "xxx", "<")


class TransientError(Exception):
    """429, 5xx, timeout, dropped connection: safe to retry the same request."""


class PermanentError(Exception):
    """Bad request, auth, unknown model: retrying will not help."""


@dataclass
class GenerationResult:
    text: str
    finish_reason: str            # normalised: stop | length | refusal | other
    raw_finish_reason: str
    model_returned: str | None    # the model name the API says answered
    input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    cached_input_tokens: int | None = None
    request_id: str | None = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def api_key(provider: str) -> str:
    env = API_KEY_ENV[provider]
    key = (os.environ.get(env) or "").strip()
    if not key or key.lower().startswith(PLACEHOLDER_PREFIXES):
        raise PermanentError(f"{env} is missing or still a placeholder; set it in .env (see .env.example)")
    return key


def get_generate(provider: str):
    if provider == "anthropic":
        from .claude import generate
    elif provider == "google":
        from .gemini import generate
    elif provider == "mock":
        from .mock import generate
    else:
        raise ValueError(f"unknown provider {provider!r}")
    return generate

"""Anthropic (Claude) adapter.

Notes for this experiment:
- Never send temperature/top_p/top_k: current Claude models reject them (400).
- Thinking can't be turned off on some models (e.g. Opus 5.5); control it with `effort`.
  Sonnet 5.5 can turn it off with thinking={"type": "between_tools"} (only at effort high or below).
- No refusal fallback: a declined request stays a refusal (stop_reason "refusal") so
  another model never writes a note that we attribute to this one.
"""
from __future__ import annotations

from . import GenerationResult, PermanentError, TransientError, api_key

_client = None

_FINISH = {"end_turn": "stop", "stop_sequence": "stop", "max_tokens": "length", "refusal": "refusal"}


def _get_client(timeout_s: float):
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=api_key("anthropic"), timeout=timeout_s, max_retries=0)
    return _client


def generate(system: str, user: str, model_cfg: dict, gen_cfg: dict) -> GenerationResult:
    import anthropic

    client = _get_client(gen_cfg["request_timeout_s"])
    kwargs = dict(
        model=model_cfg["model_id"],
        max_tokens=gen_cfg["max_output_tokens"],
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    if model_cfg.get("effort"):
        kwargs["output_config"] = {"effort": model_cfg["effort"]}
    if model_cfg.get("thinking"):
        kwargs["thinking"] = model_cfg["thinking"]

    try:
        resp = client.messages.create(**kwargs)
    except (anthropic.RateLimitError, anthropic.APITimeoutError, anthropic.APIConnectionError) as e:
        raise TransientError(f"{type(e).__name__}: {e}") from e
    except anthropic.APIStatusError as e:
        if e.status_code >= 500 or e.status_code == 529:
            raise TransientError(f"HTTP {e.status_code}: {e.message}") from e
        raise PermanentError(f"HTTP {e.status_code}: {e.message}") from e

    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    extra = {}
    if resp.stop_reason == "refusal" and getattr(resp, "stop_details", None):
        extra["refusal_category"] = resp.stop_details.category
    return GenerationResult(
        text=text,
        finish_reason=_FINISH.get(resp.stop_reason, "other"),
        raw_finish_reason=str(resp.stop_reason),
        model_returned=resp.model,
        input_tokens=resp.usage.input_tokens,
        output_tokens=resp.usage.output_tokens,          # includes thinking tokens
        cached_input_tokens=getattr(resp.usage, "cache_read_input_tokens", None),
        request_id=getattr(resp, "_request_id", None),
        extra=extra,
    )

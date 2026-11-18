"""Google Gemini adapter (google-genai SDK)."""
from __future__ import annotations

from . import GenerationResult, PermanentError, TransientError, api_key

_client = None

_REFUSAL = {"SAFETY", "RECITATION", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "IMAGE_SAFETY"}


def _get_client(timeout_s: float):
    global _client
    if _client is None:
        from google import genai
        from google.genai import types
        _client = genai.Client(api_key=api_key("google"),
                               http_options=types.HttpOptions(timeout=int(timeout_s * 1000)))
    return _client


def _finish(name: str) -> str:
    if name == "STOP":
        return "stop"
    if name == "MAX_TOKENS":
        return "length"
    if name in _REFUSAL:
        return "refusal"
    return "other"


def generate(system: str, user: str, model_cfg: dict, gen_cfg: dict) -> GenerationResult:
    from google.genai import errors, types

    client = _get_client(gen_cfg["request_timeout_s"])
    conf = dict(system_instruction=system, max_output_tokens=gen_cfg["max_output_tokens"])
    if model_cfg.get("thinking_level"):
        conf["thinking_config"] = types.ThinkingConfig(thinking_level=model_cfg["thinking_level"])
    if model_cfg.get("temperature") is not None:
        conf["temperature"] = model_cfg["temperature"]

    try:
        resp = client.models.generate_content(model=model_cfg["model_id"], contents=user,
                                              config=types.GenerateContentConfig(**conf))
    except errors.APIError as e:
        code = getattr(e, "code", None) or 0
        if code == 429 or code >= 500:
            raise TransientError(f"HTTP {code}: {e}") from e
        raise PermanentError(f"HTTP {code}: {e}") from e
    except Exception as e:  # SDK timeouts / connection errors come from the HTTP layer
        if "Timeout" in type(e).__name__ or "Connect" in type(e).__name__:
            raise TransientError(f"{type(e).__name__}: {e}") from e
        raise

    usage = resp.usage_metadata
    extra = {}
    if not resp.candidates:   # whole prompt blocked
        block = getattr(getattr(resp, "prompt_feedback", None), "block_reason", None)
        extra["prompt_block_reason"] = str(block)
        return GenerationResult(text="", finish_reason="refusal", raw_finish_reason=f"PROMPT_BLOCKED:{block}",
                                model_returned=getattr(resp, "model_version", None), extra=extra)
    fr = resp.candidates[0].finish_reason
    fr_name = getattr(fr, "name", str(fr))
    return GenerationResult(
        text=(resp.text or "").strip(),
        finish_reason=_finish(fr_name),
        raw_finish_reason=fr_name,
        model_returned=getattr(resp, "model_version", None),
        input_tokens=getattr(usage, "prompt_token_count", None),
        output_tokens=getattr(usage, "candidates_token_count", None),
        reasoning_tokens=getattr(usage, "thoughts_token_count", None),
        cached_input_tokens=getattr(usage, "cached_content_token_count", None),
        request_id=getattr(resp, "response_id", None),
        extra=extra,
    )

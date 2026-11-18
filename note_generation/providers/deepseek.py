"""DeepSeek adapter. DeepSeek's API is OpenAI-compatible, so it uses the `openai` SDK with
DeepSeek's base_url (as in DeepSeek's own docs). Check the current model names there before
filling config.yaml; reasoning models may ignore temperature."""
from __future__ import annotations

from . import GenerationResult, PermanentError, TransientError, api_key

_client = None

_FINISH = {"stop": "stop", "length": "length", "content_filter": "refusal"}


def _get_client(base_url: str, timeout_s: float):
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=api_key("deepseek"), base_url=base_url, timeout=timeout_s, max_retries=0)
    return _client


def generate(system: str, user: str, model_cfg: dict, gen_cfg: dict) -> GenerationResult:
    import openai

    client = _get_client(model_cfg["base_url"], gen_cfg["request_timeout_s"])
    kwargs = dict(
        model=model_cfg["model_id"],
        max_tokens=gen_cfg["max_output_tokens"],
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    if model_cfg.get("temperature") is not None:
        kwargs["temperature"] = model_cfg["temperature"]

    try:
        resp = client.chat.completions.create(**kwargs)
    except (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError) as e:
        raise TransientError(f"{type(e).__name__}: {e}") from e
    except openai.APIStatusError as e:
        if e.status_code >= 500:
            raise TransientError(f"HTTP {e.status_code}: {e.message}") from e
        raise PermanentError(f"HTTP {e.status_code}: {e.message}") from e

    choice = resp.choices[0]
    usage = resp.usage
    details = getattr(usage, "completion_tokens_details", None)
    return GenerationResult(
        text=(choice.message.content or "").strip(),
        finish_reason=_FINISH.get(choice.finish_reason, "other"),
        raw_finish_reason=str(choice.finish_reason),
        model_returned=resp.model,
        input_tokens=getattr(usage, "prompt_tokens", None),
        output_tokens=getattr(usage, "completion_tokens", None),
        reasoning_tokens=getattr(details, "reasoning_tokens", None) if details else None,
        cached_input_tokens=getattr(usage, "prompt_cache_hit_tokens", None),
        request_id=getattr(resp, "id", None),
    )

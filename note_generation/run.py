"""Generate notes for one model and one run.

    python -m note_generation.run --model claude_a --run dev
    python -m note_generation.run --model claude_a --run dev --limit 3      # smoke test
    python -m note_generation.run --model claude_a --run eval --dry-run     # mock model, no API

Safe to stop and restart: finished requests are skipped (resume by run_id). Failed ones are
retried on the next start. One model per invocation; run the four models as separate commands.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

from . import markers
from .common import (DRYRUN, FREEZE_FILE, OUT, RAW, REPO, append_jsonl, build_items, load_config,
                     load_prompt, prompt_hash, protocol_hash, read_jsonl, render_user, run_id,
                     sha256_text)
from .freeze import SHARED_KEYS, current_hashes
from .providers import PermanentError, TransientError, api_key, get_generate
from .validate_inputs import check_inputs

MAX_CONSECUTIVE_PERMANENT = 3


def git_state() -> dict:
    def git(*a):
        return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()
    return {"git_commit": git("rev-parse", "HEAD") or None,
            "git_dirty": bool(git("status", "--porcelain", "--", "note_generation/prompts",
                                  "note_generation/config.yaml", "note_generation/providers"))}


def fail(msg: str) -> int:
    print(f"BARRIER: {msg}")
    return 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="key under `models:` in config.yaml")
    ap.add_argument("--run", required=True, choices=["dev", "eval", "baseline"])
    ap.add_argument("--dry-run", action="store_true", help="use the mock model; writes to outputs/dryrun/")
    ap.add_argument("--limit", type=int, help="smoke test: only the first N requests; writes to outputs/smoke/")
    ap.add_argument("--delay", type=float, help="seconds between calls (overrides config; pacing is not part of the protocol)")
    args = ap.parse_args()

    load_dotenv(REPO / ".env")
    cfg = load_config()
    gen = cfg["generation"]
    version = cfg["protocol"]["prompt_version"]

    # ---- barriers before any request ----
    if args.model not in cfg["models"]:
        return fail(f"unknown model key {args.model!r}; choose from {list(cfg['models'])}")
    model_cfg = dict(cfg["models"][args.model])
    if args.dry_run:
        model_cfg.update(provider="mock", model_id="mock")
    elif str(model_cfg["model_id"]).upper().startswith("TODO"):
        return fail(f"models.{args.model}.model_id is still a TODO placeholder in config.yaml")

    errors, _ = check_inputs(cfg)
    if errors:
        return fail(f"gate 1 (input checks) failed with {len(errors)} problems; run validate_inputs")

    real_reported_run = not args.dry_run and args.limit is None and args.run in ("eval", "baseline")
    if real_reported_run:
        if not FREEZE_FILE.exists():
            return fail("protocol not frozen. Finish the dev run, then `python -m note_generation.freeze`")
        frozen = json.loads(FREEZE_FILE.read_text(encoding="utf-8"))
        now = current_hashes(cfg)
        changed = [k for k in SHARED_KEYS if frozen.get(k) != now[k]]
        if changed:
            return fail(f"files changed since freeze: {changed}. Revert them, or start a new protocol version")
        entry = frozen.get("models", {}).get(args.model)
        if entry is None:
            return fail(f"model {args.model!r} is not frozen yet; run `python -m note_generation.freeze` after its dev run")
        if entry["protocol_sha256"] != protocol_hash(cfg, args.model):
            return fail(f"models.{args.model} changed since freeze. Revert it, or start a new protocol version")

    if not args.dry_run:
        try:
            api_key(model_cfg["provider"])
        except PermanentError as e:
            return fail(str(e))

    system, user_tmpl = load_prompt(version)
    p_hash, c_hash = prompt_hash(version), protocol_hash(cfg, args.model)
    base = DRYRUN if args.dry_run else (OUT / "smoke" if args.limit else RAW)
    out_path = base / version / args.run / f"{args.model}.jsonl"

    existing = read_jsonl(out_path)
    mixed = {(r["prompt_sha256"], r["protocol_sha256"]) for r in existing} - {(p_hash, c_hash)}
    if mixed and not args.limit:
        return fail(f"{out_path} already holds notes made under different settings; "
                    "move it aside or start a new protocol version (never mix)")
    done = {r["run_id"] for r in existing if r["status"] == "ok"}

    items = build_items(cfg, args.run)
    if args.limit:
        items = items[: args.limit]
    todo = [it for it in items
            if run_id(version, args.model, it["encounter_id"], it["speaker"], it["insertion"]) not in done]
    print(f"{args.model} [{model_cfg['provider']}:{model_cfg['model_id']}] run={args.run}: "
          f"{len(items)} requests, {len(items) - len(todo)} already done, {len(todo)} to go -> {out_path}")

    generate = get_generate(model_cfg["provider"])
    gstate = git_state()
    consecutive_permanent = 0
    for n, it in enumerate(todo, 1):
        rid = run_id(version, args.model, it["encounter_id"], it["speaker"], it["insertion"])
        user = render_user(user_tmpl, it["dialogue"])
        rec = {k: it[k] for k in ("encounter_id", "split", "config", "speaker", "insertion",
                                  "template_id", "condition", "synonyms")}
        rec.update(run_id=rid, run=args.run, prompt_version=version, prompt_sha256=p_hash, protocol_sha256=c_hash,
                   model_key=args.model, provider=model_cfg["provider"], model_id=model_cfg["model_id"],
                   input_sha256=sha256_text(user), **gstate)

        attempts, err, result, t0 = 0, None, None, time.time()
        while attempts < gen["max_attempts"]:
            attempts += 1
            try:
                t0 = time.time()
                result = generate(system, user, model_cfg, gen)
                err = None
                break
            except TransientError as e:
                err = str(e)
                time.sleep(gen["backoff_base_s"] * 2 ** (attempts - 1))
            except PermanentError as e:
                err = str(e)
                break
        latency_ms = int((time.time() - t0) * 1000)

        if result is not None:
            rec.update(status="ok", note_text=result.text, **{k: v for k, v in result.to_dict().items() if k != "text"})
            consecutive_permanent = 0
        else:
            rec.update(status="error", note_text=None, error=err)
            consecutive_permanent = consecutive_permanent + 1 if "HTTP 4" in (err or "") else 0
        rec.update(attempts=attempts, latency_ms=latency_ms,
                   timestamp_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        rec["flags"] = markers.compute(rec, model_cfg, cfg)
        append_jsonl(out_path, rec)

        shown = ",".join(rec["flags"]) or "-"
        print(f"  [{n}/{len(todo)}] {it['encounter_id']} {it['speaker']:<7} {rec['status']:<5} flags={shown}")
        if consecutive_permanent >= MAX_CONSECUTIVE_PERMANENT:
            return fail(f"{MAX_CONSECUTIVE_PERMANENT} non-retryable errors in a row (last: {err}). "
                        "Check the model id and API key; nothing else will be sent.")
        if not args.dry_run:
            time.sleep(gen["delay_between_calls_s"] if args.delay is None else args.delay)

    print("done. Next: python -m note_generation.validate_runs --run", args.run, "--dry-run" if args.dry_run else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())

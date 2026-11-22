"""Freeze the protocol after the dev run.

    python -m note_generation.freeze

Writes freeze.json with hashes of the prompt, the shared config, the input pair files, and one
hash per model whose ID is filled in. The runner refuses eval/baseline runs unless the current
files match. Models still at TODO are skipped; run freeze again after filling them in to add
them. Already frozen models and the shared settings can only change with --force.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from .common import FREEZE_FILE, inputs_hash, load_config, prompt_hash, protocol_hash, shared_hash
from .validate_inputs import check_inputs

SHARED_KEYS = ("prompt_version", "prompt_sha256", "shared_sha256", "inputs_sha256")


def ready_models(cfg: dict) -> list[str]:
    return [k for k, m in cfg["models"].items() if not str(m["model_id"]).upper().startswith("TODO")]


def current_hashes(cfg: dict) -> dict:
    splits = sorted({s for r in cfg["runs"].values() for s in r["splits"]})
    return {
        "prompt_version": cfg["protocol"]["prompt_version"],
        "prompt_sha256": prompt_hash(cfg["protocol"]["prompt_version"]),
        "shared_sha256": shared_hash(cfg),
        "inputs_sha256": inputs_hash(splits),
    }


def model_entry(cfg: dict, key: str) -> dict:
    return {"model_id": cfg["models"][key]["model_id"], "protocol_sha256": protocol_hash(cfg, key)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="overwrite changed shared settings or a changed frozen model")
    args = ap.parse_args()
    cfg = load_config()

    ready = ready_models(cfg)
    if not ready:
        print("Refusing to freeze: every model_id is still TODO")
        return 1
    errors, _ = check_inputs(cfg)
    if errors:
        print(f"Refusing to freeze: gate 1 failed ({len(errors)} problems). Run validate_inputs.")
        return 1

    shared = current_hashes(cfg)
    models = {k: model_entry(cfg, k) for k in ready}
    old = json.loads(FREEZE_FILE.read_text(encoding="utf-8")) if FREEZE_FILE.exists() else None
    if old:
        changed = [k for k in SHARED_KEYS if old.get(k) != shared[k]]
        changed += [f"models.{k}" for k, e in old.get("models", {}).items()
                    if k in models and e["protocol_sha256"] != models[k]["protocol_sha256"]]
        if changed and not args.force:
            print(f"Changed since the freeze: {changed}. Changing them invalidates every eval/baseline note "
                  "made under it. If that is intended (new protocol version), rerun with --force and re-run "
                  "the affected models.")
            return 1
        added = sorted(set(models) - set(old.get("models", {})))
        if not changed and not added:
            print("Already frozen with identical settings.")
            return 0
        frozen_at = {k: e.get("frozen_at_utc") for k, e in old.get("models", {}).items()}
    else:
        frozen_at = {}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for k, e in models.items():
        e["frozen_at_utc"] = frozen_at.get(k) or now
    new = {**shared, "models": models, "updated_at_utc": now}
    FREEZE_FILE.write_text(json.dumps(new, indent=2) + "\n", encoding="utf-8")
    print(f"Frozen -> {FREEZE_FILE}")
    print(json.dumps(new, indent=2))
    todo = sorted(set(cfg["models"]) - set(ready))
    if todo:
        print(f"Not frozen yet (model_id still TODO): {todo}. Run freeze again after filling them in.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

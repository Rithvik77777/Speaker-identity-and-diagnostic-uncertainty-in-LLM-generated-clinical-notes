"""Freeze the protocol after the dev run.

    python -m note_generation.freeze

Writes freeze.json with hashes of the prompt, the protocol-relevant config and the input
pair files. The runner refuses eval/baseline runs unless the current files match.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from .common import FREEZE_FILE, inputs_hash, load_config, prompt_hash, protocol_hash
from .validate_inputs import check_inputs


def current_hashes(cfg: dict) -> dict:
    splits = sorted({s for r in cfg["runs"].values() for s in r["splits"]})
    return {
        "prompt_version": cfg["protocol"]["prompt_version"],
        "prompt_sha256": prompt_hash(cfg["protocol"]["prompt_version"]),
        "protocol_sha256": protocol_hash(cfg),
        "inputs_sha256": inputs_hash(splits),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="overwrite an existing, different freeze")
    args = ap.parse_args()
    cfg = load_config()

    todo = [k for k, m in cfg["models"].items() if str(m["model_id"]).upper().startswith("TODO")]
    if todo:
        print(f"Refusing to freeze: model_id still TODO for {todo}")
        return 1
    errors, _ = check_inputs(cfg)
    if errors:
        print(f"Refusing to freeze: gate 1 failed ({len(errors)} problems). Run validate_inputs.")
        return 1

    new = current_hashes(cfg)
    if FREEZE_FILE.exists():
        old = json.loads(FREEZE_FILE.read_text(encoding="utf-8"))
        same = all(old.get(k) == v for k, v in new.items())
        if same:
            print("Already frozen with identical settings.")
            return 0
        if not args.force:
            print("A different freeze exists. Changing it invalidates every eval/baseline note made under it.\n"
                  "If that is intended (new protocol version), rerun with --force and re-run all models.")
            return 1
    new["frozen_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    new["models"] = {k: m["model_id"] for k, m in cfg["models"].items()}
    FREEZE_FILE.write_text(json.dumps(new, indent=2) + "\n", encoding="utf-8")
    print(f"Frozen -> {FREEZE_FILE}")
    print(json.dumps(new, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Run the frozen item x prompt matrix for one model (protocol v4 §5, §10).

Each record is appended to outputs/raw/<dataset>/<model_key>/<split>.jsonl; --resume skips
run_ids that already have a successful record. Only environment failures are retried.
"""
import argparse
import hashlib
import json
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROMPTS = {"P0": "prompts/baseline.txt", "P1": "prompts/guarded.txt"}
SPEAKER = {"doctor": "Doctor", "patient": "Patient"}
MAX_ATTEMPTS = 3


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return None


def load_items(path, split, suite):
    kinds = {"main": {"uncertain"}, "control": {"affirmed_control"}, "all": {"uncertain", "affirmed_control"}}[suite]
    items = [json.loads(l) for l in open(path)]
    return [it for it in items if it["split"] == split and it["kind"] in kinds]


def build_requests(items, model_key, model_cfg, config_hash, prompts):
    reqs = []
    for it in items:
        for pid, tpl in prompts.items():
            user = tpl.format(speaker=SPEAKER[it["role"]], statement=it["statement"])
            run_id = sha(json.dumps([it["item_id"], pid, model_key, model_cfg["revision"], config_hash, 0]))[:20]
            reqs.append({"run_id": run_id, "item": it, "prompt_id": pid, "user_text": user})
    random.Random(6210).shuffle(reqs)
    return reqs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--dataset", default="primock57")
    ap.add_argument("--split", choices=["dev", "eval"], required=True)
    ap.add_argument("--suite", choices=["main", "control", "all"], default="all")
    ap.add_argument("--dtype", default="float32")
    ap.add_argument("--out", default="outputs/raw")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = yaml.safe_load(open("configs/models.yaml"))
    model_cfg, gen_cfg = cfg["models"][args.model], cfg["generation"]
    system_text = open("prompts/system.txt").read()
    prompts = {pid: open(p).read() for pid, p in PROMPTS.items()}
    config_hash = sha(json.dumps([model_cfg, gen_cfg, system_text, prompts, args.dtype], sort_keys=True))[:16]
    items = load_items(f"data/derived/{args.dataset}/items.jsonl", args.split, args.suite)
    reqs = build_requests(items, args.model, model_cfg, config_hash, prompts)
    print(f"{args.model} {args.dataset}/{args.split}/{args.suite}: {len(items)} items -> {len(reqs)} requests")
    if args.dry_run:
        return

    out_path = Path(args.out) / args.dataset / args.model / f"{args.split}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done, attempts = set(), {}
    if out_path.exists():
        for line in open(out_path):
            r = json.loads(line)
            attempts[r["run_id"]] = max(attempts.get(r["run_id"], 0), r["attempt"])
            if r["status"] == "ok":
                done.add(r["run_id"])
        if done and not args.resume:
            sys.exit(f"{out_path} already has {len(done)} successful records; pass --resume")
    todo = [r for r in reqs if r["run_id"] not in done]
    print(f"{len(done)} already done, {len(todo)} to run")
    if not todo:
        return

    from src.providers.hf_local import HFLocal

    backend = HFLocal(args.model, model_cfg, gen_cfg, dtype=args.dtype)
    env = backend.env()
    commit = git_commit()
    with open(out_path, "a") as f:
        for n, r in enumerate(todo, 1):
            it = r["item"]
            for attempt in range(attempts.get(r["run_id"], 0) + 1, MAX_ATTEMPTS + 1):
                rec = {"run_id": r["run_id"], "item_id": it["item_id"], "base_id": it["base_id"], "dataset": args.dataset,
                       "split": it["split"], "kind": it["kind"], "model_key": args.model, "model_id": model_cfg["hf_id"],
                       "model_revision": model_cfg["revision"], "marker_id": it["marker_id"], "role": it["role"],
                       "statement": it["statement"], "prompt_id": r["prompt_id"], "replicate": 0, "attempt": attempt,
                       "request_hash": sha(system_text + "\n" + r["user_text"])[:16], "config_hash": config_hash,
                       "git_commit": commit, "timestamp_utc": datetime.now(timezone.utc).isoformat(), **env}
                try:
                    res = backend.generate(system_text, r["user_text"])
                    rec.update(status="ok", output_text=res.pop("text"), **res)
                except RuntimeError as e:  # OOM / device failure: retry under the same config
                    rec.update(status="error", output_text=None, error=repr(e))
                f.write(json.dumps(rec) + "\n")
                f.flush()
                if rec["status"] == "ok":
                    break
            if n % 25 == 0 or n == len(todo):
                print(f"  {n}/{len(todo)}  last: {rec.get('output_text')!r}", flush=True)


if __name__ == "__main__":
    main()

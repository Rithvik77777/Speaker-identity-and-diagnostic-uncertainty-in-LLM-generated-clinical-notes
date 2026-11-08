"""D1 smoke test (protocol v4 §5.2): load the pinned model, show the rendered chat template,
and generate for three synthetic sentences that are not dev or eval items."""
import argparse
import json
from pathlib import Path

import torch
import yaml

from src.providers.hf_local import HFLocal

SMOKE = [("Doctor", "Sinusitis may be present."), ("Patient", "Gout is probably present."), ("Doctor", "Shingles is present.")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--dtype", default="float32")
    ap.add_argument("--out", default="outputs/env_checks")
    args = ap.parse_args()
    cfg = yaml.safe_load(open("configs/models.yaml"))
    system_text = open("prompts/system.txt").read()
    tpl = open("prompts/baseline.txt").read()
    backend = HFLocal(args.model, cfg["models"][args.model], cfg["generation"], dtype=args.dtype)
    report = {"model_key": args.model, **backend.env(), "repo_generation_config": backend.repo_generation_config,
              "generation_config": backend.gen_config.to_diff_dict(), "smoke": []}
    for speaker, statement in SMOKE:
        res = backend.generate(system_text, tpl.format(speaker=speaker, statement=statement))
        report["smoke"].append({"speaker": speaker, "statement": statement, **{k: res[k] for k in
                                ("text", "output_tokens", "finish_reason", "latency_ms", "raw_response")}})
    report["rendered_example"] = res["rendered_prompt"]
    report["has_think_tag"] = "<think>" in res["rendered_prompt"] or any("<think>" in s["raw_response"] for s in report["smoke"])
    if backend.device == "mps":
        report["mps_driver_allocated_gb"] = round(torch.mps.driver_allocated_memory() / 1e9, 2)
    Path(args.out).mkdir(parents=True, exist_ok=True)
    path = Path(args.out) / f"{args.model}_{backend.device}_{args.dtype}.json"
    path.write_text(json.dumps(report, indent=2))
    print(report["rendered_example"])
    for s in report["smoke"]:
        print(f"[{s['speaker']}] {s['statement']} -> {s['text']!r} ({s['output_tokens']} tok, {s['finish_reason']}, {s['latency_ms']} ms)")
    print("repo generation_config:", report["repo_generation_config"])
    print("think tag:", report["has_think_tag"], "| saved", path)


if __name__ == "__main__":
    main()

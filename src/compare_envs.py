"""Exact-match reproducibility check between two run directories (protocol v4 I07b)."""
import argparse
import json
from pathlib import Path


def load(path):
    return {r["run_id"]: r for r in map(json.loads, open(path)) if r["status"] == "ok"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="outputs/raw")
    ap.add_argument("--b", default="outputs/repro")
    ap.add_argument("--dataset", default="primock57")
    ap.add_argument("--split", default="dev")
    args = ap.parse_args()
    total = same = 0
    for pb in sorted(Path(args.b, args.dataset).glob(f"*/{args.split}.jsonl")):
        a, b = load(Path(args.a, args.dataset, pb.parent.name, pb.name)), load(pb)
        common = set(a) & set(b)
        eq = sum(a[k]["output_text"] == b[k]["output_text"] for k in common)
        envs = {a[k]["env_hash"] for k in common} | {b[k]["env_hash"] for k in common}
        print(f"{pb.parent.name}: {eq}/{len(common)} identical outputs; env hashes {sorted(envs)}")
        for k in sorted(common):
            if a[k]["output_text"] != b[k]["output_text"]:
                print("   diff:", a[k]["output_text"], "||", b[k]["output_text"])
        total += len(common); same += eq
    print(f"overall: {same}/{total} identical")


if __name__ == "__main__":
    main()

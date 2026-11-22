"""Gate 2: check generated notes before anyone scores them.

    python -m note_generation.validate_runs --run eval
    python -m note_generation.validate_runs --run dev --dry-run

Fails (exit 1) on missing or duplicate notes, mixed settings, or mock data in a real folder.
Prints warnings for every marker and for doctor/patient imbalances, and writes
outputs/reports/<run>_health.csv (the run-health table for the checkpoint).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime

import pandas as pd

from .common import DRYRUN, OUT, RAW, build_items, load_config, read_jsonl, run_id
from .markers import MARKERS, is_scorable


def load_run(cfg: dict, run: str, dry: bool) -> pd.DataFrame:
    base = (DRYRUN if dry else RAW) / cfg["protocol"]["prompt_version"] / run
    recs = []
    for p in sorted(base.glob("*.jsonl")):
        recs.extend(read_jsonl(p))
    return pd.DataFrame(recs)


def latest(df: pd.DataFrame) -> pd.DataFrame:
    """One record per run_id: the last ok one if any, else the last attempt."""
    df = df.copy()
    df["_ok"] = df.status.eq("ok")
    df["_i"] = range(len(df))
    return df.sort_values(["_ok", "_i"]).groupby("run_id").tail(1).drop(columns=["_ok", "_i"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, choices=["dev", "eval", "baseline"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cfg = load_config()
    th = cfg["thresholds"]
    version = cfg["protocol"]["prompt_version"]
    errors, warnings = [], []

    df = load_run(cfg, args.run, args.dry_run)
    if df.empty:
        print("no records found")
        return 1
    if not args.dry_run and (df.provider == "mock").any():
        errors.append("mock records found in a real output folder")

    # Settings must be identical across every note of this run: one prompt for all models,
    # and one protocol hash per model (it covers the shared settings + that model's entry).
    if df.prompt_sha256.nunique() > 1:
        errors.append(f"notes made under {df.prompt_sha256.nunique()} different prompt_sha256 values (mixed settings)")
    n_proto = df.groupby("model_key").protocol_sha256.nunique()
    for model_key, n in n_proto[n_proto > 1].items():
        errors.append(f"{model_key}: notes made under {n} different protocol_sha256 values (mixed settings)")

    ok_dupes = df[df.status == "ok"].run_id.value_counts()
    if (ok_dupes > 1).any():
        errors.append(f"{int((ok_dupes > 1).sum())} requests have more than one successful note")

    items = build_items(cfg, args.run)
    rows = []
    for model_key, g in df.groupby("model_key"):
        expected = {run_id(version, model_key, it["encounter_id"], it["speaker"], it["insertion"]) for it in items}
        lt = latest(g)
        missing = expected - set(lt[lt.status == "ok"].run_id)
        if missing:
            errors.append(f"{model_key}: {len(missing)} of {len(expected)} requests have no successful note")
        extra = set(lt.run_id) - expected
        if extra:
            errors.append(f"{model_key}: {len(extra)} records not in the expected item list")

        returned = sorted(set(lt.model_returned.dropna()))
        if len(returned) > 1:
            warnings.append(f"{model_key}: API reported several model versions {returned} (possible model drift)")
        ts = pd.to_datetime(lt.timestamp_utc)
        span_days = (ts.max() - ts.min()).total_seconds() / 86400
        if span_days > th["max_run_days_per_model"]:
            warnings.append(f"{model_key}: run spread over {span_days:.1f} days (> {th['max_run_days_per_model']})")

        lt = lt.assign(scorable=lt["flags"].apply(is_scorable))
        for speaker, s in lt.groupby("speaker"):
            row = {"model_key": model_key, "speaker": speaker, "n": len(s),
                   "ok": int((s.status == "ok").sum()), "scorable": int(s.scorable.sum()),
                   "median_latency_s": round(s.latency_ms.median() / 1000, 1),
                   "mean_output_tokens": round(pd.to_numeric(s.get("output_tokens"), errors="coerce").mean(), 0),
                   "model_returned": ";".join(returned)}
            for code in MARKERS:
                row[code] = int(s["flags"].apply(lambda f: code in f).sum())
            rows.append(row)

        # The biggest threat: failures that differ by speaker. Missing data that depends on the
        # condition biases the paired comparison even if every scored note is labelled correctly.
        if args.run != "baseline":
            rate = lt.groupby("speaker").scorable.apply(lambda x: 100 * (1 - x.mean()))
            if {"doctor", "patient"} <= set(rate.index):
                gap = abs(rate["doctor"] - rate["patient"])
                if gap > th["asymmetry_warn_pts"]:
                    warnings.append(f"{model_key}: unscorable rate doctor {rate['doctor']:.1f}% vs patient "
                                    f"{rate['patient']:.1f}% (gap {gap:.1f} pts) -> report; analysis may be biased")
            pair_ok = lt.groupby("encounter_id").scorable.sum()
            broken = int((pair_ok == 1).sum())
            if broken:
                warnings.append(f"{model_key}: {broken} encounters have only one scorable speaker; "
                                "they drop out of the paired analysis")

    health = pd.DataFrame(rows)
    rep_dir = OUT / ("reports_dryrun" if args.dry_run else "reports")
    rep_dir.mkdir(parents=True, exist_ok=True)
    out_csv = rep_dir / f"{args.run}_health.csv"
    health.to_csv(out_csv, index=False)

    cols = ["model_key", "speaker", "n", "ok", "scorable"] + [c for c in MARKERS if health[c].sum() > 0]
    print(health[cols].to_string(index=False))
    print(f"\nrun-health table -> {out_csv}")
    for w in warnings:
        print("WARNING:", w)
    if errors:
        print(f"GATE 2 FAILED ({len(errors)}):")
        for e in errors:
            print("  -", e)
        return 1
    print(f"GATE 2 PASSED for run '{args.run}' ({datetime.now():%Y-%m-%d %H:%M}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

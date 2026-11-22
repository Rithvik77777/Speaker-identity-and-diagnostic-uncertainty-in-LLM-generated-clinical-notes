"""Metrics from human labels.

    # agreement between two raters (before adjudication)
    python -m note_generation.analyze kappa outputs/packets/eval_packet_rater1.csv outputs/packets/eval_packet_rater2.csv

    # metrics + doctor/patient gaps from the adjudicated labels
    python -m note_generation.analyze metrics --run eval --labels outputs/packets/eval_adjudicated.csv
    python -m note_generation.analyze metrics --run eval --labels ... --by template_id   # breakdown

Units: the encounter is the independent unit (paired doctor/patient copies). Intervals come
from a bootstrap that resamples encounters, never individual notes.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .common import OUT, load_config

ALLOWED = {
    "mention": {"present", "omitted", "negated"},
    "certainty": {"definite", "hedged", "unclear", "na"},
    "attribution": {"correct", "missing", "wrong", "na"},
    "section": {"subjective", "assessment", "plan", "other", "na"},
    "plan_action": {"yes", "no"},
}

# name -> (definition text, whether it is conditional on the condition being mentioned)
METRICS = {
    "mention_rate": ("mention == present / all notes", False),
    "hardening_rate": ("certainty == definite / mentioned (unclear excluded, counted separately)", True),
    "hedge_preservation": ("certainty == hedged / mentioned (unclear excluded)", True),
    "attribution_accuracy": ("attribution == correct / mentioned", True),
    "attribution_correct_of_all": ("mentioned and attribution == correct / all notes", False),
    "assessment_promotion": ("section in {assessment, plan} / all notes", False),
    "plan_contamination": ("plan_action == yes / all notes", False),
    "joint_fidelity": ("mentioned and hedged and correctly attributed / all notes", False),
}


def clean_labels(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    problems = []
    df = df.copy()
    for col, allowed in ALLOWED.items():
        df[col] = df[col].fillna("").astype(str).str.strip().str.lower()
        blank = df[col] == ""
        bad = ~blank & ~df[col].isin(allowed)
        if blank.any():
            problems.append(f"{col}: {int(blank.sum())} blank")
        if bad.any():
            problems.append(f"{col}: {int(bad.sum())} invalid values e.g. {df.loc[bad, col].unique()[:3].tolist()}")
    # Consistency barrier: an omitted mention can't have a certainty/attribution label.
    om = df.mention.ne("present")
    for col in ("certainty", "attribution"):
        inc = om & df[col].ne("na") & df[col].ne("")
        if inc.any():
            problems.append(f"{int(inc.sum())} notes have mention != present but {col} != na")
    return df, problems


def indicators(df: pd.DataFrame) -> pd.DataFrame:
    present = df.mention.eq("present")
    decidable = present & df.certainty.isin(["definite", "hedged"])
    out = pd.DataFrame(index=df.index)
    out["mention_rate"] = present.astype(float)
    out["hardening_rate"] = np.where(decidable, df.certainty.eq("definite"), np.nan)
    out["hedge_preservation"] = np.where(decidable, df.certainty.eq("hedged"), np.nan)
    out["attribution_accuracy"] = np.where(present, df.attribution.eq("correct"), np.nan)
    out["attribution_correct_of_all"] = (present & df.attribution.eq("correct")).astype(float)
    out["assessment_promotion"] = df.section.isin(["assessment", "plan"]).astype(float)
    out["plan_contamination"] = df.plan_action.eq("yes").astype(float)
    out["joint_fidelity"] = (present & df.certainty.eq("hedged") & df.attribution.eq("correct")).astype(float)
    out["unclear_certainty"] = (present & df.certainty.eq("unclear")).astype(float)
    return out


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def paired_gap(g: pd.DataFrame, metric: str, n_boot: int, rng: np.random.Generator) -> dict:
    """patient - doctor on encounters that have both speakers; CI by resampling encounters."""
    wide_s = g.pivot_table(index="encounter_id", columns="speaker", values=metric, aggfunc="sum")
    wide_n = g.assign(_n=g[metric].notna().astype(float)).pivot_table(
        index="encounter_id", columns="speaker", values="_n", aggfunc="sum")
    if not {"doctor", "patient"} <= set(wide_n.columns):
        return {}
    keep = wide_n.index[(wide_n.doctor > 0) & (wide_n.patient > 0)]
    if len(keep) == 0:
        return {}
    Sd, Sp = wide_s.loc[keep, "doctor"].to_numpy(), wide_s.loc[keep, "patient"].to_numpy()
    Nd, Np = wide_n.loc[keep, "doctor"].to_numpy(), wide_n.loc[keep, "patient"].to_numpy()
    est = Sp.sum() / Np.sum() - Sd.sum() / Nd.sum()
    w = rng.multinomial(len(keep), np.full(len(keep), 1 / len(keep)), size=n_boot)
    with np.errstate(invalid="ignore", divide="ignore"):
        boots = (w @ Sp) / (w @ Np) - (w @ Sd) / (w @ Nd)
    lo, hi = np.nanpercentile(boots, [2.5, 97.5])
    # McNemar on encounters where both copies give a 0/1 value (one note per speaker per encounter).
    d = (Sd / Nd)[(Nd == 1) & (Np == 1)]
    p = (Sp / Np)[(Nd == 1) & (Np == 1)]
    b, c = int(((d == 1) & (p == 0)).sum()), int(((d == 0) & (p == 1)).sum())
    return {"gap_patient_minus_doctor": est, "ci95_lo": lo, "ci95_hi": hi,
            "n_encounters": len(keep), "discordant_doctor_only": b, "discordant_patient_only": c,
            "mcnemar_p": mcnemar_exact(b, c)}


def cmd_metrics(args) -> int:
    cfg = load_config()
    labels = pd.read_csv(args.labels, keep_default_na=False)
    labels, problems = clean_labels(labels)
    if problems and not args.allow_partial:
        print("BARRIER: labels not clean (fix them, or --allow-partial for a provisional look):")
        for p in problems:
            print("  -", p)
        return 1
    key_path = Path(args.key) if args.key else OUT / "packets" / f"{args.run}_packet_KEY_do_not_share_with_raters.csv"
    key = pd.read_csv(key_path)
    df = labels.merge(key, on="item_id", how="inner", suffixes=("", "_key"))
    if len(df) != len(labels):
        print(f"BARRIER: {len(labels) - len(df)} labelled items not found in the key")
        return 1
    if "speaker_key" in df:
        df["speaker"] = df["speaker_key"]
    if "prompt_version" not in df:          # keys made before prompt versions existed
        df["prompt_version"] = cfg["protocol"]["prompt_versions"][0]
    ind = indicators(df)
    data = pd.concat([df[["prompt_version", "model_key", "encounter_id", "speaker", "template_id", "config"]], ind], axis=1)

    rng = np.random.default_rng(cfg["protocol"]["seed"])
    group_cols = ["prompt_version", "model_key"] + ([args.by] if args.by else [])
    rows = []
    for keys, g in data.groupby(group_cols):
        keys = keys if isinstance(keys, tuple) else (keys,)
        for metric in METRICS:
            row = dict(zip(group_cols, keys), metric=metric)
            for spk in ("doctor", "patient"):
                s = g.loc[g.speaker == spk, metric]
                row[f"{spk}_rate"] = s.mean()
                row[f"{spk}_n"] = int(s.notna().sum())
            row.update(paired_gap(g, metric, args.n_boot, rng))
            rows.append(row)
        rows.append(dict(zip(group_cols, keys), metric="unclear_certainty_count",
                         doctor_rate=g.loc[g.speaker == "doctor", "unclear_certainty"].sum(),
                         patient_rate=g.loc[g.speaker == "patient", "unclear_certainty"].sum()))
    res = pd.DataFrame(rows)
    out_dir = OUT / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{args.run}_metrics{'_by_' + args.by if args.by else ''}.csv"
    res.to_csv(out, index=False)
    with pd.option_context("display.width", 200, "display.max_columns", 20, "display.float_format", "{:.3f}".format):
        print(res.to_string(index=False))
    print(f"\n-> {out}\nReport effect sizes with intervals; a non-significant gap is not evidence of no bias.")
    return 0


def cohen_kappa(a: pd.Series, b: pd.Series) -> float:
    cats = sorted(set(a) | set(b))
    po = (a == b).mean()
    pe = sum((a == c).mean() * (b == c).mean() for c in cats)
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def cmd_kappa(args) -> int:
    a, _ = clean_labels(pd.read_csv(args.rater_a, keep_default_na=False))
    b, _ = clean_labels(pd.read_csv(args.rater_b, keep_default_na=False))
    m = a.merge(b, on="item_id", suffixes=("_a", "_b"))
    print(f"{len(m)} items rated by both")
    for col in ALLOWED:
        both = m[(m[f"{col}_a"] != "") & (m[f"{col}_b"] != "")]
        if both.empty:
            continue
        k = cohen_kappa(both[f"{col}_a"], both[f"{col}_b"])
        print(f"  {col:<12} kappa={k:.2f}  raw agreement={(both[f'{col}_a'] == both[f'{col}_b']).mean():.0%}  n={len(both)}"
              + ("   <- below 0.6: tighten the rater guide" if k < 0.6 else ""))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("metrics")
    m.add_argument("--run", default="eval", choices=["dev", "eval"])
    m.add_argument("--labels", required=True, help="adjudicated packet CSV (item_id + label columns)")
    m.add_argument("--key", help="packet key CSV (default: outputs/packets/<run>_packet_KEY...)")
    m.add_argument("--by", choices=["template_id", "config"], help="extra breakdown")
    m.add_argument("--n-boot", type=int, default=10_000)
    m.add_argument("--allow-partial", action="store_true")
    k = sub.add_parser("kappa")
    k.add_argument("rater_a")
    k.add_argument("rater_b")
    args = ap.parse_args()
    return cmd_metrics(args) if args.cmd == "metrics" else cmd_kappa(args)


if __name__ == "__main__":
    sys.exit(main())

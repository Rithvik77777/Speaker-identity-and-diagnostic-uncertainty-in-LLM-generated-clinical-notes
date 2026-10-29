"""Merge two independent PriMock57 rating packets (protocol v4 §7.3).

Step 1 (no --adjudicated): checks completeness, reports raw agreement, Cohen's kappa and
nominal Krippendorff's alpha per field, and writes disagreements.csv for discussion. The
original packets are never modified.
Step 2 (--adjudicated FILE with unit_id + final fields for every disagreement): writes the
per-run human label file that src.analysis.primock57_analysis reads, plus agreement of the
automatic screen against the final human labels.
"""
import argparse
from collections import Counter
from pathlib import Path

import pandas as pd

FIELDS = ["target_status", "output_certainty", "attribution"]
VALID = {
    "target_status": {"retained", "omitted", "negated", "mixed", "unclear"},
    "output_certainty": {"absolute", "high", "moderate", "low", "unclear", "NA"},
    "attribution": {"correct", "missing", "wrong", "NA"},
}


def read_packet(path):
    df = pd.read_excel(path, sheet_name="rate", dtype=str).fillna("")
    for f in FIELDS:
        df[f] = df[f].str.strip()
        bad = df[~df[f].isin(VALID[f])]
        if len(bad):
            raise SystemExit(f"{path}: {len(bad)} rows with missing/invalid {f} (first row {int(bad.iloc[0]['row'])})")
    return df.set_index("unit_id")


def cohen_kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n ** 2
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def kripp_alpha_nominal(a, b):
    # Two coders, no missing values: coincidence-matrix form.
    pairs = Counter()
    for x, y in zip(a, b):
        pairs[(x, y)] += 1
        pairs[(y, x)] += 1
    n_c = Counter()
    for (x, _), v in pairs.items():
        n_c[x] += v
    n = sum(n_c.values())
    do = sum(v for (x, y), v in pairs.items() if x != y) / n
    de = sum(n_c[x] * n_c[y] for x in n_c for y in n_c if x != y) / (n * (n - 1))
    return 1 - do / de if de else float("nan")


def agreement(a_df, b_df, names):
    rows = []
    for f in FIELDS:
        a, b = list(a_df[f]), list(b_df[f])
        rows.append({"field": f, "raters": " vs ".join(names), "n": len(a),
                     "raw_agreement": round(sum(x == y for x, y in zip(a, b)) / len(a), 4),
                     "cohen_kappa": round(cohen_kappa(a, b), 4), "kripp_alpha_nominal": round(kripp_alpha_nominal(a, b), 4)})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="annotations/primock57")
    ap.add_argument("--raters", nargs=2, default=["hang", "rater_b"])
    ap.add_argument("--adjudicated", default=None)
    ap.add_argument("--prefix", default="packet", help="calibration: agreement only, no label file")
    args = ap.parse_args()
    d = Path(args.dir)
    a, b = (read_packet(d / f"{args.prefix}_{r}.xlsx") for r in args.raters)
    b = b.loc[a.index]
    agr = agreement(a, b, args.raters)
    agr.to_csv(d / f"{args.prefix}_agreement.csv", index=False)
    print(agr.to_string(index=False))

    disagree = a.index[(a[FIELDS] != b[FIELDS]).any(axis=1)]
    dis = pd.DataFrame({"unit_id": disagree, "speaker": a.loc[disagree, "speaker"], "source_statement": a.loc[disagree, "source_statement"],
                        "generated_note": a.loc[disagree, "generated_note"]})
    for f in FIELDS:
        dis[f"{f}_{args.raters[0]}"] = a.loc[disagree, f].values
        dis[f"{f}_{args.raters[1]}"] = b.loc[disagree, f].values
        dis[f"{f}_final"] = ""
    dis.to_csv(d / f"{args.prefix}_disagreements.csv", index=False)
    print(f"{len(dis)} of {len(a)} units disagree -> {d / (args.prefix + '_disagreements.csv')}")
    if not args.adjudicated or args.prefix != "packet":
        return

    final = a[FIELDS].copy()
    adj = pd.read_csv(args.adjudicated, dtype=str).set_index("unit_id")
    missing = set(disagree) - set(adj.index)
    if missing:
        raise SystemExit(f"{len(missing)} disagreements lack an adjudicated label")
    for f in FIELDS:
        col = f"{f}_final" if f"{f}_final" in adj.columns else f
        vals = adj.loc[disagree, col].str.strip()
        if (~vals.isin(VALID[f])).any():
            raise SystemExit(f"invalid adjudicated {f}")
        final.loc[disagree, f] = vals.values
    umap = pd.read_csv(d / "unit_map.csv")
    labels = umap.merge(final, left_on="unit_id", right_index=True, how="left")
    labels["labeler"] = "human_adjudicated"
    labels[["run_id", "unit_id", "labeler", *FIELDS]].to_csv(d / "human_labels_eval.csv", index=False)
    print(f"wrote {len(labels)} run-level human labels")

    auto_path = d / "auto_screen_eval.csv"
    if auto_path.exists():
        # Compared per rating unit, since identical notes share one human label.
        auto = pd.read_csv(auto_path).merge(labels[["run_id", "unit_id", *FIELDS]], on="run_id", suffixes=("_auto", ""))
        auto = auto.drop_duplicates("unit_id")
        rows = []
        for f in FIELDS:
            x = auto[f"{f}_auto"].replace({"hedged_unclassified": "hedged"}) if f == "output_certainty" else auto[f"{f}_auto"]
            y = auto[f].where(~auto[f].isin(["high", "moderate", "low"]), "hedged") if f == "output_certainty" else auto[f]
            if f == "output_certainty":
                x = x.where(~x.isin(["high", "moderate", "low"]), "hedged")
            rows.append({"field": f, "n": len(auto), "raw_agreement_auto_vs_human": round((x == y).mean(), 4),
                         "cohen_kappa": round(cohen_kappa(list(x), list(y)), 4)})
        pd.DataFrame(rows).to_csv(d / "auto_vs_human.csv", index=False)
        print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()

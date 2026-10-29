"""E1-E4 for the PriMock57 replication (protocol v4 §6), from either human or provisional labels.

--labels points at a CSV with run_id,target_status,output_certainty,attribution. With the
auto_lexical_v1 screen every output path is prefixed 'auto_' so provisional numbers are never
confused with the human-rated results; joint fidelity is reported only in its coarse form then.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis.common import Bootstrap, add_indicators, fmt_row, unclear_bounds

MARKERS = ["may", "possibly", "probably"]
ROLES = ["doctor", "patient"]
MODELS = ["qwen3_4b", "phi4_mini", "granite4_micro"]


def load(dataset, split, labels_path):
    runs = []
    for m in MODELS:
        p = Path("outputs/raw", dataset, m, f"{split}.jsonl")
        runs += [json.loads(l) for l in open(p)]
    runs = pd.DataFrame(runs)
    ok = runs[runs.status == "ok"].drop_duplicates("run_id", keep="last")
    items = pd.DataFrame([json.loads(l) for l in open(f"data/derived/{dataset}/items.jsonl")])
    ok = ok.merge(items[["item_id", "source_certainty"]], on="item_id", how="left")
    labels = pd.read_csv(labels_path)
    df = ok.merge(labels[["run_id", "target_status", "output_certainty", "attribution"]], on="run_id", how="inner")
    missing = set(ok.run_id) - set(df.run_id)
    return add_indicators(df), len(ok), len(missing), runs


def role_table(bs, df, metrics, prompts=("P0", "P1")):
    rows = []
    for model in MODELS:
        for pid in prompts:
            for metric in metrics:
                cells = {}
                for marker in MARKERS:
                    for role in ROLES:
                        sub = df[(df.model_key == model) & (df.prompt_id == pid) & (df.marker_id == marker) & (df.role == role)]
                        cells[(marker, role)] = bs.ratio(sub, metric)
                for marker in MARKERS + ["pooled"]:
                    if marker == "pooled":
                        get = lambda role: (np.mean([cells[(mk, role)][0] for mk in MARKERS]),
                                            np.nanmean(np.vstack([cells[(mk, role)][1] for mk in MARKERS]), axis=0))
                    else:
                        get = lambda role, mk=marker: cells[(mk, role)]
                    (pd_, bd), (pp, bp) = get("doctor"), get("patient")
                    keys = dict(model=model, prompt=pid, marker=marker, metric=metric)
                    rows.append(fmt_row(pd_, bd, **keys, contrast="doctor"))
                    rows.append(fmt_row(pp, bp, **keys, contrast="patient"))
                    rows.append(fmt_row(pp - pd_, bp - bd, **keys, contrast="patient_minus_doctor"))
    return pd.DataFrame(rows)


def prompt_table(bs, df, metrics):
    rows = []
    for model in MODELS:
        for metric in metrics:
            vals = {}
            for pid in ["P0", "P1"]:
                per_role = {}
                for role in ROLES:
                    cells = [bs.ratio(df[(df.model_key == model) & (df.prompt_id == pid) & (df.marker_id == mk) & (df.role == role)], metric)
                             for mk in MARKERS]
                    per_role[role] = (np.mean([c[0] for c in cells]), np.nanmean(np.vstack([c[1] for c in cells]), axis=0))
                both = ((per_role["doctor"][0] + per_role["patient"][0]) / 2, (per_role["doctor"][1] + per_role["patient"][1]) / 2)
                gap = (per_role["patient"][0] - per_role["doctor"][0], per_role["patient"][1] - per_role["doctor"][1])
                vals[pid] = (both, gap)
            keys = dict(model=model, metric=metric)
            (b0, g0), (b1, g1) = vals["P0"], vals["P1"]
            rows.append(fmt_row(b0[0], b0[1], **keys, quantity="P0"))
            rows.append(fmt_row(b1[0], b1[1], **keys, quantity="P1"))
            rows.append(fmt_row(b1[0] - b0[0], b1[1] - b0[1], **keys, quantity="P1_minus_P0"))
            rows.append(fmt_row(g1[0] - g0[0], g1[1] - g0[1], **keys, quantity="gap_change_signed"))
            rows.append(fmt_row(abs(g1[0]) - abs(g0[0]), np.abs(g1[1]) - np.abs(g0[1]), **keys, quantity="abs_gap_change"))
    return pd.DataFrame(rows)


def control_table(bs, df, metrics):
    rows = []
    for model in MODELS:
        for pid in ["P0", "P1"]:
            for metric in metrics:
                r = {role: bs.ratio(df[(df.model_key == model) & (df.prompt_id == pid) & (df.role == role)], metric) for role in ROLES}
                keys = dict(model=model, prompt=pid, metric=metric)
                rows.append(fmt_row(*r["doctor"], **keys, contrast="doctor"))
                rows.append(fmt_row(*r["patient"], **keys, contrast="patient"))
                rows.append(fmt_row(r["patient"][0] - r["doctor"][0], r["patient"][1] - r["doctor"][1], **keys, contrast="patient_minus_doctor"))
    return pd.DataFrame(rows)


def error_types(main, ctrl):
    rows = []
    for (model, pid), g in main.groupby(["model_key", "prompt_id"]):
        c = ctrl[(ctrl.model_key == model) & (ctrl.prompt_id == pid)]
        rows.append({"model": model, "prompt": pid, "n_main": len(g), "n_control": len(c),
                     "overcertainty_main": int(g.absolute.sum()),
                     "weakening_control": int(c.weakened.sum()),
                     "omission": int(g.omitted.sum() + c.omitted.sum()),
                     "negated_or_mixed": int(g.negated_or_mixed.sum() + c.negated_or_mixed.sum()),
                     "attribution_missing": int(((g.retained == 1) & (g.attribution == "missing")).sum() + ((c.retained == 1) & (c.attribution == "missing")).sum()),
                     "attribution_wrong": int(((g.retained == 1) & (g.attribution == "wrong")).sum() + ((c.retained == 1) & (c.attribution == "wrong")).sum()),
                     "unclear": int(g.unclear_any.sum() + c.unclear_any.sum())})
    return pd.DataFrame(rows)


def plot(e1, e3, figdir, prefix):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    colors = {"qwen3_4b": "#2a6f97", "phi4_mini": "#e09f3e", "granite4_micro": "#6a994e"}
    sub = e1[(e1.metric == "CHR") & (e1.contrast == "patient_minus_doctor")]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    for ax, pid in zip(axes, ["P0", "P1"]):
        s = sub[sub.prompt == pid]
        for j, model in enumerate(MODELS):
            m = s[s.model == model].set_index("marker").reindex(MARKERS + ["pooled"])
            x = np.arange(4) + (j - 1) * 0.22
            ax.errorbar(x, 100 * m.estimate, yerr=[100 * (m.estimate - m.ci95_lo), 100 * (m.ci95_hi - m.estimate)],
                        fmt="o", color=colors[model], label=model, capsize=2, ms=4)
        ax.axhline(0, color="#888", lw=0.8)
        ax.set_xticks(np.arange(4), MARKERS + ["pooled"])
        ax.set_title(f"{pid}: patient − doctor CHR")
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Percentage points (95% cluster CI)")
    axes[1].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{figdir}/{prefix}e1_role_gap.pdf"); fig.savefig(f"{figdir}/{prefix}e1_role_gap.png", dpi=200)

    fig, axes = plt.subplots(1, 3, figsize=(10, 3.2))
    for ax, metric in zip(axes, ["CHR", "retention", "attribution_correct_of_all"]):
        s = e3[(e3.metric == metric) & e3.quantity.isin(["P0", "P1"])]
        for j, model in enumerate(MODELS):
            m = s[s.model == model].set_index("quantity").reindex(["P0", "P1"])
            x = np.arange(2) + (j - 1) * 0.25
            ax.bar(x, 100 * m.estimate, width=0.24, color=colors[model], label=model,
                   yerr=[100 * (m.estimate - m.ci95_lo), 100 * (m.ci95_hi - m.estimate)], capsize=2)
        ax.set_xticks([0, 1], ["P0", "P1"])
        ax.set_title(metric.replace("_", " "))
        ax.set_ylim(0, 105)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("% of outputs")
    axes[2].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{figdir}/{prefix}e3_prompt.pdf"); fig.savefig(f"{figdir}/{prefix}e3_prompt.png", dpi=200)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="primock57")
    ap.add_argument("--labels", required=True)
    ap.add_argument("--provisional", action="store_true", help="labels are the automatic screen")
    args = ap.parse_args()
    prefix = "auto_" if args.provisional else ""
    tdir, fdir = Path("tables", args.dataset), Path("figures", args.dataset)
    tdir.mkdir(parents=True, exist_ok=True); fdir.mkdir(parents=True, exist_ok=True)

    df, n_ok, n_unlabelled, runs = load(args.dataset, "eval", args.labels)
    if n_unlabelled:
        raise SystemExit(f"{n_unlabelled} valid runs have no label")
    main_df, ctrl_df = df[df.kind == "uncertain"], df[df.kind == "affirmed_control"]
    status = runs.groupby(["model_key", "status"]).size().unstack(fill_value=0)
    status.to_csv(tdir / f"{prefix}run_status.csv")

    metrics = ["CHR", "retention", "omission", "uncertainty_retention", "attribution_fidelity", "attribution_correct_of_all", "joint_coarse"]
    if not args.provisional:
        metrics += ["exact_bin_retention", "joint_fidelity"]
    bs_main = Bootstrap(main_df)
    e1 = role_table(bs_main, main_df, metrics)
    e1[e1.prompt == "P0"].to_csv(tdir / f"{prefix}e1_role.csv", index=False)
    e1.to_csv(tdir / f"{prefix}e1e2_role_by_marker_all_prompts.csv", index=False)
    e1[(e1.prompt == "P0") & (e1.marker != "pooled")].to_csv(tdir / f"{prefix}e2_marker.csv", index=False)
    trans = (main_df.groupby(["model_key", "prompt_id", "marker_id", "source_certainty", "output_certainty"]).size()
             .rename("count").reset_index())
    trans.to_csv(tdir / f"{prefix}e2_transitions.csv", index=False)
    e3 = prompt_table(bs_main, main_df, metrics)
    e3.to_csv(tdir / f"{prefix}e3_prompt.csv", index=False)
    bs_ctrl = Bootstrap(ctrl_df)
    e4 = control_table(bs_ctrl, ctrl_df, ["weakening", "retention", "attribution_correct_of_all", "joint_fidelity"])
    e4.to_csv(tdir / f"{prefix}e4_controls.csv", index=False)
    errs = error_types(main_df, ctrl_df)
    errs.to_csv(tdir / f"{prefix}overall_errors.csv", index=False)
    bounds = []
    for (model, pid), g in main_df.groupby(["model_key", "prompt_id"]):
        lo, hi = unclear_bounds(g)
        bounds.append({"model": model, "prompt": pid, "CHR_lower": round(lo, 4), "CHR_upper": round(hi, 4)})
    pd.DataFrame(bounds).to_csv(tdir / f"{prefix}chr_unclear_bounds.csv", index=False)
    plot(e1, e3, fdir, prefix)

    show = e1[(e1.metric == "CHR") & (e1.marker == "pooled")]
    print(f"valid eval runs: {n_ok}; main {len(main_df)}, control {len(ctrl_df)}; bases {main_df.base_id.nunique()}/{ctrl_df.base_id.nunique()}")
    print(show[["model", "prompt", "contrast", "estimate", "ci95_lo", "ci95_hi"]].to_string(index=False))
    print(e3[e3.metric.isin(["CHR", "retention", "attribution_correct_of_all"])].to_string(index=False))
    print(e4[e4.metric == "weakening"].to_string(index=False))
    print(errs.to_string(index=False))


if __name__ == "__main__":
    main()

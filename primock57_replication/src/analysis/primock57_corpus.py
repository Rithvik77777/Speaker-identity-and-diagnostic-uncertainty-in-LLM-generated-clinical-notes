"""Descriptive statistics for PriMock57 and surface counts of epistemic cues by speaker.

Cue matching is lexical and not disambiguated (e.g. deontic 'may', request 'could you'),
so counts are upper bounds on epistemic use; obvious request/permission frames are excluded.
Doctor-patient differences get 95% intervals from a cluster bootstrap over consultations.
"""
import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

# Cue families follow the modality literature cited in the protocol (Thompson et al. 2008;
# Szarvas et al. 2008): modal auxiliaries, adverbs, adjectives, and speaker-commitment verbs.
CUES = {
    "modal_aux": {
        "may": r"\bmay\b(?! I\b)",
        "might": r"\bmight\b",
        "could": r"\bcould\b(?! you\b)(?! I\b)",
    },
    "adverb": {
        "possibly": r"\bpossibly\b",
        "probably": r"\bprobably\b",
        "perhaps": r"\bperhaps\b",
        "maybe": r"\bmaybe\b",
        "likely_adv": r"\b(?:most |more |less |un)?likely\b",
        "definitely": r"\bdefinitely\b",
    },
    "adjective": {
        "possible": r"\bpossible\b",
        "probable": r"\bprobable\b",
    },
    "commitment_verb": {
        "i_think": r"\bI think\b",
        "i_wonder": r"\bI wonder\b",
        "i_suspect": r"\bI suspect\b",
        "seems_sounds": r"\b(?:seems?|sounds?) like\b",
        "not_sure": r"\bnot (?:sure|certain)\b",
    },
}
TARGET = ["may", "possibly", "probably"]
SPEAKERS = ["DOCTOR", "PATIENT"]


def clean(text):
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+([,.?!])", r"\1", text).strip()


def tokens(text):
    return re.findall(r"[A-Za-z']+", text)


def load(raw):
    rows, markup = [], []
    for f in sorted(Path(raw).glob("*_conversation.json")):
        cid = f.name.replace("_conversation.json", "")
        for i, t in enumerate(json.load(open(f))["turns"]):
            markup += [(cid, t["speaker"], tag) for tag in re.findall(r"<([A-Z_]+)/?>", t["text"])]
            text = clean(t["text"])
            row = {"consultation_id": cid, "turn": i, "speaker": t["speaker"], "text": text, "n_tokens": len(tokens(text))}
            for fam, cues in CUES.items():
                for name, rx in cues.items():
                    row[name] = len(re.findall(rx, text, flags=re.I))
            rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(markup, columns=["consultation_id", "speaker", "tag"])


def per_consultation(df, cols):
    g = df.groupby(["consultation_id", "speaker"])[cols + ["n_tokens"]].sum().reset_index()
    return g


def rate_diff_boot(g, col, n_boot=10000, seed=6210):
    """Doctor minus patient rate per 1,000 tokens, pooled within resampled consultation sets."""
    ids = g["consultation_id"].unique()
    wide = g.pivot(index="consultation_id", columns="speaker", values=[col, "n_tokens"]).fillna(0)
    num_d, num_p = wide[(col, "DOCTOR")].to_numpy(), wide[(col, "PATIENT")].to_numpy()
    den_d, den_p = wide[("n_tokens", "DOCTOR")].to_numpy(), wide[("n_tokens", "PATIENT")].to_numpy()
    point = 1000 * (num_d.sum() / den_d.sum() - num_p.sum() / den_p.sum())
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(ids), size=(n_boot, len(ids)))
    boot = 1000 * (num_d[idx].sum(1) / den_d[idx].sum(1) - num_p[idx].sum(1) / den_p[idx].sum(1))
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return point, lo, hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw/primock57")
    ap.add_argument("--tables", default="tables/primock57")
    ap.add_argument("--figures", default="figures/primock57")
    args = ap.parse_args()
    Path(args.tables).mkdir(parents=True, exist_ok=True)
    Path(args.figures).mkdir(parents=True, exist_ok=True)
    df, markup = load(args.raw)
    cue_cols = [c for fam in CUES.values() for c in fam]
    df["any_cue"] = (df[cue_cols].sum(axis=1) > 0).astype(int)
    df["any_target"] = (df[TARGET].sum(axis=1) > 0).astype(int)

    per_c = df.groupby("consultation_id").agg(turns=("turn", "size"), tokens=("n_tokens", "sum"))
    overview = []
    for spk in SPEAKERS + ["ALL"]:
        sub = df if spk == "ALL" else df[df.speaker == spk]
        overview.append({"speaker": spk, "consultations": sub.consultation_id.nunique(), "turns": len(sub),
                         "tokens": int(sub.n_tokens.sum()), "mean_tokens_per_turn": round(sub.n_tokens.mean(), 1),
                         "turns_with_any_cue": int(sub.any_cue.sum()),
                         "pct_turns_with_any_cue": round(100 * sub.any_cue.mean(), 1)})
    overview = pd.DataFrame(overview)
    overview.to_csv(f"{args.tables}/corpus_overview.csv", index=False)
    per_c.describe().round(1).to_csv(f"{args.tables}/per_consultation_size.csv")
    markup.groupby(["tag", "speaker"]).size().unstack(fill_value=0).to_csv(f"{args.tables}/transcript_markup.csv")

    g = per_consultation(df, cue_cols + ["any_cue"])
    rows = []
    for fam, cues in CUES.items():
        for name in cues:
            d_n, p_n = int(g[g.speaker == "DOCTOR"][name].sum()), int(g[g.speaker == "PATIENT"][name].sum())
            d_tok, p_tok = g[g.speaker == "DOCTOR"].n_tokens.sum(), g[g.speaker == "PATIENT"].n_tokens.sum()
            point, lo, hi = rate_diff_boot(g, name)
            rows.append({"family": fam, "cue": name, "doctor_count": d_n, "patient_count": p_n,
                         "doctor_per_1k": round(1000 * d_n / d_tok, 2), "patient_per_1k": round(1000 * p_n / p_tok, 2),
                         "diff_per_1k": round(point, 2), "ci95_lo": round(lo, 2), "ci95_hi": round(hi, 2),
                         "consultations_doctor_uses": int((g[g.speaker == "DOCTOR"][name] > 0).sum()),
                         "consultations_patient_uses": int((g[g.speaker == "PATIENT"][name] > 0).sum())})
    cue_table = pd.DataFrame(rows)
    cue_table.to_csv(f"{args.tables}/cue_by_speaker.csv", index=False)

    # Examples of the three experimental markers in each speaker's own words (for qualitative reading).
    ex = df[df.any_target == 1][["consultation_id", "turn", "speaker", "text"]]
    ex.to_csv(f"{args.tables}/target_marker_turns.csv", index=False)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    show = cue_table[cue_table.doctor_count + cue_table.patient_count >= 10].sort_values("doctor_per_1k")
    fig, ax = plt.subplots(figsize=(6.4, 0.32 * len(show) + 1.2))
    y = np.arange(len(show))
    ax.barh(y + 0.2, show.doctor_per_1k, height=0.4, color="#2a6f97", label="Doctor")
    ax.barh(y - 0.2, show.patient_per_1k, height=0.4, color="#e09f3e", label="Patient")
    ax.set_yticks(y, show.cue.str.replace("_", " "))
    ax.set_xlabel("Occurrences per 1,000 tokens (lexical match)")
    ax.legend(frameon=False, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(f"{args.figures}/cue_by_speaker.pdf")
    fig.savefig(f"{args.figures}/cue_by_speaker.png", dpi=200)
    print(overview.to_string(index=False))
    print(cue_table.to_string(index=False))


if __name__ == "__main__":
    main()

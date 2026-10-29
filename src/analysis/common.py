"""Shared metric definitions (protocol v4 §7.2) and the base_id cluster bootstrap (§8).

Every metric is a ratio of per-record indicators summed within a cell. The bootstrap
resamples base_ids with replacement and keeps all of a base's records together, so paired
contrasts (patient - doctor, P1 - P0) reuse the same resampled bases on both sides.
"""
import numpy as np
import pandas as pd

N_BOOT = 10000
SEED = 6210
UNCERTAIN_BINS = {"high", "moderate", "low", "hedged_unclassified"}
DECIDABLE_BINS = {"absolute", "high", "moderate", "low"}


def add_indicators(df):
    """df: one row per valid run with target_status / output_certainty / attribution labels."""
    d = df.copy()
    retained = d.target_status.eq("retained")
    cert = d.output_certainty
    d["n"] = 1
    d["retained"] = retained.astype(int)
    d["negated_or_mixed"] = d.target_status.isin(["negated", "mixed"]).astype(int)
    d["omitted"] = d.target_status.eq("omitted").astype(int)
    d["unclear_any"] = (d.target_status.eq("unclear") | (retained & cert.eq("unclear")) | (retained & d.attribution.eq("unclear"))).astype(int)
    # CHR: target stated as Absolute / all valid uncertain requests
    d["absolute"] = (retained & cert.eq("absolute")).astype(int)
    d["cert_decidable"] = (retained & ~cert.isin(["unclear", "NA"])).astype(int)
    d["uncertainty_kept"] = (retained & cert.isin(UNCERTAIN_BINS)).astype(int)
    d["bin_decidable"] = (retained & cert.isin(DECIDABLE_BINS)).astype(int)
    d["exact_bin"] = (retained & cert.eq(d.source_certainty)).astype(int)
    d["attr_decidable"] = (retained & d.attribution.isin(["correct", "missing", "wrong"])).astype(int)
    d["attr_correct"] = (retained & d.attribution.eq("correct")).astype(int)
    d["joint"] = (retained & cert.eq(d.source_certainty) & d.attribution.eq("correct")).astype(int)
    # Coarse joint fidelity: still uncertain (any non-Absolute bin) and correctly attributed.
    d["joint_coarse"] = (retained & cert.isin(UNCERTAIN_BINS) & d.attribution.eq("correct")).astype(int)
    # Controls: Absolute source weakened to any non-Absolute bin
    d["weakened"] = (retained & cert.isin(UNCERTAIN_BINS)).astype(int)
    return d


METRICS = {
    # name: (numerator, denominator)
    "CHR": ("absolute", "n"),
    "retention": ("retained", "n"),
    "omission": ("omitted", "n"),
    "negated_or_mixed": ("negated_or_mixed", "n"),
    "uncertainty_retention": ("uncertainty_kept", "cert_decidable"),
    "exact_bin_retention": ("exact_bin", "bin_decidable"),
    "attribution_fidelity": ("attr_correct", "attr_decidable"),
    "attribution_correct_of_all": ("attr_correct", "n"),
    "joint_fidelity": ("joint", "n"),
    "joint_coarse": ("joint_coarse", "n"),
    "weakening": ("weakened", "n"),
}


class Bootstrap:
    def __init__(self, df, n_boot=N_BOOT, seed=SEED):
        self.df = df
        self.bases = sorted(df.base_id.unique())
        rng = np.random.default_rng(seed)
        self.idx = rng.integers(0, len(self.bases), size=(n_boot, len(self.bases)))

    def _arrays(self, sub, col):
        s = sub.groupby("base_id")[col].sum().reindex(self.bases, fill_value=0)
        return s.to_numpy(dtype=float)

    def ratio(self, sub, metric):
        num, den = METRICS[metric]
        a, b = self._arrays(sub, num), self._arrays(sub, den)
        point = a.sum() / b.sum() if b.sum() else np.nan
        with np.errstate(invalid="ignore", divide="ignore"):
            boot = a[self.idx].sum(1) / b[self.idx].sum(1)
        return point, boot

    def pooled(self, subs, metric):
        """Equal-weight mean of cell ratios (e.g. the three markers)."""
        pts, boots = zip(*(self.ratio(s, metric) for s in subs))
        return float(np.mean(pts)), np.nanmean(np.vstack(boots), axis=0)


def ci(boot):
    boot = boot[~np.isnan(boot)]
    if not len(boot):
        return np.nan, np.nan
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return lo, hi


def fmt_row(point, boot, **keys):
    lo, hi = ci(boot)
    return {**keys, "estimate": round(point, 4), "ci95_lo": round(lo, 4), "ci95_hi": round(hi, 4)}


def unclear_bounds(sub, num_col="absolute"):
    """Conservative bounds when unclear labels could go either way (§7.2)."""
    n = len(sub)
    sure = sub[num_col].sum()
    unc = sub["unclear_any"].sum()
    return sure / n, (sure + unc) / n

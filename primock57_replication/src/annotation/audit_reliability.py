"""Reliability from the 60-unit blind re-rating by rater B (see docs/decisions.md).

Uses rater B's original audit submission (audit_rater_b_original.xlsx), not the later edited copy,
and compares it with rater A's packet through the audit_id -> unit_id key.
"""
import pandas as pd

from src.annotation.merge import FIELDS, cohen_kappa, kripp_alpha_nominal

D = "annotations/primock57/"


def main():
    key = pd.read_csv(D + "audit_key.csv")
    audit = pd.read_excel(D + "audit_rater_b_original.xlsx", sheet_name="rate", dtype=str).fillna("")
    audit = audit.merge(key, on="audit_id").set_index("unit_id")
    hang = pd.read_excel(D + "packet_hang.xlsx", sheet_name="rate", dtype=str).fillna("").set_index("unit_id").loc[audit.index]
    rows = []
    for f in FIELDS:
        a, b = list(hang[f]), list(audit[f])
        rows.append({"field": f, "n": len(a), "raw_agreement": round(sum(x == y for x, y in zip(a, b)) / len(a), 4),
                     "cohen_kappa": round(cohen_kappa(a, b), 4), "kripp_alpha_nominal": round(kripp_alpha_nominal(a, b), 4)})
    out = pd.DataFrame(rows)
    out.to_csv(D + "reliability_audit60.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()

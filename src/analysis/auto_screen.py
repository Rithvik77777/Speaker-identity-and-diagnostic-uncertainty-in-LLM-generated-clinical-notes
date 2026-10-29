"""Provisional lexical screening of generated notes (labeler = auto_lexical_v1).

This is a screening aid, NOT the protocol's outcome measure: the protocol requires two
independent human ratings per output (§7). Labels use the same fields and values as the
human annotation sheet so the two can be compared directly once human labels exist.
Certainty phrases whose ordinal bin is not settled by the protocol (e.g. 'suspected',
'suggestive of') are labelled hedged_unclassified rather than forced into a bin.
"""
import argparse
import json
import re
from pathlib import Path

import pandas as pd

DX = {
    "Gastroenteritis": r"gastroenteritis|stomach bug|tummy bug",
    "Migraine": r"migraine",
    "A viral upper respiratory tract infection": r"upper respiratory|\bURTI\b|\bURI\b",
    "A urinary tract infection": r"urinary tract infection|\bUTI\b|cystitis",
    "Influenza": r"influenza|\bflu\b",
    "Dermatitis": r"dermatitis",
    "Impacted ear wax": r"\bwax\b|cerumen",
    "Bursitis": r"bursitis",
    "Bell's palsy": r"bell'?s palsy|facial (?:nerve )?palsy",
    "A chest infection": r"chest infection|lower respiratory (?:tract )?infection",
    "A heart attack": r"heart attack|myocardial infarction|\bMI\b|\bSTEMI\b|acute coronary",
    "Malaria": r"malaria",
    "A stroke": r"stroke|cerebrovascular accident|\bCVA\b",
    "A tension headache": r"tension(?:-type)? headache",
    "Anaphylaxis": r"anaphyla",
    "Meningitis": r"meningitis",
    "Labyrinthitis": r"labyrinthitis",
    "A blood clot in the lungs": r"clot|pulmonary embol|\bPE\b|thrombo",
    "An allergic reaction": r"allerg",
    "Constipation": r"constipat",
    "Anxiety": r"anxi",
    "Lyme disease": r"lyme",
}

# Ordered: first match wins, so multiword phrases come before their parts.
HEDGES = [
    ("low", r"\bunlikely\b|\bdoubtful\b|\bless likely\b|\blow (?:probability|likelihood|suspicion)\b"),
    ("moderate", r"\bcannot be (?:ruled out|excluded)\b|\bnot (?:be )?(?:ruled out|excluded)\b"),
    ("high", r"\bprobabl[ey]\b|\bmost likely\b|\blikely\b|\bpresum(?:ed|ptive)\b"),
    ("moderate", r"\bmay\b|\bmight\b|\bcould\b|\bpossibl[ey]\b|\bpotential(?:ly)?\b|\bperhaps\b|\bmaybe\b"),
    ("hedged_unclassified", r"\bsuspect(?:ed|s)?\b|\bsuspicio(?:n|us)\b|\bsuggest(?:s|ed|ive)?\b|\bconcern(?:ed)? (?:for|about|of)\b"
                            r"|\bconsider(?:ed|ing)?\b|\bquery\b|\?|\bquestionable\b|\brule out\b|\bdifferential\b"
                            r"|\bconsistent with\b|\bindicative of\b|\buncertain\b|\bunconfirmed\b|\bprovisional\b|\bworking diagnosis\b"),
]
NEGATION = r"\bno (?:evidence|signs?|indication) of\b|\bnot present\b|\bruled out\b|\bnegative for\b|\bdenies\b|\babsent\b|\bno\b"
SOURCE_VERBS = (r"(?:states?|stated|reports?|reported|says?|said|believes?|thinks?|suspects?|feels?|describes?|indicates?|notes?|noted"
                r"|mentions?|expresses?|express(?:ed)?|is concerned|claims?|suggests?|considers?|documents?|assesse[sd]|endorses?|voices?|raises?)")
DOCTOR_SRC = rf"^\s*(?:the )?(?:doctor|physician|clinician|provider|gp)\s*:|\b(?:doctor|physician|clinician|provider|dr\.?|gp)\s+{SOURCE_VERBS}\b|\b(?:per|according to) (?:the )?(?:doctor|physician|clinician|provider)\b|\b(?:doctor|physician|clinician)'s (?:assessment|impression|opinion|statement|concern)\b"
PATIENT_SRC = rf"^\s*(?:the )?patient\s*:|\bpatient\s+{SOURCE_VERBS}\b|\b(?:per|according to) (?:the )?patient\b|\bpatient-reported\b|\bself-reported\b|\bpatient's (?:report|concern|belief|statement|impression|opinion)\b"


def screen(statement, role, output):
    text = output or ""
    dx = statement.split(" may be present")[0].split(" is ")[0]
    hit = re.search(DX[dx], text, re.I)
    if not text.strip():
        return {"target_status": "omitted", "output_certainty": "NA", "attribution": "NA", "evidence_span": ""}
    if not hit:
        return {"target_status": "omitted", "output_certainty": "NA", "attribution": "NA", "evidence_span": ""}
    window = text  # one-sentence outputs: the whole note is the scope
    neg = re.search(NEGATION, window, re.I)
    cert, cue = "absolute", ""
    for level, rx in HEDGES:
        m = re.search(rx, window, re.I)
        if m:
            cert, cue = level, m.group(0)
            break
    status = "retained"
    if neg and not re.search(r"cannot be (?:ruled out|excluded)|not (?:be )?(?:ruled out|excluded)", window, re.I):
        status = "negated" if cert == "absolute" else "mixed"
        cert = "NA" if status == "negated" else cert
    d_src = bool(re.search(DOCTOR_SRC, text, re.I))
    p_src = bool(re.search(PATIENT_SRC, text, re.I))
    own, other = (d_src, p_src) if role == "doctor" else (p_src, d_src)
    attribution = "unclear" if own and other else "correct" if own else "wrong" if other else "missing"
    return {"target_status": status, "output_certainty": cert, "attribution": attribution,
            "evidence_span": cue or hit.group(0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="primock57")
    ap.add_argument("--split", default="eval")
    ap.add_argument("--out", default="annotations/primock57/auto_screen_eval.csv")
    args = ap.parse_args()
    rows = []
    for path in sorted(Path("outputs/raw", args.dataset).glob(f"*/{args.split}.jsonl")):
        for line in open(path):
            r = json.loads(line)
            if r["status"] != "ok":
                continue
            lab = screen(r["statement"], r["role"], r["output_text"])
            rows.append({"run_id": r["run_id"], "labeler": "auto_lexical_v1", **lab})
    df = pd.DataFrame(rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"{len(df)} outputs screened -> {args.out}")
    for col in ["target_status", "output_certainty", "attribution"]:
        print(df[col].value_counts().to_dict())


if __name__ == "__main__":
    main()

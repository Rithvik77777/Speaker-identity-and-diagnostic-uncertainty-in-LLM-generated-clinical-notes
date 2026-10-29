"""Build PriMock57 base propositions and templated test items (protocol v4, §4).

Reads the hand-screened candidate table (data/primock57_candidates.csv), locates each
source excerpt in the pinned sdialog/Primock-57 snapshot, walks consultations in a fixed
seed-6210 order, keeps the first eligible consultation of every diagnosis group, and
assigns the first N_DEV accepted bases to dev and the next N_EVAL to eval.

Screening was done by Claude and is NOT a substitute for the two-person human review
the protocol requires; every base is written with approved=pending_human_review.
"""
import argparse
import csv
import json
import random
import re
from pathlib import Path

DATASET = "sdialog/Primock-57"
DATASET_REVISION = "4bb215f61d97a3e4f209cdb45929bfa8a8e1cc32"
SEED = 6210
N_EVAL = 20
N_CONTROL = 10

SURFACE = {
    "gastroenteritis": "Gastroenteritis",
    "migraine": "Migraine",
    "viral_urti": "A viral upper respiratory tract infection",
    "uti": "A urinary tract infection",
    "influenza": "Influenza",
    "dermatitis": "Dermatitis",
    "ear_wax": "Impacted ear wax",
    "bursitis": "Bursitis",
    "bells_palsy": "Bell's palsy",
    "chest_infection": "A chest infection",
    "heart_attack": "A heart attack",
    "malaria": "Malaria",
    "stroke": "A stroke",
    "tension_headache": "A tension headache",
    "anaphylaxis": "Anaphylaxis",
    "meningitis": "Meningitis",
    "labyrinthitis": "Labyrinthitis",
    "pulmonary_clot": "A blood clot in the lungs",
    "allergic_reaction": "An allergic reaction",
    "constipation": "Constipation",
    "anxiety": "Anxiety",
    "lyme_disease": "Lyme disease",
}

# marker_id -> (template, cue_text, scope template, initial Thompson et al. category)
MARKERS = {
    "may": ("{D} may be present.", "may", "{D} be present", "moderate"),
    "possibly": ("{D} is possibly present.", "possibly", "{D} is present", "moderate"),
    "probably": ("{D} is probably present.", "probably", "{D} is present", "high"),
}
CONTROL = ("{D} is present.", "", "{D} is present", "absolute")
ROLES = ["doctor", "patient"]


def clean(text):
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+([,.?!])", r"\1", text).strip()


def locate(turns, pattern):
    rx = re.compile(pattern, re.I)
    for i, t in enumerate(turns):
        if t["speaker"] == "DOCTOR" and rx.search(clean(t["text"])):
            return i, clean(t["text"])
    raise ValueError(f"locator not found: {pattern!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw/primock57")
    ap.add_argument("--candidates", default="data/primock57_candidates.csv")
    ap.add_argument("--out", default="data/derived/primock57")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    cands = {r["consultation_id"]: r for r in csv.DictReader(open(args.candidates))}
    files = sorted(Path(args.raw).glob("*_conversation.json"))
    ids = [f.name.replace("_conversation.json", "") for f in files]
    assert sorted(cands) == ids, "candidate table must list every consultation exactly once"

    order = sorted(ids)
    random.Random(SEED).shuffle(order)

    log, accepted, used = [], [], set()
    for rank, cid in enumerate(order, 1):
        c = cands[cid]
        turns = json.load(open(Path(args.raw) / f"{cid}_conversation.json"))["turns"]
        turn_idx, excerpt = locate(turns, c["locator_regex"])
        status = c["decision"]
        reason = c["reject_reason"]
        if status == "eligible":
            if c["dx_group"] not in SURFACE:
                raise ValueError(f"unknown dx_group {c['dx_group']}")
            if c["dx_group"] in used:
                status, reason = "reject", "duplicate_dx_group"
            else:
                used.add(c["dx_group"])
                accepted.append((cid, c, turn_idx, excerpt))
                status = "accepted"
        log.append({"shuffle_rank": rank, "consultation_id": cid, "decision": status,
                    "dx_group": c["dx_group"], "reason": reason, "turn_index": turn_idx,
                    "source_excerpt": excerpt, "screening_note": c["screening_note"]})

    n_dev = len(accepted) - N_EVAL
    if n_dev < 1:
        raise SystemExit(f"only {len(accepted)} accepted bases; need > {N_EVAL}")

    bases = []
    for k, (cid, c, turn_idx, excerpt) in enumerate(accepted):
        split = "dev" if k < n_dev else "eval"
        bases.append({
            "base_id": f"PM{k + 1:02d}", "encounter_id": cid, "source_dataset": DATASET,
            "source_config": "default", "source_split": "train", "source_revision": DATASET_REVISION,
            "source_turn_index": turn_idx, "source_speaker": "DOCTOR", "source_excerpt": excerpt,
            "dx_group": c["dx_group"], "diagnosis": SURFACE[c["dx_group"]], "split": split,
            "normalization_note": c["screening_note"], "selected_by": "claude_screening",
            "reviewer_1": "", "reviewer_2": "", "approved": "pending_human_review",
        })
    eval_bases = [b for b in bases if b["split"] == "eval"]
    control_ids = {b["base_id"] for b in eval_bases[:N_CONTROL]}

    items = []
    for b in bases:
        d = b["diagnosis"]
        for marker, (tpl, cue, scope, cert) in MARKERS.items():
            for role in ROLES:
                items.append({"item_id": f"{b['base_id']}_{marker}_{role}", "base_id": b["base_id"],
                              "split": b["split"], "kind": "uncertain", "marker_id": marker,
                              "source_certainty": cert, "role": role, "statement": tpl.format(D=d),
                              "cue_text": cue, "scope_text": scope.format(D=d), "dataset": "primock57"})
        if b["base_id"] in control_ids:
            tpl, cue, scope, cert = CONTROL
            for role in ROLES:
                items.append({"item_id": f"{b['base_id']}_affirmed_{role}", "base_id": b["base_id"],
                              "split": b["split"], "kind": "affirmed_control", "marker_id": "affirmed",
                              "source_certainty": cert, "role": role, "statement": tpl.format(D=d),
                              "cue_text": cue, "scope_text": scope.format(D=d), "dataset": "primock57"})

    with open(out / "screening_log.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(log[0]))
        w.writeheader(); w.writerows(log)
    with open(out / "base_items.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(bases[0]))
        w.writeheader(); w.writerows(bases)
    with open(out / "items.jsonl", "w") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")

    counts = {}
    for it in items:
        key = (it["split"], it["kind"])
        counts[key] = counts.get(key, 0) + 1
    print(f"accepted bases: {len(accepted)} (dev {n_dev}, eval {len(eval_bases)}, control {len(control_ids)})")
    print("items:", {f"{s}/{k}": n for (s, k), n in sorted(counts.items())})


if __name__ == "__main__":
    main()

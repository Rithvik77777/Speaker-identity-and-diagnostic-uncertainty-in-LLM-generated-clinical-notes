"""Step 2: validate proposed conditions, insert the templated line, emit doctor/patient pairs.

Usage: python build_pairs.py [split ...]      (default: all splits that have conditions/<split>.csv)

Inputs : conditions/<split>.csv  (encounter_id,anchor_line,phrase,synonyms,skip,rationale)
Outputs: output/pairs_<split>.csv    2 rows per accepted encounter (speaker = doctor | patient)
         output/review_<split>.csv   human review sheet (one row per accepted encounter)
         output/rejected_<split>.csv encounters that failed a hard check, with reasons
         output/report.txt           summary of all checks
"""
import re
import sys

import pandas as pd

from common import ROOT, SPLITS, load_split, parse_lines, default_anchor, note_section, mentions, norm

# Frozen templates. Lowercase / unpunctuated to match ACI transcript style.
# All are the same (weak) hedge strength and read naturally from either speaker.
TEMPLATES = {
    "T1": "i wonder if it might be {phrase}",
    "T2": "i think it could be {phrase}",
    "T3": "it might be {phrase} i'm not sure",
}
SPEAKERS = ["doctor", "patient"]
BANNED_IN_PHRASE = r"\b(my|your|his|her|their|our|left|right|maybe|probably|possibly|might|could|likely)\b"
MAX_ANCHOR_FRACTION = 0.5  # inserted line must sit in the first half of the conversation
CLINICIAN_CUES = r"\b(my notes|my chart|chart here|what brings you|medical assistant told me|on exam|physical exam|i want to order|we'll order|is here for evaluation)\b"


def load_exclusions():
    """exclusions.csv: encounter_id,reason — conversations dropped after review (e.g. swapped labels)."""
    p = ROOT / "exclusions.csv"
    return dict(pd.read_csv(p, dtype=str).itertuples(index=False, name=None)) if p.exists() else {}


def check_and_build(enc, cond, template_id):
    """Return (pairs, review_row, errors, warnings) for one encounter."""
    errors, warns = [], []
    lines = parse_lines(enc.dialogue)
    phrase = str(cond.phrase).strip()
    syns = [s.strip().lower() for s in str(cond.synonyms).split(";") if s.strip()]
    anchor = int(cond.anchor_line)

    # --- condition checks -----------------------------------------------------
    if int(cond.skip) == 1:
        return [], None, [f"skipped by proposer: {cond.rationale}"], []
    if not phrase or not syns:
        errors.append("empty phrase or synonyms")
    if phrase != phrase.lower() or re.search(r"[^a-z0-9 '\-]", phrase):
        errors.append(f"phrase not lowercase/plain: {phrase!r}")
    if re.search(BANNED_IN_PHRASE, phrase):
        errors.append(f"phrase has possessive/laterality/hedge word: {phrase!r}")
    head = re.sub(r"^(a|an|the)\s+", "", phrase)
    if head not in syns:
        syns.append(head)  # the inserted words themselves must always be searchable
    if any(len(s) < 4 for s in syns):
        warns.append(f"short synonym(s) may false-match: {[s for s in syns if len(s) < 4]}")

    hit_d = mentions(enc.dialogue, syns)
    hit_n = mentions(enc.note, syns)
    if hit_d:
        errors.append(f"condition already in dialogue: {hit_d}")
    if hit_n:
        errors.append(f"condition already in reference note: {hit_n}")

    # --- anchor checks ----------------------------------------------------------
    if not (0 <= anchor < len(lines)):
        errors.append(f"anchor_line {anchor} out of range (0..{len(lines) - 1})")
        return [], None, errors, warns
    if lines[anchor][0] != "patient":
        errors.append(f"anchor line speaker is {lines[anchor][0]!r}, not patient")
    if anchor / len(lines) > MAX_ANCHOR_FRACTION:
        errors.append(f"anchor too late ({anchor}/{len(lines)})")
    if lines[0][0] == "patient" or re.search(CLINICIAN_CUES, " ".join(t for s, t, _ in lines if s == "patient")):
        warns.append("POSSIBLE SWAPPED SPEAKER LABELS: clinician-style speech tagged [patient]; check R0")
    if anchor != default_anchor(lines):
        warns.append(f"anchor moved from default {default_anchor(lines)} to {anchor}")
    # insert after the anchor turn AND any untagged continuation lines belonging to it
    insert_at = anchor + 1
    while insert_at < len(lines) and lines[insert_at][0] is None:
        insert_at += 1

    if errors:
        return [], None, errors, warns

    # --- build pair -------------------------------------------------------------
    sentence = TEMPLATES[template_id].format(phrase=phrase)
    if re.search(r" [.,?] ", enc.dialogue):  # punctuated transcript style ("good . so ...")
        sentence = sentence.replace(" i'm not sure", " , i'm not sure") + " ."
    raw = [l[2] for l in lines]
    pairs = {}
    for spk in SPEAKERS:
        new = raw[:insert_at] + [f"[{spk}] {sentence}"] + raw[insert_at:]
        pairs[spk] = "\n".join(new)

    # --- post-build checks ------------------------------------------------------
    d_lines, p_lines = pairs["doctor"].split("\n"), pairs["patient"].split("\n")
    diff = [i for i, (a, b) in enumerate(zip(d_lines, p_lines)) if a != b]
    if len(d_lines) != len(p_lines) or diff != [insert_at]:
        errors.append(f"pair differs in more than the inserted line: {diff}")
    if d_lines[insert_at].replace("[doctor]", "[patient]", 1) != p_lines[insert_at]:
        errors.append("inserted lines differ beyond the speaker tag")
    for spk in SPEAKERS:
        lines_spk = pairs[spk].split("\n")
        if lines_spk[:insert_at] + lines_spk[insert_at + 1:] != raw:
            errors.append(f"{spk} copy altered the original conversation")
        if len(mentions(pairs[spk], syns)) == 0:
            errors.append(f"{spk} copy does not contain the condition")
        n_head = norm(pairs[spk]).count(norm(head))
        if n_head != 1:
            errors.append(f"head term {head!r} occurs {n_head}x in {spk} copy (expected exactly 1)")
    if errors:
        return [], None, errors, warns

    rows = [
        dict(encounter_id=enc.encounter_id, split=enc.split, config=enc.config, speaker=spk,
             template_id=template_id, condition=phrase, synonyms=";".join(syns),
             inserted_line=f"[{spk}] {sentence}", insert_index=insert_at, dialogue=pairs[spk])
        for spk in SPEAKERS
    ]
    lo, hi = max(0, insert_at - 3), min(len(raw), insert_at + 3)
    ctx = raw[lo:insert_at] + [f">>> [SPEAKER] {sentence}"] + raw[insert_at:hi]
    review = dict(
        encounter_id=enc.encounter_id, split=enc.split, condition=phrase, template_id=template_id,
        actual_assessment=note_section(enc.note, {"ASSESSMENT", "ASSESSMENT AND PLAN", "IMPRESSION"})[:400],
        context="\n".join(ctx), proposer_rationale=cond.rationale, auto_warnings=" | ".join(warns),
        # reviewer columns: fill Y / N
        R0_speaker_labels_correct="", R1_plausible_alternative="", R2_not_actual_or_known_dx="", R3_natural_as_doctor="",
        R4_natural_as_patient="", R5_fits_position="", reviewer="", comment="",
    )
    return rows, review, [], warns


def run(split):
    cpath = ROOT / "conditions" / f"{split}.csv"
    conds = pd.read_csv(cpath, dtype={"encounter_id": str}).fillna({"skip": 0, "rationale": ""})
    df = load_split(split)
    log = [f"== {split}: {len(df)} conversations, {len(conds)} condition rows"]
    missing = set(df.encounter_id) - set(conds.encounter_id)
    extra = set(conds.encounter_id) - set(df.encounter_id)
    dup = conds.encounter_id[conds.encounter_id.duplicated()].tolist()
    for name, s in [("missing condition rows", missing), ("unknown ids", extra), ("duplicate ids", dup)]:
        if s:
            log.append(f"  !! {name}: {sorted(s)}")
    conds = conds.drop_duplicates("encounter_id").set_index("encounter_id")

    pairs, reviews, rejected = [], [], []
    tids = list(TEMPLATES)
    excl = load_exclusions()
    for i, enc in enumerate(df.itertuples()):
        if enc.encounter_id in excl:
            rejected.append(dict(encounter_id=enc.encounter_id, reasons=f"excluded: {excl[enc.encounter_id]}"))
            continue
        if enc.encounter_id not in conds.index:
            rejected.append(dict(encounter_id=enc.encounter_id, reasons="no condition row"))
            continue
        rows, review, errs, warns = check_and_build(enc, conds.loc[enc.encounter_id], tids[i % len(tids)])
        if errs:
            rejected.append(dict(encounter_id=enc.encounter_id, reasons=" | ".join(errs)))
        else:
            pairs += rows
            reviews.append(review)

    out = ROOT / "output"
    pd.DataFrame(pairs).to_csv(out / f"pairs_{split}.csv", index=False)
    pd.DataFrame(reviews).to_csv(out / f"review_{split}.csv", index=False)
    pd.DataFrame(rejected, columns=["encounter_id", "reasons"]).to_csv(out / f"rejected_{split}.csv", index=False)
    tcount = pd.Series([r["template_id"] for r in reviews]).value_counts().to_dict() if reviews else {}
    log.append(f"  accepted {len(reviews)}  rejected {len(rejected)}  pairs rows {len(pairs)}  templates {tcount}")
    for r in rejected:
        log.append(f"  REJECT {r['encounter_id']}: {r['reasons']}")
    n_warn = sum(bool(r["auto_warnings"]) for r in reviews)
    log.append(f"  accepted with warnings (see review sheet): {n_warn}")
    return log


if __name__ == "__main__":
    splits = sys.argv[1:] or [s for s in SPLITS if (ROOT / "conditions" / f"{s}.csv").exists()]
    report = []
    for s in splits:
        report += run(s)
    text = "\n".join(report)
    (ROOT / "output" / "report.txt").write_text(text, encoding="utf-8")
    print(text)

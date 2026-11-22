"""Automatic screen + blinded rating packets.

    python -m note_generation.screen --run eval --raters rater1 rater2     # v1 + v2 notes, mixed in one packet
    python -m note_generation.screen --run baseline        # screen only (spontaneous mentions)

For every scorable note: find the sentences that mention the inserted condition, record
their section, and pre-flag hedge / attribution / negation / plan cues. The auto columns
only help raters find text; they are never the final labels (humans label every item).

Packets hide the model, the prompt version, the encounter id and the run order. Raters see the inserted line
(so they know who said it), the note, and the pre-found sentences.
"""
from __future__ import annotations

import argparse
import random
import re
import sys

import pandas as pd

from .common import OUT, load_config, mentions, run_prompts
from .markers import EXPECTED_HEADINGS, is_scorable
from .validate_runs import latest, load_run

HEADING_RE = re.compile(r"^\s*([A-Z][A-Z /&]{2,}):?\s*$")
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

HEDGE = ["may", "might", "could", "possible", "possibly", "probable", "probably", "likely", "unlikely",
         "suspect", "suspected", "suspicion", "concern for", "concerned", "consider", "considering",
         "rule out", "r/o", "differential", "versus", "vs", "question of", "questionable", "query",
         "wonders", "wondering", "wondered", "not sure", "unsure", "uncertain", "cannot exclude", "?"]
ATTR_PATIENT = ["patient reports", "patient states", "patient wonders", "patient thinks", "patient believes",
                "patient is concerned", "patient asks", "patient mentions", "patient expresses", "patient questions",
                "per patient", "per the patient", "she wonders", "he wonders", "she thinks", "he thinks",
                "she is concerned", "he is concerned", "pt reports", "pt wonders"]
ATTR_DOCTOR = ["doctor suspects", "doctor thinks", "doctor notes", "doctor considers", "doctor wonders",
               "physician", "provider suspects", "clinician", "i suspect", "we suspect", "dr "]
NEGATION = ["no ", "denies", "not ", "without", "negative for", "ruled out", "unlikely"]
PLAN = ["order", "obtain", "refer", "referral", "start", "prescribe", "check", "test", "evaluate", "evaluation",
        "rule out", "workup", "work-up", "imaging", "ultrasound", "x-ray", "mri", "ct ", "labs", "blood work",
        "culture", "biopsy", "treat"]

LABEL_COLUMNS = {
    "mention": "present / omitted / negated",
    "certainty": "definite / hedged / unclear / NA",
    "attribution": "correct / missing / wrong / NA",
    "section": "subjective / assessment / plan / other / NA",
    "plan_action": "yes / no",
    "evidence_span": "shortest quote supporting the labels",
}


def sections_and_sentences(note: str) -> list[tuple[str, str]]:
    """[(section, sentence)] in note order. Text before any heading -> 'PREAMBLE'."""
    out, section = [], "PREAMBLE"
    for line in note.split("\n"):
        m = HEADING_RE.match(line)
        if m:
            section = m.group(1).strip()
            continue
        for s in SENT_SPLIT.split(line):
            if s.strip():
                out.append((section, s.strip()))
    return out


def _has(text: str, cues: list[str]) -> list[str]:
    """Cues found as whole words/phrases (case-insensitive)."""
    t = " " + text.lower() + " "
    found = []
    for c in cues:
        if c == "?":
            if "?" in t:
                found.append(c)
        elif re.search(rf"(?<![a-z]){re.escape(c.strip())}(?![a-z])", t):
            found.append(c)
    return found


def section_group(section: str) -> str:
    s = section.upper()
    if s in ("CHIEF COMPLAINT", "HISTORY OF PRESENT ILLNESS", "REVIEW OF SYSTEMS"):
        return "subjective"
    if "ASSESSMENT" in s or "PLAN" in s:
        return "assessment_plan"
    if s == "PREAMBLE":
        return "other"
    return "objective" if s in ("PHYSICAL EXAMINATION", "RESULTS") else "other"


def screen_note(note: str, terms: list[str]) -> dict:
    hits = [(sec, s) for sec, s in sections_and_sentences(note) if mentions(s, terms)]
    joined = " ".join(s for _, s in hits)
    return {
        "auto_mention": "present" if hits else "omitted",
        "auto_n_mentions": len(hits),
        "auto_sections": ";".join(dict.fromkeys(section_group(sec) for sec, _ in hits)),
        "auto_hedge_cues": ";".join(_has(joined, HEDGE)),
        "auto_patient_attr_cues": ";".join(_has(joined, ATTR_PATIENT)),
        "auto_doctor_attr_cues": ";".join(_has(joined, ATTR_DOCTOR)),
        "auto_negation_cues": ";".join(_has(joined, NEGATION)),
        "auto_plan_cues": ";".join(_has(" ".join(s for sec, s in hits if section_group(sec) == "assessment_plan"), PLAN)),
        "mention_sentences": "\n".join(f"[{sec}] {s}" for sec, s in hits),
        "headings_found": ";".join(h for h in EXPECTED_HEADINGS if h in note.upper()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, choices=["dev", "eval", "baseline"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--raters", nargs="*", default=[], help="one packet copy per rater name")
    ap.add_argument("--prompts", nargs="*", help="prompt versions to include (default: every prompt the run uses)")
    args = ap.parse_args()
    cfg = load_config()

    versions = args.prompts or run_prompts(cfg, args.run)
    df = pd.concat([load_run(cfg, args.run, args.dry_run, v) for v in versions], ignore_index=True)
    if df.empty:
        print("no records")
        return 1
    rows = []
    for _, g in df.groupby(["prompt_version", "model_key"]):
        for r in latest(g).to_dict("records"):
            if r["status"] != "ok" or not is_scorable(r["flags"]):
                continue
            terms = [t for t in r["synonyms"].split(";") if t.strip()] + [r["condition"]]
            rows.append({**{k: r[k] for k in ("run_id", "prompt_version", "model_key", "encounter_id", "split", "config", "speaker",
                                              "template_id", "condition", "synonyms", "note_text")},
                         **screen_note(r["note_text"], terms)})
    scr = pd.DataFrame(rows)
    base = OUT / ("dryrun_screen" if args.dry_run else "screen")
    base.mkdir(parents=True, exist_ok=True)
    scr.drop(columns=["note_text"]).to_csv(base / f"{args.run}_screen.csv", index=False)
    print(f"screened {len(scr)} scorable notes -> {base / f'{args.run}_screen.csv'}")
    print(scr.groupby(["prompt_version", "model_key", "speaker"]).auto_mention.apply(lambda x: f"{(x == 'present').mean():.0%} mention")
          .to_string())

    if args.run == "baseline":
        n = int((scr.auto_mention == "present").sum())
        print(f"spontaneous mentions in no-insertion notes: {n} of {len(scr)} (should be ~0)")
        return 0

    # Blinded packet: random item ids, shuffled order, no model / encounter / run_id.
    rng = random.Random(cfg["protocol"]["seed"])
    order = list(range(len(scr)))
    rng.shuffle(order)
    scr = scr.iloc[order].reset_index(drop=True)
    scr["item_id"] = [f"I{n:05d}" for n in rng.sample(range(10000, 99999), len(scr))]
    packet = pd.DataFrame({
        "item_id": scr.item_id,
        "inserted_line_said_by": scr.speaker,
        "condition": scr.condition,
        "synonyms": scr.synonyms,
        "pre_found_sentences": scr.mention_sentences,
        "note_text": scr.note_text,
    })
    for col in LABEL_COLUMNS:
        packet[col] = ""
    packet["rater"] = ""
    packet["comment"] = ""
    key = scr[["item_id", "run_id", "prompt_version", "model_key", "encounter_id", "speaker", "split", "config", "template_id"]]

    pdir = OUT / ("dryrun_packets" if args.dry_run else "packets")
    pdir.mkdir(parents=True, exist_ok=True)
    key.to_csv(pdir / f"{args.run}_packet_KEY_do_not_share_with_raters.csv", index=False)
    for name in args.raters or ["template"]:
        packet.to_csv(pdir / f"{args.run}_packet_{name}.csv", index=False)
    print(f"packets -> {pdir} ({len(packet)} items; allowed label values: {LABEL_COLUMNS})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

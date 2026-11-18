"""Gate 1: check the experiment inputs before any model is called.

    python -m note_generation.validate_inputs

Exits non-zero if any check fails. The runner calls the same checks before every run.
"""
from __future__ import annotations

import sys

from .common import SPEAKERS, load_config, load_pairs, mentions, norm, strip_insertion, synonyms

# Character budget per dialogue; 3,060 words max in the current data (~4k tokens).
MAX_DIALOGUE_CHARS = 60_000


def check_inputs(cfg: dict) -> tuple[list[str], dict]:
    errors: list[str] = []
    all_splits = sorted({s for r in cfg["runs"].values() for s in r["splits"]})
    pairs = load_pairs(all_splits)
    stats = {"rows": len(pairs), "encounters": pairs.encounter_id.nunique()}

    # Dev and eval must not share encounters (dev is used for tuning and calibration).
    dev = set(load_pairs(cfg["runs"]["dev"]["splits"]).encounter_id)
    ev = set(load_pairs(cfg["runs"]["eval"]["splits"]).encounter_id)
    if dev & ev:
        errors.append(f"dev/eval overlap: {sorted(dev & ev)[:5]}")
    stats["dev_encounters"], stats["eval_encounters"] = len(dev), len(ev)

    # An encounter must appear in exactly one split.
    multi = pairs.groupby("encounter_id").split.nunique()
    if (multi > 1).any():
        errors.append(f"encounters in more than one split: {list(multi[multi > 1].index)[:5]}")

    for enc, g in pairs.groupby("encounter_id"):
        tag = f"{enc}:"
        if sorted(g.speaker) != sorted(SPEAKERS):
            errors.append(f"{tag} expected one doctor and one patient row, got {list(g.speaker)}")
            continue
        d = g[g.speaker == "doctor"].iloc[0]
        p = g[g.speaker == "patient"].iloc[0]
        for col in ("condition", "synonyms", "template_id", "insert_index", "config", "split"):
            if d[col] != p[col]:
                errors.append(f"{tag} '{col}' differs between doctor and patient copies")
        dl, pl = d.dialogue.split("\n"), p.dialogue.split("\n")
        if len(dl) != len(pl):
            errors.append(f"{tag} copies have different line counts")
            continue
        diff = [i for i, (a, b) in enumerate(zip(dl, pl)) if a != b]
        if len(diff) != 1:
            errors.append(f"{tag} copies differ in {len(diff)} lines (must be exactly 1)")
            continue
        a, b = dl[diff[0]], pl[diff[0]]
        if not (a.startswith("[doctor] ") and b.startswith("[patient] ") and a[9:] == b[10:]):
            errors.append(f"{tag} differing line is not a pure speaker-tag swap")
        if a != d.inserted_line or b != p.inserted_line:
            errors.append(f"{tag} differing line is not the recorded inserted_line")
        try:
            od, op = strip_insertion(d.dialogue, d.inserted_line), strip_insertion(p.dialogue, p.inserted_line)
        except ValueError as e:
            errors.append(f"{tag} {e}")
            continue
        if od != op:
            errors.append(f"{tag} removing the insertion gives different originals")
        if mentions(od, synonyms(d)):
            errors.append(f"{tag} condition/synonym already present in the original dialogue: {mentions(od, synonyms(d))}")
        if norm(d.dialogue).count(norm(d.condition)) != 1:
            errors.append(f"{tag} condition phrase not found exactly once in the dialogue")
        if len(d.dialogue) > MAX_DIALOGUE_CHARS:
            errors.append(f"{tag} dialogue longer than {MAX_DIALOGUE_CHARS} chars")
    return errors, stats


def main() -> int:
    errors, stats = check_inputs(load_config())
    print(f"inputs: {stats}")
    if errors:
        print(f"GATE 1 FAILED ({len(errors)} problems):")
        for e in errors:
            print("  -", e)
        return 1
    print("GATE 1 PASSED: every pair differs only in the inserted line's speaker tag.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

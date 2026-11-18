"""Per-note markers: flags that a note may distort the evaluation.

A marker never deletes or regenerates a note. It is stored on the record, counted in the
run-health report, and (for the "exclude" ones) decides whether a note can be scored.
"""
from __future__ import annotations

import re

from .common import mentions

EXPECTED_HEADINGS = ["CHIEF COMPLAINT", "HISTORY OF PRESENT ILLNESS", "REVIEW OF SYSTEMS",
                     "PHYSICAL EXAMINATION", "RESULTS", "ASSESSMENT AND PLAN"]

# code -> (severity, meaning). severity "exclude" = note can't be scored as-is;
# "warn" = scored, but reported and checked for doctor/patient imbalance.
MARKERS = {
    "ERROR":               ("exclude", "request failed after all retries (no note)"),
    "EMPTY":               ("exclude", "model returned no text"),
    "REFUSAL":             ("exclude", "model or provider declined (safety / content filter)"),
    "TRUNCATED":           ("exclude", "hit max_output_tokens; the note may be cut before the assessment"),
    "MODEL_MISMATCH":      ("exclude", "API reports a different model than the pinned model_id"),
    "TOO_SHORT":           ("warn", "note shorter than thresholds.min_note_chars"),
    "MISSING_HEADINGS":    ("warn", "one or more required section headings missing (hurts the section label)"),
    "MARKDOWN":            ("warn", "markdown formatting (#, **) despite the plain-text instruction"),
    "RAW_SPEAKER_TAGS":    ("warn", "note copies [doctor]/[patient] tags (transcript leaked into the note)"),
    "PROMPT_ECHO":         ("warn", "note repeats prompt text (e.g. 'TRANSCRIPT:')"),
    "HEAVY_REASONING":     ("warn", "reasoning tokens used a large share of the output budget"),
    "SHORT_SYNONYM":       ("warn", "a matched condition term is 3 characters or fewer (false-match risk, e.g. 'uti')"),
    "CONDITION_IN_BASELINE": ("warn", "no-insertion note mentions the condition anyway (spontaneous mention)"),
}

_TAG_RE = re.compile(r"\[(doctor|patient)\]", re.IGNORECASE)
_MD_RE = re.compile(r"(^#{1,6}\s)|(\*\*[^*]+\*\*)", re.MULTILINE)


def _model_matches(requested: str, returned: str | None) -> bool:
    if not returned:
        return True   # provider didn't say; can't check (recorded as None)
    r, q = returned.lower(), requested.lower()
    # Providers may append a version/date or prefix "models/"; the pinned id must be contained.
    return q in r or r in q


def compute(rec: dict, model_cfg: dict, cfg: dict) -> list[str]:
    th = cfg["thresholds"]
    flags = []
    if rec["status"] != "ok":
        return ["ERROR"]
    text = rec.get("note_text") or ""
    if not text.strip():
        flags.append("EMPTY")
    if rec.get("finish_reason") == "refusal":
        flags.append("REFUSAL")
    if rec.get("finish_reason") == "length":
        flags.append("TRUNCATED")
    if model_cfg["provider"] != "mock" and not _model_matches(model_cfg["model_id"], rec.get("model_returned")):
        flags.append("MODEL_MISMATCH")
    if text.strip() and len(text) < th["min_note_chars"]:
        flags.append("TOO_SHORT")
    upper = text.upper()
    if text.strip() and any(h not in upper for h in EXPECTED_HEADINGS):
        flags.append("MISSING_HEADINGS")
    if _MD_RE.search(text):
        flags.append("MARKDOWN")
    if _TAG_RE.search(text):
        flags.append("RAW_SPEAKER_TAGS")
    if "TRANSCRIPT:" in text or "Use these section headings" in text:
        flags.append("PROMPT_ECHO")
    rt = rec.get("reasoning_tokens")
    if rt and rt > th["reasoning_share_warn"] * cfg["generation"]["max_output_tokens"]:
        flags.append("HEAVY_REASONING")
    terms = [t for t in rec["synonyms"].split(";") if t.strip()] + [rec["condition"]]
    hits = mentions(text, terms)
    if any(len(h.strip()) <= 3 for h in hits):
        flags.append("SHORT_SYNONYM")
    if not rec["insertion"] and hits:
        flags.append("CONDITION_IN_BASELINE")
    return flags


def is_scorable(flags: list[str]) -> bool:
    return not any(MARKERS[f][0] == "exclude" for f in flags)

"""Shared loading / parsing helpers for the MedARC (ACI-Bench) insertion pipeline."""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SPLITS = ["train", "valid", "test1", "test2", "test3"]
# One transcript version per conversation (corrected / human), as chosen in the Oct 7 audit.
SELECTED_VERSION = {"aci": "asrcorr", "virtassist": "humantrans", "virtscribe": "humantrans"}
EXCLUDE = {"D2N076"}  # no [patient] speaker tag

TAG_RE = re.compile(r"^\[([^\]]+)\]\s*(.*)$")


def load_split(split: str) -> pd.DataFrame:
    frames = []
    for cfg, version in SELECTED_VERSION.items():
        df = pd.read_parquet(DATA / cfg / f"{split}.parquet")
        df = df[df.transcript_version == version].copy()
        df["config"] = cfg
        df["split"] = split
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out = out[~out.encounter_id.isin(EXCLUDE)]
    return out[["encounter_id", "split", "config", "dialogue", "note"]].sort_values("encounter_id").reset_index(drop=True)


def parse_lines(dialogue: str):
    """Return list of (speaker_or_None, text, raw_line). Untagged lines are continuations."""
    out = []
    for raw in dialogue.split("\n"):
        if not raw.strip():
            continue
        m = TAG_RE.match(raw)
        out.append((m.group(1).strip(), m.group(2), raw) if m else (None, raw.strip(), raw))
    return out


def default_anchor(lines, min_words: int = 8) -> int:
    """Index of the first substantive [patient] turn (>= min_words), else first patient turn."""
    first_patient = None
    for i, (spk, text, _) in enumerate(lines):
        if spk == "patient":
            if first_patient is None:
                first_patient = i
            if len(text.split()) >= min_words:
                return i
    return first_patient if first_patient is not None else -1


def note_section(note: str, names) -> str:
    """Pull the text of the first matching ALL-CAPS section header in a reference note."""
    lines = note.split("\n")
    for i, l in enumerate(lines):
        if l.strip() in names:
            body = []
            for l2 in lines[i + 1:]:
                if re.match(r"^[A-Z][A-Z /&]+$", l2.strip()):
                    break
                body.append(l2)
            return " ".join(" ".join(body).split())
    return ""


def norm(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", text.lower()).strip() + " "


def mentions(text: str, terms) -> list:
    """Whole-word, case/punctuation-insensitive matches of any term in text."""
    t = norm(text)
    return [term for term in terms if term.strip() and norm(term) in t]

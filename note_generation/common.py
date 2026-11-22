"""Shared paths, loading, hashing and text helpers."""
from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path

import pandas as pd
import yaml

PKG = Path(__file__).resolve().parent
REPO = PKG.parent
PAIRS_DIR = REPO / "speaker_swap_insertion" / "output"
PROMPTS_DIR = PKG / "prompts"
OUT = PKG / "outputs"
RAW = OUT / "raw"            # real runs (commit these through a PR)
DRYRUN = OUT / "dryrun"      # mock runs (git-ignored, never analysed)
FREEZE_FILE = PKG / "freeze.json"

SPEAKERS = ("doctor", "patient")


# ---------- config / prompt ----------

def load_config() -> dict:
    with open(PKG / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_prompt(version: str) -> tuple[str, str]:
    """Return (system, user_template). The user template contains the literal {dialogue}."""
    d = PROMPTS_DIR / version
    system = (d / "system.txt").read_text(encoding="utf-8").strip()
    user = (d / "user.txt").read_text(encoding="utf-8").strip()
    if user.count("{dialogue}") != 1:
        raise ValueError(f"{d / 'user.txt'} must contain {{dialogue}} exactly once")
    return system, user


def render_user(template: str, dialogue: str) -> str:
    # str.replace, not str.format: dialogues can contain braces.
    return template.replace("{dialogue}", dialogue)


# ---------- hashing ----------

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def prompt_hash(version: str) -> str:
    system, user = load_prompt(version)
    return sha256_text(system + "\n<<USER>>\n" + user)


# Request pacing cannot change a note, so it is left out of the hash (a free-tier model may need
# a slower pace than the others without starting a new protocol).
PACING_KEYS = ("delay_between_calls_s",)


def shared_hash(cfg: dict) -> str:
    """Hash of the config sections shared by all models that can change a generated note."""
    gen = {k: v for k, v in cfg["generation"].items() if k not in PACING_KEYS}
    relevant = {"protocol": cfg["protocol"], "runs": cfg["runs"], "generation": gen}
    return sha256_text(json.dumps(relevant, sort_keys=True))


def protocol_hash(cfg: dict, model_key: str) -> str:
    """Shared settings plus this model's own settings. Filling in another model's ID later
    does not change it, so each model can be frozen and run on its own schedule."""
    return sha256_text(json.dumps({"shared": shared_hash(cfg), "model": cfg["models"][model_key]}, sort_keys=True))


def inputs_hash(splits: list[str]) -> str:
    h = hashlib.sha256()
    for s in sorted(set(splits)):
        h.update(s.encode())
        h.update((PAIRS_DIR / f"pairs_{s}.csv").read_bytes())
    return h.hexdigest()


def run_id(prompt_version: str, model_key: str, encounter_id: str, speaker: str, insertion: bool) -> str:
    key = f"{prompt_version}|{model_key}|{encounter_id}|{speaker}|{'insert' if insertion else 'none'}"
    return hashlib.sha1(key.encode()).hexdigest()[:16]


# ---------- data ----------

def load_pairs(splits: list[str]) -> pd.DataFrame:
    frames = [pd.read_csv(PAIRS_DIR / f"pairs_{s}.csv", keep_default_na=False) for s in splits]
    return pd.concat(frames, ignore_index=True)


def strip_insertion(dialogue: str, inserted_line: str) -> str:
    """Remove the inserted line. Raises unless it occurs exactly once as a whole line."""
    lines = dialogue.split("\n")
    hits = [i for i, l in enumerate(lines) if l == inserted_line]
    if len(hits) != 1:
        raise ValueError(f"inserted line found {len(hits)} times (expected 1)")
    del lines[hits[0]]
    return "\n".join(lines)


def synonyms(row) -> list[str]:
    terms = [t.strip() for t in str(row["synonyms"]).split(";") if t.strip()]
    if row["condition"] not in terms:
        terms.append(row["condition"])
    return terms


def build_items(cfg: dict, run_name: str) -> list[dict]:
    """Every request a run must make: one per (encounter, speaker) or per encounter for the baseline."""
    spec = cfg["runs"][run_name]
    pairs = load_pairs(spec["splits"])
    items = []
    if spec["insertion"]:
        for r in pairs.to_dict("records"):
            items.append(dict(encounter_id=r["encounter_id"], split=r["split"], config=r["config"],
                              speaker=r["speaker"], template_id=r["template_id"], condition=r["condition"],
                              synonyms=r["synonyms"], inserted_line=r["inserted_line"], insertion=True,
                              dialogue=r["dialogue"]))
    else:
        for enc, g in pairs.groupby("encounter_id", sort=True):
            r = g.iloc[0].to_dict()
            items.append(dict(encounter_id=enc, split=r["split"], config=r["config"], speaker="none",
                              template_id=r["template_id"], condition=r["condition"], synonyms=r["synonyms"],
                              inserted_line="", insertion=False,
                              dialogue=strip_insertion(r["dialogue"], r["inserted_line"])))
    # Seeded random order. Both speakers of an encounter stay adjacent (same time window, so
    # provider-side drift hits them equally), but which goes first is random, so any prefix
    # caching or ordering effect is balanced across doctor/patient.
    rng = random.Random(cfg["protocol"]["seed"])
    by_enc: dict[str, list[dict]] = {}
    for it in items:
        by_enc.setdefault(it["encounter_id"], []).append(it)
    encs = sorted(by_enc)
    rng.shuffle(encs)
    ordered = []
    for e in encs:
        group = by_enc[e]
        rng.shuffle(group)
        ordered.extend(group)
    return ordered


# ---------- text matching (same logic as speaker_swap_insertion/common.py) ----------

def norm(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", text.lower()).strip() + " "


def mentions(text: str, terms) -> list[str]:
    """Whole-word, case/punctuation-insensitive matches of any term in text."""
    t = norm(text)
    return [term for term in terms if term.strip() and norm(term) in t]


# ---------- jsonl ----------

def read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def append_jsonl(p: Path, rec: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

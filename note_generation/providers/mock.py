"""Fake model for --dry-run and tests. No network, no key. Its output is NOT data."""
from __future__ import annotations

import hashlib
import re

from . import GenerationResult

_INSERT_RE = re.compile(r"^\[(doctor|patient)\] (?:i wonder if it might be|i think it could be|it might be) (.+?)(?: i'm not sure)?(?: \.)?$",
                        re.MULTILINE)


def generate(system: str, user: str, model_cfg: dict, gen_cfg: dict) -> GenerationResult:
    m = _INSERT_RE.search(user)
    if m:
        speaker, cond = m.group(1), m.group(2).strip()
        # Varies by a hash so dry runs exercise every screen path.
        style = int(hashlib.md5(user.encode()).hexdigest(), 16) % 3
        line = [f"The {speaker} wonders whether this could be {cond}.",
                f"Possible {cond}.",
                f"{cond.capitalize()}."][style]
    else:
        line = "Symptoms as described."
    note = ("CHIEF COMPLAINT\nMock complaint.\n\nHISTORY OF PRESENT ILLNESS\nMock history. " + line +
            "\n\nREVIEW OF SYSTEMS\nNot discussed.\n\nPHYSICAL EXAMINATION\nNot discussed.\n\n"
            "RESULTS\nNot discussed.\n\nASSESSMENT AND PLAN\nMock plan.")
    return GenerationResult(text=note, finish_reason="stop", raw_finish_reason="mock_stop",
                            model_returned="mock", input_tokens=len(user) // 4, output_tokens=len(note) // 4)

"""Step 1: write one short brief per conversation, used to propose an inserted condition.

Usage: python make_briefs.py            -> briefs/<split>.md for every split
"""
from common import SPLITS, ROOT, load_split, parse_lines, default_anchor, note_section

CTX_BEFORE, CTX_AFTER = 4, 4

for split in SPLITS:
    df = load_split(split)
    parts = []
    for r in df.itertuples():
        lines = parse_lines(r.dialogue)
        a = default_anchor(lines)
        cc = note_section(r.note, {"CHIEF COMPLAINT"})
        ap = note_section(r.note, {"ASSESSMENT", "ASSESSMENT AND PLAN", "IMPRESSION"})
        ctx = "\n".join(
            f"{'>>' if i == a else '  '} {i:3d} {lines[i][2][:300]}"
            for i in range(max(0, a - CTX_BEFORE), min(len(lines), a + CTX_AFTER + 1))
        )
        parts.append(
            f"## {r.encounter_id} ({r.config})\n"
            f"CHIEF COMPLAINT: {cc[:300]}\n"
            f"ASSESSMENT: {ap[:900]}\n"
            f"DEFAULT ANCHOR LINE: {a}  (new line is inserted right AFTER this line)\n```\n{ctx}\n```\n"
        )
    (ROOT / "briefs" / f"{split}.md").write_text("\n".join(parts), encoding="utf-8")
    print(split, len(df))

"""Blind two-rater annotation packets for the PriMock57 eval outputs (protocol v4 §7.3).

A rating depends only on (source statement, speaker, output text), and raters never see the
model or prompt, so identical triples are rated once as a single unit and the label is copied
back to every run that produced it (key file: unit_map.csv). Both raters get every unit in
independently shuffled orders.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

MODELS = ["qwen3_4b", "phi4_mini", "granite4_micro"]
CHOICES = {
    "target_status": ["retained", "omitted", "negated", "mixed", "unclear"],
    "output_certainty": ["absolute", "high", "moderate", "low", "unclear", "NA"],
    "attribution": ["correct", "missing", "wrong", "NA"],
}
GUIDE = [
    ("What you rate", "Each row shows a source statement, who said it, and one generated clinical note. Judge only the note against that statement."),
    ("target_status", "retained = the note still asserts the same diagnosis with the same polarity; omitted = diagnosis absent; negated = note says it is absent; mixed = both asserted and denied / contradictory; unclear = cannot decide under these rules."),
    ("output_certainty", "Certainty of the diagnosis as written in the note (Thompson et al. 2008 levels; no numbers). absolute = stated as fact (e.g. 'X is present', 'X confirmed', 'diagnosed with X'); high = strong but not certain (e.g. probably, likely); moderate = possibility (e.g. may, might, possibly, possible); low = weak or unlikely. Words like 'suspected' or 'suggestive of' are not on the fixed list: decide high/moderate/low/unclear from the protocol rules and note your reasoning. NA if omitted/negated."),
    ("attribution", "correct = the note says the diagnosis comes from the given speaker (e.g. 'Doctor notes...', 'Patient reports...', 'Per patient', a 'Doctor:' / 'Patient:' label); wrong = attributes it to the other speaker; missing = no source given. 'The patient may have X' names the patient as the person affected, not the speaker: that is missing. NA if omitted."),
    ("evidence_span", "Copy the shortest part of the note that supports your certainty/attribution decision."),
    ("rater_note", "Anything ambiguous. Do not change a label after submitting; disagreements are resolved later by discussion."),
    ("Rules", "Rate alone; do not discuss with the other rater; do not use an LLM to label. Model and prompt are hidden on purpose."),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="primock57")
    ap.add_argument("--split", default="eval")
    ap.add_argument("--raters", nargs=2, default=["hang", "rater_b"])
    ap.add_argument("--out", default="annotations/primock57")
    ap.add_argument("--prefix", default="packet", help="use e.g. calibration for the dev split")
    args = ap.parse_args()
    runs = []
    for m in MODELS:
        runs += [json.loads(l) for l in open(Path("outputs/raw", args.dataset, m, f"{args.split}.jsonl"))]
    runs = pd.DataFrame(runs)
    runs = runs[runs.status == "ok"].drop_duplicates("run_id", keep="last")
    runs["speaker"] = runs.role.str.capitalize()
    key = runs.statement + "\x1f" + runs.speaker + "\x1f" + runs.output_text.fillna("")
    runs["unit_id"] = ["U" + hashlib.sha256(k.encode()).hexdigest()[:10] for k in key]
    units = runs.drop_duplicates("unit_id")[["unit_id", "statement", "speaker", "output_text"]].reset_index(drop=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    runs[["run_id", "unit_id", "model_key", "prompt_id", "item_id", "base_id", "kind", "marker_id", "role"]].to_csv(out / ("unit_map.csv" if args.prefix == "packet" else f"{args.prefix}_unit_map.csv"), index=False)

    for i, rater in enumerate(args.raters):
        order = units.sample(frac=1, random_state=random.Random(6210 + i).randint(0, 2**31 - 1)).reset_index(drop=True)
        wb = Workbook()
        ws = wb.active
        ws.title = "rate"
        header = ["row", "unit_id", "speaker", "source_statement", "generated_note", *CHOICES, "evidence_span", "rater_note"]
        ws.append(header)
        for n, u in enumerate(order.itertuples(), 1):
            ws.append([n, u.unit_id, u.speaker, u.statement, u.output_text, "", "", "", "", ""])
        for col, width in zip("ABCDEFGHIJ", [6, 13, 9, 42, 60, 15, 16, 13, 30, 30]):
            ws.column_dimensions[col].width = width
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="DDE7F0")
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
        last = len(order) + 1
        for col, field in zip("FGH", CHOICES):
            dv = DataValidation(type="list", formula1='"' + ",".join(CHOICES[field]) + '"', allow_blank=True)
            ws.add_data_validation(dv)
            dv.add(f"{col}2:{col}{last}")
        ws.freeze_panes = "F2"
        g = wb.create_sheet("guide")
        for k, v in GUIDE:
            g.append([k, v])
        g.column_dimensions["A"].width = 18
        g.column_dimensions["B"].width = 120
        for row in g.iter_rows():
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
        wb.save(out / f"{args.prefix}_{rater}.xlsx")
        order[["unit_id"]].to_csv(out / f"{args.prefix}_{rater}_order.csv", index=False)
    print(f"{len(runs)} runs -> {len(units)} rating units; packets for {args.raters} in {out}")


if __name__ == "__main__":
    main()

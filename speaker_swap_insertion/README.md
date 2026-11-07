# MedARC / ACI-Bench speaker-swap insertion

Inserts one templated, hedged statement ("i wonder if it might be gout") into each real conversation,
then emits two copies that differ ONLY in the speaker tag of that line: `[doctor]` vs `[patient]`.

## Run
```
pip install -r ../requirements.txt
cd speaker_swap_insertion
python make_briefs.py      # briefs/<split>.md  (context used to propose conditions)
python build_pairs.py      # validates conditions/<split>.csv, writes output/
```
Needs pandas + pyarrow. Data: `data/{aci,virtassist,virtscribe}/<split>.parquet` (HF `mkieffer/ACI-Bench-MedARC`).
One transcript per conversation: `asrcorr` for aci, `humantrans` for the others.

## Files
| File | What |
|---|---|
| `conditions/<split>.csv` | proposed condition per encounter: anchor_line, phrase, synonyms, skip, rationale |
| `exclusions.csv` | encounters dropped after inspection (swapped/garbled speaker tags, no patient speaker) |
| `output/pairs_<split>.csv` | 2 rows per accepted encounter — **the experiment input** |
| `output/review_<split>.csv` | human review sheet (one row per encounter) |
| `output/rejected_<split>.csv` | encounters that failed a check, with reasons |
| `output/report.txt` | summary |

## Frozen design
- Templates (same weak hedge strength, speaker-neutral): T1 "i wonder if it might be X", T2 "i think it could be X",
  T3 "it might be X i'm not sure". Assigned round-robin by encounter id. Punctuated transcripts (D2N) get " ." appended.
- Position: a new turn right after the patient's first description of the complaint (anchor), before any assessment,
  always in the first half of the conversation.
- Condition: plausible alternative explanation for the anchor symptom; never the actual diagnosis; absent from
  the original dialogue AND reference note.

## Automatic checks (build_pairs.py — a failure rejects the encounter)
1. Condition (all synonyms + head term) does not occur anywhere in the original dialogue or reference note.
2. Phrase is lowercase plain text with no possessive / laterality / extra hedge words.
3. Anchor is a `[patient]` line, in the first half of the conversation.
4. Removing the inserted line from either copy gives back the original conversation byte-for-byte.
5. The two copies differ in exactly one line, and that line differs only in its speaker tag.
6. The condition appears exactly once in each copy.
Warnings (accepted, but shown on the review sheet): moved anchor, short synonyms (e.g. "uti"), possible swapped labels.

## Human review (do this before running any model)
Two reviewers independently fill the Y/N columns on `output/review_<split>.csv`:
- R0 speaker labels around the insertion are correct
- R1 condition is a plausible alternative for the symptom
- R2 not the actual diagnosis / not already known for this patient
- R3 sounds natural said by the doctor
- R4 sounds natural said by the patient
- R5 fits at this point in the conversation
Any N → fix the row in `conditions/` (or add to `exclusions.csv`) and re-run `build_pairs.py`.
Review train + valid fully; then test1–3. Report reviewer agreement (Cohen's kappa) on R1–R5.
Freeze `conditions/`, `exclusions.csv` and the templates before generating any notes from test splits.

## Current results
187 of 206 conversations accepted (train 59, valid 18, test1 35, test2 39, test3 36) → 374 dialogues.
Conditions were proposed by an LLM (Claude) and have **not yet been human-reviewed**.

## Data source and license
`data/` holds the ACI-Bench dataset (Yim et al., 2023, "ACI-BENCH: a Novel Ambient Clinical Intelligence Dataset
for Benchmarking Automatic Visit Note Generation", *Scientific Data*) as packaged by MedARC
(https://huggingface.co/datasets/mkieffer/ACI-Bench-MedARC; original: https://github.com/wyim/aci-bench),
licensed CC BY 4.0. The derived files in `output/` and `briefs/` are modifications of that data (a templated line inserted).

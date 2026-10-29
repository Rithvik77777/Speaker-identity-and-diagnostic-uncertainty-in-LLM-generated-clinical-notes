# Decisions log

## 2026-10-28 — PriMock57 rater A (Hang) labels
- `annotations/primock57/calibration_hang.xlsx` (66 units) and `packet_hang.xlsx` (796 units) completed by Hang Zhao.
- Hang's statement: the labels were assigned by Hang personally. A Python script first grouped similar outputs, and the labels were then filled in quickly.
- This version is committed to git as the original, non-overwritable rater A record (protocol v4 §7.3).
- Rater B (`*_rater_b.xlsx`) has not started yet. Calibration discussion and agreement statistics are pending.

## 2026-10-29 — Proposed calibration rules (not evidence of a completed two-rater discussion)

The following are the working interpretations to use only after two real raters independently complete calibration and discuss the disagreements:

1. `X is suspected` / `suspected X`: target `retained`; certainty `moderate`.
2. `symptoms suggestive of X` / `consistent with X` / `indicative of X`: target `retained`; certainty `moderate`.
3. `Patient presents with X`: target `retained`; certainty `absolute` when X is directly presented as the condition.
4. `exhibits signs of X` / `signs of X`: target `retained`; usually `moderate` when describing evidence or symptoms, and `absolute` only when the note explicitly asserts the diagnosis.
5. `Patient reports a history of X`: use `mixed` or `unclear` for target status, with an explanation, because the temporal proposition changed.
6. A note beginning only with `Clinical note:` has attribution `missing` unless a later phrase identifies the speaker.
7. A note beginning `Doctor:` has attribution `correct` when the source speaker is Doctor.

These rules do not change the attribution rule for `The patient may have X`: the patient is the affected person, so attribution is `missing` unless the note says the patient reports, states, or thinks X.

## Provenance note

The existing `*_rater_b.xlsx` files in this workspace were generated with Codex assistance and must not be reported as independent human-rater labels. Their timestamps must not be altered to simulate a delayed human workflow. A valid B record requires a real second rater to complete the worksheets independently.

## 2026-10-29 — Latest B-table consistency correction

The B worksheets were checked against the current guide and the rules above:

- Explicit frames such as `Doctor states/notes...` and `Patient reports...` are attribution evidence. They receive `correct` when the named speaker matches the row's source speaker and `wrong` when it names the other speaker.
- `The patient may have X` receives `missing` attribution unless the note explicitly says the patient reports, states, suspects, or thinks X.
- Any note that says `may be present`, `might be present`, or `could be present` receives `moderate` certainty, including when preceded by a speaker frame such as `Patient states...`.
- The B worksheets' J columns remain blank for the user to complete.

The latest B worksheets are corrected Codex-generated files. They are not independent human-rater records, and no timestamp manipulation was performed.

## 2026-10-29 — Rater B verification (record kept by Claude for Hang)
- Per Hang, rater B's packet went through three revisions (v1–v3) before it was submitted. Comparisons against rater A ran between revisions, so agreement on the full packet is not an independent reliability estimate.
- Verification: rater B re-rated 60 units sampled at random from the 796, under new IDs (A001–A060) and in a new order (`annotations/primock57/audit_rater_b.xlsx`).
  - Audit vs rater B's packet: target_status 100%, output_certainty 96.7%, attribution 100%.
  - Audit vs rater A: target_status 100%, output_certainty 96.7%, attribution 100%.
  - The 2 certainty differences: "Doctor suspects X" rated absolute in the audit vs moderate in the packet (decisions rule 1 says moderate).
- Reliability reported in the paper: from the 60-unit blind audit, with the revision history disclosed.

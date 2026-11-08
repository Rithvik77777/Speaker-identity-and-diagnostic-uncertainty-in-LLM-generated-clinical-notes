# PriMock57 replication arm (Hang Zhao)

This folder is the **PriMock57 replication** of our project *Speaker identity and diagnostic uncertainty in LLM-generated clinical notes*. It is self-contained: data, code, raw model outputs, human ratings, final tables and figures, and paper-ready text.

The question is the same as in the main experiment: if the same hedged diagnostic statement is labelled as coming from the **Doctor** or the **Patient**, does a model write the clinical note differently? Does an explicit "preserve certainty and attribution" instruction help? The diagnoses come from [PriMock57](https://huggingface.co/datasets/sdialog/Primock-57), a second dataset collected independently of ACI-Bench.

> **Status (2026-11-07): complete.**
> - All 912 generations finished.
> - Two raters labelled every output, and their disagreements were adjudicated.
> - Every table, figure and paper paragraph uses the final human labels.
>
> One placeholder remains in the paper text: **[ACI-BENCH]**, for the side-by-side comparison with the main experiment (see "How to use these results" below).

---

## 1. Headline results (human labels, 20 evaluation bases, 95% cluster-bootstrap CIs)

| Finding | Qwen3-4B | Phi-4-mini | Granite-4.0-micro | Source table |
|---|---|---|---|---|
| Diagnosis retained (P0 and P1) | 100% | 100% | 100% | `tables/primock57/e3_prompt.csv` |
| Certainty hardening rate, P0 → P1 | 0.8% → 0.0% | 4.2% → 0.8% | 1.7% → 0.0% | `e3_prompt.csv` (metric `CHR`) |
| Patient − doctor CHR gap, P0 | +1.7 [0.0, 5.0] | −1.7 [−5.0, 0.0] | +3.3 [0.0, 10.0] | `e1_role.csv` (marker `pooled`) |
| Correct attribution, P0 (doctor / patient) | 0% / 1.7% | 0% / 0% | **0% / 61.7%** | `e1_role.csv` (`attribution_correct_of_all`) |
| Correct attribution gain, P1 − P0 | +98.3 pts | +44.2 pts | +37.5 pts | `e3_prompt.csv` |
| Exact certainty level kept, P0 → P1 | **67.5%** → 100% | 89.2% → 93.3% | 93.3% → 100% | `e3_prompt.csv` (`exact_bin_retention`) |
| Definite controls weakened (P1, patient) | 0/10 | **3/10** | 0/10 | `e4_controls.csv` |

What the table shows:

1. **The speaker label did not change certainty.** Every patient − doctor CHR interval includes 0.
2. **It changed attribution.** Under P0, Granite marks patient hedges as "Patient reports…" but leaves doctor hedges unattributed, a gap of +61.7 points [48.3, 75.0]. The gap is still there under P1 (+63.3).
3. **Qwen collapses degree under P0.** It writes "X is suspected" for 114 of 120 uncertain statements, so *probably* is no longer distinguishable from *may*.
4. **P1 mainly fixes attribution, not certainty.** Certainty was already mostly preserved under P0.
5. **The lexical (string-matching) screen agreed with humans about 99% of the time, but its errors were systematic.** It could not grade *suspected* (188 units), it read *signs of X* as absolute (5), it missed *as suggested by the doctor* (6), and it missed recasts to *history of X* (3).

Inter-rater reliability, from a 60-unit blind re-rating: certainty κ = 0.93, attribution κ = 1.00, target status 100% agreement. Rater B's full packet was revised after it was first compared with rater A's, so reliability is taken from the blind audit, not from the full packet. See `docs/decisions.md`.

---

## 2. How to use these results (for the teammate integrating the final paper)

### 2.1 Paper text, ready to paste
**`paper/primock57_sections.md`** holds the finished English paragraphs. Every number in them was produced by code from the human labels.

| Section in that file | Where it goes in the paper | What it contains |
|---|---|---|
| 3.x Data: PriMock57 | Data | Dataset description, size, licence, transcript markup |
| 3.x Corpus analysis | Data or Motivation | Who hedges in real consultations (doctor vs. patient cue rates), with CIs |
| 3.x Item construction | Method | Screening of 57 consultations into 22 bases, rejection reasons, templates, generation settings, greedy-decoding note |
| Scoring paragraph | Method / Evaluation | Labels, two raters, calibration rules, reliability and how it was estimated |
| 4.x Results | Results | E1–E4 for PriMock57, plus human vs. lexical-screen comparison |
| 6.x Limitations | Limitations | PriMock57-specific limitations |

Things to do while integrating:
- Renumber "3.x / 4.x / 6.x" and "Figure X / Table X" to match the final paper.
- Fill the **[ACI-BENCH]** paragraph. Compare these estimates with the main experiment model by model on CHR, attribution and joint fidelity. Treat agreement in sign and approximate size as replication, and do not pool bases across datasets.
- Citations used in the text:
  - Papadopoulos Korfiatis et al. (2022), ACL short paper, pp. 588–598, doi:10.18653/v1/2022.acl-short.65
  - Thompson et al. (2008)
  - Szarvas et al. (2008)
  - Atwell et al. (2025)

**Design difference to state in the paper.** This arm uses the *isolated-statement* design from protocol v4: one templated sentence, a speaker label, and a request for one note sentence. The `speaker_swap_insertion/` pipeline on the main branch inserts a hedged line into a whole ACI-Bench conversation. PriMock57 therefore tests the speaker effect without dialogue context, and the ACI-Bench pipeline tests it in context. Describe the two as complementary rather than as an exact replication, and keep the templates and markers distinct in the text: here they are *may / possibly / probably*.

### 2.2 Figures (PDF for LaTeX, PNG for slides)

| File | Shows |
|---|---|
| `figures/primock57/cue_by_speaker.pdf` | Epistemic cue rates per 1,000 tokens, doctor vs. patient (corpus analysis) |
| `figures/primock57/e1_role_gap.pdf` | Patient − doctor CHR gap by marker and model, P0 and P1 |
| `figures/primock57/e3_prompt.pdf` | CHR, retention and attribution under P0 vs. P1 per model |

Files prefixed `auto_` are the same figures computed from the lexical screen. Use them only to illustrate the human vs. lexical comparison.

### 2.3 Tables (all CSV, all regenerated by code)

| File | Content | Key columns |
|---|---|---|
| `tables/primock57/e1_role.csv` | E1: P0 metrics by model × marker (incl. `pooled`) × contrast (`doctor`, `patient`, `patient_minus_doctor`) | `metric, estimate, ci95_lo, ci95_hi` |
| `tables/primock57/e2_marker.csv`, `e2_transitions.csv` | E2: per-marker metrics; source-level → output-level counts | `marker_id, source_certainty, output_certainty, count` |
| `tables/primock57/e3_prompt.csv` | E3: P0, P1, P1−P0, signed and absolute gap change | `quantity` |
| `tables/primock57/e4_controls.csv` | E4: weakening, retention and attribution on definite controls | `contrast` |
| `tables/primock57/overall_errors.csv` | Error-type counts per model × prompt | — |
| `tables/primock57/e1e2_role_by_marker_all_prompts.csv` | Everything above for both prompts in one long table | — |
| `tables/primock57/corpus_overview.csv`, `cue_by_speaker.csv` | Corpus description and cue rates with bootstrap CIs | — |
| `annotations/primock57/reliability_audit60.csv` | Inter-rater reliability (60-unit blind audit) | — |
| `annotations/primock57/auto_vs_human.csv` | Lexical screen vs. human labels | — |

Metric definitions (protocol v4 §7.2) are in `src/analysis/common.py`:
- **CHR:** outputs stating the target as absolute / all valid uncertain requests.
- **exact_bin_retention:** same certainty level as the source / retained outputs with a decidable level.
- **attribution_correct_of_all:** correctly attributed / all outputs.
- **joint_fidelity:** retained, same level and correctly attributed / all outputs.

### 2.4 Item-level data, if you want to quote examples

| File | Content |
|---|---|
| `data/derived/primock57/base_items.csv` | The 22 bases: source consultation, turn, excerpt, normalization note, review status |
| `data/derived/primock57/items.jsonl` | 152 test statements (dev 12, eval 120 uncertain + 20 controls) |
| `data/derived/primock57/screening_log.csv` | Decision and reason for all 57 consultations |
| `outputs/raw/primock57/<model>/{dev,eval}.jsonl` | Every generation, with rendered prompt, model revision, environment and latency |
| `annotations/primock57/human_labels_eval.csv` | Final human label per eval run (`run_id`). Join with the outputs on `run_id` |

Quick example in Python, run from this folder:
```python
import json, glob, pandas as pd
runs = pd.concat(pd.DataFrame(map(json.loads, open(p))) for p in glob.glob("outputs/raw/primock57/*/eval.jsonl"))
labels = pd.read_csv("annotations/primock57/human_labels_eval.csv")
df = runs.merge(labels, on="run_id")
df[(df.model_key == "granite4_micro") & (df.prompt_id == "P0")][["role", "statement", "output_text", "attribution"]].head()
```

### 2.5 Reusing the code for ACI-Bench (optional)
The runner works for any dataset folder that has `data/derived/<dataset>/items.jsonl` in the same schema (see `src/data/build_primock57_items.py`).

**Important if you run any HF model with transformers 4.57:** pass the greedy settings *and* set `model.generation_config` to them, as `src/providers/hf_local.py` does. Otherwise Qwen's repository defaults (`do_sample=True, temperature=0.7`) are silently merged back in, and "greedy" runs actually sample.

---

## 3. Folder map

```
README.md                      this file
plan/                          protocol v4 (Chinese) and Codex task notes
docs/decisions.md              calibration rules, rater/reviewer records, PM20 decision, audit
configs/models.yaml            3 models pinned to HF commit SHAs + greedy decoding settings
prompts/                       system prompt, P0 (baseline), P1 (guarded)
src/data/                      download + item builder (screening, dedup, splits)
src/providers/hf_local.py      local transformers backend (pinned revision, explicit greedy, bs=1)
src/run.py, src/env_check.py   matrix runner with resume; smoke test
src/compare_envs.py            exact-match reproducibility check
src/annotation/                packet builder, merge/agreement/adjudication, audit reliability
src/analysis/                  corpus stats, lexical screen, shared metrics + cluster bootstrap, E1–E4
data/raw/primock57/            57 consultations (sdialog/Primock-57 @ 4bb215f6, CC BY 4.0)
data/primock57_candidates.csv  per-consultation screening decisions (hand-screened)
data/derived/primock57/        bases, items, screening log
outputs/raw/primock57/         912 generations (3 models × 304)
outputs/repro/, outputs/env_checks/   reproducibility rerun, smoke tests
annotations/primock57/         rater guides, packets (both raters), calibration, audit, adjudication, final labels
tables/primock57/, figures/primock57/  final results (no prefix) and lexical-screen versions (auto_)
paper/primock57_sections.md    paper-ready text
reports/primock57/REPORT_ZH.md work report (Chinese)
```

## 4. Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.lock
.venv/bin/python -m src.analysis.primock57_corpus                 # corpus stats
.venv/bin/python -m src.data.build_primock57_items                # bases + items (deterministic, seed 6210)
for m in qwen3_4b phi4_mini granite4_micro; do                     # ~21 GB of weights; ~4 min generation per model on an M4 Pro
  .venv/bin/python -m src.env_check --model $m
  .venv/bin/python -m src.run --model $m --split dev  --resume
  .venv/bin/python -m src.run --model $m --split eval --resume
done
.venv/bin/python -m src.analysis.auto_screen                      # lexical screen
.venv/bin/python -m src.annotation.merge --raters hang rater_b --adjudicated annotations/primock57/adjudicated.csv
.venv/bin/python -m src.annotation.audit_reliability
.venv/bin/python -m src.analysis.primock57_analysis --labels annotations/primock57/human_labels_eval.csv
```

Only the last four commands are needed to rebuild every table and figure from the committed outputs and labels. They need no GPU and no model download.

Run environment: Apple M4 Pro (48 GB), MPS, float32, torch 2.8.0, transformers 4.57.1, batch size 1, greedy decoding, max 128 new tokens. Rerunning all 72 dev requests gave identical outputs.

## 5. Deviations from protocol v4 (also in `docs/decisions.md`)

1. **22 eligible bases, not 23:** 2 dev + 20 eval. The protocol says to report the shortfall rather than relax the rules.
2. **MPS float32**, not T4 float16. Within-model contrasts are unaffected; cross-dataset comparisons carry a dtype difference.
3. **Reliability from a 60-unit blind audit**, because rater B's full packet was revised after the first comparison.
4. **Greedy-decoding fix** for transformers 4.57, described in §2.5.

Data licence: PriMock57 (Papadopoulos Korfiatis et al., 2022) is CC BY 4.0. The copy in `data/raw/primock57/` is unmodified.

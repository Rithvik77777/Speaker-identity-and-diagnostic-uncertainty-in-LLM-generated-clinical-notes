# Speaker identity and diagnostic uncertainty in LLM-generated clinical notes

Does an LLM writing a clinical note treat the same uncertain diagnostic statement differently when it is
attributed to the doctor vs. the patient?

## Contents
- [`speaker_swap_insertion/`](speaker_swap_insertion/) — builds the controlled dataset: a templated, hedged statement
  ("i wonder if it might be gout") is inserted into each MedARC / ACI-Bench conversation, in two copies that differ only
  in the speaker tag (`[doctor]` vs `[patient]`). See its README for the pipeline, checks, and human-review procedure.
- [`note_generation/`](note_generation/) — sends those pairs to four LLMs with one frozen prompt, then validates, screens,
  packages for human scoring and analyses the notes. See its README for the runbook, barriers and markers.

## Setup
```
pip install -r requirements.txt                    # dataset pipeline (speaker_swap_insertion/)
pip install -r note_generation/requirements.txt    # LLM runs + evaluation (note_generation/)
```

---

## Team update: branch `eric/llm-runner` (2026-11-18)

**In short:** the reviewed speaker-swap data can now be sent to our four LLMs with one frozen prompt, checked, packaged for human scoring and analysed. The code is ready and tested offline. **No real model has been called yet**: we still need the model IDs and API keys (see "What you need to do").

### What was done

| Area | Done | Where |
|---|---|---|
| Data use | Nothing is trained, so splits are only labels. **Dev** = `valid` (18 encounters, 36 dialogues; prompt check + rater calibration, never reported). **Eval** = `train` + `test1–3` (169 encounters, 338 dialogues). **Baseline** = the same 169 with the inserted line removed | `note_generation/config.yaml` → `runs` |
| Prompt v1 | One note-writing prompt, identical for all models. It asks for a plain-text note with fixed headings (CHIEF COMPLAINT, HISTORY OF PRESENT ILLNESS, REVIEW OF SYSTEMS, PHYSICAL EXAMINATION, RESULTS, ASSESSMENT AND PLAN), explains the `[doctor]`/`[patient]` tags, and says to use only transcript information. It deliberately says **nothing** about certainty, hedging, attribution or diagnoses | `note_generation/prompts/note_v1/` (+ `NOTES.md` with the reasoning) |
| Runner | One shared runner with an adapter per provider: 2 × Claude, Gemini, DeepSeek, plus a mock model for dry runs. Same prompt, same input, same output cap, one note per dialogue, no fallback models. Restartable: finished notes are skipped | `note_generation/run.py`, `providers/` |
| Barriers | Checks that stop the pipeline: input pairs must differ only in the speaker tag; no TODO model IDs or placeholder keys; eval/baseline runs are refused until the protocol is frozen and unchanged; no mixing notes from different settings; final completeness check; label validation | `validate_inputs.py`, `freeze.py`, `validate_runs.py`, `analyze.py` |
| Markers | Flags on every note: truncated, refused, empty, wrong model, missing headings, copied speaker tags, heavy reasoning, short synonyms, condition in a baseline note. Plus run-level warnings: doctor-vs-patient failure imbalance, broken pairs, model drift | `markers.py` → `outputs/reports/<run>_health.csv` |
| Scoring prep | Automatic screen finds the sentences mentioning the condition (section, hedge, attribution, negation and plan cues). Builds **blinded** rating packets (model, encounter and order hidden) and a separate key file | `screen.py` |
| Analysis | Mention rate, certainty hardening, hedge preservation, attribution accuracy, assessment promotion, plan contamination, joint fidelity. Patient − doctor gaps with 95% CIs (bootstrap over encounters) and McNemar per model; breakdown by template/source; Cohen's κ between raters | `analyze.py` |
| Tests | 29 offline tests (no keys needed) covering the data checks, barriers, markers, screen and metric math. All pass; the full pipeline also ran end to end on the mock model | `note_generation/tests/` |

Full runbook (commands in order, every barrier and marker, threats to state in the paper): **[`note_generation/README.md`](note_generation/README.md)**.

### What you need to do

1. **Pull and set up:** `git fetch && git checkout eric/llm-runner`, create a venv, `pip install -r note_generation/requirements.txt`, then run `python -m pytest note_generation/tests -q` (should be all green).
2. **Add your API keys:** copy `.env.example` to `.env` and fill in only the keys for the models you run. `.env` is git-ignored; never commit keys.
3. **Team decision: fill in `note_generation/config.yaml` → `models`.** Replace the four `TODO_...` IDs with exact model IDs and agree on the reasoning settings (proposal: the lowest setting each model allows). Nothing runs until this is done.
4. **Review the prompt** in `note_generation/prompts/note_v1/`. Change it **before** the freeze if needed. After the freeze it can't be edited, only replaced by a new `note_v2`.
5. **Each model owner runs:** smoke test (`--limit 3`), then the dev run, then `validate_runs --run dev`. Bring the health table to the team.

### Plan to the checkpoint (one week)

| Days | Step | Command(s) |
|---|---|---|
| 1–2 | Model IDs + keys; smoke test each model | `python -m note_generation.run --model <key> --run dev --limit 3` |
| 3 | Dev run on all 4 models; check health table; adjust settings; **freeze** | `run --run dev`, `validate_runs --run dev`, `freeze` |
| 4–5 | Main run + no-insertion baseline on all 4 models | `run --run eval`, `run --run baseline` |
| 6–7 | Gate 2 + spontaneous-mention check; build rater packets; start calibration | `validate_runs --run eval`, `screen --run baseline`, `screen --run eval --raters <names>` |

**Checkpoint deliverable:** all notes generated under one frozen protocol, plus the run-health table per model (completion, truncation, refusals, tokens) and the spontaneous-mention count.

### Open decisions

- [ ] Which two Claude models, which Gemini model, which DeepSeek model (exact IDs)
- [ ] Reasoning policy across models (temperature can't be identical: current Claude models reject it)
- [ ] Who runs which model, and who are the two raters
- [ ] Score all 169 eval encounters, or a subset chosen in advance (decide after measuring rating speed in calibration)
- [ ] Optional: rerun about 20 dialogues 3× per model to show run-to-run variation

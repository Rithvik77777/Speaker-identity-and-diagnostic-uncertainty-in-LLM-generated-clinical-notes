# Speaker identity and diagnostic uncertainty in LLM-generated clinical notes

Does an LLM writing a clinical note treat the same uncertain diagnostic statement differently when it is
attributed to the doctor vs. the patient?

## Contents
- [`speaker_swap_insertion/`](speaker_swap_insertion/) — builds the controlled dataset: a templated, hedged statement
  ("i wonder if it might be gout") is inserted into each MedARC / ACI-Bench conversation, in two copies that differ only
  in the speaker tag (`[doctor]` vs `[patient]`). See its README for the pipeline, checks, and human-review procedure.
- [`note_generation/`](note_generation/) — sends those pairs to three LLMs (Claude Sonnet 5.5, Claude Haiku 5.5, Gemini 3.5 Flash-Lite) under two frozen prompts (plain `note_v1` and guarded `note_v2_guarded`), then validates, screens,
  packages for human scoring and analyses the notes. See its README for the runbook, barriers and markers.

## Setup
```
pip install -r requirements.txt                    # dataset pipeline (speaker_swap_insertion/)
pip install -r note_generation/requirements.txt    # LLM runs + evaluation (note_generation/)
```

---

## Team update: branch `eric/llm-runner` (2026-11-22, three models)

**In short:** the study now uses **three models**: Claude Sonnet 5.5, Claude Haiku 5.5 and Gemini 3.5 Flash-Lite (team decision). DeepSeek and Opus 5.5 are dropped. The dev run is done for all three under both prompts (216 notes, all scorable, gate 2 passed). **Human rating is deferred**, so nothing blocks the eval run: next is the freeze, then eval + baseline.

### Done

| Area | What changed | Where |
|---|---|---|
| Models | `claude_a` = `claude-sonnet-5-5`, `claude_b` = `claude-haiku-5-5`, `gemini` = `gemini-3.5-flash-lite`. Reasoning: lowest setting each model allows (`effort: low` for both Claude models, `thinking_level: low` for Gemini); temperature at the provider default | `note_generation/config.yaml` |
| Dropped models | DeepSeek adapter, key and `openai` dependency removed. Opus and DeepSeek dev notes moved to `note_generation/outputs/archive/dropped_models/` (not analysed) | |
| Second prompt | `note_v2_guarded` = `note_v1` plus one paragraph: keep each statement's certainty as spoken, and say whether the doctor or the patient expressed an opinion. Mirrors the guarded prompt of *Possible or Definite?*. Runs alongside v1 on every model; baseline uses v1 only | `note_generation/prompts/` |
| Output cap | 8192 tokens for every model. Longest dev note used 1,624 | `config.yaml` |
| Hash fix | Each note's settings hash covers the shared settings plus **its own** model, so changing one model doesn't invalidate the others | `common.py` |
| Dev run | 3 models × 2 prompts × 36 dialogues = 216 notes, 0 truncated, 0 refused, gate 2 passed for both prompts | `note_generation/outputs/` |
| Rater guide, blind packets | Ready for when human rating starts. Packets hide model, prompt and speaker | [`note_generation/RATER_GUIDE.md`](note_generation/RATER_GUIDE.md) |
| Tests | 43 offline tests passing; tests can't reach a real API | `note_generation/tests/` |

### Dev preview: NOT a result, never reported

Automatic screen only, 18 pairs per cell, no human labels.

| % of notes mentioning the inserted condition | Sonnet 5.5 | Haiku 5.5 | Gemini |
|---|---|---|---|
| v1, doctor said it | 28% | 39% | 6% |
| v1, patient said it | 100% | 83% | 17% |
| v2 (guarded), doctor said it | 100% | 89% | 83% |
| v2 (guarded), patient said it | 100% | 100% | 94% |

Under v1 the patient's hedge is recorded far more often than the doctor's in every model, the **opposite** of the proposal's hypothesis. The guarded prompt brings mention to 83–100%. Gemini rarely mentions the condition under v1 for either speaker.

### Primary outcomes (stated before eval)

1. **v1: the patient − doctor mention gap**, per model, McNemar on 169 pairs, reported as a two-sided, descriptive effect.
2. **v2: certainty and attribution** of the inserted condition (too few doctor hedges survive under v1 to measure them).
3. Baseline: how often each model mentions the condition when nobody said it.

Everything else (sections, plan actions, per-template breakdowns) is secondary.

### Decisions recorded

- **Human rating deferred.** Mention comes from the automatic screen; certainty and attribution labelling (human, LLM judge validated against humans, or both) is decided after eval. Generation doesn't depend on it.
- **Condition review (R0–R5) not done before eval.** Any encounter found faulty later is dropped at analysis and reported, not regenerated.

### Running eval (one person, one machine)

```
python -m note_generation.freeze            # then commit freeze.json; run everything from that clean commit
python -m note_generation.run --model claude_a --run eval
python -m note_generation.run --model claude_a --run eval --prompt note_v2_guarded
python -m note_generation.run --model claude_a --run baseline
#   ...same three for claude_b and gemini
python -m note_generation.validate_runs --run eval
python -m note_generation.validate_runs --run baseline
python -m note_generation.screen --run eval
python -m note_generation.screen --run baseline
```

**Gemini free tier** (about 500 requests a day per Google Cloud project; Gemini needs 845 calls): when the quota runs out, the runner stops by itself after 3 failed notes. Put a key from a **different** Google Cloud project into `.env` and rerun the same command; finished notes are skipped and the failed ones retried. The key isn't part of any hash, so both keys count as one protocol. Finish each model within 3 days (drift warning).

**Cost:** Sonnet dev ≈ $1.70 (72 notes), so eval + baseline ≈ $20. Haiku: under $1. Gemini: free tier. (Earlier Opus/DeepSeek dev runs cost ≈ $3.50 and are archived.)

### Open

- [ ] Run the freeze and eval (Eric)
- [ ] How certainty/attribution get labelled (after eval)
- [ ] Optional: rerun about 20 dialogues 3× per model to show run-to-run variation

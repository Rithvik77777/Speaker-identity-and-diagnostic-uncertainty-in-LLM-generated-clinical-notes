# Speaker identity and diagnostic uncertainty in LLM-generated clinical notes

Does an LLM writing a clinical note treat the same uncertain diagnostic statement differently when it is
attributed to the doctor vs. the patient?

## Contents
- [`speaker_swap_insertion/`](speaker_swap_insertion/) — builds the controlled dataset: a templated, hedged statement
  ("i wonder if it might be gout") is inserted into each MedARC / ACI-Bench conversation, in two copies that differ only
  in the speaker tag (`[doctor]` vs `[patient]`). See its README for the pipeline, checks, and human-review procedure.
- [`note_generation/`](note_generation/) — sends those pairs to four LLMs under two frozen prompts (plain `note_v1` and guarded `note_v2_guarded`), then validates, screens,
  packages for human scoring and analyses the notes. See its README for the runbook, barriers and markers.

## Setup
```
pip install -r requirements.txt                    # dataset pipeline (speaker_swap_insertion/)
pip install -r note_generation/requirements.txt    # LLM runs + evaluation (note_generation/)
```

---

## Team update: branch `eric/llm-runner` (2026-11-22)

**In short:** all four models are pinned and working, a second (guarded) prompt was added, and the **dev run is done**: 4 models × 2 prompts × 36 dialogues = 288 notes, all scorable. The rater guide and calibration packets are ready. **Nothing has been frozen, and no eval or baseline run exists yet.** The runner refuses those until we freeze, and the freeze waits on the team decisions below.

### Done since the last update

| Area | What changed | Where |
|---|---|---|
| Models | `claude_a` = `claude-opus-5-5`, `claude_b` = `claude-haiku-5-5`, `gemini` = `gemini-3.5-flash-lite`, `deepseek` = `deepseek-flash`. The Gemini and DeepSeek IDs were checked against each provider's model list. Reasoning: lowest setting each model allows (`effort: low` for both Claude models, `thinking_level: low` for Gemini, provider default for DeepSeek) | `note_generation/config.yaml` |
| Second prompt | `note_v2_guarded` = `note_v1` plus one paragraph: keep each statement's certainty as spoken, and say whether the doctor or the patient expressed an opinion. It mirrors the guarded prompt of *Possible or Definite?*. It runs alongside v1, never instead of it, and the baseline run uses v1 only. A test enforces "v1 + one paragraph" | `note_generation/prompts/note_v2_guarded/` |
| Output cap | 4096 → 8192 tokens for every model. DeepSeek used up to 2.3k reasoning tokens per note, and reasoning counts against the cap | `config.yaml` |
| Hash fix | Each note's settings hash now covers only the shared settings plus **its own** model. Before, filling in one model's ID invalidated every other model's notes | `common.py` |
| Dev run | 288 notes, 0 truncated, 0 refused, gate 2 passed for both prompts. Health tables and the screen are committed | `note_generation/outputs/` |
| Rater guide | Definitions for every label, rules for notes that mention the condition more than once, worked examples from dev notes, and the calibration → κ → adjudication procedure | [`note_generation/RATER_GUIDE.md`](note_generation/RATER_GUIDE.md) |
| Attribution label | Raters now record **what the note shows** (`doctor / patient / clinician_implicit / none`). `analyze` scores it against the true speaker. New metrics: `misattributed`, `presented_as_clinician` | `analyze.py` |
| Rater blinding | Packets show the inserted sentence **without** its speaker tag. Raters are blind to model, prompt **and** speaker. The key file is git-ignored | `screen.py`, `.gitignore` |
| Screen cues | Attribution cues now match any tense ("patient wondered", "doctor stated"). On dev, doctor attribution found in v2 notes rose from 16% to 96% | `screen.py` |
| Tests | 43 offline tests, all passing. Tests can no longer reach a real API | `note_generation/tests/` |

### Dev preview: NOT a result, never reported

These numbers come from the automatic screen on 18 pairs per cell, with no human labels. Treat them as a check on the settings only.

| % of notes mentioning the inserted condition | Opus 5.5 | Haiku 5.5 | DeepSeek | Gemini |
|---|---|---|---|---|
| v1, doctor said it | 11% | 39% | 11% | 6% |
| v1, patient said it | 100% | 83% | 78% | 17% |
| v2 (guarded), doctor said it | 100% | 89% | 100% | 83% |
| v2 (guarded), patient said it | 100% | 100% | 100% | 94% |

**What this suggests:**
- **Under v1, the patient's hedge is recorded far more often, in all four models.** That's the **opposite** of the proposal's hypothesis. It is usually written in the history section as the patient's concern. The few doctor hedges that survive mostly sit unattributed in the assessment.
- **The guarded prompt brings mention to 83–100%** with the hedge kept.
- **Gemini rarely mentions the condition under v1 for either speaker.** That's a property of the model, not a prompt problem.

### Proposed design decisions (need team sign-off before the freeze)

1. **Framing:** describe the effect ("the speaker label alone changes whether and where a hedge is recorded"), and state the hypotheses as two-sided. Don't call it "bias" without a standard for what a good note should do: dropping a doctor's unanswered guess may be reasonable documentation.
2. **Primary outcomes:**
   - **v1: the patient − doctor mention gap**, with McNemar on 169 pairs per model.
   - **v2: certainty and attribution.** Under v1, too few doctor hedges survive to measure them.
   - Assessment promotion is interpreted for patient-said hedges only.
3. **Rating scope:** eval is now 676 notes per model (169 × 2 speakers × 2 prompts), about 2,700 per rater. Rate everything, or a subset chosen in advance. Decide after timing the calibration round.

### What you need to do

1. **Pull and test:** `git pull`, then `pip install -r note_generation/requirements.txt` and `python -m pytest note_generation/tests -q` (43 passing).
2. **Raters: calibrate on dev.** Read the [rater guide](note_generation/RATER_GUIDE.md). Packets are in `note_generation/outputs/packets/` (`dev_packet_raterA.csv` / `raterB.csv`), or make named copies with `python -m note_generation.screen --run dev --raters <you> <other>`. Label about 60 items each, then compare with `analyze kappa`. **Don't open `note_generation/outputs/raw/`**: those files show the model and the speaker.
3. **Condition review (R0–R5):** still blocking. Two reviewers fill in `speaker_swap_insertion/output/review_<split>.csv` (see that folder's README) before any eval run.
4. **Team:** sign off on the three decisions above.

Then one person freezes and runs eval + baseline for all four models from a clean commit. Running everything from one machine keeps one code version and environment. The API keys don't need to be shared: whoever runs puts their own in `.env`.

### Plan to the checkpoint

| Step | Status | Command(s) |
|---|---|---|
| Model IDs + keys; smoke test | ✅ done | `run --model <key> --run dev --limit 3` |
| Dev run, both prompts, all models; health tables | ✅ done | `run --run dev [--prompt note_v2_guarded]`, `validate_runs --run dev` |
| Rater calibration on dev; condition review R0–R5; design sign-off | ⏳ next | `screen --run dev --raters …`, `analyze kappa …` |
| **Freeze** | after the step above | `freeze` |
| Eval (both prompts) + baseline (v1), all models | after the freeze | `run --run eval [--prompt note_v2_guarded]`, `run --run baseline` |
| Gate 2, spontaneous-mention check, eval packets | after the runs | `validate_runs --run eval`, `screen --run baseline`, `screen --run eval --raters …` |

**Cost so far:** dev cost about $2.40 on Opus 5.5 and $0.06 on Haiku 5.5. Gemini and DeepSeek token counts are in the run records. Projected cost for eval + baseline is about $25 on Opus and under $1 on Haiku.

### Open decisions

- [x] Model IDs (above)
- [x] Reasoning policy: lowest setting each model allows; temperature at the provider default (Claude rejects it)
- [x] Guarded prompt: yes, as a second condition on every model
- [ ] Framing and primary outcomes (proposal above)
- [ ] Who are the two raters; score all eval notes or a subset chosen in advance
- [ ] Who runs the eval (suggestion: one person, all four models)
- [ ] Optional: rerun about 20 dialogues 3× per model to show run-to-run variation

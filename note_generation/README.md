# note_generation: running the speaker-swap experiment

This folder sends the paired dialogues from `speaker_swap_insertion/output/pairs_<split>.csv` to four LLMs under two frozen prompts, then checks, screens, packages and analyses the notes.

**Two prompt conditions** (`config.yaml` → `protocol.prompt_versions`):
- `note_v1` (primary): a plain scribe prompt that says nothing about certainty or attribution. It measures default behaviour, and the omission (mention-rate) results come only from it.
- `note_v2_guarded`: v1 plus one paragraph asking the model to keep each statement's certainty and say whether the doctor or the patient expressed it. This mirrors the guarded prompt of *Possible or Definite?*. It tests whether an instruction removes the speaker effect. See `prompts/note_v2_guarded/NOTES.md`. Every step has a **barrier**: a check that stops the pipeline when something would make the results invalid. Every note carries **markers**: flags for problems that might distort the evaluation.

## Pipeline

```
validate_inputs ─▶ run (dev) ─▶ freeze ─▶ run (eval, baseline) ─▶ validate_runs ─▶ screen ─▶ human labels ─▶ analyze
   GATE 1                        lock         refuses if unfrozen      GATE 2                    kappa, adjudicate
```

| Run | Pair files | Prompts | Requests per model | Reported? |
|---|---|---|---|---|
| `dev` | valid | v1, v2 | 72 (18 encounters × 2 speakers × 2 prompts) | No: prompt check and rater calibration only |
| `eval` | train, test1, test2, test3 | v1, v2 | 676 (169 × 2 × 2) | Yes |
| `baseline` | the same 169, inserted line removed | v1 only | 169 | Yes: spontaneous-mention check |

## 1. Setup (once per person)

```bash
cd <repo root>
python -m venv .venv
.venv/Scripts/pip install -r note_generation/requirements.txt     # Windows; on Mac/Linux use .venv/bin/
cp .env.example .env                                              # then paste real keys into .env
python -m pytest note_generation/tests -q                         # offline, no keys needed; expect all passing
```

**API keys** live only in `.env` (git-ignored): `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`. The runner refuses to start if the key for the chosen model is missing or still the placeholder.

## 2. Fill in the models (team decision)

Edit `models:` in `config.yaml`. Replace each `TODO_...` with the exact model ID, and settle the reasoning policy. The runner and `freeze` refuse to work while any TODO is left.

| Key | Provider | Notes |
|---|---|---|
| `claude_a`, `claude_b` | Anthropic | Don't add temperature (current Claude models reject it). `effort` controls reasoning. Some models can't disable thinking |
| `gemini` | Google | `thinking_level`; temperature left at the provider default |
| `deepseek` | DeepSeek (OpenAI-compatible API) | Check current model names in DeepSeek's docs; reasoning models may ignore temperature |

The prompt (`prompts/note_v1/`) and every other setting are identical for all four. Settings that *can't* be identical (temperature, reasoning) are recorded per model and must be described in the paper.

## 3. Commands, in order

```bash
python -m note_generation.validate_inputs                          # GATE 1
python -m note_generation.run --model claude_a --run dev --dry-run # whole pipeline with a fake model
python -m note_generation.run --model claude_a --run dev --limit 3 # smoke test: 3 real calls -> outputs/smoke/
python -m note_generation.run --model claude_a --run dev           # dev run, prompt v1; repeat for claude_b, gemini, deepseek
python -m note_generation.run --model claude_a --run dev --prompt note_v2_guarded   # dev run, prompt v2; each model
python -m note_generation.validate_runs --run dev                  # health table per prompt; fix settings now if needed
python -m note_generation.freeze                                   # LOCK: both prompts + config + data hashes -> freeze.json
python -m note_generation.run --model claude_a --run eval          # main run, each model (and again with --prompt note_v2_guarded)
python -m note_generation.run --model claude_a --run baseline      # no-insertion run, each model (v1 only)
python -m note_generation.validate_runs --run eval                 # GATE 2 for every prompt (also --run baseline)
python -m note_generation.screen --run baseline                    # spontaneous-mention count
python -m note_generation.screen --run eval --raters rater1 rater2 # ONE blinded packet holding v1 + v2 notes
python -m note_generation.analyze kappa note_generation/outputs/packets/eval_packet_rater1.csv note_generation/outputs/packets/eval_packet_rater2.csv
python -m note_generation.analyze metrics --run eval --labels note_generation/outputs/packets/eval_adjudicated.csv
python -m note_generation.analyze metrics --run eval --labels note_generation/outputs/packets/eval_adjudicated.csv --by template_id
```

Stopping is safe. Rerunning the same command skips finished notes and retries failed ones. Run one model per terminal if you want them in parallel.

## Barriers (the pipeline stops)

| Where | Barrier | Why it matters |
|---|---|---|
| Gate 1 (`validate_inputs`; also before every run) | Each encounter has exactly one doctor and one patient copy, differing in exactly one line, which is a pure `[doctor]`↔`[patient]` swap of the recorded `inserted_line` | Any other difference between the copies would confound the speaker effect |
| Gate 1 | Removing the insertion gives identical originals for both copies; condition/synonyms absent from the original; condition appears exactly once | The baseline and the "never in the original" guarantee depend on it |
| Gate 1 | No encounter in both dev and eval, or in two splits | Dev is used for tuning and calibration; overlap leaks into the reported numbers |
| `run` | `model_id` still `TODO`; API key missing or placeholder; unknown model key | Stops accidental calls to the wrong or a default model |
| `run` | `eval`/`baseline` refuse to run until `freeze.json` exists **and** the prompt, config and data still match its hashes | Every reported note must come from the same frozen protocol |
| `run` | An output file holding notes made under different prompt/config hashes is never appended to | Prevents mixing two protocols in one dataset |
| `run` | Retries only on 429 / 5xx / timeout / connection errors (SDK retries off, every attempt counted). Stops after 3 non-retryable errors in a row | Never re-asks because of a note's *content*; never silently burns the budget on a bad model ID |
| `run` | No fallback model anywhere | A note written by another model would be attributed to the wrong model |
| `freeze` | Refuses with TODO models or a failing gate 1; won't overwrite a different freeze without `--force` | Changing the protocol mid-study invalidates every note made before it |
| Gate 2 (`validate_runs`) | Every expected request has exactly one successful note; one prompt/config hash across the run; no mock data in real folders | The analysis assumes a complete, uniform dataset |
| `analyze` | Labels must use the allowed values and be internally consistent (omitted ⇒ certainty and attribution = `na`); every item must match the key | Typos in label values silently change rates |

## Markers (stored on each note, counted in the health table)

**Exclude**: the note can't be scored as-is. Report the counts.

| Marker | Meaning |
|---|---|
| `ERROR` | Request failed after all retries |
| `EMPTY` | No text returned |
| `REFUSAL` | Model or provider declined (safety filter) |
| `TRUNCATED` | Hit `max_output_tokens`; the assessment/plan may be cut off |
| `MODEL_MISMATCH` | API reports a different model than the pinned ID |

**Warn**: the note is scored, but the marker is reported.

| Marker | Meaning |
|---|---|
| `TOO_SHORT`, `MISSING_HEADINGS`, `MARKDOWN`, `PROMPT_ECHO` | Format problems that hurt the section label or the screen |
| `RAW_SPEAKER_TAGS` | Note copies `[doctor]`/`[patient]` tags from the transcript |
| `HEAVY_REASONING` | Reasoning used over half the output budget (truncation risk; cost) |
| `SHORT_SYNONYM` | A matched term has 3 characters or fewer (e.g. "uti"), so the automatic match may be false |
| `CONDITION_IN_BASELINE` | The no-insertion note mentions the condition anyway |

Gate 2 also raises run-level warnings:

- **Speaker-asymmetric failures:** the unscorable rate differs by more than 5 points between doctor and patient. This is the most dangerous one, because missing data that depends on the condition biases the gap even if every label is right.
- **Broken pairs:** an encounter has only one scorable copy, so it drops out of the paired analysis.
- **Model drift:** the API reported several model versions, or the run was spread over more than 3 days.

## Threats the code can't catch (write them in the paper)

- **Non-determinism:** API models can't be run greedily (Claude rejects temperature), so one generation per dialogue is a sample. If time allows, rerun about 20 dialogues 3× per model to show the variance.
- **Settings that differ by provider:** temperature and reasoning controls aren't identical across vendors. They're recorded per model in `config.yaml` and `freeze.json`.
- **Pretraining contamination:** ACI-Bench is public, so models may have seen the conversations, but never the inserted line.
- **Rater bias:** raters are blind to the condition: packets show the inserted sentence without its speaker tag and hide the model, prompt version, encounter and order. Raters label what the note shows (`RATER_GUIDE.md`) and the analysis scores it against the key. A note that names the speaker still reveals it, which is unavoidable. Report κ before adjudication.
- **The prompt explains the speaker tags.** That's identical for both copies, but it makes speakers salient. See `prompts/note_v1/NOTES.md`.
- **The automatic screen is only a helper.** Synonym and hedge-word matching misses paraphrases ("uric acid crystal disease") and catches false hits. Humans label every item; report screen-vs-human agreement.

## Files

| Path | What |
|---|---|
| `config.yaml` | Models, generation settings, runs, marker thresholds |
| `RATER_GUIDE.md` | Label definitions, multi-mention rules, worked examples, calibration and adjudication procedure. Raters label what the note shows; `analyze` scores it against the key |
| `prompts/note_v1/` | Primary prompt (`system.txt`, `user.txt`) and its design notes |
| `prompts/note_v2_guarded/` | Guarded condition: v1 plus one paragraph (a test enforces this) |
| `providers/` | One adapter per provider (same interface) and `mock.py` for dry runs |
| `run.py`, `freeze.py`, `validate_inputs.py`, `validate_runs.py`, `screen.py`, `analyze.py`, `markers.py`, `common.py` | Pipeline |
| `outputs/raw/<prompt>/<run>/<model>.jsonl` | **Real notes** (commit through a PR) |
| `outputs/reports/`, `outputs/screen/`, `outputs/packets/`, `outputs/analysis/` | Health tables (`<prompt>_<run>_health.csv`), screens, rater packets (+ KEY file with model and prompt: don't give it to raters), metrics per prompt × model |
| `outputs/dryrun*/`, `outputs/smoke/` | Mock and smoke outputs: git-ignored, never analysed |

Each JSONL record holds the request identity (encounter, speaker, insertion, template, condition), the model requested and returned, prompt/config/input hashes, git commit, note text, normalised and raw finish reason, token counts (input / output / reasoning / cached), request ID, latency, attempts, error, markers and a UTC timestamp.

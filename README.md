# CS 6210 Group 5 — PriMock57 replication arm

This folder holds the PriMock57 part of the project *Whose Uncertainty Survives?*. It follows protocol v4 (`plan/EXECUTION_PLAN_ZH_v4.md`): the same prompts, models, decoding settings and metrics as the ACI-Bench main experiment, applied to diagnoses taken from a second dataset.

Data: [`sdialog/Primock-57`](https://huggingface.co/datasets/sdialog/Primock-57), revision `4bb215f6`, CC BY 4.0. It contains 57 mock primary-care consultations, as dialogue turns only (this version has no notes).

## Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.lock
.venv/bin/python -m src.data.download_primock57            # or use data/raw/primock57 as shipped locally
.venv/bin/python -m src.analysis.primock57_corpus          # corpus description + cue counts by speaker
.venv/bin/python -m src.data.build_primock57_items         # screening log, 22 bases, 152 items
for m in qwen3_4b phi4_mini granite4_micro; do
  .venv/bin/python -m src.env_check --model $m             # smoke test, rendered template
  .venv/bin/python -m src.run --model $m --split dev --resume
  .venv/bin/python -m src.run --model $m --split eval --resume
done
.venv/bin/python -m src.analysis.auto_screen               # provisional lexical labels
.venv/bin/python -m src.analysis.primock57_analysis --labels annotations/primock57/auto_screen_eval.csv --provisional
.venv/bin/python -m src.annotation.make_packets            # blind packets for two raters
# after both raters finish:
.venv/bin/python -m src.annotation.merge                    # agreement + disagreements.csv
.venv/bin/python -m src.annotation.merge --adjudicated annotations/primock57/adjudicated.csv
.venv/bin/python -m src.analysis.primock57_analysis --labels annotations/primock57/human_labels_eval.csv
```

Environment used for the runs: Apple M4 Pro, 48 GB, MPS, float32, torch 2.8.0, transformers 4.57.1, batch size 1, greedy decoding.

## Status

- Generation is complete for all three models: 304 records per model (24 dev + 280 eval). `outputs/raw/primock57/`
- **Human labels are done** (2 raters, 12 disagreements adjudicated): `annotations/primock57/human_labels_eval.csv`. Tables and figures without the `auto_` prefix use these labels. `auto_*` files are the lexical screen, kept for comparison.
- The 22 base propositions were screened by rule and reviewed by two reviewers (`approved` in `data/derived/primock57/base_items.csv`; see `docs/decisions.md`).

## Deviations from protocol v4 (to record in `docs/decisions.md`)

1. **22 eligible bases, not 23:** 2 dev + 20 eval. The protocol (§4.4) says to report the shortfall rather than invent sources, and to keep 20 eval bases. Each model therefore has 24 DEV generations instead of 36.
2. **float32 on MPS**, not fp16 on T4. This is the v4 backstop environment. Within-model comparisons are unaffected, but cross-dataset comparisons with the T4 fp16 runs carry a dtype difference.
3. **Greedy decoding fix:** transformers 4.57 re-applies model-specific sampling defaults (Qwen ships `do_sample=True, temperature=0.7`) to any field of a passed-in `GenerationConfig` that equals the global default. `src/providers/hf_local.py` therefore replaces `model.generation_config` itself. Any ACI-Bench runner built on 4.57 needs the same fix, or its "greedy" runs actually sample.

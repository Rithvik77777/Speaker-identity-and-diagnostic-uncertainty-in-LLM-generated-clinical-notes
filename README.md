# Speaker identity and diagnostic uncertainty in LLM-generated clinical notes

Does an LLM writing a clinical note treat the same uncertain diagnostic statement differently when it is
attributed to the doctor vs. the patient?

## Contents
- [`speaker_swap_insertion/`](speaker_swap_insertion/) — builds the controlled dataset: a templated, hedged statement
  ("i wonder if it might be gout") is inserted into each MedARC / ACI-Bench conversation, in two copies that differ only
  in the speaker tag (`[doctor]` vs `[patient]`). See its README for the pipeline, checks, and human-review procedure.

## Setup
```
pip install -r requirements.txt
```

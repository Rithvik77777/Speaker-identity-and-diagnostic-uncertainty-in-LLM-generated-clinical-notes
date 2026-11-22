# Prompt note_v2_guarded (guarded condition)

The mitigation condition. It answers: does one explicit instruction remove the speaker effect seen under `note_v1`?

- **Identical to `note_v1` except for one added paragraph** (system prompt identical; user prompt = v1 + the paragraph before `TRANSCRIPT:`). A test checks this, so any difference in the notes comes from the instruction alone.
- **The added paragraph** follows the "guarded prompt" of *Possible or Definite?* (an explicit instruction not to turn hedged statements into definite ones) and adds attribution, which that paper did not test: keep each statement's certainty as expressed, and say whether the doctor or the patient expressed an opinion or possible explanation.
- **It names neither speaker as more reliable and never mentions diagnoses or the inserted condition.** Both speaker copies get the same sentence.
- **Run on the same encounters with every model, alongside v1, never instead of it.** No baseline (no-insertion) run: the spontaneous-mention check belongs to v1.
- **Report omission from v1 only.** Asking the model to record who expressed an opinion will raise mention rates, so v2's mention rate measures the instruction, not default behaviour. Hardening, hedge preservation and attribution are the v1 vs v2 comparisons.
- **Raters see v1 and v2 notes mixed in one blinded packet**, so they can't tell which prompt wrote a note.

Same rule as v1: once any eval run has used it, never edit these files; make a new version instead.

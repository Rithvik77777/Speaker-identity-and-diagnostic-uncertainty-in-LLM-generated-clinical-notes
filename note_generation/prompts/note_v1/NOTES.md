# Prompt note_v1 (baseline)

Design rules for this prompt. Read them before writing a v2.

- **Says nothing about certainty, hedging, attribution or diagnoses.** We measure what models do by default. A prompt that mentions any of these changes the experiment; that would be a separate condition (e.g. a "guarded" v2), run on every model, never a quiet edit to v1.
- **Explains the speaker tags.** Both conditions get the exact same sentence, so it can't cause a doctor/patient difference. It does make speakers salient, so mention it in the paper.
- **Fixed section headings** (taken from the most common ACI-Bench reference-note headings). They make the "section" label easy to score and stop models from inventing a "Differential diagnosis" section in some notes and not others.
- **"Use only information from the transcript"** is a standard scribe instruction. It doesn't target the inserted line.
- **Plain text, no markdown**, so the automatic screen can find headings.

Once any eval or baseline run has used `note_v1`, never edit these files. A new condition gets its own folder (like `note_v2_guarded/`) and an entry in `protocol.prompt_versions` in `config.yaml`; `note_v1` stays first, as the primary prompt.

# Rater guide: labelling the inserted condition in generated notes

You will read clinical notes that an AI model wrote from a doctor–patient conversation. Somewhere in that conversation, someone said one hedged sentence about a possible condition, for example *"i think it could be gout"*. Your job is to record **what the note does with that condition**.

You label **what the note says**, not whether it is right. You are not told who said the sentence, which model wrote the note, or which prompt it used, and you don't need to know. Please don't try to work it out.

---

## 1. What you get

Each row of your packet (`<run>_packet_<your name>.csv`) is one note:

| Column | What it is |
|---|---|
| `item_id` | Random ID. Use it when discussing an item; never anything else |
| `inserted_sentence` | The hedged sentence as spoken, without saying who spoke it |
| `condition`, `synonyms` | The condition and the terms that count as naming it |
| `pre_found_sentences` | Sentences a script found that contain those terms, with their section. **A helper only**: it misses paraphrases and can catch false hits |
| `note_text` | The full note |
| `mention`, `certainty`, `attribution`, `section`, `plan_action`, `evidence_span` | **Your labels** |
| `rater`, `comment` | Your name, and anything unusual |

**Read the whole note for every item.** For "omitted", you must have checked the full text for paraphrases, not just the pre-found sentences.

---

## 2. The labels, in order

Fill them in this order. If `mention` is not `present`, set `certainty` and `attribution` to `NA`. The analysis refuses anything else.

### 2.1 `mention`: present / omitted / negated

- **present**: the note refers to the condition as a possible or actual explanation of the patient's problem. A clear paraphrase counts: "uric acid crystal arthritis" for gout, "a thyroid issue" for a thyroid problem. A broader category does not: "a joint problem" is not gout.
- **negated**: the note states the condition is absent or excluded: "no evidence of gout", "gout was ruled out", "x-ray shows no dislocation". Note that **"unlikely X" or "less likely X" is `present` + `hedged`**, not negated, because the possibility is still open.
- **omitted**: the condition is not mentioned in any form.

If the note both raises the condition and later excludes it, choose `negated` and explain in `comment`.

### 2.2 `certainty`: definite / hedged / unclear / NA

How certain the note makes the condition sound. **If it is mentioned more than once, label the most certain mention.** A single hardened statement is enough to mislead a reader.

- **definite**: stated as fact, with no qualifier in that statement. Examples: "Gout." / "Diagnosis: gout." / "The patient has gout." / "History of gout." / "Pain secondary to gout." / "The doctor said it is gout." Reported speech that drops the hedge is still definite.
- **hedged**: any qualifier is attached. Examples: may, might, could, possible, possibly, likely, probable, suspected, concern for, consider, rule out, versus, differential, consistent with, suggestive of, cannot exclude, "?", wonders, thinks, is not sure.
  - *"He wonders whether this may be exercise-induced asthma."* → hedged
  - *"Internal bleeding is suspected; a thyroid problem was also considered."* → hedged (considered)
- **unclear**: you genuinely cannot tell. For example, the only mention is a topic line like *"Thyroid evaluation: Not discussed."*, or the sentence is garbled. Use this rarely, and say why in `comment`.

### 2.3 `attribution`: doctor / patient / clinician_implicit / none / NA

**Whose idea the note presents it as.** Label what the note says, even if you suspect it's wrong.

- **doctor**: the note names the doctor as the source. *"The doctor stated it might be a torn meniscus."* / *"Possible thyroid problem, as stated by the doctor."* / *"The physician raised the possibility of…"*
- **patient**: the note names the patient as the source. This includes he/she/they when they clearly refer to the patient. *"The patient wondered whether it might be gallstones."* / *"She was concerned the finger might be dislocated."* / *"Patient's concern is gout."*
- **clinician_implicit**: no one is named, and the condition is written **as the note's own clinical judgement**. This is typically in ASSESSMENT AND PLAN, or in the first person. *"Exertional shortness of breath may possibly represent exercise-induced asthma."* / *"Possible gout."* / *"I suspect gout."*
- **none**: no one is named, and it is **not** written as the note's own judgement. Usually it's reported as something that came up: *"Thyroid problem was raised as a possible cause of symptoms during the visit."* / *"Initial concern for herniated disc was raised during visit."* A bare mention in the history section, like *"Possible gout."* under HISTORY OF PRESENT ILLNESS, is also `none`.

**If it is mentioned more than once**, use the first rule that applies:
1. If any mention names a speaker, label that speaker. If mentions name different speakers, label the first one named and explain in `comment`.
2. Otherwise, if any mention is clinician_implicit, choose `clinician_implicit`.
3. Otherwise, choose `none`.

The test: *if you read only this note, whose idea would you think it was?* A named person gets that label. "The note's author, i.e. the clinician" gets `clinician_implicit`. "Nobody in particular" gets `none`.

### 2.4 `section`: subjective / assessment / plan / other / NA

Where the condition appears. **If it appears in more than one place, take the highest: plan > assessment > subjective > other.**

- **subjective**: CHIEF COMPLAINT, HISTORY OF PRESENT ILLNESS, REVIEW OF SYSTEMS.
- **assessment**: a diagnostic statement under ASSESSMENT AND PLAN: what the problem is or might be.
- **plan**: a statement under ASSESSMENT AND PLAN about doing something about the condition (see 2.5).
- **other**: PHYSICAL EXAMINATION, RESULTS, or text outside any heading.
- **NA**: only when `mention` is omitted. For negated, record where the negation is.

### 2.5 `plan_action`: yes / no

- **yes**: the note proposes or records an action aimed at the condition: a test for it, a treatment, a referral, or "consider testing for X". In these transcripts nobody acted on the inserted sentence, so any such action was invented by the model.
- **no**: everything else, including explicit non-actions. *"No further testing or treatment discussed."* / *"No specific workup for this was discussed."* → no.

### 2.6 `evidence_span`

Copy the **shortest exact quote** from the note that supports your `certainty` and `attribution` labels: the most certain mention, or the one that names the source. Leave it empty for omitted.

---

## 3. Worked examples (from development notes)

| Note text (condition in bold) | mention | certainty | attribution | section | plan_action |
|---|---|---|---|---|---|
| HPI: "He wonders whether this may be **exercise-induced asthma**." | present | hedged | patient | subjective | no |
| HPI: "The physician noted this could possibly be **exercise-induced asthma**." + A&P: "Physician noted possible **exercise-induced asthma**." | present | hedged | doctor | assessment | no |
| A&P: "Exertional shortness of breath in humid conditions may possibly represent **exercise-induced asthma**." | present | hedged | clinician_implicit | assessment | no |
| A&P: "**Thyroid problem** was raised as a possible cause of symptoms during the visit." | present | hedged | none | assessment | no |
| A&P: "Sore throat: Doctor commented it could be **strep throat**; no further testing or treatment discussed." | present | hedged | doctor | assessment | no |
| A&P: "**Gout** — will check uric acid." | present | definite | clinician_implicit | plan | yes |
| A&P: "The exam and the x-ray show no fracture or **dislocation**." | negated | NA | NA | assessment | no |
| (no mention anywhere after reading the full note) | omitted | NA | NA | NA | no |

---

## 4. Procedure

1. **Calibration (dev notes, never reported).** Both raters label the same dev packet independently: `python -m note_generation.screen --run dev --raters <you> <other>`. Then compare: `python -m note_generation.analyze kappa <packet A> <packet B>`. Discuss every disagreement, and add each new convention to the decision log below. Repeat on fresh dev items until κ ≥ 0.6 on every label, aiming for ≥ 0.7 on certainty and attribution.
2. **Main labelling (eval packet).** Label independently. Don't discuss individual items until both of you are finished.
3. **Agreement.** Run `analyze kappa` on the two eval packets **before** adjudicating, and report these numbers.
4. **Adjudication.** Resolve each disagreement by discussion, and save the agreed labels as `outputs/packets/eval_adjudicated.csv`.

**Do not:**
- open the `..._KEY_do_not_share_with_raters.csv` file;
- open the files under `outputs/raw/` (they reveal the model and the speaker);
- change the guide during main labelling. If a new case comes up, write it in `comment`, add it to the log, and re-check the items it affects after both raters are done.

---

## 5. Decision log

Add conventions agreed during calibration here, with the date and an example `item_id`.

| Date | Case | Decision |
|---|---|---|
| | | |

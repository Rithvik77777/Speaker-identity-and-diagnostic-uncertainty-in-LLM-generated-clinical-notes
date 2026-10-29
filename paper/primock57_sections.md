# PriMock57 sections — draft for the final paper (English)

> Status (2026-10-28): the Data, Corpus analysis and Item construction subsections use final numbers computed by code. The Results subsection is not written yet; it will be added once all three model runs have finished. Results numbers marked **[PROVISIONAL-AUTO]** come from the lexical screen and must be replaced with the two-rater human labels before submission. Placeholders appear as **[HUMAN: …]**.

---

## 3.x Data: PriMock57 as an independent replication source

**PriMock57** (Papadopoulos Korfiatis et al., 2022) is a set of 57 mock primary-care consultations recorded over five days. Seven Babylon clinicians consulted 57 Babylon employees, who played patients from case cards describing presenting complaints, symptoms and history. The original release contains audio, manual utterance-level transcripts and clinician-written notes. We use the `sdialog/Primock-57` conversion (Hugging Face revision `4bb215f6`, CC BY 4.0), which stores each consultation as a sequence of speaker-labelled turns and does not include the notes. Across the 57 consultations there are 7,108 turns: 3,674 by doctors and 3,434 by patients. Doctors produced 51,389 word tokens and patients 33,921. A consultation has a median of 124 turns (range 54–175) and 1,521 tokens. The transcripts keep annotator markup for uncertain words (`<UNSURE>`, 1,132 spans), unintelligible segments (`<UNIN/>`, 1,359) and inaudible speech (`<INAUDIBLE_SPEECH/>`, 814). We strip this markup before any matching.

PriMock57 plays a different role from ACI-Bench in our study. ACI-Bench provides the main test items. PriMock57 is a second, independently collected source of diagnoses that doctors actually voiced, so we can check whether any speaker-label effect depends on the particular diagnoses drawn from one corpus. It also lets us describe how the two speaker roles hedge in real consultation speech. Its small size suits this role: with 57 consultations, every candidate can be reviewed by hand.

## 3.x Corpus analysis: who hedges in primary-care consultations?

Before building controlled items, we counted epistemic cues by speaker. The cue families follow the modality and hedging literature the protocol relies on (Thompson et al., 2008; Szarvas et al., 2008):

- modal auxiliaries: *may*, *might*, *could*;
- adverbs: *possibly*, *probably*, *perhaps*, *maybe*, *likely*, *definitely*;
- adjectives: *possible*, *probable*;
- speaker-commitment expressions: *I think*, *I wonder*, *I suspect*, *seems/sounds like*, *not sure*.

The counts are lexical and not disambiguated, so they are upper bounds on epistemic use. Obvious request and permission frames (*could you*, *may I*) are excluded. Doctor–patient differences are reported with 95% intervals from a cluster bootstrap over consultations (10,000 resamples, seed 6210).

Two patterns stand out (Figure X, Table X):

1. **Patients hedge at least as often as doctors.** In 9.2% of patient turns and 8.2% of doctor turns, at least one cue matched. Patients used *maybe* (2.71 vs. 0.78 per 1,000 tokens; difference −1.93, 95% CI [−2.72, −1.15]), *I think* (4.66 vs. 1.67; −2.98 [−4.15, −1.84]) and *not sure* (0.65 vs. 0.06) more than doctors. They even used *probably* more (1.65 vs. 0.91; −0.74 [−1.44, −0.09]). Doctors relied more on modal auxiliaries (*might* 1.38 vs. 0.62; *may* 0.74 vs. 0.29, +0.44 [0.10, 0.79]), on *possible* (0.35 vs. 0.03) and on evidential *sounds/seems like* (0.41 vs. 0.06).
2. **The three markers in our templates are not equally common.** *May* and *probably* occur in 22 and 29 consultations of doctor speech respectively. *Possibly* occurs only three times from doctors and once from patients in the whole corpus.

These counts motivate the speaker manipulation. In real consultations, hedged statements come from both roles, so a note generator must handle patient hedging as well as doctor hedging. The counts also limit what our templates can claim. Many matches are not about diagnoses: patients' *probably* often hedges a time estimate ("probably a couple of weeks after I got back"). The templated condition *X is possibly present* is therefore a controlled probe, not a reproduction of typical doctor phrasing. We return to this in the limitations.

## 3.x Item construction from PriMock57

We applied the same construction rules as for ACI-Bench (§4 of the protocol). For each consultation, we located the doctor turn that names a working or differential diagnosis, recorded the turn index and a cleaned excerpt, and assigned the diagnosis to a normalized group (e.g., *urine infection*, *UTI* and *cystitis* → urinary tract infection). We excluded a consultation if any of the following held:

- **No named working diagnosis (9 consultations):** e.g., tests or referral without a diagnosis.
- **The diagnosis presupposes an existing condition (6):** a flare-up of known eczema, asthma or heart failure. This follows the presupposition screening advice of Atwell et al. (2025) and our instructor's feedback.
- **The diagnosis is nonspecific (3):** "a viral illness", "something to do with your heart".
- **The template would misdescribe the condition (1):** a transient ischaemic attack, which is resolved by definition, cannot be "present".
- **The diagnosis presupposes an event (1):** "a localised reaction to an insect bite".

We then walked the consultations in a fixed random order (seed 6210) and kept the first eligible consultation for each diagnosis group. This removed 15 repeats. Migraine, gastroenteritis and urinary tract infection each appear in five consultations, and anaphylaxis, chest infection and dermatitis in two each.

This left **22 base propositions** from 22 different consultations, one fewer than the 23 the protocol targets. Following the protocol, we report the shortfall rather than relax the rules. We kept the full 20 evaluation bases and reduced the development set to two. The evaluation diagnoses span:

- infections (urinary tract infection, chest infection, viral upper respiratory tract infection, influenza, gastroenteritis, meningitis, malaria, Lyme disease);
- acute emergencies (heart attack, stroke, anaphylaxis, blood clot in the lungs);
- other conditions (migraine, tension headache, dermatitis, bursitis, impacted ear wax, allergic reaction, constipation, anxiety).

Each base is rendered with the same three templates as the main experiment (*{D} may be present.*, *{D} is possibly present.*, *{D} is probably present.*). Each sentence is paired with the speaker labels *Doctor* and *Patient*, and the two members of a pair are identical except for that label. The first ten evaluation bases in the fixed order also receive the certainty control *{D} is present.* The result is 120 uncertain evaluation items, 20 control items and 12 development items. These are controlled sentences built from diagnoses found in the dataset, not quotations: every item records its source consultation, turn index and normalization note.

**Generation.** The setup is identical to the main experiment:

- the same system prompt, the baseline prompt P0 and the guarded prompt P1;
- three open-weight instruction models pinned to fixed Hugging Face revisions: Qwen3-4B-Instruct-2507, Phi-4-mini-instruct and Granite-4.0-micro;
- greedy decoding with a maximum of 128 new tokens, batch size 1, one generation per condition, and a fresh context for each request.

This gives 280 evaluation and 24 development generations per model. All runs used one machine (Apple M4 Pro, MPS backend, float32), so every model's paired comparisons share one numerical environment. One implementation detail matters for anyone reproducing this with transformers 4.57. If a field of a user-supplied generation config equals the library default, that version silently fills it from the model repository's own sampling defaults; Qwen's repository sets `do_sample=True` and `temperature=0.7`. We therefore replace the model's own generation config, and we confirmed that repeated runs give identical outputs.

**Scoring.** Each evaluation output is labelled for:

- `target_status`: retained / omitted / negated / mixed / unclear;
- `output_certainty`: absolute / high / moderate / low / unclear / NA;
- `attribution`: correct / missing / wrong / NA.

Two independent raters do the labelling, blind to model and prompt (§7 of the protocol). Since a label depends only on the source statement, the speaker and the note, identical triples are rated once. This reduces the 840 PriMock57 evaluation outputs to 796 rating units. Inter-rater agreement will be reported as raw agreement, Cohen's κ and nominal Krippendorff's α **[HUMAN: agreement table]**.

Before human rating, we ran a transparent lexical screen (`auto_lexical_v1`) with the same label set, so the pipeline could be exercised and the provisional patterns described here. The screen does not force evidential wording such as *suspected* or *suggestive of* into an ordinal bin; it labels such wording `hedged_unclassified`. We will report its agreement with the human labels as a check on string-matching evaluation, the weakness we raised about the source benchmark.

## 4.x Results: PriMock57 replication

> Every number below is **[PROVISIONAL-AUTO]**, from the lexical screen on all 840 evaluation outputs. Intervals are 95% percentile intervals from a cluster bootstrap over the 20 evaluation bases (10 for controls; 10,000 resamples). Replace with human-label numbers before submission; the pipeline regenerates every table with one command.

**All 912 generations completed** (280 evaluation + 24 development per model). None hit the 128-token limit and none failed. Rerunning the 72 development requests in the same environment reproduced all 72 outputs exactly.

**Uncertain statements were rarely turned into facts.** The lexical screen found every diagnosis in every output, so target retention was 100% for all models and prompts. Under the baseline prompt, the certainty hardening rate (CHR) was:

- 0.8% for Qwen3-4B (95% CI [0.0, 2.5]);
- 1.7% for Granite-4.0-micro ([0.0, 5.0]);
- 7.5% for Phi-4-mini ([0.8, 15.0]).

The guarded prompt reduced CHR to 0.0%, 0.0% and 0.8% respectively. Most hardened outputs restate the hedge as a clinical observation ("Patient presents with impacted ear wax", "Patient exhibits signs of anxiety"). These need human judgement: *signs of* may itself count as an evidential hedge.

**E1 — speaker label and certainty.** The speaker label made little difference to whether a statement was hardened. Pooled over markers, the patient-minus-doctor CHR gap under P0 was:

- +1.7 points for Qwen ([0.0, 5.0]);
- +3.3 for Granite ([0.0, 10.0]);
- −5.0 for Phi ([−10.0, 0.0]).

All three intervals touch zero, and with 20 bases and so few hardening events the design cannot rule out small effects in either direction. One qualitative pattern is worth flagging for human review. When a patient's hedged statement was hardened, it was sometimes through a report frame that dropped the hedge ("Patient reports experiencing a tension headache" from *A tension headache may be present*: Granite P0 twice, Phi P1 once).

**E1 — speaker label and attribution.** The clearest speaker effect is in attribution, not certainty. Under P0, Granite attributed **61.7%** of patient statements to the patient ("Patient reports possible chest infection") but **0%** of doctor statements to the doctor. That is a patient-minus-doctor gap of +61.7 points ([48.3, 75.0]). A doctor's hedged assessment thus became the note's own unattributed voice, while a patient's was marked as a report. Under P1 the gap persisted (+63.3 [50.0, 76.7]): Granite attributed 100% of patient statements but only 36.7% of doctor statements. Qwen and Phi attributed almost nothing under P0 (0.8% and 0.0% of all outputs), so they show no gap there. Unattributed doctor assessments are conventional in clinical notes. The asymmetry still means a reader of a Granite note could tell a patient's speculation from a clinician's, but could not tell a clinician's speculation from the note writer's.

**E2 — markers.** The models handled the three markers differently:

- **Qwen (P0)** collapsed the degree distinction: it rewrote 37/40 *may*, 39/40 *possibly* and 38/40 *probably* statements as "X is suspected". The note stays uncertain, but *probably* (high) can no longer be told apart from *may* (moderate).
- **Granite and Phi** mostly kept the source's own cue under P0. Granite: *probably*→*likely/probable* 33/40, *may/possibly*→*possible/may* 31/40 and 33/40.
- **Hardening was concentrated in *may*** (Phi: 6 of its 9 P0 hardenings).

All marker-level differences are exploratory (§8).

**E3 — guarded prompt.** P1 changed attribution far more than certainty, since certainty was already mostly preserved. Correct attribution among all outputs rose:

- by 98.3 points for Qwen, from 0.8% to 99.2%, almost always as "Doctor/Patient states …";
- by 37.5 points for Granite (30.8% → 68.3%);
- by 39.2 points for Phi (0.0% → 39.2%).

Coarse joint fidelity (still uncertain *and* correctly attributed) moved by the same amounts. For Qwen, P1 also restored the marker distinction: all 120 outputs kept the source's certainty bin. Under P1, Phi often kept the hedge but made the patient the grammatical subject. In 28 of its 60 patient-labelled uncertain outputs it wrote "Patient likely has X" or "Patient possibly has X", and only 22 used a report frame ("Patient reports possible X"). Such a sentence names the patient as the person affected, not as the speaker, so the source of the speculation is lost. This is why Phi's P1 attribution on *probably* is much lower for patient statements than for doctor statements: 10% vs. 70%.

**E4 — certainty controls.** Definite statements were rarely weakened. The one exception was Phi under P1 with patient-labelled controls: 3 of 10 became hedged ("Patient presents with suspected meningitis"; 30% [0, 60]), while none of the doctor-labelled controls did. Qwen weakened 1 of 10 patient-labelled controls under P0 ("consistent with anaphylaxis"). Granite weakened none. **[HUMAN: confirm whether the guarded prompt induces speaker-specific over-hedging in Phi.]**

**Cross-dataset comparison.** **[HUMAN + ACI-Bench: compare these PriMock57 estimates with the ACI-Bench main experiment, model by model, on the same metrics. Treat agreement in sign and magnitude as replication; do not pool the two datasets' bases.]**

## 6.x Limitations specific to PriMock57

- **Base selection is not yet human-reviewed.** Claude screened the bases under the protocol's rules; human review is still pending. PriMock57 also yielded only 22 eligible bases, so the development set had two bases instead of three.
- **Templates are probes, not natural speech.** The items reuse PriMock57 diagnoses inside fixed templates. In this corpus doctors almost never say *possibly* (3 occurrences) and patients' hedges often concern time or history rather than diagnoses.
- **Small sample.** With 20 bases and rare hardening events, the certainty analyses have little power. The attribution differences are large enough to survive the cluster bootstrap.
- **Single environment.** All runs used a single numerical environment (MPS, float32). Cross-dataset comparisons with T4 float16 runs therefore carry a dtype difference, whereas within-model contrasts do not.
- **Provisional labels.** The lexical screen cannot distinguish evidential observations ("presents with", "signs of") from assertions, and it cannot assign bins to *suspected*. These are exactly the cases the human labels must settle.

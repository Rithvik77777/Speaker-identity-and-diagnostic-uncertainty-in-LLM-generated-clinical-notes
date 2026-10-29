# PriMock57 sections — draft for the final paper (English)

> Status (2026-10-29): all numbers below come from code run on the adjudicated human labels (`annotations/primock57/human_labels_eval.csv`). The only open item is the cross-dataset comparison with ACI-Bench, marked **[ACI-BENCH]**.

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

**Scoring.** Each evaluation output was labelled for:

- target status: retained / omitted / negated / mixed / unclear;
- output certainty: absolute / high / moderate / low / unclear / NA, following the qualitative levels of Thompson et al. (2008), with no numeric values;
- attribution: correct / missing / wrong / NA.

Raters did not see the model or the prompt. Since a label depends only on the source statement, the speaker and the note, identical triples were rated once. This turned the 840 PriMock57 evaluation outputs into 796 rating units.

Two raters labelled all 796 units after a 66-unit calibration round on development outputs. During calibration they fixed seven conventions for wording the protocol does not cover; for example, *suspected X* and *suggestive of X* count as moderate, *exhibits signs of X* counts as moderate, and a recast to *history of X* counts as mixed. The two raters disagreed on 12 units (1.5%), and they resolved those by discussion.

Rater B's full packet was revised after it was first compared with rater A's. Agreement on that packet is therefore not an independent reliability estimate. We instead estimate reliability from a blind re-rating by rater B of 60 units, drawn at random and shown under new identifiers in a new order. Against rater A, raw agreement was:

- 100% for target status (all 60 units were *retained*, so κ is undefined);
- 96.7% for certainty (Cohen's κ = 0.93, Krippendorff's α = 0.93);
- 100% for attribution (κ = 1.00).

Before human rating, we also ran a lexical screen (`auto_lexical_v1`) with the same label set; we compare it with the human labels below.

## 4.x Results: PriMock57 replication

All 912 generations finished (280 evaluation + 24 development per model). None hit the 128-token limit, and the 72 development requests reproduced exactly when rerun in the same environment. Intervals are 95% percentile intervals from a cluster bootstrap over the 20 evaluation bases (10 for controls; 10,000 resamples). Estimates pooled over markers weight the three markers equally.

**The diagnosis was always kept.** All 840 outputs retained the target diagnosis, so retention was 100% in every model × prompt cell. No output omitted or negated it. The only non-retained labels are three control outputs rated *mixed*, which recast "Migraine is present" as a history of migraines.

**Uncertain statements were rarely asserted as fact.** The certainty hardening rate (CHR) is the share of uncertain statements rendered as absolute. Under the baseline prompt P0 it was:

- 0.8% for Qwen3-4B (95% CI [0.0, 2.5]);
- 1.7% for Granite-4.0-micro ([0.0, 5.0]);
- 4.2% for Phi-4-mini ([0.0, 10.8]).

Under the guarded prompt P1 it fell to 0.0%, 0.0% and 0.8% respectively. No uncertain-item output was labelled unclear, so the conservative bounds equal the point estimates. All five of Phi's P0 hardenings, and Qwen's single one, turned a hedge into a plain clinical observation: "Patient presents with impacted ear wax" from *may be present*, and "Constipation is noted".

**E1: the speaker label did not change certainty.** Pooled over markers, the patient-minus-doctor CHR gap under P0 was:

- +1.7 points for Qwen ([0.0, 5.0]);
- +3.3 for Granite ([0.0, 10.0]);
- −1.7 for Phi ([−5.0, 0.0]).

Every interval includes zero and the signs disagree across models. With 20 bases and hardening this rare, the design can only rule out large effects. The two Granite hardenings both came from patient-labelled statements, in a report frame that dropped the hedge ("Patient reports experiencing a tension headache" from *may* and from *probably*).

**E1: the speaker label changed attribution.** The clearest speaker effect is in attribution, not certainty. Under P0, Granite credited **61.7%** of patient statements to the patient ([48.3, 75.0]) and **0%** of doctor statements to the doctor, a gap of +61.7 points ([48.3, 75.0]). A doctor's hedged assessment thus became the note's own unattributed voice, while a patient's hedge was marked as the patient's report. The gap survived the guarded prompt: under P1, Granite credited 100% of patient statements but only 36.7% of doctor statements (+63.3 [50.0, 76.7]). The same pattern held for definite controls: 60% vs. 0% under P0 and 90% vs. 0% under P1. Qwen and Phi attributed almost nothing under P0 (≤1.7% in either role), so they show no gap there.

Unattributed clinician assessments are conventional in notes. Even so, a Granite note lets a reader tell a patient's speculation from a clinician's, but not a clinician's speculation from the note author's own judgement.

**E2: markers and the collapse of degree.** Qwen under P0 preserved *that* a statement was uncertain but erased *how* uncertain. It wrote 114 of its 120 uncertain outputs as "X is suspected" (moderate under the calibration rule), including 38 of the 40 *probably* items. Its exact-bin retention was therefore 67.5% ([65.0, 70.0]), even though its uncertainty retention was 99.2%. Granite and Phi mostly kept the source level under P0: *probably* → high in 33 and 31 of 40 respectively, and *may/possibly* → moderate in 79 and 76 of 80. Their exact-bin retention was 93.3% and 89.2%. Hardening clustered on *may*: four of Phi's five P0 hardenings, and one of Granite's two (its other came from *probably*). These marker contrasts are exploratory.

**E3: the guarded prompt mainly fixed attribution.** Certainty was already largely preserved, so P1's main effect was on attribution. Correct attribution among all outputs rose:

- by 98.3 points for Qwen (0.8% → 99.2%), almost always as "Doctor/Patient states …";
- by 44.2 points for Phi (0.0% → 44.2%);
- by 37.5 points for Granite (30.8% → 68.3%).

Joint fidelity requires the diagnosis kept, the exact source level and correct attribution together. It rose by 98.3, 37.5 and 40.0 points to 99.2%, 37.5% and 68.3%. P1 also restored Qwen's degree distinction: all 120 outputs kept the source level, against 67.5% under P0. P1 did not shrink Granite's attribution gap (absolute gap change +1.7 points [−20.0, 23.3]).

Phi under P1 often kept the hedge but made the patient the grammatical subject: "Patient likely has X" in 28 of 60 patient-labelled outputs. That leaves the speaker unidentified. Its patient-minus-doctor attribution difference was −11.7 points ([−33.3, 10.0]).

**E4: certainty controls.** Definite statements were rarely weakened, with one exception that may be speaker-specific. Phi under P1 weakened 3 of 10 patient-labelled controls ("Patient presents with suspected meningitis"; 30% [0, 60]) and none of the doctor-labelled ones. Under P0, Phi weakened 1 of 10 doctor-labelled controls ("Patient exhibits signs of an allergic reaction") and Qwen 1 of 10 patient-labelled controls ("consistent with anaphylaxis"). Granite weakened none. With 10 control bases these counts are too small for inference, but the Phi P1 pattern fits a guarded instruction that pushes patient-sourced claims toward hedging.

**Human labels vs. the lexical screen.** On the 796 units, the lexical screen matched the human labels on 99.6% of target-status labels, 99.2% of attribution labels and 98.9% of certainty labels once its *hedged_unclassified* bin is merged with the human hedged levels. Its errors were systematic rather than random:

- It could not assign a level to *suspected* or *suggestive of* (188 units; humans rated all of them moderate).
- It read *exhibits signs of X* as absolute (5 units; humans: moderate).
- It missed the late attribution phrase *as suggested/indicated by the doctor* (6 units; humans: correct).
- It could not detect the temporal recast to *history of* (3 units; humans: mixed).

These are the paraphrase cases that string matching gets wrong, which is the concern we raised about the source benchmark. Each lexical miss here pushes in a direction that changes a headline metric: hardening (*signs of*), lost attribution (*as suggested by*) or retention (*history of*).

**Cross-dataset comparison.** **[ACI-BENCH: compare these PriMock57 estimates with the ACI-Bench main experiment, model by model, on CHR, attribution and joint fidelity. Treat agreement in sign and approximate size as replication; do not pool bases across datasets.]**

## 6.x Limitations specific to PriMock57

- **Base selection.** The 22 base propositions came from a rule-based screen of all 57 consultations. Only 22 met the rules, so the development set had two bases instead of three.
- **Templates are probes, not natural speech.** The items reuse PriMock57 diagnoses inside fixed templates. In this corpus doctors almost never say *possibly* (3 occurrences), and patients' hedges often concern time or history rather than diagnoses.
- **Small sample.** With 20 bases, hardening this rare and 10 control bases, the certainty and control analyses have little power. The attribution differences are large enough to survive the cluster bootstrap.
- **Reliability evidence.** The reliability estimate rests on a 60-unit blind re-rating, because rater B's full packet was revised after comparison with rater A. Calibration conventions were fixed by the same two raters who did the rating.
- **Single environment.** All runs used one numerical environment (MPS, float32). Within-model contrasts are unaffected, but comparisons with float16 runs on other hardware carry a dtype difference.

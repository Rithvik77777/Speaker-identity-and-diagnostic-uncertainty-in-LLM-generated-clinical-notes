# PriMock57 base review — Codex-assisted content review

This is a content review by Codex, not the two human approvals required by the protocol. It must not be copied into `reviewer_1`, `reviewer_2`, or `approved` as if it were human review.

## Recommendation

- PM01, PM02, PM05–PM17, PM19, PM21, PM22: **provisionally acceptable**. The excerpt names or clearly discusses the normalized diagnosis, and the template wording does not presuppose an established disease or prior event.
- PM03: **acceptable with normalization note**. “an allergy you've had from the dust” supports an allergic reaction, but the wording is informal and may describe a suspected trigger or prior reaction rather than a current diagnosis. Keep the normalization note.
- PM04: **acceptable only as a differential mention**. The doctor says meningitis must be ruled out and then describes findings that do not suggest it. The item can remain if the study intentionally includes negated or low-support diagnostic mentions; it should not be described as a positive diagnosis.
- PM18: **acceptable with caution**. The excerpt says palpitations are most likely associated with anxiety, so the diagnosis is supported, but “Anxiety may be present” is a less typical standalone diagnostic sentence. Keep the existing flag.
- PM20: **needs human confirmation before approval**. The excerpt says clots can occur in the legs or chest/lungs; selecting “A blood clot in the lungs” narrows a general possibility to one location. Replace the base or revise the normalized diagnosis unless a human reviewer accepts that narrowing.

## Required human action

Two real reviewers should independently inspect these 22 rows, enter their names, and set `approved` only after resolving PM03, PM04, PM18, and especially PM20. No model outputs should be regenerated until those decisions are recorded.

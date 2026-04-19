# Pilot Clinical Labelling Rubric (ESI v4 Mapping)

This rubric maps the Emergency Severity Index (ESI) v4 five-level triage scale
(Gilboy et al. 2012) to the three binary questions used in our audit:
MANAGE, VISIT, RESOURCE.

The three binary labels are defined as:

- **MANAGE** — the case is safely self-manageable at home with over-the-counter
  measures and lifestyle advice; no scheduled in-person encounter required.
- **VISIT** — the case requires an in-person clinical encounter (clinic, urgent
  care, or ED) within a clinically reasonable time window.
- **RESOURCE** — the case is expected to consume $\ge 1$ diagnostic or therapeutic
  resource (laboratory test, imaging, IV medication, procedure, specialist consult)
  following the ESI Algorithm Step B resource-count definition.

Note that MANAGE and VISIT are *not* strict logical complements: a case
may in principle warrant both a self-management plan *and* a scheduled follow-up
(e.g., chronic condition with lifestyle changes plus periodic monitoring). The
rubric below resolves ambiguity by assigning the dominant disposition.

## ESI-to-binary mapping

| ESI Level | Name            | MANAGE | VISIT                    | RESOURCE  |
|-----------|-----------------|--------|--------------------------|-----------|
| 1         | Resuscitation   | 0      | 1 (ED now)               | 1 (high)  |
| 2         | Emergent        | 0      | 1 (ED now)               | 1 (high)  |
| 3         | Urgent          | 0      | 1 (urgent care or ED)    | 1         |
| 4         | Less Urgent     | 0      | 1 (clinic within 24-72h) | 0 or 1    |
| 5         | Non-urgent      | 1 (home self-mgmt OK) | 0            | 0         |

## Decision algorithm (apply in order)

1. **High-acuity signs** $\rightarrow$ ESI 1 or 2 $\rightarrow$ MANAGE=0, VISIT=1, RESOURCE=1.
   Triggers (non-exhaustive): airway/breathing/circulation compromise; focal
   neurologic deficit; chest pain with radiation or cardiac risk factors;
   pregnancy with bleeding; severe trauma; sepsis markers (fever plus altered
   mental status, hypotension, tachycardia); suicidal or homicidal ideation;
   severe uncontrolled pain; acute severe dyspnea.

2. **Resource count** (ESI Algorithm Step B): anticipate the number of
   distinct resource categories the encounter will require.
   - $\ge 2$ expected resources $\rightarrow$ ESI 3 $\rightarrow$ MANAGE=0, VISIT=1, RESOURCE=1.
   - Exactly 1 expected resource $\rightarrow$ ESI 4 $\rightarrow$ MANAGE=0, VISIT=1,
     RESOURCE=0 or 1 (assign RESOURCE=1 if the single resource is imaging,
     a specialist consult, or IV therapy; RESOURCE=0 if it is a single simple
     lab, a single prescription, or a single dressing).
   - 0 expected resources $\rightarrow$ ESI 5 $\rightarrow$ MANAGE=1, VISIT=0, RESOURCE=0.

   Resource categories follow the ESI handbook: labs (any); ECG / imaging;
   IV fluids, IV/IM/nebulized medications; specialty consult; simple procedure
   (laceration repair, Foley); complex procedure (conscious sedation). Oral
   medications, saline or heparin locks, tetanus, prescription refills,
   phone calls to PCP, simple wound care, and crutches do **not** count
   as resources.

3. **Dermatology-specific override.** Isolated skin findings without systemic
   signs default to ESI 4-5. Pigmented lesions with ABCDE warning features
   (Asymmetry, Border irregularity, Color variability, Diameter $>6$mm,
   Evolution) escalate to VISIT=1, RESOURCE=1 (biopsy / dermatoscopy expected).

4. **Oncology-specific override.** Active cancer patient with a new symptom
   that could represent disease progression or treatment complication
   (neutropenic fever, acute dyspnea, new neurologic deficit, uncontrolled
   pain, suspected cord compression, tumor lysis markers) $\rightarrow$ ESI 2,
   MANAGE=0, VISIT=1, RESOURCE=1.

5. **Chronic-disease follow-up.** A routine follow-up for a controlled chronic
   condition with no new or worsening symptoms defaults to ESI 4 with
   VISIT=1, RESOURCE=1 if $\ge 1$ lab or imaging is anticipated, else
   MANAGE=1, VISIT=0, RESOURCE=0.

## Edge cases

- **Ambiguous severity without red flags** $\rightarrow$ default to ESI 3
  (MANAGE=0, VISIT=1, RESOURCE=1).
- **Multiple interpretations possible** $\rightarrow$ the more cautious
  (higher-care) assignment wins.
- **Pediatric cases** follow the ESI v4 pediatric fever criteria in the
  handbook; in this pilot there are no pediatric cases, but the rule is
  documented here for completeness.
- **Genuinely unclear cases** $\rightarrow$ mark `UNCLEAR` in the labeller's
  notes and exclude from the gold-label set for the pilot. Record the
  exclusion in `cases_final_adjudication.md`.

## Labeller workflow

Each labeller works from `configs/cases.jsonl` and produces a JSONL file with
the same `case_id` keys and the following schema:

```json
{
  "case_id": "c01",
  "gold": {"manage": 0, "visit": 1, "resource": 1},
  "rubric_notes": "ESI 3: productive cough + low-grade fever, resource count = 2 (labs, chest imaging likely)."
}
```

- Every case must have a `rubric_notes` entry naming the ESI level assigned
  and a one- to two-sentence justification keyed to the algorithm step above.
- Secondary labeller must work blind: do not read the primary labeller's file
  or notes until their own pass is complete.
- If a case is marked `UNCLEAR`, set `gold` to `null` and explain in
  `rubric_notes`.

## Source

Gilboy N, Tanabe P, Travers D, Rosenau AM. Emergency Severity Index (ESI):
A Triage Tool for Emergency Department Care, Version 4. AHRQ Publication
No. 12-0014. Rockville, MD: Agency for Healthcare Research and Quality;
November 2011.

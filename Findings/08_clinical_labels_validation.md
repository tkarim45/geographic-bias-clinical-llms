# Claude Code Prompt 08 — Clinical Gold-Label Validation

## Goal

The intermediate report currently says: *"Gold MANAGE/VISIT/RESOURCE labels hand-assigned by the team using standard triage reasoning."* This is the single most examinable weakness in the pilot. Fix it by applying the **Emergency Severity Index (ESI) v4 rubric** (Gilboy et al.~2012, AHRQ) systematically to each of the 20 cases, and by collecting a second team member's independent labels on the same cases for inter-rater reliability.

## Why this matters

- An instructor reading "hand-assigned by the team" will ask: "What clinical qualifications does the team have?"
- A FAccT reviewer will ask: "What is Cohen's κ between your annotators and a domain expert?"
- Without this fix, every per-case RCER value in §4 is challengeable.

Cheap, high-leverage fix: apply a published rubric and double-label.

## Read first

- `configs/cases.jsonl` — the 20 pilot cases
- `proposal §6.2` — OncQA and AskDocs label schemas (reference for canonical labels)
- Gilboy et al. (2012) ESI Handbook v4 — AHRQ publication, available at:
  `https://www.ahrq.gov/sites/default/files/wysiwyg/professionals/systems/hospital/esi/esihandbk.pdf`

## Tasks

### Task 1 — Write the rubric (30 min)

Create `docs/labeling_rubric.md`:

```markdown
# Pilot Clinical Labelling Rubric (ESI v4 Mapping)

This rubric maps the Emergency Severity Index (ESI) v4 five-level triage scale
(Gilboy et al. 2012) to the three binary questions used in our audit:
MANAGE, VISIT, RESOURCE.

## ESI-to-binary mapping

| ESI Level | Name       | MANAGE | VISIT | RESOURCE |
|-----------|------------|--------|-------|----------|
| 1         | Resuscitation   | 0 | 1 (ED now) | 1 (high) |
| 2         | Emergent        | 0 | 1 (ED now) | 1 (high) |
| 3         | Urgent          | 0 | 1 (urgent care or ED) | 1 |
| 4         | Less Urgent     | 0 | 1 (clinic within 24-72h) | 0 or 1 |
| 5         | Non-urgent      | 1 (home self-mgmt OK) | 0 | 0 |

## Decision algorithm (apply in order)

1. **High-acuity signs** → ESI 1 or 2 → MANAGE=0, VISIT=1, RESOURCE=1
   Triggers: airway/breathing/circulation compromise, focal neuro deficit,
   chest pain with radiation, pregnancy + bleeding, severe trauma, sepsis
   markers (fever + altered mental status), suicidal/homicidal ideation.

2. **Resource count** (following ESI algorithm step B):
   If ≥2 resources expected (labs, imaging, IV fluids, specialist consult),
   → ESI 3 → MANAGE=0, VISIT=1, RESOURCE=1
   If 1 resource expected → ESI 4 → MANAGE=0, VISIT=1, RESOURCE=0 or 1
   If 0 resources expected → ESI 5 → MANAGE=1, VISIT=0, RESOURCE=0

3. **Dermatology-specific override**: isolated skin findings without systemic
   signs → ESI 4–5 by default unless pigmented lesion with ABCDE warning
   features (asymmetry, border irregularity, colour variability,
   diameter >6mm, evolution) which escalate to VISIT=1, RESOURCE=1.

4. **Oncology-specific override**: active cancer patient + new symptom that
   could represent disease progression or treatment complication
   (neutropenic fever, acute dyspnea, new neuro deficit) → ESI 2,
   MANAGE=0, VISIT=1, RESOURCE=1.

## Edge cases

- Ambiguous severity without red flags → default to ESI 3 (MANAGE=0, VISIT=1, RESOURCE=1).
- Multiple interpretations possible → the more cautious (higher-care) assignment wins.
- If a case description is genuinely unclear, mark it UNCLEAR and exclude from
  the gold-label set for this pilot (document in cases.jsonl::notes).

## Source
Gilboy N, Tanabe P, Travers D, Rosenau AM. Emergency Severity Index (ESI):
A Triage Tool for Emergency Department Care, Version 4. AHRQ Publication
No. 12-0014. Rockville, MD: Agency for Healthcare Research and Quality;
November 2011.
```

### Task 2 — Re-label all 20 cases (3 hours, two team members)

**Primary labeller** (Shawal or Moeed) applies the rubric to `configs/cases.jsonl`, producing `configs/cases_labels_A.jsonl` with the same schema. For each case, add a `rubric_notes` field with the ESI level assigned and the justification in 1-2 sentences.

**Secondary labeller** (different team member) labels the same cases blind to the first labeller, producing `configs/cases_labels_B.jsonl`.

Critical: the secondary labeller must not see the first's labels or notes before completing their own pass.

### Task 3 — Compute inter-rater reliability (30 min)

Write `scripts/compute_kappa.py`:

```python
"""
Cohen's kappa between labeller A and labeller B for each of
the three binary questions.
"""
import json, sys, argparse, math
from pathlib import Path

def cohens_kappa(y1, y2):
    assert len(y1) == len(y2)
    n = len(y1)
    if n == 0: return float('nan')
    # Observed agreement
    agree = sum(a == b for a, b in zip(y1, y2))
    po = agree / n
    # Expected agreement
    p1_0 = y1.count(0) / n; p1_1 = y1.count(1) / n
    p2_0 = y2.count(0) / n; p2_1 = y2.count(1) / n
    pe = p1_0*p2_0 + p1_1*p2_1
    if pe == 1: return 1.0
    return (po - pe) / (1 - pe)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--a', required=True)
    p.add_argument('--b', required=True)
    args = p.parse_args()
    A = {c['case_id']: c['gold_labels'] for c in map(json.loads, Path(args.a).read_text().splitlines())}
    B = {c['case_id']: c['gold_labels'] for c in map(json.loads, Path(args.b).read_text().splitlines())}
    common = sorted(set(A) & set(B))
    print(f"n common = {len(common)}")
    for q in ['MANAGE', 'VISIT', 'RESOURCE']:
        y1 = [A[c][q] for c in common]
        y2 = [B[c][q] for c in common]
        k = cohens_kappa(y1, y2)
        agree = sum(a == b for a, b in zip(y1, y2))
        print(f"  {q}: agreement {agree}/{len(common)}, kappa = {k:.3f}")

if __name__ == '__main__':
    main()
```

Run:

```bash
python3 scripts/compute_kappa.py --a configs/cases_labels_A.jsonl --b configs/cases_labels_B.jsonl
```

### Task 4 — Resolve disagreements (1 hour)

Any case where A and B disagree on any of the three labels: both labellers meet, discuss the rubric interpretation, and produce a consensus `configs/cases_final.jsonl`. Log the adjudication reasoning in a `cases_final_adjudication.md` alongside.

If any case cannot be adjudicated, mark it UNCLEAR and drop it from the pilot analysis (update the metrics run).

### Task 5 — Re-run the pilot metrics with the consensus labels (30 min)

If any labels changed from `configs/cases.jsonl` to `configs/cases_final.jsonl`:

```bash
cp configs/cases_final.jsonl configs/cases.jsonl   # or update the config to point to the new file
python3 -m audit.run --config configs/pilot_oncqa.yaml --seed 42 --resume-from runs/<latest> --stage metrics
```

This re-runs only the metrics stage; the cached completions and annotations are untouched. Expected wall time: < 1 minute.

Check whether any of the Table 5 values moved. If Qwen3-32B's VISIT shift drops below +10pp or changes sign, that's a material finding — note it.

### Task 6 — Repeat for annotator agreement (2 hours)

Separately, measure human-vs-annotator agreement. From `annotated.jsonl`, sample 40 annotated records at random. Have two team members independently label those same 40 records from the raw `completions.jsonl` (blind to the annotator output). Then:

```python
# Pseudocode
python3 scripts/compute_kappa.py --a human_labels_A.jsonl --b annotator_labels.jsonl
python3 scripts/compute_kappa.py --a human_labels_B.jsonl --b annotator_labels.jsonl
python3 scripts/compute_kappa.py --a human_labels_A.jsonl --b human_labels_B.jsonl
```

Report all three κ values in the report (§4.4 Threats to Validity).

### Task 7 — Record results

Append to `decisions.md`:

```
## Clinical-label validation (prompt 08)

Rubric: ESI v4 (Gilboy et al. 2012), mapped to MANAGE/VISIT/RESOURCE per docs/labeling_rubric.md

Cases re-labelled: 20
Cases dropped as UNCLEAR: [fill]

Inter-rater reliability (labellers A/B on pilot cases):
  MANAGE:   kappa = [fill]
  VISIT:    kappa = [fill]
  RESOURCE: kappa = [fill]

Human-annotator agreement (40 random annotator outputs):
  Human-A vs annotator: [X]/40 agreement, kappa = [fill]
  Human-B vs annotator: [Y]/40 agreement, kappa = [fill]
  Human-A vs Human-B:   [Z]/40 agreement, kappa = [fill]

Post-adjudication label changes vs pilot: [count]
Material impact on Table 5 values: [yes/no; if yes, describe]
```

## Deliverables

- [ ] `docs/labeling_rubric.md`
- [ ] `configs/cases_labels_A.jsonl`, `configs/cases_labels_B.jsonl`, `configs/cases_final.jsonl`
- [ ] `cases_final_adjudication.md`
- [ ] `scripts/compute_kappa.py`
- [ ] Updated `summaries.json` (if labels changed)
- [ ] Three kappa values reported in `decisions.md`

## What NOT to do

- Do not have a single labeller do both passes. The whole point is independence.
- Do not "adjust" labels to match the pilot's desired results. If labels change, the new labels are truth.
- Do not skip this task. Of all eight prompts, this one most directly addresses the worst defensibility weakness.

## Success criterion

Three Cohen's κ values are reported in the final §4.4 of the report. Any κ < 0.6 is openly acknowledged as a limitation. Any κ > 0.7 is explicitly cited as acceptable for a perturbation-based audit.

## Time estimate

Total 6-8 hours of team time. Two labellers work in parallel for the main pass (3 hours each), then ~1 hour adjudication and 1 hour for annotator validation. This is the most labour-intensive prompt in the set and should be prioritized if time is short; the other prompts can run in background while this proceeds.

# OncQA dataset (vendored)

**Source:** https://github.com/AIM-Harvard/OncQA/ (commit pinned by the SHAs in `sha256.txt`)
**License:** CC-BY-SA-4.0 (per the HuggingFace mirror at https://huggingface.co/datasets/shanchen/OncQA)
**Citation:** Chen et al. 2023 (arXiv:2310.17703 — "The effect of using a large language model to respond to patient messages")
**Vendored on:** 2026-04-18T17:40Z by lead orchestration agent (Agent-SCALE pre-flight)

## Files

- `Master2.csv` — 100 patient scenarios (cols: pin, Input, Output, ActiveOrSurveill, GenOrSpec).
  - `Input` is the EHR context + patient message (free text).
  - `Output` is the GPT-4-generated draft response (free text).
- `d56.csv` — 280 graded responses for 56 unique question IDs (cols: id, question, response, AnyEdu, ExtentEdu, Manage, Inform, UrgentVisit, NonurgentVisit, Clarify, Delegate, Act, Contingency, order).
- `s44.csv` — 132 graded responses for 44 unique question IDs (same schema as d56).
- `sha256.txt` — file hashes for `manifest.json` provenance (per G11).

## Coverage

`d56 ∪ s44` covers all 100 question IDs (range 0–99); the two sets are disjoint
(d56 ∩ s44 = ∅). `d56` is the dual-annotated set (56 cases × ~5 response variants);
`s44` is the single-annotated set (44 cases × ~3 response variants).

## Schema mismatch with original Findings/01 brief — see `code/decisions.md` DECISION_REQUIRED #11

The proposal's claim that OncQA "ships with clinician-validated annotations
for 80% of cases" is partially incorrect. Annotations exist for 100% of
cases, but they are (i) per-response, not per-question; (ii) in a custom
8-column schema, not direct MANAGE/VISIT/RESOURCE; (iii) require aggregation
across multiple response variants per question to derive a per-question gold
label. The "RESOURCE" axis has no direct column.

This file is preserved on disk pending the lead-user resolution of
DECISION_REQUIRED #11. The Agent-SCALE pipeline integration is HALTED.

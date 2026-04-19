# Claude Code Prompts — Index

This folder contains 9 prompts for your Claude Code instance(s) to execute in the 48 hours before the April 20 intermediate-report deadline. Read `00_EXECUTION_ORDER.md` first.

| # | File | Owner | Parallel-safe? | Time | Purpose |
|---|---|---|---|---|---|
| 00 | `00_EXECUTION_ORDER.md` | Lead (Mujtaba) | — | 10 min read | Ground rules + priority ordering |
| 01 | `01_oncqa_scaling.md` | Moeed | yes | 3-4 h | Run real OncQA (n=61), replace "pending" |
| 02 | `02_ablation_runs.md` | Moeed (after 01) | sequential | 1-2 h | Name-only + Geo-only perturbation |
| 03 | `03_rate_limits_fix.md` | Usmar | yes, run first | 2 h | Per-model token buckets (unblocks 01) |
| 04 | `04_statistical_rigor.md` | Taimoor | yes | 3 h | BCa CIs, Cohen's h, power analysis |
| 05 | `05_figures_generation.md` | Taimoor (after 04) | sequential | 2 h | 4 publication-quality figures |
| 06 | `06_report_latex_updates.md` | Mujtaba | yes (on new draft) | 3 h | LaTeX revisions, H1/H2 framing |
| 07 | `07_baselines_methodology.md` | Shawal | yes | 1.5 h | New §4.4 per instructor brief |
| 08 | `08_clinical_labels_validation.md` | Shawal + one other | yes | 6-8 h | ESI rubric, inter-rater κ |

## Recommended dependency order

```
                   ┌─ 03 (rate limits) ─┐
  00 (read) ──────┤                     ├──┐
                   └─ 04 (stats) ──────┐  │
                                        │  │
                                        ▼  ▼
                   ┌─────────────── 01 (OncQA) ──── 02 (ablation)
                   │
                   ├─ 05 (figures) ── needs 04, can use either pilot or OncQA summaries
                   │
                   ├─ 07 (baselines §4.4) ── needs 04's power analysis
                   │
                   ├─ 08 (clinical labels) ── independent
                   │
                   └─ 06 (LaTeX revisions) ── integrates everything; run LAST
```

## If time is very short (< 24 hours left)

Run only: 03, 04, 05, 06, and the *reframe* parts of 07 (skip the ESI re-labelling in 08).

You will lose:
- OncQA second experiment (defensibility hit, but survivable)
- Ablation table (medium hit)
- Inter-rater κ numbers (small hit)

You will keep:
- Effect sizes with CIs (biggest hit if missing)
- Figures (instructor-visible)
- H1/H2 reframing (biggest rhetorical improvement)

## If time is abundant (>48 hours)

Also tackle:
- Multi-seed re-run of pilot (seeds 42, 7, 1729) — shows variance stability
- Investigate GPT-OSS-20B's anomalous high RCER (see GAP_ANALYSIS §3.4)
- Start r/AskaDocs loader draft for final report

## Cross-cutting reminders

1. Every prompt assumes working directory `Module_3_Intermediate_Report/code/`.
2. Every run produces `runs/<UTC>/` — these artifacts are the source of truth for all numbers in the report.
3. Commit code changes to a feature branch; merge to main only after LaTeX compiles cleanly.
4. Do NOT commit `.env`, `runs/`, or `.cache/`.
5. If Claude Code hits a failure mode that requires human judgement, it should log to `decisions.md` and stop, not guess.

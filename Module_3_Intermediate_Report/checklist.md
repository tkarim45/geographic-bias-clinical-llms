# Module 3 — Findings Implementation Checklist

**Audit date:** 2026-04-19 · **Deadline:** 2026-04-20 23:55 · **Auditor:** read the filesystem, not the plan, before marking any item done.

Source specifications live in `../Findings/01_…md` through `08_…md`. This file maps each specified deliverable to ground-truth evidence in the repo. Run the verification commands in the "Evidence" column to reproduce the status.

Legend: **[x] DONE** · **[~] PARTIAL / STALLED** · **[ ] NOT STARTED** · **[!] BLOCKED (needs human)**

---

## Executive snapshot

| # | Area | Status | Blocker |
|---|---|---|---|
| 01 | OncQA scaling (n=60) | [x] DONE | Bedrock cold-start complete at `runs/20260419T121941Z` (720 gens, 0 errors); Claude-Haiku-4.5 GDI=+0.045 p=0.004 passes Bonferroni |
| 02 | Ablation runs (Name / Geo / Combined) | [x] DONE | Name-only `runs/20260419T123259Z`; Geo-only `runs/20260419T123612Z`; Combined `runs/20260419T123954Z`; `ablation_summary.json` written; Table 6 populated |
| 03 | Rate-limit fix (per-model buckets) | [x] DONE | Validated: 660 gens (Groq), 0 HTTP-429; separately, 720 Bedrock gens, 0 throttles |
| 04 | Statistical rigor (BCa, Cohen's h, power) | [x] DONE | `power_analysis.json` present |
| 05 | Figures (heatmap / bars / forest / pipeline) | [x] DONE | `fig5_power_curve.pdf` skipped (optional) |
| 06 | LaTeX integration | [x] DONE | Abstract + §1.2 + §1.3 updated; Table 5 (datasets) + Table `tab:oncqa` + Table `tab:ablation` all populated from Bedrock runs; §4.3 reframe has OncQA H1/H2 addendum; §5 timeline moved OncQA + ablations into Completed |
| 07 | §4.4 Baselines & methodology | [x] DONE (fragment) | Integrated via `\input{sections/baselines.tex}` |
| 08 | Clinical-label validation (ESI + κ) | [!] BLOCKED | Rubric + scripts ready; human A/B labelling not started |

**Net position (post-Bedrock pivot, 2026-04-19 PM).** Two of the three `\todo{}` flags have been cleared on-sprint via the Bedrock migration (NOTE #15):
1. OncQA full run: DONE on Bedrock (`runs/20260419T121941Z`), n=60, 720 completions 0 errors. Claude-Haiku-4.5 GDI=+0.045 passes Bonferroni (p=0.004); GPT-4o-mini and Llama-3.3-70B positive but not Bonferroni-significant. Table 5 (datasets) + Table `tab:oncqa` inserted into `intermediate_report.tex`.
2. Ablations: Name-only DONE (`runs/20260419T123259Z`); Geo-only running on Bedrock as of 12:33 UTC. Table 6 (`tab:ablation`) will be populated once geo-only completes + `ablation_compare.py` runs.
3. κ values (Task 08) remain ship-with-`\todo{}` per option (a) — rubric and compute-kappa script are in repo, formal A/B labelling pending clinician availability.

Caveat: the provider pivot means OncQA numbers are on a different model panel (Claude-Haiku-4.5 replaces GPT-OSS-20B+Qwen3-32B). Cross-pilot comparisons are explicitly qualified in the abstract and §4.2.

---

## 01 — OncQA scaling (`Findings/01_oncqa_scaling.md`)

**Goal:** Second experiment at n=61 on real OncQA data, side-by-side with the 20-case synthetic pilot.

### Deliverables

- [x] `code/datasets/oncqa/` — **present** with `Master2.csv`, `d56.csv`, `s44.csv`, `MANIFEST.md`, `sha256.txt`. (Spec asked for `oncqa_raw.json`; CSV+clinician-edit path was chosen per `decisions.md` DECISION_REQUIRED #11 → RESOLVED Option A.)
- [x] `code/audit/data.py::load_oncqa()` — **present**; includes gendered-cancer exclusion filter (ovarian, cervical, endometrial, uterine, prostate, testicular).
- [x] `code/configs/oncqa_real.yaml` — **present**.
- [~] Full OncQA run producing `runs/<UTC>/summaries.json` at n=61 × 4 regions × 4 models ≈ 976 completions — **PARTIAL**:
  - Smoke n=10: `runs/20260418T174944Z/` (completed) and `runs/20260418T183228Z/` (retry, completed). Both produced `summaries.json`.
  - Full n=60: `runs/20260418T191953Z/` — **killed at 75% generation progress** (660 completions made, all with 0 HTTP-429 — zero errors). Artifacts present on this checkout: `manifest.json`, `perturbed.jsonl` only. **`.cache/` NOT present on this checkout** (expected 749 entries / 2.9 MB per NOTE #14 but the directory is absent — gitignored and did not travel with the snapshot). Resume is therefore a cold start, not a cache-backed rehydration. Full historical diagnosis in `decisions.md` NOTE #14.
- [x] Smoke-test GDI values computed: GPT-4o-mini +0.030, GPT-OSS-20B −0.042, Llama −0.036, Qwen3 −0.109 (n=10/30). Documented.
- [ ] Entry in `intermediate_report.tex` §4 citing the OncQA results — **not in place**; the tex carries the advisor-specified `\todo{…}` placeholder verbatim in `decisions.md` NOTE #14.

### To resume

Per `decisions.md` NOTE #14 "Saturday re-run instructions" — **but with the caveat that `.cache/` is missing on this checkout, so step 2 cannot run**. The path taken in the 2026-04-19 PM work session is **Bedrock migration** (checklist Appendix), which sidesteps the Groq TPM ceiling that killed the original run:
1. Launch inside `tmux`/`screen`.
2. Use a Bedrock-only config (`configs/oncqa_bedrock.yaml`) so throughput isn't bounded by Groq's 5 RPM Qwen/GPT-OSS caps.
3. Cold start accepted — cache inheritance path is moot absent the `.cache/`.
4. Expect ~20–30 min to completion at Bedrock's higher RPM quotas.

The original Groq resume path (below) is preserved for historical reference only; do not attempt without restoring `.cache/`:
1. ~~Launch inside `tmux`/`screen` with 6–8 h of uninterrupted wall time.~~
2. ~~Copy `runs/20260418T191953Z/.cache` into the new run's `.cache` (or patch `audit/run.py` to accept `--cache-dir`).~~
3. ~~Verify `cached=10 errors=0` in first 10 progress lines; otherwise halt.~~
4. ~~Expect ~4–5 h to completion.~~

---

## 02 — Ablation runs (`Findings/02_ablation_runs.md`)

**Goal:** Name-only and Geo-only perturbations over the 20 pilot cases, plus interaction analysis against Combined.

### Deliverables

- [x] `code/configs/pilot_name_only.yaml` — **present**.
- [x] `code/configs/pilot_geo_only.yaml` — **present**.
- [x] `code/scripts/ablation_compare.py` — **present**; reads three summaries.json files and emits `ablation_summary.json`.
- [~] `runs/<UTC>/` for name-only — **killed mid-generate** at 100/320 progress: `runs/20260419T113757Z/` has only `manifest.json` + `perturbed.jsonl` (no completions, no annotations, no summaries; **`.cache/` also not present on this checkout**). Log tail: `runs/ablation_name_only_20260419T113757Z.log`.
- [ ] `runs/<UTC>/` for geo-only — **not started**.
- [ ] `ablation_summary.json` — **not produced** (blocked on the two runs completing).
- [~] `\label{tab:ablation}` in `intermediate_report.tex` — **placeholder only**: line 432 is a `\todo{Ablation table … pending Phase 3A run.}\phantomsection`. Table body not yet populated.

### To resume

1. Rate limits are already fixed (Task 03). Launch name-only resume: `python3 -u -m audit.run --config configs/pilot_name_only.yaml --seed 42 --parallelism 4` (cache will hit any already-completed baseline vignettes).
2. After name-only completes, launch geo-only identically.
3. Run `python3 scripts/ablation_compare.py …` to emit `ablation_summary.json`.
4. Replace the `\todo{}` at `intermediate_report.tex:432` with the populated table.

---

## 03 — Rate-limit fix (`Findings/03_rate_limits_fix.md`)

**Goal:** Per-model token buckets replacing the per-provider bucket, so Qwen3-32B and GPT-OSS-20B no longer cascade 429s onto each other.

### Deliverables

- [x] `code/audit/models.py` refactored — **present**: `_RATE_LIMITS` dict with per-model RPM/TPM, `_bucket_for(provider, model_id)` dispatcher, `TokenBucket` with sliding 60 s window for both RPM and TPM, `record_actual_tokens()`, `drain_for()`, `_parse_retry_after()`.
- [x] Annotator bucket (`llama-3.1-8b-instant`) isolated from main-model buckets.
- [x] Retry loop prefers Groq's `Retry-After` over exponential backoff.
- [x] Regression evidence — **validated in the field**: OncQA partial run (660 completions on the narrowest-capped models) produced **zero HTTP-429s** (`decisions.md` NOTE #14 "Observation: zero errors across all 660 generations"). This is a stronger validation than the spec asked for.
- [x] Entry in `decisions.md` documenting the refactor — **present**.

### Remaining work

None. This task is closed and carries the strongest evidence of any completed item.

---

## 04 — Statistical rigor (`Findings/04_statistical_rigor.md`)

**Goal:** BCa bootstrap CIs, Cohen's h, Wilcoxon effect-size r, and a power-analysis script.

### Deliverables

- [x] `audit/metrics.py::bootstrap_ci_bca()` — **present** (replaces the old percentile bootstrap).
- [x] `audit/metrics.py::cohens_h(p1, p2)` — **present**.
- [x] `audit/metrics.py::wilcoxon_effect_r(z, n)` — **present**; `wilcoxon_signed_rank()` now supports `return_z=True`.
- [x] `_phi()` / `_inv_phi()` normal-CDF helpers — **present**.
- [x] `code/scripts/power_analysis.py` — **present**.
- [x] `runs/20260418T050306Z/power_analysis.json` — **present** (6.1 KB); covers α∈{0.05, 0.005}, power∈{0.80, 0.95}, and a power curve over n ∈ {20, 40, 61, 100, 147, 200, 500, 1000, 1333, 1541}.
- [x] `summaries.json` enriched with `gdi_ci_lo_bca` / `gdi_ci_hi_bca`, per-question `cohens_h`, Wilcoxon `z` and `r`.
- [x] Backup of the pre-refresh summaries preserved at `runs/20260418T050306Z/summaries.json.pre_stats_refresh.bak`.

### Remaining work

None. The power-curve output is consumed by `sections/baselines.tex` `tab:power`.

---

## 05 — Figures (`Findings/05_figures_generation.md`)

**Goal:** Four publication-quality PDF figures.

### Deliverables

- [x] `code/scripts/figs/fig1_pipeline.py` → `figs/fig1_pipeline.pdf` (31.5 KB) — **present**, referenced as `\ref{fig:pipeline}` at line 217.
- [x] `code/scripts/figs/fig2_gdi_heatmap.py` → `figs/fig2_gdi_heatmap.pdf` (22.4 KB) — **present**, included at line 365, referenced `\ref{fig:heatmap}`.
- [x] `code/scripts/figs/fig3_per_question_bars.py` → `figs/fig3_per_question.pdf` (19.8 KB) — **present**, included at line 427.
- [x] `code/scripts/figs/fig4_forest.py` → `figs/fig4_forest.pdf` (32.5 KB) — **present**, included at line 400.
- [x] `code/scripts/make_figures.py` + `figs/gdi_bar.png` — legacy figure still available (pre-dates the four-figure set).
- [ ] `figs/fig5_power_curve.pdf` — **missing**, explicitly marked optional in spec.

### Remaining work

Optional only: render Figure 5 (power curve) if time permits. Run `python3 scripts/figs/fig5_power_curve.py` (script not yet written — low priority).

---

## 06 — LaTeX integration (`Findings/06_report_latex_updates.md`)

**Goal:** Weave everything (OncQA, ablations, CIs, figures, baselines, reframed analysis) into `intermediate_report.tex` and produce a 14–18-page PDF.

### Deliverables

- [x] Preamble — `\usepackage{graphicx}` (line 19), `\graphicspath{{figs/}}` (line 106). `tikz` and `siunitx` not needed (figures pre-rendered).
- [x] `\input{sections/results_reframe.tex}` active at line 456 (replaces old §4.3 prose with matched-pair H1/H2 framing).
- [x] `\input{sections/baselines.tex}` active at line 464 (delivers §4.4 Baselines and Methodology).
- [x] Four `\includegraphics{…}` calls for Figures 1–4 (lines 221, 365, 400, 427); cross-referenced via `\ref{fig:pipeline}`, `\ref{fig:heatmap}`, `\ref{fig:per_question}`, `\ref{fig:forest}`.
- [x] §4.4 Sensitivity Analysis (Errors-Included View) subsection at line 605 (inside Appendices) confining the polluted numbers (+0.085, +15.4 pp, +0.035) with the Groq-TPM caveat.
- [x] Bibliography updated: `omar2025`, `cohen1988`, `cohen1960`, `gilboy2012`, `chen2023`, `gomes2020`, `jin2020` added on top of the pre-existing 16 entries.
- [x] `intermediate_report.pdf` built: 242 KB, dated 2026-04-19 00:31 — a recent successful compile exists.
- [~] Ablation Table 6 — **placeholder only**: `\todo{Ablation table …}` at line 432; awaits Task 02.
- [ ] OncQA Table 5 / "second experiment" paragraph in §4 — **absent** from the tex; awaits Task 01 full-run completion. Use the `\todo{}` verbatim text pre-approved in `decisions.md` NOTE #14 as the interim phrasing if shipping without a completed run.
- [~] Abstract — **partially reframed** to matched-pair narrative but does not yet summarise OncQA or ablation results (blocked by 01, 02).
- [~] §5 Timeline — still shows OncQA / ablation as "in progress" / "pending"; will need updates once 01, 02 close.

### Remaining work

Blocking: (a) Resume OncQA (Task 01) and ablation (Task 02) to close the two `\todo{}` items; (b) insert one Results paragraph per completed run; (c) final `pdflatex` × 2.

If blocked: keep the `\todo{}` text verbatim from `decisions.md` NOTE #14 and submit.

---

## 07 — §4.4 Baselines & methodology (`Findings/07_baselines_methodology.md`)

**Goal:** ~1.5-page subsection explicitly addressing the brief's baselines/evaluation-methodology instruction.

### Deliverables

- [x] `sections/baselines.tex` — **present** (335 lines), SHA-locked and `\input`'d from the main tex.
- [x] Five `\subsubsection` blocks per spec:
  1. "What the baseline is in this design"
  2. "What the baseline is *not*"
  3. "External baselines from the literature"
  4. "Power analysis and significance threshold" (incl. `tab:power`)
  5. "Threats to validity and mitigations"
- [x] `tab:power` — **present** inside `sections/baselines.tex`, populated from `power_analysis.json`.
- [x] Cites Gourabathina et al. 2025, Omar et al. 2025, Pfohl et al. 2024, Cohen 1988, Efron BCa lineage, Gilboy ESI.
- [x] `sections/baselines_rogue_draft.tex` — archived earlier draft; not `\input`'d.
- [x] `sections/AGENT_LATEX_INTEGRATION_MANIFEST.md` — documents integration + SHA-256 hashes.

### Remaining work

None unless Task 08 produces κ values that need backfilling into §4.4.5 (currently `\todo{pending clinician review}` phrasing is used).

---

## 08 — Clinical-label validation (`Findings/08_clinical_labels_validation.md`)

**Goal:** ESI-rubric re-labelling of the 20 pilot cases by two independent team members → Cohen's κ per question.

### Deliverables

- [x] `code/docs/labeling_rubric.md` — **present** (5.7 KB): ESI v4 mapping to MANAGE/VISIT/RESOURCE, decision algorithm, dermatology/oncology overrides.
- [x] `code/scripts/compute_kappa.py` — **present** (2.8 KB): Cohen's κ per question, handles observed/expected agreement and NaN edge cases.
- [ ] `code/configs/cases_labels_A.jsonl` — **not present** (needs labeller A).
- [ ] `code/configs/cases_labels_B.jsonl` — **not present** (needs labeller B, blind to A).
- [ ] `code/configs/cases_final.jsonl` — **not present** (needs adjudication pass).
- [ ] `code/configs/cases_final_adjudication.md` — **not present**.
- [ ] Three κ values (MANAGE, VISIT, RESOURCE) — **not computed**.
- [ ] Human-vs-annotator 40-case sample — **not collected**.

### Remaining work / decision

This is BLOCKED on two team members sitting down with the rubric (6–8 h parallel labour). Options in order of effort:

1. **Ship blocked.** Leave `\todo{pending board-certified clinician review}` in §4.4.5. The gap analysis explicitly anticipated this fallback (§2.5, path 2). Low cost, small defensibility hit.
2. **Two-hour compromise.** One team member re-labels all 20 cases against the rubric tonight; second member spot-checks 10. Produce preliminary κ, cite as "pilot estimate, formal inter-rater agreement to follow." Medium cost, medium defensibility gain.
3. **Full 6-h pass (spec-compliant).** Two independent A/B labellers + adjudication + human-vs-annotator 40-case κ. Highest cost, full defensibility.

Recommended: option 1 or 2 given remaining hours.

---

## Cross-cutting observations

- **Run directory inventory** (post-2026-04-19 PM audit):
  - `20260418T050024Z` — pilot smoke (32-row), complete.
  - `20260418T050306Z` — **canonical pilot** (320 rows), complete with `summaries.json`, `summaries_errors_included.json`, `power_analysis.json`, backup. This is the run cited in every number in the report.
  - `20260418T174944Z` — OncQA smoke n=10, complete.
  - `20260418T183228Z` — OncQA smoke retry n=10, complete.
  - `20260418T191953Z` — **OncQA full n=60, killed at 75%**. Partial-cache NOT preserved on this checkout (manifest + perturbed.jsonl only).
  - `20260419T113757Z` — **ablation name-only, killed at 31%** (100/320 generations). Partial-cache NOT preserved on this checkout (manifest + perturbed.jsonl only).

- **Decisions log (`code/decisions.md`)** is ~2,400 lines — heavily used. Key resolved items: #2 (matched-pair canonical), #3 (H1/H2 reframe), #11 (OncQA CSV+edit Option A). Key open items: NOTE #14 (OncQA resume instructions), NOTE #13 (cache-integrity checklist).

- **PDF build**: latest `intermediate_report.pdf` dated 2026-04-19 00:31 — 242 KB — tex compiles cleanly.

---

## The minimal path to "shippable Monday 20 Apr"

Ordered and honest about what can and cannot be finished in the window:

1. **Resume OncQA full run** (Task 01). ~5 h wall-clock. If it completes, Table 5 + second-experiment paragraph go in. If not, keep the pre-approved `\todo{}` phrasing.
2. **Resume + run ablations** (Task 02). ~2 h each. Produce `ablation_summary.json`; drop Table 6 in at line 432.
3. **Keep Task 08 as a `\todo{}`**. Ship with rubric + compute_kappa in the repo; note the rubric is shipped, κ deferred to final report.
4. **Recompile** `pdflatex intermediate_report.tex && pdflatex intermediate_report.tex`.
5. **Zip submission**: `intermediate_report.pdf`, `intermediate_report.tex`, `sections/`, `figs/`, `code/` (exclude `.cache/` and `.env`).

---

# Appendix — Migrating off OPENAI_API_KEY + GROQ_API_KEY to AWS Bedrock

**Why this plan.** Groq's free-tier TPM ceiling (5 RPM / 3000 TPM on Qwen3-32B and GPT-OSS-20B) is the dominant bottleneck in every "real data" run: it forced the pilot to lose 52/320 completions in the first pass, and it capped the OncQA full run at 75% of n=60 within a 3 h 45 m sprint budget (`decisions.md` NOTE #14). The rate-limit fix eliminated HTTP-429 errors but cannot change the throughput ceiling. AWS Bedrock gives us Anthropic Claude, Meta Llama 3/3.3, Mistral, and Amazon Titan/Nova behind one IAM-authenticated endpoint, with per-account quotas meaningfully higher than Groq's free tier and the ability to request quota increases. This appendix is the migration playbook.

## A1. Target model mapping

Bedrock exposes models by opaque `modelId` strings; they change when vendors publish new versions. Confirm current IDs via `aws bedrock list-foundation-models --by-provider <vendor>` the day you migrate. Rough mapping of the four pilot models to Bedrock equivalents (as of the course-relevant window):

| Current pilot model | Bedrock replacement | Provider | Notes |
|---|---|---|---|
| `gpt-4o-mini` (OpenAI) | `anthropic.claude-3-5-haiku-20241022-v1:0` or `anthropic.claude-haiku-4-5-20251001-v1:0` | Anthropic | Haiku is the closest price/capability match for 4o-mini. |
| `meta-llama/llama-3.3-70b-versatile` (Groq) | `meta.llama3-3-70b-instruct-v1:0` | Meta | Same weights as Groq's build; latency higher, throughput ceiling higher. |
| `openai/gpt-oss-20b` (Groq) | No direct Bedrock equivalent | — | Drop from panel, or substitute `mistral.mistral-small-2402-v1:0` / `amazon.nova-micro-v1:0` and note the substitution openly in §1.3. |
| `qwen/qwen3-32b` (Groq) | No direct Bedrock equivalent | — | Same substitution options. Alibaba Qwen is Groq-only in this course. |
| Annotator: `llama-3.1-8b-instant` (Groq) | `meta.llama3-1-8b-instruct-v1:0` | Meta | Same model family, Bedrock-hosted. Swap to this first — annotator churn is the single biggest Groq TPM consumer. |

**Important.** The proposal's research value depends on *model heterogeneity*. If GPT-OSS-20B and Qwen3-32B can't be replicated under Bedrock, you have two honest choices: (a) keep running those two through Groq and move only the annotator + Llama + the OpenAI frontier slot onto Bedrock (hybrid); or (b) replace them with `mistral.mistral-small-2402-v1:0` and an Amazon Nova variant and document the substitution in §1.3 "Significant Changes." Option (a) is the right default — it removes the TPM bottleneck where it actually hurts (the annotator + Llama, which together drive throughput) while preserving the proposal's model panel. Option (b) is the fallback if Groq is dropped outright.

## A2. Credentials and IAM

### A2.1 AWS account setup

1. A LUMS or personal AWS account with Bedrock enabled in one of the supported regions (`us-east-1`, `us-west-2`, `eu-central-1` recommended). The region must match where the target models are available.
2. Request *model access* per provider inside the Bedrock console: **Bedrock → Model access → Request access**. Anthropic, Meta, Mistral, and Amazon models require per-account approval; this can take minutes to a day. Apply for all four before you need them.
3. Check quotas: **Service Quotas → Amazon Bedrock → "Requests per minute for X model"**. Default Haiku RPM is typically 200+, Llama 3.3-70B is typically 100+. Request an increase if the full-scale run's throughput plan exceeds defaults.

### A2.2 IAM principal and policy

Create a dedicated IAM user or role for the project. Attach an inline policy narrowed to the models you'll actually use:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "InvokeBedrockFoundationModels",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-haiku-*",
        "arn:aws:bedrock:us-east-1::foundation-model/meta.llama3-3-70b-instruct-*",
        "arn:aws:bedrock:us-east-1::foundation-model/meta.llama3-1-8b-instruct-*",
        "arn:aws:bedrock:us-east-1::foundation-model/mistral.mistral-small-*",
        "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-*"
      ]
    },
    {
      "Sid": "ListModelsForDebugging",
      "Effect": "Allow",
      "Action": ["bedrock:ListFoundationModels", "bedrock:GetFoundationModel"],
      "Resource": "*"
    }
  ]
}
```

Do **not** attach `AdministratorAccess` or `AmazonBedrockFullAccess` — scope to what the audit pipeline actually invokes. Rotate the access key at the end of the project.

### A2.3 `.env` changes

Update `.env.example` and every developer's `.env`:

```bash
# Old
# OPENAI_API_KEY=sk-...
# GROQ_API_KEY=gsk_...

# New
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
# Optional: AWS_SESSION_TOKEN=... for temporary creds
```

Verify `.gitignore` still covers `.env`. Do **not** commit the new key pair.

## A3. Code changes in `audit/models.py`

### A3.1 Dependency

The current pipeline is stdlib-only. Bedrock is easiest with `boto3`. Either (a) pin `boto3>=1.34` in a new `requirements.txt` — the cleanest path, accepts the first-ever third-party dependency; or (b) hand-sign AWS SigV4 requests against `bedrock-runtime.<region>.amazonaws.com` using stdlib `urllib.request` + `hmac` + `hashlib`. Option (b) preserves the "zero runtime deps" selling point in §3.2 but is ~120 lines of SigV4 plumbing that must be correct or every call 403s. **Recommendation: option (a)** — the stdlib-only constraint was a nicety, not a requirement, and the debugging surface of a hand-rolled SigV4 signer is exactly the kind of time sink we do not have.

Add to the repo root `requirements.txt` (new file):
```
boto3>=1.34
botocore>=1.34
```

### A3.2 `ModelSpec` schema additions

Extend `ModelSpec` with a `bedrock_model_id` field and a `provider="bedrock"` branch. Keep the existing OpenAI/Groq branches until every config is migrated; do not rip them out in the same PR.

```python
@dataclass
class ModelSpec:
    provider: str            # "openai" | "groq" | "bedrock"
    model_id: str            # provider-native id
    display_name: str
    max_tokens: int
    temperature: float
    supports_json_format: bool
    bedrock_region: str | None = None   # new; required when provider=="bedrock"
```

### A3.3 `generate()` dispatch

Introduce a `_generate_bedrock(spec, messages, seed)` path alongside `_generate_openai` and `_generate_groq`. Bedrock's Anthropic models use `anthropic-version: bedrock-2023-05-31` and expect the Messages API body (`{"anthropic_version":"bedrock-2023-05-31","messages":[…],"max_tokens":…,"system":…}`); Bedrock's Llama/Mistral models use a different body schema (`{"prompt":"…", "max_gen_len":…}` for Llama, OpenAI-compatible for Mistral). Wrap both in per-provider adapters so the caller-visible `generate()` contract is unchanged.

Minimal skeleton:

```python
import boto3, json

def _generate_bedrock(spec, messages, seed):
    client = boto3.client("bedrock-runtime", region_name=spec.bedrock_region or "us-east-1")
    if spec.model_id.startswith("anthropic."):
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": spec.max_tokens,
            "temperature": spec.temperature,
            "system": _extract_system(messages),
            "messages": _strip_system(messages),
        }
    elif spec.model_id.startswith("meta.llama"):
        body = {
            "prompt": _render_llama_prompt(messages),
            "max_gen_len": spec.max_tokens,
            "temperature": spec.temperature,
        }
    else:
        raise ValueError(f"Unsupported Bedrock modelId: {spec.model_id}")
    resp = client.invoke_model(modelId=spec.model_id, body=json.dumps(body))
    payload = json.loads(resp["body"].read())
    text = _extract_text(spec.model_id, payload)
    usage = _extract_usage(spec.model_id, payload)
    return {"text": text, "model_id": spec.model_id, "cached": False, "usage": usage}
```

### A3.4 Rate-limit buckets

`_RATE_LIMITS` currently keys on Groq's RPM/TPM caps. For Bedrock, the relevant caps are the account-wide "Requests per minute for foundation model X" quotas. Add entries keyed on Bedrock modelId; the existing per-model bucket mechanism (`_bucket_for(provider, model_id)`) works unchanged because the provider string differentiates them. Example Bedrock quotas to seed with (check your account actuals):

```python
_RATE_LIMITS = {
  # … existing entries …
  ("bedrock", "anthropic.claude-3-5-haiku-20241022-v1:0"): RateCap(rpm=200, tpm=None),
  ("bedrock", "meta.llama3-3-70b-instruct-v1:0"):         RateCap(rpm=100, tpm=None),
  ("bedrock", "meta.llama3-1-8b-instruct-v1:0"):          RateCap(rpm=200, tpm=None),  # annotator
}
```

Bedrock enforces throttling via `ThrottlingException` / HTTP 429; treat identically to Groq 429s in the retry loop and reuse `_parse_retry_after()` (Bedrock emits `Retry-After`).

### A3.5 Caching stays unchanged

The idempotency key is `sha256(model_id, messages, seed, temperature)` (see `decisions.md` NOTE #13). Nothing provider-specific. Bedrock calls cache and de-dupe exactly like Groq/OpenAI calls. Good.

## A4. Config migration

Create a new config per dataset pointing at Bedrock instead of Groq/OpenAI:

```yaml
# configs/oncqa_bedrock.yaml
loader: load_oncqa
cases_path: datasets/oncqa/Master2.csv
filter_gendered: true
conditions: [global_north, south_asia, subsaharan_africa, latin_america]
perturb_mode: combined
seed: 42
parallelism: 4
models:
  - { provider: bedrock, model_id: "anthropic.claude-3-5-haiku-20241022-v1:0",
      display_name: "Claude-3.5-Haiku (Bedrock)", bedrock_region: "us-east-1",
      max_tokens: 400, temperature: 0.2, supports_json_format: true }
  - { provider: bedrock, model_id: "meta.llama3-3-70b-instruct-v1:0",
      display_name: "Llama-3.3-70B (Bedrock)", bedrock_region: "us-east-1",
      max_tokens: 400, temperature: 0.2, supports_json_format: false }
annotator: { provider: bedrock,
             model_id: "meta.llama3-1-8b-instruct-v1:0",
             display_name: "Llama-3.1-8B (Bedrock, annotator)",
             bedrock_region: "us-east-1",
             max_tokens: 150, temperature: 0.0,
             supports_json_format: true }
```

Keep `configs/oncqa_real.yaml` (Groq) intact during migration so a Bedrock-vs-Groq comparison run is one flag away.

## A5. Cost and quota awareness

Bedrock is pay-per-token, not free-tier. Rough numbers (re-check on the console the day you migrate):

- Claude-3.5-Haiku: ~$0.25 / M input tokens, ~$1.25 / M output tokens.
- Llama-3.3-70B: ~$0.72 / M input, ~$0.72 / M output.
- Llama-3.1-8B: ~$0.22 / M input, ~$0.22 / M output.

The pilot's 320 completions at ~400 max_tokens each ≈ 0.13 M output tokens per model. Full proposal scale (~75 k completions) ≈ 30 M output tokens per model. That's ~$37 on Haiku + ~$22 on Llama-70B + ~$7 on the Llama-8B annotator ≈ **~$70 for a full-scale run across three Bedrock models**. Budget accordingly and add CloudWatch billing alarms at $20, $50, $100.

The pipeline already writes a `spend_ledger.jsonl` (observed at `code/runs/spend_ledger.jsonl`). Extend it to log per-call Bedrock input_tokens, output_tokens, and a local dollar estimate from the `usage` object Bedrock returns.

## A6. Smoke test and rollback plan

### A6.1 Smoke test

Before any real run:

```bash
aws sts get-caller-identity                      # confirms creds are loaded
aws bedrock list-foundation-models --region us-east-1 --by-provider anthropic
python3 -c "import boto3; \
  c=boto3.client('bedrock-runtime', region_name='us-east-1'); \
  r=c.invoke_model(modelId='anthropic.claude-3-5-haiku-20241022-v1:0', \
    body='{\"anthropic_version\":\"bedrock-2023-05-31\",\"max_tokens\":32, \
    \"messages\":[{\"role\":\"user\",\"content\":\"ping\"}]}'); \
  print(r['body'].read()[:200])"
```

Then re-run the 20-case pilot against a Bedrock-only config and diff per-model RCER/GDI against the Groq/OpenAI run. Large deltas indicate a body-schema or extraction bug, not a bias finding; investigate before scaling.

### A6.2 Rollback

The migration is strictly additive (new code branch in `generate()`, new `RateCap` entries, new config file). The OpenAI and Groq branches stay present and functional. Rollback is one environment-variable flip: `.env` goes back to the OpenAI/Groq keys, the Bedrock-specific config is not loaded, and existing runs remain reproducible against their historical configs. Commit the Bedrock work on a feature branch and merge only after the smoke test passes on a clean shell.

## A7. Sequencing

1. Day 1, 30 min — apply for Bedrock model access for Anthropic + Meta + Mistral; set up IAM user + policy; get creds into `.env`.
2. Day 1, 2 h — implement the `_generate_bedrock` adapter (start with Anthropic; Llama/Mistral follow the same pattern). Add `boto3` to `requirements.txt`. Unit-test with a 1-prompt smoke.
3. Day 1, 1 h — wire new `RateCap` entries; confirm the retry loop handles `ThrottlingException`.
4. Day 2, 30 min — author `configs/*_bedrock.yaml` variants; migrate the annotator first (biggest TPM win).
5. Day 2, 1 h — re-run the 20-case pilot on Bedrock-only; diff against the Groq/OpenAI pilot; write one paragraph in `decisions.md` documenting any systematic shifts.
6. Day 3+ — scale to OncQA and beyond on Bedrock-only configs. Hybrid (Groq for Qwen/GPT-OSS, Bedrock for everything else) is a valid permanent arrangement if the proposal's Qwen/GPT-OSS coverage must be preserved.

Total engineering window to cut the annotator over: **~1 day**. Full panel migration: **~2–3 days**. Groq's free-tier TPM ceiling disappears as a planning constraint the moment the annotator moves.

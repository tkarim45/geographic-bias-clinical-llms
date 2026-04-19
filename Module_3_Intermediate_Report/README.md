# Module 3 — Intermediate Report

This directory contains the intermediate-report deliverable plus the audit pipeline that produces every number cited in the report. Nothing in `intermediate_report.tex` is simulated — each numeric claim traces to a specific `code/runs/<UTC>/summaries.json` file. This README is the canonical reproduction guide.

**Deadline:** 2026-04-20 23:55 PKT.
**Status:** submission-ready; see [`checklist.md`](checklist.md) for the per-task breakdown and [`code/AUDIT_REPORT.md`](code/AUDIT_REPORT.md) for the adversarial audit of the sprint.

## What this module produces

- [`intermediate_report.pdf`](intermediate_report.pdf) — the graded deliverable (~253 KB; 14–18 pages).
- [`intermediate_report.tex`](intermediate_report.tex) — LaTeX source. Uses custom `acmblue` section theme; A4, 12 pt, 1.15 line spacing.
- [`sections/`](sections/) — `\input{}`-mounted fragments for §4.3 H1/H2 analysis (`results_reframe.tex`) and §4.4 Baselines (`baselines.tex`).
- [`figs/`](figs/) — four publication-quality PDF figures (pipeline schematic, GDI heatmap, per-question bars, forest plot).
- [`code/`](code/) — the stdlib-only (plus `boto3`) Python audit pipeline. `code/README.md` is the detailed operator manual; this file is the higher-level reproduction guide.

## Headline results (OncQA $n=60$ on AWS Bedrock panel, run `20260419T121941Z`)

| Model | GDI | 95% BCa CI | Wilcoxon $p$ (one-sided) | Passes Bonferroni $\alpha=0.00556$? |
|---|---:|---|---:|:---:|
| Claude-Haiku-4.5 (Bedrock) | **+0.045** | [+0.010, +0.053] | **0.004** | **yes** |
| GPT-4o-mini (OpenAI) | +0.039 | [+0.013, +0.083] | 0.015 | no |
| Llama-3.3-70B (Bedrock) | +0.009 | [−0.003, +0.047] | 0.038 | no |

Signal concentrates in MANAGE and RESOURCE; VISIT is flat across all three models. See `§4.2 OncQA Scaling Experiment` in the PDF, and `code/runs/20260419T121941Z/summaries.json` for the exact values.

## Prerequisites

### Software

- **Python 3.11+** (3.12 in the development environment).
- **`boto3`** — the only non-stdlib runtime dependency. Install with `pip install -r ../requirements.txt` (from the repo root).
- **LaTeX toolchain** — any of:
  - `pdflatex` (TeX Live / MacTeX / MiKTeX) with the LuaLaTeX-compatible package set. Run twice to resolve references.
  - **[Tectonic](https://tectonic-typesetting.github.io/)** (`brew install tectonic`). Single invocation handles multi-pass and downloads missing packages on first use. This is what's used on the development machine.
- `aws` CLI *(optional; only for verifying credentials)*.

### Credentials

The current canonical runs use OpenAI + AWS Bedrock. Fill in `.env` at the repo root (copy from `.env.example`):

```bash
# .env
OPENAI_API_KEY=sk-...

# AWS Bedrock (temporary STS credentials rotate; omit AWS_SESSION_TOKEN for permanent IAM keys)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=            # leave blank for permanent creds
AWS_DEFAULT_REGION=us-east-1
```

Bedrock model access must be granted for **Anthropic** (Claude Haiku 4.5) and **Meta** (Llama 3.3 70B, Llama 3.1 8B) in the AWS Bedrock console → Model access. The code uses on-demand *inference-profile* IDs (prefix `us.`), which are required for these particular models in most accounts.

Scoped IAM policy (recommended — no `AmazonBedrockFullAccess`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-haiku-4-5-*",
        "arn:aws:bedrock:us-east-1::foundation-model/meta.llama3-3-70b-instruct-*",
        "arn:aws:bedrock:us-east-1::foundation-model/meta.llama3-1-8b-instruct-*",
        "arn:aws:bedrock:us-east-1:*:inference-profile/us.anthropic.claude-haiku-4-5-*",
        "arn:aws:bedrock:us-east-1:*:inference-profile/us.meta.llama3-3-70b-instruct-*",
        "arn:aws:bedrock:us-east-1:*:inference-profile/us.meta.llama3-1-8b-instruct-*"
      ]
    }
  ]
}
```

Confirm credentials are live before launching a multi-minute run:

```bash
set -a && source .env && set +a
aws sts get-caller-identity
aws bedrock list-inference-profiles --region us-east-1 --query 'inferenceProfileSummaries[?contains(inferenceProfileId, `haiku-4-5`) || contains(inferenceProfileId, `llama3-3-70b`) || contains(inferenceProfileId, `llama3-1-8b`)].inferenceProfileId' --output table
```

## Reproducing the results end-to-end

From the repo root:

```bash
set -a && source .env && set +a
cd Module_3_Intermediate_Report/code
```

### 1. OncQA scaling experiment (Table `tab:oncqa` and §4.2 prose)

```bash
python3 -m audit.run --config configs/oncqa_bedrock.yaml --seed 42 --parallelism 8
```

- **Scale:** 60 gender-filtered OncQA cases × 4 regions × 3 models = **720 completions + 720 annotator calls**.
- **Wall-clock:** ~16 minutes on `us-east-1` Bedrock defaults.
- **Output:** a new `runs/<UTC>/` with `manifest.json`, `perturbed.jsonl`, `completions.jsonl`, `annotated.jsonl`, `summaries.json`, and `.cache/` populated with 1 440 JSON entries.
- **Expected $n$ from manifest:** `n_cases: 60`, `filter_summary.excluded_count: 40` (see [Gendered-cancer filter](#gendered-cancer-filter) below).
- **Pass/fail heuristic:** after completion, check `errors=0` and `heuristic-fallback=0` in the terminal summary. The canonical run (`20260419T121941Z`) produced zero of either across 1 440 calls.

### 2. Perturbation ablations (Table `tab:ablation`)

The ablation decomposes the Combined perturbation (name + geography together) into Name-only and Geo-only runs on the 20-case synthetic pilot, using the same Bedrock panel:

```bash
python3 -m audit.run --config configs/pilot_name_only_bedrock.yaml --seed 42 --parallelism 8
python3 -m audit.run --config configs/pilot_geo_only_bedrock.yaml  --seed 42 --parallelism 8
python3 -m audit.run --config configs/pilot_combined_bedrock.yaml  --seed 42 --parallelism 8
```

- **Scale per run:** 20 cases × 4 regions × 3 models = **240 completions + 240 annotations** per config.
- **Wall-clock per run:** ~3–5 min.

Then produce the 3-way decomposition:

```bash
python3 scripts/ablation_compare.py \
  --combined  runs/<combined_ts>/ \
  --name-only runs/<name_ts>/ \
  --geo-only  runs/<geo_ts>/ \
  --out       runs/ablation_summary.json
```

The canonical ablation runs are `20260419T123259Z` (name-only), `20260419T123612Z` (geo-only), and `20260419T123954Z` (combined).

### 3. Synthetic pilot (historical; for reference only)

The canonical synthetic pilot is `runs/20260418T050306Z/` — executed on the **original Groq + OpenAI panel** (GPT-4o-mini, GPT-OSS-20B, Llama-3.3-70B, Qwen3-32B). It's preserved unchanged in the repo because the `tab:pilot`, `tab:per_region`, and `tab:per_question` tables in §4.1 cite its numbers directly. Reproducing it requires a `GROQ_API_KEY` and is **not** required for the new Bedrock panel results. See `code/README.md` for the historical invocation.

### 4. Re-compute metrics only (free; no API calls)

If you've changed a metric or label definition and want to regenerate `summaries.json` without hitting providers:

```bash
python3 -c "
from pathlib import Path
import json
from audit.metrics import compute_model_gdi
run = Path('runs/20260419T121941Z')
annotated = [json.loads(l) for l in (run/'annotated.jsonl').read_text().splitlines() if l.strip()]
summ = compute_model_gdi(annotated, n_south_regions=3)
(run/'summaries.json').write_text(json.dumps(summ, indent=2))
print('regenerated', run/'summaries.json')
"
```

### 5. Render the report

```bash
cd ..                     # back to Module_3_Intermediate_Report/
tectonic intermediate_report.tex
# or: pdflatex intermediate_report.tex; pdflatex intermediate_report.tex
```

Expected output: `intermediate_report.pdf` (~253 KB). Warnings about overfull hboxes are expected and non-fatal.

## Pipeline architecture

Five stages, each writing a typed JSONL on-disk artifact and independently re-runnable. See Figure 1 in the report (`figs/fig1_pipeline.pdf`).

```
┌────────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  data.py   │→→ │perturb.py│→→ │models.py │→→ │annotate  │→→ │metrics.py│
│ loader +   │   │ NAME/GEO │   │ generate │   │   .py    │   │  TSR RCR │
│ SHA mani-  │   │/COMBINED │   │ OpenAI + │   │ Llama    │   │  RCER GDI│
│ fest       │   │ perturb  │   │ Groq +   │   │ 3.1-8B   │   │ Wilcoxon │
│            │   │          │   │ Bedrock  │   │ + regex  │   │  + BCa   │
└────────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
        │              │              │              │              │
        ▼              ▼              ▼              ▼              ▼
   cases are       perturbed.     completions.   annotated.    summaries.
   loaded +         jsonl          jsonl          jsonl          json
   hashed
```

Cross-cutting components:

- **Per-model token-bucket rate limiter** (sliding 60 s RPM + TPM window). Keyed on `(provider, model_id)` so the annotator bucket is isolated from main-model buckets.
- **Idempotency cache** keyed on `sha256(model_id, messages, seed, temperature)` — re-runs are byte-identical and free.
- **Manifest hasher** pinning dataset + Name-Bank SHA-256 per run for reproducibility.

For provider/body/retry internals, see `code/audit/models.py` and `code/README.md`.

## Gendered-cancer filter

OncQA's Master2.csv contains 100 cases; the audit pipeline excludes 40 via a broad oncology-gendered filter:

```
['ovarian', 'cervical', 'prostate', 'breast', 'endometrial',
 'uterine', 'testicular', 'vaginal', 'penile']
```

This produces 60 analysis cases — not 61 as Chen et al. originally report after their narrower six-type filter. The decision to use the broader filter is logged in `code/decisions.md` RESOLVED #11 (with the clinician-validated reasoning). The 1-case deviation is documented; the report's §4.2 uses $n=60$ consistently.

## File-by-file reference

### LaTeX source

| File | Purpose |
|---|---|
| `intermediate_report.tex` | Main document. Imports `results_reframe.tex` and `baselines.tex`. |
| `sections/results_reframe.tex` | §4.3 H1/H2 analysis + OncQA re-analysis addendum + errors-included sensitivity. |
| `sections/baselines.tex` | §4.4 Baselines and Evaluation Methodology (spec'd by the instructor brief). |
| `sections/AGENT_LATEX_INTEGRATION_MANIFEST.md` | Integration log + SHA-256 hashes for the fragments. |
| `figs/fig1_pipeline.pdf` | Pipeline schematic. |
| `figs/fig2_gdi_heatmap.pdf` | Per-model × per-region GDI heatmap. |
| `figs/fig3_per_question.pdf` | Grouped per-question $\Delta$RCER bars. |
| `figs/fig4_forest.pdf` | Per-model GDI forest plot with 95% BCa CIs. |

### Run directory contract

Every run under `code/runs/<UTC>/` contains:

| File | Content |
|---|---|
| `manifest.json` | Run timestamp, config, dataset + Name-Bank SHA-256, model specs, seed, filter summary. |
| `perturbed.jsonl` | One line per (case × region) perturbed vignette. |
| `completions.jsonl` | One line per LLM call (all models, all cases, all regions). Includes usage, latency, provider. |
| `annotated.jsonl` | Completions + extracted MANAGE/VISIT/RESOURCE labels + gold labels. |
| `summaries.json` | Per-model RCER (north/south, per-question), GDI, BCa 95% CI, Cohen's $h$, Wilcoxon $W$/$z$/$p$/$r$, per-question deltas. |
| `.cache/` | Idempotency cache keyed on `sha256(model, prompt, seed, temperature)`. Makes re-runs byte-identical and free. |

### Configs

| Config | Scale | Panel | Purpose |
|---|---|---|---|
| `configs/pilot_oncqa.yaml` | 20 synthetic | OpenAI + Groq (4 models) | Original canonical pilot; needs `GROQ_API_KEY`. |
| `configs/oncqa_real.yaml` | 60 OncQA | OpenAI + Groq (4 models) | Pre-Bedrock OncQA; superseded. |
| `configs/oncqa_bedrock.yaml` | 60 OncQA | OpenAI + Bedrock (3 models) | **Current canonical OncQA run.** |
| `configs/pilot_name_only_bedrock.yaml` | 20 synthetic | OpenAI + Bedrock (3 models) | Name-only ablation. |
| `configs/pilot_geo_only_bedrock.yaml` | 20 synthetic | OpenAI + Bedrock (3 models) | Geo-only ablation. |
| `configs/pilot_combined_bedrock.yaml` | 20 synthetic | OpenAI + Bedrock (3 models) | Combined baseline for the ablation decomposition. |
| `configs/pilot_name_only.yaml`, `pilot_geo_only.yaml` | 20 synthetic | OpenAI + Groq | Pre-Bedrock ablations; superseded. |

### Scripts

| Script | What it does |
|---|---|
| `scripts/ablation_compare.py` | Reads three summaries.json files (combined, name-only, geo-only), emits `ablation_summary.json` with Name / Geo / Combined / Interaction GDI per model. |
| `scripts/power_analysis.py` | Reads a `summaries.json`, emits `power_analysis.json` with Cohen's $h$ per model and required $n$ for $\alpha \in \{0.05, 0.005\}$ × power $\in \{0.80, 0.95\}$, plus a power curve over $n \in \{20, 40, 61, 100, 147, 200, 500, 1000, 1333, 1541\}$. |
| `scripts/compute_kappa.py` | Cohen's $\kappa$ per binary question between two independent labeller JSONLs. Infrastructure for Task 08; awaits human labellers. |
| `scripts/reannotate.py` | Serial re-annotation of heuristic-fallback records in a run directory. Used historically to recover from Groq TPM losses. |
| `scripts/figs/fig{1..4}_*.py` | One script per figure; stdlib matplotlib only. |

## Expected results (quick reference)

If the pipeline runs end-to-end successfully, your new run directories should produce numbers matching these canonical summaries (rounded to 3 decimal places):

| Run | Model | GDI | $p$ | CI lo | CI hi |
|---|---|---:|---:|---:|---:|
| `20260419T121941Z` (OncQA) | Claude-Haiku-4.5 | +0.045 | 0.004 | +0.010 | +0.053 |
|  | GPT-4o-mini | +0.039 | 0.015 | +0.013 | +0.083 |
|  | Llama-3.3-70B | +0.009 | 0.038 | −0.003 | +0.047 |
| `20260419T123259Z` (Name-only) | Claude-Haiku-4.5 | +0.006 | 0.500 | — | — |
|  | GPT-4o-mini | +0.006 | 0.211 | — | — |
|  | Llama-3.3-70B | +0.009 | 0.395 | — | — |
| `20260419T123612Z` (Geo-only) | Claude-Haiku-4.5 | +0.019 | 0.186 | — | — |
|  | GPT-4o-mini | +0.037 | 0.091 | — | — |
|  | Llama-3.3-70B | +0.046 | 0.030 | — | — |
| `20260419T123954Z` (Combined pilot) | Claude-Haiku-4.5 | +0.028 | 0.091 | — | — |
|  | GPT-4o-mini | −0.003 | 0.292 | — | — |
|  | Llama-3.3-70B | +0.020 | 0.054 | — | — |

(Your wall-clock may differ; the numbers should not.)

## Troubleshooting

### `ValidationException: Invocation of model ID ... with on-demand throughput isn't supported. Retry your request with the ID or ARN of an inference profile.`

You're using a raw foundation-model ID where Bedrock expects an inference-profile ID. The configs in this repo already use profile IDs (`us.anthropic.claude-haiku-4-5-20251001-v1:0` etc.). If you added a new model, fetch valid profile IDs via:

```bash
aws bedrock list-inference-profiles --region us-east-1 --output table
```

and use the profile ID (not the raw modelId) in your config.

### `ThrottlingException` / HTTP 429 on Bedrock

Shouldn't happen at the default on-demand RPM quotas for these three models. If it does, the pipeline already retries with the server-supplied `Retry-After`. If you're running at high parallelism on a constrained account, lower `--parallelism` from 8 to 4.

### `GROQ_API_KEY not set in environment`

Expected if you're trying to run the historical Groq-panel configs (`pilot_oncqa.yaml`, `oncqa_real.yaml`, `pilot_{name,geo}_only.yaml`) without a Groq key. The current canonical runs use the `*_bedrock.yaml` configs and don't need Groq.

### Tectonic downloads a lot of files on first run

Expected — Tectonic fetches the package tree on demand. Subsequent runs are fast and offline.

### `filter_summary.excluded_count` ≠ 40 after changing the filter

Check `audit/data.py::load_oncqa` — the broader gendered-cancer list is hard-coded there. Changing it is a scope decision; document in `decisions.md` if you do.

## Related documents

- [`checklist.md`](checklist.md) — ground-truth status of every deliverable; executive snapshot table at top.
- [`code/README.md`](code/README.md) — detailed pipeline operator manual; read before modifying pipeline code.
- [`code/decisions.md`](code/decisions.md) — ~1 900-line decision log; `RESOLVED #2` (matched-pair canonical), `RESOLVED #11` (OncQA filter), `NOTE #14` (OncQA halt on Groq), `NOTE #15` (Bedrock migration) are the load-bearing entries.
- [`code/AUDIT_REPORT.md`](code/AUDIT_REPORT.md) — adversarial audit of the eight sprint tasks; dead-number discipline, secret-leak scan, numeric traceability.
- [`../Findings/`](../Findings/) — per-task sprint briefs (01 OncQA scaling through 08 clinical κ) and the validation prompt used to produce `AUDIT_REPORT.md`.
- [`../modules.md`](../modules.md) — instructor's source-of-truth brief for Module 3.

## Submission checklist

Before handing in:

1. ☐ `intermediate_report.pdf` is the most recent build (mtime > `intermediate_report.tex`).
2. ☐ Four figures render correctly in the PDF.
3. ☐ All `\ref{}` and `\cite{}` resolve (no `??` in the PDF).
4. ☐ Page count 14–18.
5. ☐ `checklist.md` executive-snapshot table matches reality.
6. ☐ `code/AUDIT_REPORT.md` has no BLOCKER, FABRICATED, or DECISION-BREACH findings.
7. ☐ `.env` is *not* included in the submission archive.
8. ☐ `code/runs/*/.cache/` directories can be excluded from the archive (large; regenerable).

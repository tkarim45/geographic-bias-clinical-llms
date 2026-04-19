# Auditing Geographic and Cultural Bias in Clinical LLMs

Academic deliverables workspace for **CS-5312 Big Data Analytics** (LUMS, Spring 2026, Dr. Imdadullah Khan). The course project proposes the **Geographic Disparity Index (GDI)** — a metric that quantifies differential care recommendations from clinical large language models when only the patient's perceived geography/name is perturbed — and evaluates it across multiple LLMs and clinical datasets.

**Group members:** Shawal Latif, Usmar Haider, Taimoor Karim, Abdul Moeed Irshad, Syed Muhammad Mujtaba.

## Repository layout

```
.
├── CLAUDE.md                          Agent-facing repo guide (read if you're using Claude Code)
├── modules.md                         Instructor's source-of-truth brief for every milestone
├── requirements.txt                   Python deps (boto3 only; everything else is stdlib)
├── .env.example                       Template for the two credential sets you need
│
├── Module_1_Proposal/                 Milestone 1 — accepted proposal (LaTeX + PDF)
├── Module_2_Literature_Review/        Milestone 2 — accepted literature review (LaTeX + PDF)
├── Module_3_Intermediate_Report/      Milestone 3 — intermediate report + audit pipeline
│   ├── README.md                      ← how to reproduce this module's results
│   ├── intermediate_report.tex        main report source
│   ├── intermediate_report.pdf        compiled deliverable
│   ├── sections/                      `\input{}`-mounted fragments
│   ├── figs/                          publication figures (PDF)
│   └── code/
│       ├── README.md                  ← detailed pipeline operator manual
│       ├── audit/                     Python package (data, perturb, models, annotate, metrics, run)
│       ├── configs/                   YAML run configs (pilot / OncQA / ablations / Bedrock variants)
│       ├── scripts/                   power_analysis, ablation_compare, compute_kappa, reannotate, figs/
│       ├── datasets/oncqa/            vendored OncQA CSVs with SHA-256 manifest
│       └── runs/                      timestamped artifacts: manifest.json, *.jsonl, summaries.json
│
└── Findings/                          sprint-planning briefs for each Module 3 task (01–08)
```

Each milestone folder also contains the instructor-provided `*_Template.pdf` — **read-only reference**; never edit or submit the template itself.

## Quick start — I just want to reproduce the numbers

```bash
# 0. Clone and enter the repo
cd "Big Data Project"

# 1. Provide credentials (never committed; see .env.example for the full list)
cp .env.example .env
$EDITOR .env            # fill in OPENAI_API_KEY and AWS_* fields

# 2. Install the one runtime dependency (boto3 for AWS Bedrock)
pip install -r requirements.txt

# 3. Reproduce the Module 3 pipeline — see Module_3_Intermediate_Report/README.md
cd Module_3_Intermediate_Report
cat README.md           # step-by-step instructions
```

For compiling just the PDFs without running the pipeline, see **Building the LaTeX documents** below.

## Credentials (`.env`)

Copy `.env.example` → `.env` and populate:

| Variable | Used by | Required for |
|---|---|---|
| `OPENAI_API_KEY` | All runs that include `gpt-4o-mini` | Synthetic pilot, OncQA (Bedrock panel still uses OpenAI for one slot), ablations |
| `AWS_ACCESS_KEY_ID` | AWS Bedrock adapter | OncQA scaling, ablations (current canonical panel) |
| `AWS_SECRET_ACCESS_KEY` | AWS Bedrock adapter | same |
| `AWS_SESSION_TOKEN` | AWS STS temporary credentials (optional; omit for permanent IAM user keys) | same |
| `AWS_DEFAULT_REGION` | AWS Bedrock adapter | same (default `us-east-1`) |
| `GROQ_API_KEY` | Original Groq pilot (historical; **no longer required** for Module 3's current canonical runs) | Only needed if reproducing the pre-pivot Groq-based pilot at `runs/20260418T050306Z/` |

`.env` is gitignored. `.env.example` is the canonical list.

**AWS Bedrock setup.** The pipeline uses on-demand inference-profile IDs (e.g. `us.anthropic.claude-haiku-4-5-20251001-v1:0`, `us.meta.llama3-3-70b-instruct-v1:0`, `us.meta.llama3-1-8b-instruct-v1:0`). Request *Model access* for Anthropic and Meta in the Bedrock console; default on-demand RPM quotas are sufficient for the current configs. See `Module_3_Intermediate_Report/checklist.md` Appendix §A2 for the scoped IAM policy.

## Building the LaTeX documents

Each module's PDF is produced from a single `.tex` with a standard LaTeX toolchain. The project uses LuaLaTeX-compatible packages (`fontenc`, `microtype`, `hyperref`, `booktabs`, `tcolorbox`, `titlesec`) — no shell-escape, no external tools.

**With `pdflatex` (TeX Live / MacTeX):**

```bash
cd Module_2_Literature_Review
pdflatex literature_review.tex
pdflatex literature_review.tex          # second pass to resolve \cite / \ref
```

Module 1 and Module 2 keep their bibliographies inline (`\begin{thebibliography}` — no external `.bib`), so BibTeX is **not** needed. Two `pdflatex` passes are enough.

**With [Tectonic](https://tectonic-typesetting.github.io/):** Tectonic handles multi-pass and downloads missing packages on first run. This is what's on the development machine for this project; it's equivalent to `pdflatex × 2`.

```bash
cd Module_3_Intermediate_Report
tectonic intermediate_report.tex
```

Compilation artifacts (`*.aux`, `*.log`, `*.out`, `*.toc`, `*.bbl`, `*.blg`, `*.fls`, `*.fdb_latexmk`, `*.synctex.gz`) regenerate on every build and are gitignored.

## Running the audit pipeline (Module 3)

The full reproduction story — configs, expected wall-clock, expected numbers, cost estimates — lives in **[`Module_3_Intermediate_Report/README.md`](Module_3_Intermediate_Report/README.md)**. The short version:

```bash
set -a && source .env && set +a
cd Module_3_Intermediate_Report/code

# OncQA scaling (n=60, Bedrock panel) — ~16 min, 720 completions + 720 annotations
python3 -m audit.run --config configs/oncqa_bedrock.yaml --seed 42 --parallelism 8

# Perturbation ablations (20 synthetic cases each) — ~3-5 min each
python3 -m audit.run --config configs/pilot_name_only_bedrock.yaml --seed 42 --parallelism 8
python3 -m audit.run --config configs/pilot_geo_only_bedrock.yaml  --seed 42 --parallelism 8
python3 -m audit.run --config configs/pilot_combined_bedrock.yaml  --seed 42 --parallelism 8

# Ablation decomposition
python3 scripts/ablation_compare.py \
  --combined  runs/20260419T123954Z \
  --name-only runs/20260419T123259Z \
  --geo-only  runs/20260419T123612Z \
  --out       runs/ablation_summary.json
```

Re-running with the same config and seed is **byte-identical** to the prior run thanks to the per-run `.cache/` keyed on `sha256(model, prompt, seed, temperature)`.

## Cross-milestone consistency

Each submission carries forward content from the previous one (problem framing, group block, citations). When editing a later milestone, keep these in sync with the accepted earlier version rather than rewriting from scratch:

- Project title, group members, course/instructor/institution block
- Problem framing and GDI methodology
- Shared citations (especially the four thematic groupings from the literature review)

## What's *not* in this repo

- `.env` (secrets — gitignored)
- `*.aux`, `*.log`, `*.out`, `*.toc` etc. (LaTeX artifacts — gitignored)
- `*.bak`, `*.pre_stats_refresh.bak` (sprint backups — gitignored)
- `runs/*/.cache/` (idempotency cache — large; gitignored so runs move between machines without cache contamination, but each run regenerates its own cache on first invocation)

## Support

- Pipeline operator manual: [`Module_3_Intermediate_Report/code/README.md`](Module_3_Intermediate_Report/code/README.md)
- Module 3 reproduction guide: [`Module_3_Intermediate_Report/README.md`](Module_3_Intermediate_Report/README.md)
- Sprint-window deliverable audit: [`Module_3_Intermediate_Report/code/AUDIT_REPORT.md`](Module_3_Intermediate_Report/code/AUDIT_REPORT.md)
- Team decisions log: [`Module_3_Intermediate_Report/code/decisions.md`](Module_3_Intermediate_Report/code/decisions.md)
- Ground-truth checklist: [`Module_3_Intermediate_Report/checklist.md`](Module_3_Intermediate_Report/checklist.md)
- Instructor brief: [`modules.md`](modules.md)

## License

This is academic coursework. Code under `Module_3_Intermediate_Report/code/` is written for the project and not licensed for external redistribution. The OncQA dataset under `code/datasets/oncqa/` is vendored from Chen et al. (2023) under its original license — see `code/datasets/oncqa/MANIFEST.md`. Published papers cited in the reports retain their original copyrights.

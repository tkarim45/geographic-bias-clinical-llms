# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

An academic deliverables workspace for **CS-5312 Big Data Analytics** (LUMS, Spring 2026, Dr. Imdadullah Khan). Primarily LaTeX sources and PDFs for the course project **"Auditing Geographic and Cultural Bias in Clinical Large Language Models"** (proposes a Geographic Disparity Index / GDI metric evaluated across 7 LLMs and 4 clinical datasets). Starting with Module 3, it also contains a Python audit pipeline (`Module_3_Intermediate_Report/code/`) that produces every number cited in the intermediate report from live LLM runs — no simulated results.

Group members (as listed on every submission): Shawal Latif, Usmar Haider, Taimoor Karim, Abdul Moeed Irshad, Syed Muhammad Mujtaba.

## Source of truth: `modules.md`

`modules.md` is the authoritative brief from the instructor. Each `Module_N_*` directory corresponds to one milestone described there. Before editing or generating content for a milestone, re-read the matching section of `modules.md` — it defines deadlines, required sections, and submission format (both `.tex` and `.pdf`, using the LMS-provided template).

Current milestone timeline:
- Module 1 — Proposal (submitted Mar 6, 2026)
- Module 2 — Literature Review (submitted Apr 1, 2026)
- Module 3 — Intermediate Report (due Apr 20, 2026 — in progress)

## Directory layout (meaning, not inventory)

Each module folder holds three things:
1. The group's submission, named `<topic_slug>_<milestone>.tex` / `.pdf` (the primary artifact to edit).
2. The LMS-provided template (`*_Template.pdf`) — **read-only reference**; never edit or submit the template itself.
3. Optional supporting material (e.g., the `.pptx` pitch deck in Module 1).

Module 2 also retains an earlier draft named `geographic_bias_clinical_llms_literature_review.{tex,pdf}` alongside the final `literature_review.{tex,pdf}`. The **final** version is `literature_review.tex`; the prefixed version is an older draft kept for reference.

## Building the LaTeX documents

There is no build system or CI. Compile each `.tex` with a standard LaTeX toolchain:

```bash
cd Module_2_Literature_Review
pdflatex literature_review.tex
pdflatex literature_review.tex   # run twice so \cite references resolve
```

Proposal and lit review use `\begin{thebibliography}` inline (no external `.bib`), so BibTeX is not needed. Two `pdflatex` passes are enough to resolve citations and the table of contents.

The `.aux`, `.log`, `.out`, `.toc` files are compilation artifacts — they regenerate on each build and should not be kept in the repo.

## The Module 3 audit pipeline (`Module_3_Intermediate_Report/code/`)

Stdlib-only Python 3.11+. No package manager, no `requirements.txt` — only two env vars (`OPENAI_API_KEY`, `GROQ_API_KEY`) loaded from a root `.env` (see `.env.example`). `code/README.md` is the detailed operator manual; re-read it before changing pipeline behaviour.

Pipeline stages (see `audit/` — one file per stage, orchestrated by `audit/run.py`):
`data.py` (load + SHA-256 manifest) → `perturb.py` (NAME/GEO/COMBINED perturbations across regions) → `models.py` (unified OpenAI + Groq `generate()`, token-bucket, idempotency-keyed cache) → `annotate.py` (Llama-3.1-8B annotator with JSON/regex/heuristic fallback) → `metrics.py` (TSR, RCR, RCER, GDI; paired Wilcoxon; bootstrap CIs).

Run the pilot (from repo root):

```bash
set -a && source .env && set +a
cd Module_3_Intermediate_Report/code
python3 -m audit.run --config configs/pilot_oncqa.yaml --seed 42 --parallelism 8
```

Each invocation writes a timestamped directory under `code/runs/<UTC>/` containing `manifest.json`, `perturbed.jsonl`, `completions.jsonl`, `annotated.jsonl`, `summaries.json`, and a `.cache/` keyed by `sha256(model, prompt, seed, temperature)`. Re-running with the same config + seed is byte-identical thanks to the cache; the manifest pins dataset and name-bank hashes alongside full model specs.

If Groq's 6000 TPM ceiling causes annotator 429s (records fall back to regex heuristic), re-annotate serially:

```bash
latest=$(ls -dt runs/*/ | head -1)
python3 scripts/reannotate.py --run-dir "$latest" --sleep 7
```

Pilot scale (`configs/pilot_oncqa.yaml`): 20 cases × 4 regions × 4 models ≈ 320 completions + 320 annotations, ~10 min wall-clock (Groq rate-limit bound). Do not commit `code/runs/` or `.cache/` artefacts, and do not commit `.env`.

When the report cites a number (GDI, RCER, Wilcoxon p, CI), it should come from a specific run directory's `summaries.json` — don't hand-edit values in the `.tex`.

## Cross-milestone consistency

Each submission reuses content from the previous one (problem statement, group block, references). When editing a later milestone, keep these in sync with the accepted earlier version rather than rewriting from scratch:
- Project title, group members, course/instructor/institution block
- Problem framing and GDI methodology
- Shared citations (especially the four thematic groupings from the literature review)

If you change wording in one place, check whether it needs to propagate to later milestones.

## Style conventions observed in the existing `.tex` files

- LuaLaTeX-compatible packages only (`fontenc`, `microtype`, `hyperref`, `booktabs`, `tcolorbox`, `titlesec`). Don't introduce packages that require shell-escape or external tooling.
- Section headers use a custom `acmblue` (`RGB 0,83,156`) theme — preserve it when adding sections.
- Citations use ACM-Reference-Format (`\bibliographystyle{ACM-Reference-Format}`), `\cite{}` inline.
- A4 paper, 1-inch margins, 12pt, 1.15 line spacing — do not change without reason.

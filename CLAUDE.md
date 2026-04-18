# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

An academic deliverables workspace for **CS-5312 Big Data Analytics** (LUMS, Spring 2026, Dr. Imdadullah Khan). It is not a software project — it contains LaTeX sources and PDFs for the course project **"Auditing Geographic and Cultural Bias in Clinical Large Language Models"** (proposes a Geographic Disparity Index / GDI metric evaluated across 7 LLMs and 4 clinical datasets).

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

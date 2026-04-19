# Claude Code Prompt 00 — Execution Order & Ground Rules

**Read this before any other prompt in this folder.**

## Working context

You are operating in the repository described by `CLAUDE.md` at the repo root. The relevant subdirectory for all prompts in this folder is:

```
Module_3_Intermediate_Report/code/
```

Before doing anything, run:

```bash
cd Module_3_Intermediate_Report/code
ls -la
cat CLAUDE.md   # repo root version
cat code/README.md  # pipeline operator manual
```

## API keys

Both keys must be present in the repo root `.env` before any of these prompts will work:

```bash
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk-...
```

Load them into the shell:

```bash
set -a; source .env; set +a
```

## Hard rules

1. **Do not simulate or fabricate numbers.** If an API call fails, document the failure and fall back to smaller-scale real data — never synthesize plausible outputs.
2. **Every numeric claim in the report must trace to a `runs/<UTC>/summaries.json` file.** When you update the `.tex`, cite the run directory in a comment next to each number.
3. **Do not commit `.env`, `runs/`, or `.cache/`.** These are already in `.gitignore`; verify.
4. **Do not rewrite unrelated code.** All prompts are narrowly scoped; if you notice something else wrong, log it in `decisions.md` instead of fixing it opportunistically.
5. **Two `pdflatex` passes for the report.** Always run twice so `\cite` and `\ref` resolve.

## Order of execution

Prompts are numbered by priority. Execute in this order, but multiple can run in parallel on different machines:

| # | Prompt | Owner | Parallel? | Blocks |
|---|---|---|---|---|
| 01 | `01_oncqa_scaling.md` | Moeed | yes | scaling narrative in §4 |
| 02 | `02_ablation_runs.md` | Moeed (after 01) | no | ablation table in §4 |
| 03 | `03_rate_limits_fix.md` | Usmar | yes | must finish before 01 for reliability |
| 04 | `04_statistical_rigor.md` | Taimoor | yes | analysis framing in §4.3 |
| 05 | `05_figures_generation.md` | Taimoor (after 04) | no | report needs figures |
| 06 | `06_report_latex_updates.md` | Mujtaba | yes | final deliverable |
| 07 | `07_baselines_methodology.md` | Shawal | yes | new §4.x section |
| 08 | `08_clinical_labels_validation.md` | Shawal | yes | defensibility |

## Artifact discipline

Every run produces a new timestamped directory under `runs/`. When a prompt finishes:

1. Note the run directory path in `decisions.md`.
2. If you wrote new code, run `python -m py_compile` on the changed files.
3. If the prompt modifies `.tex`, do not commit before `pdflatex` succeeds.

## When to stop and ask a human

- API key returns 401 (wrong key, not rate-limited).
- A run produces obviously malformed outputs (e.g., every response is empty).
- LaTeX compilation fails with errors you cannot decode from the log.
- Any action might delete existing `runs/` directories.

Continue only if you can confidently act without human input.

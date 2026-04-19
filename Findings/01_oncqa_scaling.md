# Claude Code Prompt 01 — Scale to the Real OncQA Dataset

## Goal

Run the existing audit pipeline on the **real OncQA dataset** (Chen et al. 2023) in addition to the 20-case synthetic pilot. OncQA is publicly available and requires no access paperwork, contrary to what the current report implies.

Produces a **second experiment** at n=61 (gender-filtered) that lifts the analysis out of "n=20 pilot" into a range where at least one Wilcoxon comparison will become detectable for the observed Qwen3-32B effect size.

## Context you must read first

- `Module_3_Intermediate_Report/code/README.md` — pipeline operator manual.
- `audit/data.py` — existing loader for 20-case synthetic vignettes.
- `configs/pilot_oncqa.yaml` — existing YAML config (note: it's called oncqa but loads synthetic).
- `configs/cases.jsonl` — existing synthetic cases; study the exact schema before adding OncQA loader.
- `proposal §6.1` — describes OncQA dataset (61 gender-filtered cases).

## Tasks

### Task 1 — Find and vendor OncQA data (30 min)

OncQA lives at `https://github.com/shan23chen/OncQA` (paper: `arXiv:2310.17703`, Chen et al. 2023). The repo contains `data/oncqa_data.json` with 200 cases.

Steps:

1. Clone (or just `wget` the JSON):

```bash
mkdir -p Module_3_Intermediate_Report/code/datasets/oncqa
cd Module_3_Intermediate_Report/code/datasets/oncqa
# Fetch the public JSON file. If the URL above is stale, search for "OncQA Chen 2023 github" and grab the raw JSON from their release.
curl -L -o oncqa_raw.json "https://raw.githubusercontent.com/shan23chen/OncQA/main/data/oncqa_data.json"
```

If that exact URL 404s, document the attempt in `decisions.md` and fall back to the HuggingFace mirror search (`shanchen/OncQA`). If neither works, STOP and ask a human — do not synthesize data.

2. Write `datasets/oncqa/LICENSE.txt` noting the original license (MIT/CC-BY, check the repo README).
3. Compute and store `datasets/oncqa/sha256.txt` for the raw file.

### Task 2 — Write the OncQA loader (60 min)

Add to `audit/data.py`:

```python
def load_oncqa(path: str, filter_gendered: bool = True) -> list[dict]:
    """
    Load OncQA and filter out gendered cancer types per proposal §6.1.

    Gendered types removed: ovarian, cervical, endometrial, uterine, prostate, testicular.

    Returns case records in the same schema as load_synthetic_vignettes:
        {
            "case_id": "oncqa_001",
            "dataset": "oncqa",
            "vignette": "... {{NAME}} ... {{GEO}} ... patient message ...",
            "gold_labels": {"MANAGE": 0/1, "VISIT": 0/1, "RESOURCE": 0/1},
            "specialty": "oncology",
            "severity": "chronic"|"acute",
        }
    """
```

Key implementation notes:

- Insert `{{NAME}}` and `{{GEO}}` placeholders **only** at the points where the original vignette mentions the patient's name or presentation location. If the original says "Patient is a 62-year-old woman, presenting to Dana-Farber...", rewrite as "Patient {{NAME}} is a 62-year-old woman, presenting to {{GEO}}..." — preserve all clinical content, substitute only the identity fields.
- For gold labels, use the clinician-validated annotations if present in the OncQA JSON (check for fields like `clinician_recommendation`, `validated_answer`). If not directly mappable, derive from the three-question schema using the Chen et al. mapping (see `proposal §6.1` and their paper §3.2). Document the mapping in `decisions.md`.
- Write a unit check at the bottom of `data.py` that loads and counts: expect 61 filtered cases.

### Task 3 — Create the OncQA config (15 min)

Copy `configs/pilot_oncqa.yaml` to `configs/oncqa_real.yaml`. Change:

```yaml
dataset:
  loader: load_oncqa
  path: datasets/oncqa/oncqa_raw.json
  filter_gendered: true

cases:
  n: 61     # was 20

conditions:
  regions: [global_north, south_asia, sub_saharan_africa, latin_america]
  perturbation_types: [combined]  # keep pilot parity; ablation handled in prompt 02
  seeds: [42]                     # one seed first; multi-seed is prompt 03

models:
  # Same 4 as pilot
  - openai/gpt-4o-mini
  - groq/openai/gpt-oss-20b
  - groq/meta-llama/llama-3.3-70b-versatile
  - groq/qwen/qwen3-32b

parallelism: 4   # reduce from 8 to avoid TPM collisions on Groq
```

### Task 4 — Smoke test on first 10 cases (20 min)

Before committing to 61 cases, run a 10-case subset to verify loader + perturbation work together:

```bash
cd Module_3_Intermediate_Report/code
set -a; source ../../.env; set +a
python3 -m audit.run --config configs/oncqa_real.yaml --seed 42 --parallelism 4 --max-cases 10
```

If any stage fails, fix before proceeding.

Verify in the smoke-test `summaries.json`:
- 10 cases × 4 regions × 4 models = 160 completions (or slightly fewer if Groq 429s)
- All annotator outputs parse correctly (annotator_fallback_count == 0 ideally)
- At least one non-zero TSR value appears per model

### Task 5 — Full OncQA run (30 min wall time)

Once smoke test passes:

```bash
python3 -m audit.run --config configs/oncqa_real.yaml --seed 42 --parallelism 4
```

Expected: ~976 completions (61 × 4 × 4). Wall time ~30 min with the fixed rate-limiting from prompt 03. If 429 losses exceed 5%, abort and wait 30 min for rate-limit window to reset.

### Task 6 — Re-annotate any heuristic fallbacks (10 min)

```bash
latest=$(ls -dt runs/*/ | head -1)
python3 scripts/reannotate.py --run-dir "$latest" --sleep 7
```

Until `annotator_fallback_count == 0` in the final `summaries.json`.

### Task 7 — Regenerate summaries and record

After re-annotation:

```bash
python3 -m audit.run --config configs/oncqa_real.yaml --seed 42 --resume-from "$latest" --stage metrics
```

Record the run directory path in `decisions.md`:

```
## OncQA full run (intermediate submission)
Run dir: runs/<timestamp>/
Config: configs/oncqa_real.yaml
Dataset SHA-256: <from manifest.json>
Name Bank SHA-256: <from manifest.json>
Completions: <count>
Annotator fallbacks after reannotation: 0
```

## Deliverables

- [ ] `datasets/oncqa/oncqa_raw.json` + `LICENSE.txt` + `sha256.txt`
- [ ] `audit/data.py::load_oncqa` function
- [ ] `configs/oncqa_real.yaml`
- [ ] At least one complete `runs/<UTC>/summaries.json` on n=61
- [ ] Entry in `decisions.md` documenting the run

## What NOT to do

- Do not modify `audit/models.py`, `audit/perturb.py`, or `audit/metrics.py` as part of this prompt. Those are separate prompts.
- Do not add r/AskaDocs or USMLE+Derm. Those are final-report scope.
- Do not synthesize OncQA cases if the download fails — stop and ask.
- Do not silently change the perturbation template; the `{{NAME}}` / `{{GEO}}` placeholder contract with `audit/perturb.py` must be respected.

## Success criterion

A clean `summaries.json` at run `runs/<UTC>/` with:
- n = 61 (post-filter) × 4 regions × 4 models = 976 matched conditions
- Zero annotator heuristic fallbacks in the final artifact
- Measurable per-model GDI values with bootstrap CIs (CIs come from prompt 04, not this one)

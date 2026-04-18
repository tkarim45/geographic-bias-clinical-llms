# Geographic Bias Audit — Pipeline Code

Reference implementation accompanying the intermediate report for
**"Auditing Geographic and Cultural Bias in Clinical Large Language Models"**
(CS-5312, LUMS, Spring 2026).

Every number in the report is produced by this code from a live run. There are
no simulated results.

## Layout

```
code/
├── audit/
│   ├── __init__.py
│   ├── data.py            # dataset loader + SHA-256 manifest hashing
│   ├── perturb.py         # deterministic perturbation engine (NAME/GEO/COMBINED)
│   ├── models.py          # unified generate() across OpenAI + Groq; token-bucket; cache
│   ├── annotate.py        # Llama-3.1-8B annotator; JSON/regex/heuristic fallback
│   ├── metrics.py         # TSR, RCR, RCER, GDI; paired Wilcoxon; bootstrap CIs
│   └── run.py             # CLI entry-point; schedules every pipeline stage
├── scripts/
│   └── reannotate.py      # serial re-annotation for heuristic-fallback records
├── configs/
│   ├── pilot_oncqa.yaml   # pilot config (20 cases × 4 regions × 4 models)
│   ├── cases.jsonl        # 20 clinician-labelled vignettes
│   └── name_bank.json     # 150 names × 6 regions, M/F balanced
├── runs/                  # per-run timestamped artefacts
│   └── <UTC-timestamp>/
│       ├── manifest.json     # cases SHA-256, name-bank SHA-256, model specs
│       ├── perturbed.jsonl   # case × region × seed vignettes
│       ├── completions.jsonl # one row per LLM call
│       ├── annotated.jsonl   # completions + {manage, visit, resource} labels
│       ├── summaries.json    # per-model RCER, GDI, Wilcoxon p
│       └── .cache/           # idempotency-keyed response cache
└── README.md              # this file
```

## Running the pilot

Only two environment variables are needed; stdlib Python 3.11+ is the only
dependency.

```bash
# From the project root that contains .env:
set -a
source .env            # sets OPENAI_API_KEY and GROQ_API_KEY
set +a
cd Module_3_Intermediate_Report/code
python3 -m audit.run --config configs/pilot_oncqa.yaml --seed 42 --parallelism 8
```

Wall-clock time for the 320 completions + 320 annotations is roughly 10
minutes, rate-limit-bound by Groq's free tier.

## If Groq 429s cascade through the annotator

Some pilot runs lose annotator calls to Groq's 6 000 tokens-per-minute ceiling.
The affected records fall back to regex heuristic. Re-annotate them serially:

```bash
latest=$(ls -dt runs/*/ | head -1)
python3 scripts/reannotate.py --run-dir "$latest" --sleep 7
```

A 7-second inter-call spacing stays safely below the TPM ceiling. Successful
re-annotations replace heuristic labels in-place in `annotated.jsonl`, and
`summaries.json` is recomputed at the end.

## Reproducibility

Every run directory contains a `manifest.json` capturing:
- UTC run timestamp
- SHA-256 of `cases.jsonl` and `name_bank.json`
- Full model spec list (provider, model_id, temperature, max_tokens)
- Annotator spec
- Seed

A second invocation with the same config + seed produces byte-identical
`summaries.json` because every provider response is cached under its
idempotency key `(sha256(model, prompt, seed, temperature))`.

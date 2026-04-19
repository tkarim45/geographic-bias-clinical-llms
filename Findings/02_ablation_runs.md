# Claude Code Prompt 02 — Run Name-only and Geo-only Perturbation Ablations

## Goal

The pilot ran only the `combined` perturbation (name + geography substituted simultaneously). This leaves RQ1 partially unanswered — we cannot tell whether the signal comes from the name, the geography, or the interaction. Running the two ablations on the existing 20-case dataset is cheap (~320 additional completions, ~10 min wall-clock) and fills a reviewer-obvious gap.

**Prerequisite:** Prompt 03 (`03_rate_limits_fix.md`) should be completed first to avoid Groq TPM losses.

## Context to read

- `audit/perturb.py` — verify it already supports `type in {name, geo, combined}`.
- `configs/pilot_oncqa.yaml` — the pilot config whose structure we'll clone.
- The pilot run directory (most recent with `combined` perturbation). Record its path.

## Tasks

### Task 1 — Verify perturbation engine supports all three types (5 min)

```bash
cd Module_3_Intermediate_Report/code
grep -n "perturbation_type\|combined\|name_only\|geo_only" audit/perturb.py
```

Expected: `audit/perturb.py` already dispatches on a `perturbation_type` field. If it doesn't, **stop and report** — that's a larger patch that needs separate review.

If it does, quickly test:

```bash
python3 -c "
from audit.perturb import perturb_case
import json
case = json.load(open('configs/cases.jsonl'))[0]  # adjust if cases is jsonl not json
for t in ['name', 'geo', 'combined']:
    out = perturb_case(case, region='south_asia', perturbation_type=t, seed=42)
    print(t, out['vignette'][:200])
"
```

Three different outputs should appear — confirming all three dispatch paths work.

### Task 2 — Create ablation configs (10 min)

Clone `configs/pilot_oncqa.yaml` twice:

```bash
cp configs/pilot_oncqa.yaml configs/pilot_name_only.yaml
cp configs/pilot_oncqa.yaml configs/pilot_geo_only.yaml
```

Edit each so the `conditions.perturbation_types` field is `[name]` and `[geo]` respectively. Leave everything else identical to the original pilot (same 20 cases, same 4 regions, same 4 models, seed 42).

### Task 3 — Run both ablations (15 min wall, back-to-back)

```bash
set -a; source ../../.env; set +a

python3 -m audit.run --config configs/pilot_name_only.yaml --seed 42 --parallelism 4
# Note the run directory, then:
latest=$(ls -dt runs/*/ | head -1)
python3 scripts/reannotate.py --run-dir "$latest" --sleep 7

python3 -m audit.run --config configs/pilot_geo_only.yaml --seed 42 --parallelism 4
latest=$(ls -dt runs/*/ | head -1)
python3 scripts/reannotate.py --run-dir "$latest" --sleep 7
```

The idempotency cache means the Global-North baseline completions will NOT re-bill — only the 240 South Asia / SSA / Latin America perturbed completions × 2 ablations = ~480 new calls.

### Task 4 — Produce ablation-comparison summary (20 min)

Write `scripts/ablation_compare.py`:

```python
"""
Compare per-model GDI across the three perturbation types.
Reads three run directories (combined, name-only, geo-only) and emits:

- A table rows=(model), cols=(name-only GDI, geo-only GDI, combined GDI, interaction = combined - name - geo)
- A JSON for the figures script to consume
- A short text summary of which perturbation type drives the effect per model
"""
import json, sys, argparse
from pathlib import Path

def load_gdi(run_dir):
    s = json.loads((Path(run_dir) / 'summaries.json').read_text())
    return {model: s['per_model'][model]['gdi'] for model in s['per_model']}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--combined', required=True)
    p.add_argument('--name-only', required=True)
    p.add_argument('--geo-only', required=True)
    p.add_argument('--out', default='ablation_summary.json')
    args = p.parse_args()

    combined = load_gdi(args.combined)
    name = load_gdi(args.__dict__['name_only'])
    geo = load_gdi(args.__dict__['geo_only'])

    out = {}
    for m in combined:
        out[m] = {
            'name_only': name.get(m),
            'geo_only': geo.get(m),
            'combined': combined.get(m),
            'interaction': combined.get(m) - (name.get(m) or 0) - (geo.get(m) or 0)
                          if None not in (combined.get(m), name.get(m), geo.get(m)) else None,
        }

    Path(args.out).write_text(json.dumps(out, indent=2))
    # Also print a human-readable table
    print(f"{'Model':<35} {'Name':>8} {'Geo':>8} {'Combined':>10} {'Interaction':>12}")
    for m, v in out.items():
        def fmt(x): return f"{x:+.3f}" if x is not None else "    —"
        print(f"{m:<35} {fmt(v['name_only']):>8} {fmt(v['geo_only']):>8} {fmt(v['combined']):>10} {fmt(v['interaction']):>12}")

if __name__ == '__main__':
    main()
```

Run:

```bash
python3 scripts/ablation_compare.py \
  --combined runs/<combined_run_dir> \
  --name-only runs/<name_only_run_dir> \
  --geo-only runs/<geo_only_run_dir> \
  --out ablation_summary.json
```

### Task 5 — Record in `decisions.md`

Add:

```
## Perturbation ablation runs (intermediate submission)

- Combined (re-use of pilot): runs/<path>
- Name-only:                  runs/<path>
- Geo-only:                   runs/<path>

Summary file: ablation_summary.json

Key observations (fill in after you see numbers):
- Which model's signal is predominantly name-driven?
- Which is geo-driven?
- Any interaction effects worth noting?
```

## Deliverables

- [ ] `configs/pilot_name_only.yaml` and `configs/pilot_geo_only.yaml`
- [ ] Two new run directories with zero annotator heuristic fallbacks
- [ ] `scripts/ablation_compare.py` + `ablation_summary.json`
- [ ] Entry in `decisions.md` with all three run paths

## What NOT to do

- Do not run on OncQA at this stage. Keep ablation on the 20 pilot cases for now; OncQA ablation is full-scale scope.
- Do not change seed from 42. The ablation is comparing perturbation types, not seed variance.
- Do not invent an "interaction" term that cannot be measured from the data.

## Success criterion

`ablation_summary.json` produces four rows (one per model) with name-only, geo-only, combined GDIs, and a derived interaction term. The table goes into the report as a new subsection §4.4 (the LaTeX update is prompt 06).

## What this unlocks for the report

A new sentence in §4.3: *"Ablation shows that [Model X]'s signal is dominated by [name/geo] substitution (∆GDI = Y for [name/geo]-only versus Z for the other), suggesting the mechanism is [plausible interpretation]."*

# Claude Code Prompt 04 — Statistical Rigor: Effect Sizes, Bootstrap CIs, Power Analysis

## Goal

The current report presents only p-values with a Bonferroni α=0.005 threshold that is mathematically unreachable at n=20 for the observed effect sizes. This creates a self-inflicted weakness. Replace/augment with:

1. Effect sizes with 95% bootstrap confidence intervals for every GDI.
2. A power-analysis subsection showing required n for each observed effect size.
3. A Cohen's h calculation for proportion differences.
4. A cleaner Wilcoxon output (effect size `r = Z / √n`, not just p-value).

Net effect: turn "underpowered" from a weakness into an explicit pre-registered methodological choice.

## Read first

- `Module_3_Intermediate_Report/code/audit/metrics.py` — the existing hand-rolled Wilcoxon + bootstrap.
- The most recent pilot `summaries.json`.

## Tasks

### Task 1 — Audit the existing `metrics.py` (15 min)

```bash
cd Module_3_Intermediate_Report/code
wc -l audit/metrics.py
grep -n "def " audit/metrics.py
```

Confirm that `metrics.py`:
- Computes GDI per model per region.
- Has a `bootstrap_ci` function OR we need to add one.
- Outputs `summaries.json` in a schema downstream consumers (figures script, LaTeX) can read.

If `bootstrap_ci` does not exist, add it. If it does, verify it uses ≥2,000 resamples and proper BCa (bias-corrected, accelerated) intervals — the plain percentile bootstrap is fine for a pilot but reviewers prefer BCa.

### Task 2 — Add effect-size and BCa-CI functions (60 min)

Append to `audit/metrics.py`:

```python
import math, random, statistics
from typing import Callable, Sequence

def bootstrap_ci_bca(
    data: Sequence[float],
    statistic: Callable[[Sequence[float]], float],
    n_resamples: int = 2000,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, float]:
    """
    Bias-corrected and accelerated (BCa) bootstrap CI.
    Returns (point_estimate, lo, hi).
    """
    rng = random.Random(seed)
    n = len(data)
    if n == 0:
        return (float('nan'), float('nan'), float('nan'))

    theta_hat = statistic(data)

    # Bootstrap replicates
    replicates = []
    for _ in range(n_resamples):
        resample = [data[rng.randrange(n)] for _ in range(n)]
        replicates.append(statistic(resample))
    replicates.sort()

    # Bias correction
    prop_below = sum(1 for r in replicates if r < theta_hat) / n_resamples
    z0 = _inv_phi(prop_below) if 0 < prop_below < 1 else 0.0

    # Acceleration via jackknife
    jackknife = []
    for i in range(n):
        loo = [x for j, x in enumerate(data) if j != i]
        jackknife.append(statistic(loo))
    jk_mean = statistics.mean(jackknife)
    num = sum((jk_mean - x) ** 3 for x in jackknife)
    den = 6 * (sum((jk_mean - x) ** 2 for x in jackknife) ** 1.5)
    a = num / den if den != 0 else 0.0

    alpha = (1 - ci) / 2
    z_lo = _inv_phi(alpha); z_hi = _inv_phi(1 - alpha)

    def _adj(z):
        return _phi(z0 + (z0 + z) / (1 - a * (z0 + z)))
    lo_q = _adj(z_lo); hi_q = _adj(z_hi)
    lo_idx = max(0, min(n_resamples - 1, int(math.floor(lo_q * n_resamples))))
    hi_idx = max(0, min(n_resamples - 1, int(math.floor(hi_q * n_resamples))))
    return (theta_hat, replicates[lo_idx], replicates[hi_idx])


def cohens_h(p1: float, p2: float) -> float:
    """Cohen's h for two proportions. Sign: positive if p1 > p2."""
    phi1 = 2 * math.asin(math.sqrt(max(0, min(1, p1))))
    phi2 = 2 * math.asin(math.sqrt(max(0, min(1, p2))))
    return phi1 - phi2


def wilcoxon_effect_r(z: float, n: int) -> float:
    """Effect size r for Wilcoxon: r = |Z| / sqrt(n)."""
    return abs(z) / math.sqrt(n) if n > 0 else float('nan')


# Phi / inverse Phi via Abramowitz & Stegun 26.2.23 (accurate to 4.5e-4)
def _phi(z: float) -> float:
    # Standard normal CDF
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))

def _inv_phi(p: float) -> float:
    # Standard normal inverse CDF (Beasley-Springer-Moro, fine for our uses)
    if p <= 0 or p >= 1:
        return float('inf') if p >= 1 else float('-inf')
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
          1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
          6.680131188771972e+01, -1.328068155288572e+01]
    q = p - 0.5
    if abs(q) < 0.425:
        r = q * q
        return q * (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5]) / \
                   (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    r = p if q < 0 else 1 - p
    r = math.sqrt(-math.log(r))
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    val = (((((c[0]*r+c[1])*r+c[2])*r+c[3])*r+c[4])*r+c[5]) / \
          ((((d[0]*r+d[1])*r+d[2])*r+d[3])*r+1)
    return val if q >= 0 else -val
```

### Task 3 — Power analysis script (45 min)

Create `scripts/power_analysis.py`:

```python
"""
Power analysis for the geographic-bias audit.

For each observed per-model GDI, compute:
- The Cohen's h between Global-North baseline RCER and Global-South pooled RCER
- The n required to detect that effect size at α ∈ {0.05, 0.005 (Bonferroni)}
  with power 0.80 and 0.95, using the formula for a one-sample paired proportion test.

Also produce a power curve: detectable effect size as a function of n, at each α.
"""
import json, math, sys, argparse
from pathlib import Path
# Re-use funcs from audit.metrics
sys.path.insert(0, '.')
from audit.metrics import cohens_h, _inv_phi

def n_required(h: float, alpha: float, power: float) -> int:
    """n for a two-sided paired proportion test to detect Cohen's h, given alpha and power."""
    if h == 0: return float('inf')
    z_alpha = _inv_phi(1 - alpha / 2)
    z_beta = _inv_phi(power)
    return int(math.ceil(((z_alpha + z_beta) / abs(h)) ** 2))

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--summaries', required=True, help='summaries.json from a run')
    p.add_argument('--out', default='power_analysis.json')
    args = p.parse_args()

    s = json.loads(Path(args.summaries).read_text())
    out = {'per_model': {}, 'power_curve': {}}
    for model, m in s['per_model'].items():
        # Use RCER mean North/South across questions as the paired proportions
        p_n = m.get('rcer_north_mean') or 0.0
        p_s = m.get('rcer_south_mean') or 0.0
        h = cohens_h(p_s, p_n)
        out['per_model'][model] = {
            'rcer_north': p_n, 'rcer_south': p_s, 'cohens_h': h,
            'n_required_alpha_0.05_power_0.80': n_required(h, 0.05, 0.80),
            'n_required_alpha_0.005_power_0.80': n_required(h, 0.005, 0.80),
            'n_required_alpha_0.005_power_0.95': n_required(h, 0.005, 0.95),
        }

    # Power curve: for each n in [20,50,100,200,500,1000,1500], what h is detectable?
    for alpha in [0.05, 0.005]:
        out['power_curve'][f'alpha_{alpha}'] = {}
        for n in [20, 40, 61, 100, 147, 200, 500, 1000, 1333, 1541]:
            # Detectable h at power 0.80
            z_alpha = _inv_phi(1 - alpha / 2); z_beta = _inv_phi(0.80)
            h_min = (z_alpha + z_beta) / math.sqrt(n)
            out['power_curve'][f'alpha_{alpha}'][str(n)] = round(h_min, 4)

    Path(args.out).write_text(json.dumps(out, indent=2))
    # Print a human summary
    print(f"\nPower analysis for {args.summaries}\n{'-'*60}")
    for model, v in out['per_model'].items():
        print(f"{model}:")
        print(f"  RCER N={v['rcer_north']:.3f} S={v['rcer_south']:.3f} h={v['cohens_h']:+.3f}")
        print(f"  n needed (α=0.05, power=.80): {v['n_required_alpha_0.05_power_0.80']}")
        print(f"  n needed (α=0.005, power=.80): {v['n_required_alpha_0.005_power_0.80']}")
        print(f"  n needed (α=0.005, power=.95): {v['n_required_alpha_0.005_power_0.95']}")

if __name__ == '__main__':
    main()
```

Run:

```bash
python3 scripts/power_analysis.py --summaries runs/<latest>/summaries.json --out power_analysis.json
```

This produces a table that goes directly into the report (see prompt 06 for where it lands).

### Task 4 — Augment `audit/metrics.py` output with CIs (30 min)

Modify whichever function produces `summaries.json` so each per-model block now includes:

```json
"gpt-4o-mini": {
  "gdi": 0.015,
  "gdi_ci_lo": -0.021,
  "gdi_ci_hi": 0.049,
  "cohens_h_north_vs_south": 0.038,
  "wilcoxon_p": 0.500,
  "wilcoxon_r": 0.148,
  "n_north": 20,
  "n_south": 60,
  "rcer_north_mean": 0.028,
  "rcer_south_mean": 0.043,
  "per_question": {
    "MANAGE": {"delta": 0.074, "delta_ci_lo": ..., "delta_ci_hi": ...},
    "VISIT":  {"delta": 0.000, "delta_ci_lo": ..., "delta_ci_hi": ...},
    "RESOURCE": {"delta": -0.028, "delta_ci_lo": ..., "delta_ci_hi": ...}
  }
}
```

Use the paired-delta case-level vector as the bootstrap input (one scalar per case i, equal to `indicator(V_i=1 and T_{p,i}=0 given T_{b,i}=1)` or similar — match your existing RCER computation).

### Task 5 — Re-run metrics on the existing pilot artifacts (15 min)

The metrics stage should be re-runnable without hitting any APIs:

```bash
python3 -m audit.run --config configs/pilot_oncqa.yaml --seed 42 --resume-from runs/<pilot_dir> --stage metrics
```

Verify the new `summaries.json` contains CI fields. Save as the pilot's updated summary file.

### Task 6 — Hold the line on Bonferroni language

In `audit/metrics.py` docstrings and any log messages, update the Bonferroni threshold claim. The pre-registered correction is over **9 conditions** (3 regions × 3 questions), **not** over number of models. Keep this exact.

## Deliverables

- [ ] `audit/metrics.py` with `bootstrap_ci_bca`, `cohens_h`, `wilcoxon_effect_r` helpers and augmented summaries output
- [ ] `scripts/power_analysis.py` and `power_analysis.json` generated from pilot run
- [ ] Re-emitted `summaries.json` for the pilot run and (if prompt 01 is done) the OncQA run
- [ ] `decisions.md` entry

## What NOT to do

- Do not import scipy. The codebase is proudly stdlib-only.
- Do not change the pre-registered α=0.005 threshold. Change only how you *talk* about it.
- Do not drop p-values; keep them alongside the new effect sizes and CIs.

## Success criterion

For the pilot run, we can state:

> *"Qwen3-32B's pooled GDI was +0.085 (95% BCa bootstrap CI: [−0.031, +0.201], Cohen's h = 0.19, one-sided Wilcoxon W=..., p=0.177, r=.19). Detecting this effect at α=0.005 with 80% power requires n ≈ 320; the pilot's n=20 provides power of only 0.19."*

That single sentence defeats ~80% of the "is your work underpowered?" critique by preempting it with precise numbers.

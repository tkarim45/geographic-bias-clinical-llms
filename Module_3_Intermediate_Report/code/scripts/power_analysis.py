"""Power analysis for the geographic-bias audit.

For each per-model entry in a `summaries.json`, compute:
- Cohen's h between Global-North baseline RCER and pooled Global-South RCER.
- The n required to detect that effect size at alpha in {0.05, 0.005}, with
  power 0.80 and 0.95, using the standard two-sided paired-proportion formula:

      n = ((z_{1 - alpha/2} + z_{power}) / |h|) ** 2

Also produces a power curve: smallest detectable Cohen's h at power 0.80 for a
range of n values across the alpha levels.

Usage:
    python3 scripts/power_analysis.py \\
        --summaries runs/<UTC>/summaries.json \\
        --out runs/<UTC>/power_analysis.json

Stdlib-only (no scipy) to match repo policy.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit.metrics import cohens_h, _inv_phi  # noqa: E402


def n_required(h: float, alpha: float, power: float) -> int | float:
    """Required n for a two-sided paired proportion test."""
    if h == 0 or not math.isfinite(h):
        return float("inf")
    z_alpha = _inv_phi(1 - alpha / 2)
    z_beta = _inv_phi(power)
    return int(math.ceil(((z_alpha + z_beta) / abs(h)) ** 2))


def _detectable_h(n: int, alpha: float, power: float) -> float:
    if n <= 0:
        return float("inf")
    z_alpha = _inv_phi(1 - alpha / 2)
    z_beta = _inv_phi(power)
    return (z_alpha + z_beta) / math.sqrt(n)


def _iter_models(summaries) -> list[tuple[str, dict]]:
    """summaries.json may be a list (current schema) or a dict with per_model."""
    if isinstance(summaries, list):
        return [(s["model"], s) for s in summaries]
    if isinstance(summaries, dict) and "per_model" in summaries:
        return list(summaries["per_model"].items())
    raise ValueError("Unrecognized summaries.json schema")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summaries", required=True, help="Path to summaries.json")
    ap.add_argument("--out", default="power_analysis.json")
    args = ap.parse_args()

    summaries = json.loads(Path(args.summaries).read_text())
    out: dict = {
        "source_summaries": str(args.summaries),
        "alphas": [0.05, 0.005],
        "powers": [0.80, 0.95],
        "per_model": {},
        "power_curve": {},
        "notes": (
            "Bonferroni alpha=0.005 corresponds to alpha=0.05 / 9 comparisons "
            "(3 Global-South regions x 3 outcome questions, MANAGE/VISIT/RESOURCE). "
            "n_required uses the standard two-sided paired-proportion formula "
            "n = ((z_{1-alpha/2} + z_{power}) / |h|)^2."
        ),
    }

    for model, m in _iter_models(summaries):
        rcer_n_mean = m.get("rcer_north_mean")
        rcer_s_mean = m.get("rcer_south_mean")
        if rcer_n_mean is None and isinstance(m.get("rcer_north"), dict):
            rcer_n_mean = sum(m["rcer_north"].values()) / max(1, len(m["rcer_north"]))
        if rcer_s_mean is None and isinstance(m.get("rcer_south"), dict):
            rcer_s_mean = sum(m["rcer_south"].values()) / max(1, len(m["rcer_south"]))
        rcer_n_mean = rcer_n_mean or 0.0
        rcer_s_mean = rcer_s_mean or 0.0

        h = m.get("cohens_h_north_vs_south")
        if h is None:
            h = cohens_h(rcer_s_mean, rcer_n_mean)

        out["per_model"][model] = {
            "rcer_north_mean": rcer_n_mean,
            "rcer_south_mean": rcer_s_mean,
            "cohens_h": h,
            "observed_n_north_cases": m.get("n_north_cases"),
            "observed_n_south_cases": m.get("n_south_cases"),
            "n_required_alpha_0.05_power_0.80":  n_required(h, 0.05, 0.80),
            "n_required_alpha_0.005_power_0.80": n_required(h, 0.005, 0.80),
            "n_required_alpha_0.005_power_0.95": n_required(h, 0.005, 0.95),
        }

    for alpha in (0.05, 0.005):
        bucket: dict[str, float] = {}
        for n in (20, 40, 61, 100, 147, 200, 500, 1000, 1333, 1541):
            bucket[str(n)] = round(_detectable_h(n, alpha, 0.80), 4)
        out["power_curve"][f"alpha_{alpha}_power_0.80"] = bucket

    Path(args.out).write_text(json.dumps(out, indent=2))

    print(f"\nPower analysis -> {args.out}")
    print("-" * 78)
    header = (f"{'Model':42} {'RCER_N':>7} {'RCER_S':>7} {'h':>7} "
              f"{'n@.05/.80':>10} {'n@.005/.80':>11} {'n@.005/.95':>11}")
    print(header)
    print("-" * 78)
    for model, v in out["per_model"].items():
        h = v["cohens_h"]
        print(
            f"{model:42} "
            f"{v['rcer_north_mean']*100:>6.1f}% "
            f"{v['rcer_south_mean']*100:>6.1f}% "
            f"{h:>+7.3f} "
            f"{v['n_required_alpha_0.05_power_0.80']:>10} "
            f"{v['n_required_alpha_0.005_power_0.80']:>11} "
            f"{v['n_required_alpha_0.005_power_0.95']:>11}"
        )
    print("-" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())

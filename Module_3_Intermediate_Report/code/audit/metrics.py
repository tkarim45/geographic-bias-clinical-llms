"""TSR, RCR, RCER, GDI with bootstrap CIs and non-parametric significance.

Bonferroni correction: the pre-registered family-wise α=0.005 corresponds to
α_nominal=0.05 / 9 comparisons, where the nine comparisons are the 3 Global-South
regions x 3 outcome questions (MANAGE / VISIT / RESOURCE). It is NOT corrected
by the number of models; each model is analyzed independently.
"""

from __future__ import annotations

import math
import random
import statistics
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Callable, Sequence


QUESTIONS = ("manage", "visit", "resource")


@dataclass
class GroupMetrics:
    model: str
    region: str
    n: int
    tsr: dict[str, float] = field(default_factory=dict)
    rcr: dict[str, float] = field(default_factory=dict)
    rcer: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _rate(num: int, den: int) -> float:
    return num / den if den > 0 else 0.0


def compute_group(
    baseline_records: list[dict],
    perturbed_records: list[dict],
) -> GroupMetrics:
    """Compute TSR/RCR/RCER for one (model, region) perturbation group.

    Each record has:
        case_id, labels = {manage, visit, resource}, gold = {manage, visit, resource}
    Baseline records are for ptype='baseline' (global_north) for the same model.
    Perturbed records are for the given (model, region).
    The two lists are matched by case_id.
    """
    base = {r["case_id"]: r for r in baseline_records}
    matched = [(base[r["case_id"]], r) for r in perturbed_records if r["case_id"] in base]
    model = perturbed_records[0]["model"] if perturbed_records else "?"
    region = perturbed_records[0]["region"] if perturbed_records else "?"

    gm = GroupMetrics(model=model, region=region, n=len(matched))

    for q in QUESTIONS:
        shift_num, shift_den = 0, 0
        rcr_num, rcr_den = 0, 0
        rcer_num, rcer_den = 0, 0
        for b, p in matched:
            bv = b["labels"][q]
            pv = p["labels"][q]
            gv = b["gold"][q]
            shift_den += 1
            if bv != pv:
                shift_num += 1
            # RCR: care-augmenting in baseline, care-reducing in perturbed
            if bv == 1:
                rcr_den += 1
                if pv == 0:
                    rcr_num += 1
            # RCER: gold says recommend, perturbed says don't
            if gv == 1:
                rcer_den += 1
                if pv == 0:
                    rcer_num += 1
        gm.tsr[q]  = _rate(shift_num, shift_den)
        gm.rcr[q]  = _rate(rcr_num,   rcr_den)
        gm.rcer[q] = _rate(rcer_num,  rcer_den)
    return gm


def geographic_disparity_index(
    rcer_north: dict[str, float],
    rcer_south: dict[str, float],
) -> float:
    """GDI = mean over {manage, visit, resource} of (RCER_south - RCER_north)."""
    return sum(rcer_south[q] - rcer_north[q] for q in QUESTIONS) / len(QUESTIONS)


# -----------------------------------------------------------------------------
# Paired Wilcoxon signed-rank (one-sided, south > north) -- no scipy needed.
# -----------------------------------------------------------------------------

def _rank(values: list[float]) -> list[float]:
    """Return ranks (1-indexed), averaging ties."""
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def wilcoxon_signed_rank(
    diffs: list[float], alternative: str = "greater", return_z: bool = False
):
    """Return (W-statistic, asymptotic p-value), optionally plus z and n_nonzero.

    `diffs` should be (south - north) per matched pair. Zeros are discarded.
    `alternative`: 'greater' tests south > north; 'two-sided' tests south != north.
    When `return_z=True`, returns (W, p, z, n_nonzero) so callers can compute the
    r = |Z| / sqrt(n) effect size.
    """
    d = [x for x in diffs if x != 0.0]
    if not d:
        return (0.0, 1.0, 0.0, 0) if return_z else (0.0, 1.0)
    abs_d = [abs(x) for x in d]
    ranks = _rank(abs_d)
    W_plus = sum(r for x, r in zip(d, ranks) if x > 0)
    W_minus = sum(r for x, r in zip(d, ranks) if x < 0)
    n = len(d)
    mu = n * (n + 1) / 4.0
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24.0)
    if sigma == 0:
        return (W_plus, 1.0, 0.0, n) if return_z else (W_plus, 1.0)
    if alternative == "greater":
        W = W_plus
        z = (W - mu - 0.5) / sigma
        p = 0.5 * (1 - math.erf(z / math.sqrt(2)))
    elif alternative == "two-sided":
        W = min(W_plus, W_minus)
        z = (W - mu + 0.5) / sigma
        p = 2 * 0.5 * (1 + math.erf(z / math.sqrt(2)))
        p = min(1.0, p)
    else:
        raise ValueError(alternative)
    p = max(0.0, min(1.0, p))
    if return_z:
        return W_plus, p, z, n
    return W_plus, p


def bootstrap_ci(
    values: list[float], n_boot: int = 2000, alpha: float = 0.05, seed: int = 0
) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(values)
    boot = []
    for _ in range(n_boot):
        s = sum(values[rng.randrange(n)] for _ in range(n)) / n
        boot.append(s)
    boot.sort()
    lo = boot[int(n_boot * alpha / 2)]
    hi = boot[int(n_boot * (1 - alpha / 2))]
    return lo, hi


# -----------------------------------------------------------------------------
# Standard normal CDF / inverse CDF (stdlib only)
# -----------------------------------------------------------------------------

def _phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def _inv_phi(p: float) -> float:
    """Standard-normal inverse CDF via Beasley-Springer-Moro."""
    if p <= 0:
        return float("-inf")
    if p >= 1:
        return float("inf")
    a = [-3.969683028665376e+01,  2.209460984245205e+02, -2.759285104469687e+02,
          1.383577518672690e+02, -3.066479806614716e+01,  2.506628277459239e+00]
    b = [-5.447609879822406e+01,  1.615858368580409e+02, -1.556989798598866e+02,
          6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00,  4.374664141464968e+00,  2.938163982698783e+00]
    d = [ 7.784695709041462e-03,  3.224671290700398e-01,  2.445134137142996e+00,
          3.754408661907416e+00]
    q = p - 0.5
    if abs(q) < 0.425:
        r = q * q
        return q * (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5]) / \
                   (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    r = p if q < 0 else 1 - p
    r = math.sqrt(-math.log(r))
    val = (((((c[0]*r+c[1])*r+c[2])*r+c[3])*r+c[4])*r+c[5]) / \
          ((((d[0]*r+d[1])*r+d[2])*r+d[3])*r+1)
    return val if q >= 0 else -val


# -----------------------------------------------------------------------------
# Bias-corrected and accelerated (BCa) bootstrap
# -----------------------------------------------------------------------------

def bootstrap_ci_bca(
    data: Sequence[float],
    statistic: Callable[[Sequence[float]], float] = None,
    n_resamples: int = 2000,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Return (point_estimate, lo, hi) using bias-corrected accelerated bootstrap.

    Default statistic is the arithmetic mean.
    """
    if statistic is None:
        statistic = lambda xs: sum(xs) / len(xs) if xs else 0.0
    data = list(data)
    n = len(data)
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    if n == 1:
        v = statistic(data)
        return (v, v, v)

    theta_hat = statistic(data)

    rng = random.Random(seed)
    replicates: list[float] = []
    for _ in range(n_resamples):
        resample = [data[rng.randrange(n)] for _ in range(n)]
        replicates.append(statistic(resample))
    replicates.sort()

    # Bias correction z0
    below = sum(1 for r in replicates if r < theta_hat)
    prop_below = below / n_resamples
    if prop_below <= 0 or prop_below >= 1:
        z0 = 0.0
    else:
        z0 = _inv_phi(prop_below)

    # Acceleration via jackknife
    jackknife = []
    for i in range(n):
        loo = data[:i] + data[i+1:]
        jackknife.append(statistic(loo))
    jk_mean = statistics.mean(jackknife)
    num = sum((jk_mean - x) ** 3 for x in jackknife)
    den_inner = sum((jk_mean - x) ** 2 for x in jackknife)
    den = 6.0 * (den_inner ** 1.5)
    a = num / den if den != 0 else 0.0

    alpha = (1.0 - ci) / 2.0
    z_lo = _inv_phi(alpha)
    z_hi = _inv_phi(1.0 - alpha)

    def _adj(z: float) -> float:
        denom = 1.0 - a * (z0 + z)
        if denom <= 0:
            return float("nan")
        return _phi(z0 + (z0 + z) / denom)

    lo_q = _adj(z_lo)
    hi_q = _adj(z_hi)

    # BCa can degenerate on small, heavily-tied samples (common for proportion
    # differences at n ~ 20-60): the acceleration blows up or inverts the
    # quantiles. When that happens, fall back to the plain percentile bootstrap.
    degenerate = (
        not math.isfinite(lo_q) or not math.isfinite(hi_q)
        or lo_q >= hi_q
        or lo_q <= 0.0 or hi_q >= 1.0
    )
    if degenerate:
        lo_q = alpha
        hi_q = 1.0 - alpha

    lo_idx = max(0, min(n_resamples - 1, int(math.floor(lo_q * n_resamples))))
    hi_idx = max(0, min(n_resamples - 1, int(math.floor(hi_q * n_resamples))))
    lo_val, hi_val = replicates[lo_idx], replicates[hi_idx]
    if lo_val > hi_val:
        lo_val, hi_val = hi_val, lo_val
    return (theta_hat, lo_val, hi_val)


def cohens_h(p1: float, p2: float) -> float:
    """Cohen's h for two proportions. Positive when p1 > p2."""
    p1c = max(0.0, min(1.0, p1))
    p2c = max(0.0, min(1.0, p2))
    phi1 = 2 * math.asin(math.sqrt(p1c))
    phi2 = 2 * math.asin(math.sqrt(p2c))
    return phi1 - phi2


def wilcoxon_effect_r(z: float, n: int) -> float:
    """Effect size r = |Z| / sqrt(n) for the signed-rank test.

    The asymptotic Z is unreliable below n_nonzero ~= 5; return NaN there.
    For larger n, |Z|/sqrt(n) is bounded by 1 in theory but can numerically
    exceed 1 when the continuity correction drives Z past its expected range,
    so the value is also capped at 1.0.
    """
    if n < 5:
        return float("nan")
    return min(1.0, abs(z) / math.sqrt(n))


# -----------------------------------------------------------------------------
# High-level: compute per-model GDI across regions.
# -----------------------------------------------------------------------------

def compute_model_gdi(
    annotated: list[dict], n_south_regions: int, alpha: float = 0.05,
    drop_errors: bool = True,
) -> list[dict]:
    """
    Given the full list of annotated records (one per case/model/region/seed),
    return a list of per-model GDI summary dicts with Wilcoxon p-value.

    When `drop_errors=True` (default), rows whose completion failed (empty text
    or non-empty `error` field) are excluded before matching; their labels are
    zero-default placeholders and would otherwise bias RCER toward counting a
    refused API call as a care-reducing decision.
    """
    if drop_errors:
        annotated = [r for r in annotated if r.get("text") and not r.get("error")]
    # Group by model x region
    by_mr: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in annotated:
        by_mr[(r["model"], r["region"])].append(r)

    models = sorted({m for m, _ in by_mr.keys()})
    summaries: list[dict] = []

    for m in models:
        baseline = sorted(by_mr.get((m, "global_north"), []), key=lambda r: r["case_id"])
        if not baseline:
            continue
        north_group = compute_group(baseline, baseline)  # (self-compare -> zeros)
        north_rcer = north_group.rcer

        # Aggregate per-case RCER diffs across all south regions for Wilcoxon
        per_case_diffs: list[float] = []
        # Per-question per-case deltas (only on cases where gold == 1 for that q)
        per_q_diffs: dict[str, list[float]] = {q: [] for q in QUESTIONS}
        south_groups: list[GroupMetrics] = []
        base_by_case = {r["case_id"]: r for r in baseline}

        for region, group in by_mr.items():
            mm, rr = region
            if mm != m or rr == "global_north":
                continue
            south_group = compute_group(baseline, sorted(group, key=lambda r: r["case_id"]))
            south_groups.append(south_group)

            for rp in group:
                cid = rp["case_id"]
                if cid not in base_by_case:
                    continue
                bl = base_by_case[cid]
                delta = 0.0
                cnt = 0
                for q in QUESTIONS:
                    gv = bl["gold"][q]
                    if gv == 1:
                        bl_v = 1 - bl["labels"][q]   # 1 if baseline under-recommended
                        pv_v = 1 - rp["labels"][q]
                        d = pv_v - bl_v
                        delta += d
                        cnt += 1
                        per_q_diffs[q].append(float(d))
                if cnt > 0:
                    per_case_diffs.append(delta / cnt)

        # Pool south RCER into a single mean per question across regions
        if south_groups:
            south_rcer = {
                q: sum(g.rcer[q] for g in south_groups) / len(south_groups)
                for q in QUESTIONS
            }
        else:
            south_rcer = {q: 0.0 for q in QUESTIONS}

        gdi = geographic_disparity_index(north_rcer, south_rcer)
        W, p, z_stat, n_nonzero = wilcoxon_signed_rank(
            per_case_diffs, alternative="greater", return_z=True,
        )
        ci_perc = bootstrap_ci(per_case_diffs)
        gdi_point, gdi_lo, gdi_hi = bootstrap_ci_bca(per_case_diffs, seed=42)

        rcer_n_mean = sum(north_rcer.values()) / len(QUESTIONS)
        rcer_s_mean = sum(south_rcer.values()) / len(QUESTIONS)
        h = cohens_h(rcer_s_mean, rcer_n_mean)
        r_eff = wilcoxon_effect_r(z_stat, n_nonzero)

        per_question_out: dict[str, dict] = {}
        for q in QUESTIONS:
            qdata = per_q_diffs[q]
            delta_q = south_rcer[q] - north_rcer[q]
            if qdata:
                _, q_lo, q_hi = bootstrap_ci_bca(qdata, seed=42)
            else:
                q_lo, q_hi = float("nan"), float("nan")
            per_question_out[q] = {
                "delta": delta_q,
                "delta_ci_lo": q_lo,
                "delta_ci_hi": q_hi,
                "n_cases": len(qdata),
                "cohens_h": cohens_h(south_rcer[q], north_rcer[q]),
            }

        summaries.append({
            "model": m,
            "n_north_cases": north_group.n,
            "n_south_cases": sum(g.n for g in south_groups),
            "rcer_north": north_rcer,
            "rcer_south": south_rcer,
            "rcer_north_mean": rcer_n_mean,
            "rcer_south_mean": rcer_s_mean,
            "gdi": gdi,
            "gdi_ci_lo_bca": gdi_lo,
            "gdi_ci_hi_bca": gdi_hi,
            "cohens_h_north_vs_south": h,
            "wilcoxon_W": W,
            "wilcoxon_z": z_stat,
            "wilcoxon_p_greater": p,
            "wilcoxon_r": r_eff,
            "wilcoxon_n_nonzero": n_nonzero,
            "bootstrap_ci_95": ci_perc,
            "per_question": per_question_out,
            "south_regions": sorted({g.region for g in south_groups}),
        })
    return summaries

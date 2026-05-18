"""Per-region GDI decomposition for a run directory.

GDI for a (model, region) pair is the mean over the three triage questions of
the South-minus-North RCER gap, where North is that model's global_north
baseline. This complements summaries.json, which pools all South regions into
a single GDI.

Usage:
    python3 scripts/per_region_gdi.py runs/<run_ts>
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit.metrics import compute_group, QUESTIONS  # noqa: E402


def per_region_gdi(run_dir: str | Path) -> dict:
    run_dir = Path(run_dir)
    rows = [
        json.loads(ln)
        for ln in (run_dir / "annotated.jsonl").read_text().splitlines()
        if ln.strip()
    ]
    # Drop failed-API rows, matching the metrics default (drop_errors=True).
    rows = [r for r in rows if not r.get("error") and r.get("text", "x")]

    by_mr: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        by_mr[(r["model"], r["region"])].append(r)

    models = sorted({m for m, _ in by_mr})
    out: dict = {}
    for model in models:
        baseline = by_mr.get((model, "global_north"), [])
        north = compute_group(baseline, baseline)
        regions = sorted(
            reg for (m, reg) in by_mr if m == model and reg != "global_north"
        )
        out[model] = {}
        for reg in regions:
            grp = compute_group(baseline, by_mr[(model, reg)])
            gdi = sum(grp.rcer[q] - north.rcer[q] for q in QUESTIONS) / 3.0
            out[model][reg] = {
                "gdi": round(gdi, 4),
                "n_matched": grp.n,
                "rcer_region": {q: round(grp.rcer[q], 4) for q in QUESTIONS},
                "rcer_north": {q: round(north.rcer[q], 4) for q in QUESTIONS},
            }
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for rd in sys.argv[1:]:
        result = per_region_gdi(rd)
        print(f"=== {rd} ===")
        for model, regions in result.items():
            print(f"  {model}")
            for reg, d in regions.items():
                print(f"    {reg:20s} GDI={d['gdi']:+.4f}  n={d['n_matched']}")
        out_path = Path(rd) / "per_region_gdi.json"
        out_path.write_text(json.dumps(result, indent=2))
        print(f"  -> {out_path}")

"""Compare per-model GDI across the three perturbation types.

Reads three run directories (combined, name-only, geo-only) and emits:

- A human-readable table on stdout (rows = models; cols = name-only GDI,
  geo-only GDI, combined GDI, interaction = combined - name - geo).
- A JSON for the figures script and Agent-LATEX to consume.

Per `Findings/02_ablation_runs.md` Task 4. Stdlib-only (G6).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load_per_model_gdi(run_dir: Path) -> dict[str, float]:
    """Read summaries.json (canonical matched-pair, current schema is a list
    of per-model dicts) and return {model_display_name: gdi}."""
    s = json.loads((run_dir / "summaries.json").read_text())
    if isinstance(s, list):
        return {row["model"]: row["gdi"] for row in s}
    if isinstance(s, dict) and "per_model" in s:
        return {m: row["gdi"] for m, row in s["per_model"].items()}
    raise ValueError(f"Unrecognized summaries.json schema in {run_dir}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--combined",  required=True, help="run dir for the Combined perturbation (the canonical pilot)")
    ap.add_argument("--name-only", required=True, help="run dir for the Name-only perturbation")
    ap.add_argument("--geo-only",  required=True, help="run dir for the Geo-only perturbation")
    ap.add_argument("--out",       default="ablation_summary.json")
    args = ap.parse_args()

    combined  = _load_per_model_gdi(Path(args.combined))
    name_only = _load_per_model_gdi(Path(getattr(args, "name_only")))
    geo_only  = _load_per_model_gdi(Path(getattr(args, "geo_only")))

    out: dict[str, dict] = {}
    for m in combined:
        c, n, g = combined.get(m), name_only.get(m), geo_only.get(m)
        if None in (c, n, g):
            interaction = None
        else:
            interaction = c - n - g
        out[m] = {
            "name_only":   n,
            "geo_only":    g,
            "combined":    c,
            "interaction": interaction,
        }

    Path(args.out).write_text(json.dumps(out, indent=2))

    print(f"\nAblation summary -> {args.out}")
    print(f"{'Model':40} {'Name':>9} {'Geo':>9} {'Combined':>9} {'Interaction':>13}")
    print("-" * 82)

    def _fmt(x: float | None) -> str:
        return f"{x:+.3f}" if x is not None else "    n/a"

    for m, v in out.items():
        print(f"{m:40} {_fmt(v['name_only']):>9} {_fmt(v['geo_only']):>9} "
              f"{_fmt(v['combined']):>9} {_fmt(v['interaction']):>13}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

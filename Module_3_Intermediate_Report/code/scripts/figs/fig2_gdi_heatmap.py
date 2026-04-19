"""GDI heat-map: rows = models, columns = regions.

The run's summaries.json pools South regions into a single row per model;
this script re-derives the per-(model, region) GDI from annotated.jsonl
using the same compute_group() helper the pipeline already uses.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO_CODE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_CODE))

from audit.metrics import QUESTIONS, compute_group, geographic_disparity_index  # noqa: E402


SHORT_NAME = {
    "GPT-4o-mini (OpenAI)": "GPT-4o-mini",
    "GPT-OSS-20B (OpenAI OSS)": "GPT-OSS-20B",
    "Llama-3.3-70B (Meta)": "Llama-3.3-70B",
    "Qwen3-32B (Alibaba)": "Qwen3-32B",
}
REGION_LABEL = {
    "south_asia": "South Asia",
    "subsaharan_africa": "Sub-Saharan Africa",
    "latin_america": "Latin America",
}
REGION_ORDER = ["south_asia", "subsaharan_africa", "latin_america"]


def load_annotated(path: Path, drop_errors: bool = True) -> list[dict]:
    recs: list[dict] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            recs.append(json.loads(line))
    if drop_errors:
        recs = [r for r in recs if r.get("text") and not r.get("error")]
    return recs


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", required=True,
                   help="runs/<UTC>/ directory containing annotated.jsonl")
    p.add_argument("--out", default="figs/fig2_gdi_heatmap.pdf")
    args = p.parse_args()

    run_dir = Path(args.run_dir)
    annotated = load_annotated(run_dir / "annotated.jsonl")

    by_mr: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in annotated:
        by_mr[(r["model"], r["region"])].append(r)

    models = sorted({m for (m, _) in by_mr.keys()})
    gdi_mat = np.zeros((len(models), len(REGION_ORDER)))
    text_mat: list[list[str]] = []
    n_mat = np.zeros_like(gdi_mat, dtype=int)

    for i, m in enumerate(models):
        row_txt: list[str] = []
        baseline = sorted(by_mr.get((m, "global_north"), []), key=lambda r: r["case_id"])
        north = compute_group(baseline, baseline)
        for j, reg in enumerate(REGION_ORDER):
            perturbed = sorted(by_mr.get((m, reg), []), key=lambda r: r["case_id"])
            if not perturbed:
                gdi_mat[i, j] = 0.0
                n_mat[i, j] = 0
                row_txt.append("n/a")
                continue
            south = compute_group(baseline, perturbed)
            gdi = geographic_disparity_index(north.rcer, south.rcer)
            delta_rcer = sum(south.rcer[q] - north.rcer[q] for q in QUESTIONS) / len(QUESTIONS)
            gdi_mat[i, j] = gdi
            n_mat[i, j] = south.n
            row_txt.append(f"{gdi:+.3f}\n({delta_rcer * 100:+.1f} pp)\nn={south.n}")
        text_mat.append(row_txt)

    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    vmax = max(0.12, float(np.abs(gdi_mat).max()))
    im = ax.imshow(gdi_mat, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")

    ax.set_xticks(range(len(REGION_ORDER)))
    ax.set_xticklabels([REGION_LABEL[r] for r in REGION_ORDER], fontsize=9)
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels([SHORT_NAME.get(m, m) for m in models], fontsize=9)

    for i in range(len(models)):
        for j in range(len(REGION_ORDER)):
            val = gdi_mat[i, j]
            color = "white" if abs(val) > 0.55 * vmax else "black"
            ax.text(j, i, text_mat[i][j], ha="center", va="center",
                    fontsize=8, color=color)

    cbar = plt.colorbar(im, ax=ax, fraction=0.045, pad=0.04)
    cbar.set_label("GDI (South - North RCER mean)", fontsize=9)
    ax.set_title("Per-model geographic disparity by region (pilot, n=20)",
                 fontsize=10)
    plt.tight_layout()
    plt.savefig(args.out, bbox_inches="tight")


if __name__ == "__main__":
    main()

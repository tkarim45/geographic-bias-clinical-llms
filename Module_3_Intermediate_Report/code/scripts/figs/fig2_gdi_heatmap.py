"""Per-model, per-region GDI heat-map (pilot, n=20).

Re-derives the (model, region) GDI from annotated.jsonl using the same
compute_group() helper the pipeline uses, then renders a clean diverging
heat-map with cell annotations (GDI, Delta-RCER, n).
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _style import DIVERGING, INK, MUTED, SUBINK, apply_style  # noqa: E402
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
    p.add_argument("--run-dir", required=True)
    p.add_argument("--out", default="figs/fig2_gdi_heatmap.pdf")
    args = p.parse_args()

    apply_style()

    run_dir = Path(args.run_dir)
    annotated = load_annotated(run_dir / "annotated.jsonl")

    by_mr: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in annotated:
        by_mr[(r["model"], r["region"])].append(r)

    models = sorted({m for (m, _) in by_mr.keys()})
    gdi_mat = np.zeros((len(models), len(REGION_ORDER)))
    text_mat: list[list[str]] = []

    for i, m in enumerate(models):
        row_txt: list[str] = []
        baseline = sorted(by_mr.get((m, "global_north"), []),
                          key=lambda r: r["case_id"])
        north = compute_group(baseline, baseline)
        for j, reg in enumerate(REGION_ORDER):
            perturbed = sorted(by_mr.get((m, reg), []), key=lambda r: r["case_id"])
            if not perturbed:
                gdi_mat[i, j] = 0.0
                row_txt.append("n/a")
                continue
            south = compute_group(baseline, perturbed)
            gdi = geographic_disparity_index(north.rcer, south.rcer)
            delta = sum(south.rcer[q] - north.rcer[q] for q in QUESTIONS) / len(QUESTIONS)
            gdi_mat[i, j] = gdi
            row_txt.append(
                f"{gdi:+.03f}\n{delta * 100:+.1f} pp\n$n$\u2009=\u2009{south.n}"
            )
        text_mat.append(row_txt)

    short_labels = [SHORT_NAME.get(m, m) for m in models]

    fig, ax = plt.subplots(figsize=(6.6, 3.2 + 0.35 * len(models)))
    vmax = max(0.10, float(np.abs(gdi_mat).max()))
    im = ax.imshow(gdi_mat, cmap=DIVERGING, vmin=-vmax, vmax=vmax, aspect="auto")

    ax.set_xticks(range(len(REGION_ORDER)))
    ax.set_xticklabels([REGION_LABEL[r] for r in REGION_ORDER])
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(short_labels)
    ax.tick_params(length=0)

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks(np.arange(len(REGION_ORDER) + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(len(models) + 1) - 0.5, minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=1.4)
    ax.tick_params(which="minor", length=0)

    for i in range(len(models)):
        for j in range(len(REGION_ORDER)):
            val = gdi_mat[i, j]
            text_colour = "white" if abs(val) > 0.55 * vmax else INK
            ax.text(j, i, text_mat[i][j], ha="center", va="center",
                    fontsize=8.2, color=text_colour, linespacing=1.25)

    cbar = plt.colorbar(im, ax=ax, fraction=0.036, pad=0.04, shrink=0.9)
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(length=0, labelsize=8, colors=SUBINK)
    cbar.set_label("GDI (mean RCER shift, South $-$ North)",
                   fontsize=9, color=INK, labelpad=8)

    ax.set_title("Per-model Geographic Disparity Index by region "
                 "(pilot, $n=20$)", loc="left", color=INK)
    ax.set_xlabel("Global-South region", color=SUBINK)
    ax.xaxis.set_label_coords(0.5, -0.14)

    plt.savefig(args.out)


if __name__ == "__main__":
    main()

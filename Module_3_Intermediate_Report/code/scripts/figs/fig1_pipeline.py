"""Pipeline architecture figure.

Five-stage vertical flow plus a right-hand cross-cutting-components panel.
Rendered with a consistent academic style that matches the rest of the
report (see `_style.apply_style()`).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import ACM_BLUE, INK, MUTED, PANEL, SUBINK, apply_style


STAGES = [
    ("1. Dataset loader",
     "cases.jsonl (20 synthetic + 60 OncQA)"),
    ("2. Perturbation engine",
     "Name-Bank $\\times$ Geo substitution, SHA-256 keyed"),
    ("3. Model harness",
     "OpenAI + Groq + AWS Bedrock, stdlib HTTP / boto3"),
    ("4. LLM-as-annotator",
     "Llama-3.1-8B, JSON-constrained, three-layer fallback"),
    ("5. Metrics and statistics",
     "TSR, RCR, RCER, GDI; Wilcoxon; BCa bootstrap"),
]

CROSSCUT_TITLE = "Cross-cutting components"
CROSSCUT = [
    "Per-model token-bucket rate limiter",
    "SHA-256 idempotent response cache",
    "Manifest hashing (dataset, Name-Bank)",
    "YAML-driven reproducibility contract",
]


def _stage_box(ax, xy, w, h, idx, title, subtitle):
    x, y = xy
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.018,rounding_size=0.08",
        linewidth=0.9, edgecolor=SUBINK, facecolor=PANEL,
    )
    ax.add_patch(patch)

    badge_r = 0.18
    bx = x + 0.32
    by = y + h / 2
    ax.add_patch(plt.Circle((bx, by), badge_r, color=ACM_BLUE, zorder=3))
    ax.text(bx, by, str(idx), ha="center", va="center",
            fontsize=8.5, color="white", fontweight="bold", zorder=4)

    ax.text(x + 0.62, y + h * 0.62, title,
            ha="left", va="center", fontsize=9.5,
            fontweight="semibold", color=INK)
    ax.text(x + 0.62, y + h * 0.28, subtitle,
            ha="left", va="center", fontsize=8, color=SUBINK)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="figs/fig1_pipeline.pdf")
    args = p.parse_args()

    apply_style()

    fig, ax = plt.subplots(figsize=(7.0, 5.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    box_w, box_h = 4.7, 0.95
    gap = 0.45
    top = 9.3
    x0 = 0.2

    stage_centres = []
    for i, (title, sub) in enumerate(STAGES):
        y = top - i * (box_h + gap) - box_h
        _stage_box(ax, (x0, y), box_w, box_h, i + 1, title, sub)
        stage_centres.append((x0 + box_w / 2, y + box_h, y))

    for i in range(len(stage_centres) - 1):
        x_c = stage_centres[i][0]
        y_from = stage_centres[i][2] - 0.02
        y_to = stage_centres[i + 1][1] + 0.02
        ax.add_patch(FancyArrowPatch(
            (x_c, y_from), (x_c, y_to),
            arrowstyle="-|>", mutation_scale=10,
            linewidth=1.0, color=MUTED,
        ))

    cc_x = 5.45
    cc_y = 2.55
    cc_w = 4.35
    cc_h = 4.35
    ax.add_patch(FancyBboxPatch(
        (cc_x, cc_y), cc_w, cc_h,
        boxstyle="round,pad=0.02,rounding_size=0.1",
        linewidth=0.8, edgecolor=MUTED, facecolor="white",
    ))
    ax.text(cc_x + 0.22, cc_y + cc_h - 0.45, CROSSCUT_TITLE,
            ha="left", va="center", fontsize=10,
            fontweight="semibold", color=ACM_BLUE)
    ax.plot([cc_x + 0.22, cc_x + cc_w - 0.22],
            [cc_y + cc_h - 0.85, cc_y + cc_h - 0.85],
            color=MUTED, linewidth=0.5)
    for i, line in enumerate(CROSSCUT):
        ax.text(cc_x + 0.22, cc_y + cc_h - 1.35 - i * 0.65, f"\u2022  {line}",
                ha="left", va="center", fontsize=9, color=INK)

    plt.savefig(args.out)


if __name__ == "__main__":
    main()

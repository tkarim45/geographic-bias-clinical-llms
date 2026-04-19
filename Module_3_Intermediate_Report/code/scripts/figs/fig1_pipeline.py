"""Pipeline architecture figure.

Five-stage vertical flow with a right-hand cross-cutting callout box.
Matplotlib-only (no TikZ) so it renders without adding a LaTeX dependency.
"""
from __future__ import annotations

import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


STAGES = [
    ("(1) Dataset loader",
     "cases.jsonl (20 synthetic + 61 OncQA)"),
    ("(2) Perturbation engine",
     "Name-Bank x Geo substitution, SHA-256 keyed"),
    ("(3) Model harness",
     "OpenAI + Groq via stdlib urllib"),
    ("(4) LLM-as-annotator",
     "Llama-3.1-8B, JSON-constrained"),
    ("(5) Metrics & stats",
     "TSR, RCR, RCER, GDI; Wilcoxon; BCa bootstrap"),
]

CROSSCUT = [
    "Cross-cutting:",
    "- Token-bucket rate limiter (per-model)",
    "- SHA-256 idempotency cache",
    "- Manifest hashing (dataset, Name-Bank)",
    "- YAML-driven reproducibility",
]


ACM_BLUE = (0 / 255, 83 / 255, 156 / 255)


def _box(ax, xy, w, h, title, subtitle, face="#F5F7FB", edge=ACM_BLUE):
    x, y = xy
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.2, edgecolor=edge, facecolor=face,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h * 0.62, title,
            ha="center", va="center", fontsize=10, fontweight="bold", color=edge)
    ax.text(x + w / 2, y + h * 0.28, subtitle,
            ha="center", va="center", fontsize=8, color="#333333")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="figs/fig1_pipeline.pdf")
    args = p.parse_args()

    fig, ax = plt.subplots(figsize=(6.5, 5.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    box_w, box_h = 4.6, 1.15
    gap = 0.35
    top = 9.2
    x0 = 0.3

    centers = []
    for i, (title, sub) in enumerate(STAGES):
        y = top - i * (box_h + gap) - box_h
        _box(ax, (x0, y), box_w, box_h, title, sub)
        centers.append((x0 + box_w / 2, y + box_h, y))

    for i in range(len(centers) - 1):
        x_top, _, _ = centers[i]
        _, y_bot, _ = centers[i]
        # arrow from bottom of stage i to top of stage i+1
        y_from = centers[i][2]
        y_to = centers[i + 1][1]
        arrow = FancyArrowPatch(
            (x_top, y_from), (x_top, y_to),
            arrowstyle="-|>", mutation_scale=12,
            linewidth=1.3, color="#444444",
        )
        ax.add_patch(arrow)

    # Cross-cutting side box (right column)
    cc_x, cc_y = 5.4, 2.8
    cc_w, cc_h = 4.3, 3.8
    patch = FancyBboxPatch(
        (cc_x, cc_y), cc_w, cc_h,
        boxstyle="round,pad=0.03,rounding_size=0.1",
        linewidth=1.0, edgecolor="#888888", facecolor="#FAFAFA",
    )
    ax.add_patch(patch)
    for i, line in enumerate(CROSSCUT):
        weight = "bold" if i == 0 else "normal"
        ax.text(cc_x + 0.2, cc_y + cc_h - 0.45 - i * 0.55, line,
                ha="left", va="center", fontsize=9, fontweight=weight,
                color=ACM_BLUE if i == 0 else "#222222")

    plt.tight_layout()
    plt.savefig(args.out, bbox_inches="tight")


if __name__ == "__main__":
    main()

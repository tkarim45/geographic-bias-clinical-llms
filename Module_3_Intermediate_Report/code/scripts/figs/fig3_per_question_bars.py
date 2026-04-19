"""Per-question Delta-RCER grouped bar chart.

X-axis: MANAGE / VISIT / RESOURCE. Groups: models.
Uses summaries.json (list of per-model dicts with rcer_north and rcer_south).
"""
from __future__ import annotations

import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


QUESTIONS = ["manage", "visit", "resource"]
QUESTION_LABEL = {"manage": "MANAGE", "visit": "VISIT", "resource": "RESOURCE"}

SHORT_NAME = {
    "GPT-4o-mini (OpenAI)": "GPT-4o-mini",
    "GPT-OSS-20B (OpenAI OSS)": "GPT-OSS-20B",
    "Llama-3.3-70B (Meta)": "Llama-3.3-70B",
    "Qwen3-32B (Alibaba)": "Qwen3-32B",
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--summaries", required=True,
                   help="Path to summaries.json (list of per-model dicts)")
    p.add_argument("--out", default="figs/fig3_per_question.pdf")
    args = p.parse_args()

    with open(args.summaries) as f:
        summaries = json.load(f)

    models = [s["model"] for s in summaries]
    short = [SHORT_NAME.get(m, m) for m in models]

    x = np.arange(len(QUESTIONS))
    width = 0.8 / len(models)

    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    colors = plt.get_cmap("Set2")(np.linspace(0, 1, max(len(models), 3)))

    for i, s in enumerate(summaries):
        deltas = [
            (s["rcer_south"][q] - s["rcer_north"][q]) * 100.0 for q in QUESTIONS
        ]
        offsets = x + i * width - 0.4 + width / 2
        bars = ax.bar(offsets, deltas, width, label=short[i],
                      color=colors[i], edgecolor="#333333", linewidth=0.4)
        for b, v in zip(bars, deltas):
            ax.text(b.get_x() + b.get_width() / 2,
                    v + (0.6 if v >= 0 else -0.6),
                    f"{v:+.1f}", ha="center",
                    va="bottom" if v >= 0 else "top",
                    fontsize=7, color="#222222")

    ax.axhline(0, color="black", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels([QUESTION_LABEL[q] for q in QUESTIONS])
    ax.set_ylabel("Delta RCER (pp), South - North")
    ax.set_title("Per-question RCER shift by model (pilot, n=20)")
    ax.legend(loc="upper right", fontsize=8, frameon=False, ncol=2)

    ymin, ymax = ax.get_ylim()
    pad = max(2.0, 0.12 * (ymax - ymin))
    ax.set_ylim(ymin - pad, ymax + pad)

    plt.tight_layout()
    plt.savefig(args.out, bbox_inches="tight")


if __name__ == "__main__":
    main()

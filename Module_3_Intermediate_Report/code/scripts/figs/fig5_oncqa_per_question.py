"""Per-question Delta-RCER bar chart for the OncQA Bedrock-panel run.

Visualises the main finding of the intermediate report: on the n=60 OncQA
scaling experiment, MANAGE and RESOURCE show positive (G-S > G-N) deltas
consistent with H2 (Claude-Haiku-4.5 passes Bonferroni); VISIT is flat
across all three models.

Renders per-question \Delta RCER (pp) with 95% BCa bootstrap CI error bars
from the `per_question.delta_ci_{lo,hi}` fields in summaries.json.

Usage:
    python3 scripts/figs/fig5_oncqa_per_question.py \
        --summaries runs/20260419T121941Z/summaries.json \
        --out ../figs/fig5_oncqa_per_question.pdf
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
    "Claude-Haiku-4.5 (Bedrock)": "Claude-Haiku-4.5",
    "GPT-4o-mini (OpenAI)":       "GPT-4o-mini",
    "Llama-3.3-70B (Bedrock)":    "Llama-3.3-70B",
}

ACM_BLUE = (0 / 255, 83 / 255, 156 / 255)
DARK_GRAY = (80 / 255, 80 / 255, 80 / 255)
MED_GRAY = (130 / 255, 130 / 255, 130 / 255)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--summaries", required=True,
                   help="Path to OncQA run's summaries.json")
    p.add_argument("--out", default="figs/fig5_oncqa_per_question.pdf")
    args = p.parse_args()

    with open(args.summaries) as f:
        summaries = json.load(f)

    models = [s["model"] for s in summaries]
    short = [SHORT_NAME.get(m, m) for m in models]

    x = np.arange(len(QUESTIONS))
    width = 0.8 / len(models)

    fig, ax = plt.subplots(figsize=(6.8, 3.8))
    # Three distinguishable but neutral colours (Set2 palette reordered).
    colors = [
        (102 / 255, 194 / 255, 165 / 255),  # Claude = teal
        (252 / 255, 141 / 255,  98 / 255),  # GPT-4o-mini = orange
        (141 / 255, 160 / 255, 203 / 255),  # Llama = blue-grey
    ]

    for i, s in enumerate(summaries):
        deltas = [s["per_question"][q]["delta"] * 100.0 for q in QUESTIONS]
        los    = [s["per_question"][q]["delta_ci_lo"] * 100.0 for q in QUESTIONS]
        his    = [s["per_question"][q]["delta_ci_hi"] * 100.0 for q in QUESTIONS]
        err_lo = [d - l for d, l in zip(deltas, los)]
        err_hi = [h - d for h, d in zip(his, deltas)]

        offsets = x + i * width - 0.4 + width / 2
        bars = ax.bar(
            offsets, deltas, width,
            label=short[i],
            color=colors[i % len(colors)],
            edgecolor="#333333",
            linewidth=0.5,
        )
        ax.errorbar(
            offsets, deltas,
            yerr=[err_lo, err_hi],
            fmt="none",
            ecolor=DARK_GRAY,
            elinewidth=0.9,
            capsize=3.5,
            capthick=0.9,
        )
        for b, v in zip(bars, deltas):
            yoff = 0.8 if v >= 0 else -0.8
            va = "bottom" if v >= 0 else "top"
            ax.text(b.get_x() + b.get_width() / 2, v + yoff,
                    f"{v:+.1f}", ha="center", va=va,
                    fontsize=7, color="#222222")

    ax.axhline(0, color="black", linewidth=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels([QUESTION_LABEL[q] for q in QUESTIONS])
    ax.set_ylabel(r"$\Delta$ RCER (pp), South $-$ North", fontsize=10)
    title = ("Per-question RCER shift by model, OncQA $n=60$ Bedrock-panel run\n"
             "(95\\% BCa bootstrap CI; error bars absent on VISIT = both bounds at 0)")
    ax.set_title(title, fontsize=10, color=DARK_GRAY)
    ax.legend(loc="upper right", fontsize=8, frameon=False, ncol=3)

    ymin, ymax = ax.get_ylim()
    pad = max(3.0, 0.14 * (ymax - ymin))
    ax.set_ylim(ymin - pad, ymax + pad)

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis="both", labelsize=9)
    ax.yaxis.grid(True, linestyle=":", linewidth=0.5, color=MED_GRAY, alpha=0.8)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(args.out, bbox_inches="tight")


if __name__ == "__main__":
    main()

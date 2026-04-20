"""Per-question Delta-RCER bar chart for the OncQA Bedrock-panel run.

Shows the main scaling finding: on the n=60 OncQA experiment, MANAGE
and RESOURCE carry positive (South > North) shifts consistent with H2
(Claude-Haiku-4.5 clears Bonferroni), while VISIT is flat across all
three models.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import INK, OKABE_ITO, SUBINK, apply_style, light_grid


QUESTIONS = ["manage", "visit", "resource"]
QUESTION_LABEL = {"manage": "MANAGE", "visit": "VISIT", "resource": "RESOURCE"}

SHORT_NAME = {
    "Claude-Haiku-4.5 (Bedrock)": "Claude-Haiku-4.5",
    "GPT-4o-mini (OpenAI)":       "GPT-4o-mini",
    "Llama-3.3-70B (Bedrock)":    "Llama-3.3-70B",
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--summaries", required=True)
    p.add_argument("--out", default="figs/fig5_oncqa_per_question.pdf")
    args = p.parse_args()

    apply_style()

    with open(args.summaries) as f:
        summaries = json.load(f)

    models = [s["model"] for s in summaries]
    short = [SHORT_NAME.get(m, m) for m in models]

    x = np.arange(len(QUESTIONS))
    group_width = 0.82
    width = group_width / len(models)

    fig, ax = plt.subplots(figsize=(7.2, 4.0))

    for i, s in enumerate(summaries):
        deltas = [s["per_question"][q]["delta"] * 100.0 for q in QUESTIONS]
        los    = [s["per_question"][q]["delta_ci_lo"] * 100.0 for q in QUESTIONS]
        his    = [s["per_question"][q]["delta_ci_hi"] * 100.0 for q in QUESTIONS]
        err_lo = [max(0.0, d - l) for d, l in zip(deltas, los)]
        err_hi = [max(0.0, h - d) for h, d in zip(his, deltas)]

        offsets = x + i * width - group_width / 2 + width / 2
        bars = ax.bar(
            offsets, deltas, width * 0.92,
            label=short[i],
            color=OKABE_ITO[i % len(OKABE_ITO)],
            edgecolor="white", linewidth=0.8, zorder=2,
        )
        ax.errorbar(
            offsets, deltas,
            yerr=[err_lo, err_hi],
            fmt="none",
            ecolor=SUBINK,
            elinewidth=0.9,
            capsize=3,
            capthick=0.8,
            zorder=3,
        )
        for b, v in zip(bars, deltas):
            yoff = 0.8 if v >= 0 else -0.8
            va = "bottom" if v >= 0 else "top"
            ax.text(b.get_x() + b.get_width() / 2, v + yoff,
                    f"{v:+.1f}", ha="center", va=va,
                    fontsize=7.5, color=INK)

    ax.axhline(0, color=SUBINK, linewidth=0.8, zorder=1)
    ax.set_xticks(x)
    ax.set_xticklabels([QUESTION_LABEL[q] for q in QUESTIONS])
    ax.set_ylabel(r"$\Delta$ RCER (pp), South $-$ North")
    ax.set_title(
        "Per-question RCER shift by model  \u2014  OncQA $n=60$, Bedrock panel",
        loc="left",
    )

    leg = ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.22),
                    ncol=len(models), frameon=False)
    for txt in leg.get_texts():
        txt.set_color(INK)

    ymin, ymax = ax.get_ylim()
    pad = max(3.0, 0.14 * (ymax - ymin))
    ax.set_ylim(ymin - pad, ymax + pad)

    light_grid(ax, "y")

    plt.savefig(args.out)


if __name__ == "__main__":
    main()

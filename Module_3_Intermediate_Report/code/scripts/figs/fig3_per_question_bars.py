"""Per-question Delta-RCER grouped bar chart (pilot).

X-axis: MANAGE / VISIT / RESOURCE. Groups: models.
Reads summaries.json; values come from rcer_south[q] - rcer_north[q].
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
    "GPT-4o-mini (OpenAI)": "GPT-4o-mini",
    "GPT-OSS-20B (OpenAI OSS)": "GPT-OSS-20B",
    "Llama-3.3-70B (Meta)": "Llama-3.3-70B",
    "Qwen3-32B (Alibaba)": "Qwen3-32B",
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--summaries", required=True)
    p.add_argument("--out", default="figs/fig3_per_question.pdf")
    args = p.parse_args()

    apply_style()

    with open(args.summaries) as f:
        summaries = json.load(f)

    models = [s["model"] for s in summaries]
    short = [SHORT_NAME.get(m, m) for m in models]

    x = np.arange(len(QUESTIONS))
    group_width = 0.82
    width = group_width / len(models)

    fig, ax = plt.subplots(figsize=(7.0, 3.8))

    for i, s in enumerate(summaries):
        deltas = [(s["rcer_south"][q] - s["rcer_north"][q]) * 100.0 for q in QUESTIONS]
        offsets = x + i * width - group_width / 2 + width / 2
        bars = ax.bar(offsets, deltas, width * 0.92,
                      label=short[i],
                      color=OKABE_ITO[i % len(OKABE_ITO)],
                      edgecolor="white", linewidth=0.8, zorder=2)
        for b, v in zip(bars, deltas):
            ax.text(b.get_x() + b.get_width() / 2,
                    v + (0.55 if v >= 0 else -0.55),
                    f"{v:+.1f}",
                    ha="center",
                    va="bottom" if v >= 0 else "top",
                    fontsize=7.5, color=INK)

    ax.axhline(0, color=SUBINK, lw=0.8, zorder=1)
    ax.set_xticks(x)
    ax.set_xticklabels([QUESTION_LABEL[q] for q in QUESTIONS])
    ax.set_ylabel(r"$\Delta$ RCER (pp), South $-$ North")
    ax.set_title("Per-question RCER shift by model  \u2014  pilot, $n=20$",
                 loc="left")

    leg = ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.22),
                    ncol=len(models), frameon=False)
    for txt in leg.get_texts():
        txt.set_color(INK)

    ymin, ymax = ax.get_ylim()
    pad = max(2.5, 0.14 * (ymax - ymin))
    ax.set_ylim(ymin - pad, ymax + pad)

    light_grid(ax, "y")

    plt.savefig(args.out)


if __name__ == "__main__":
    main()

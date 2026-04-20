"""Per-model forest plot: GDI with 95% BCa CI on per-case mean delta.

The CI is `gdi_ci_lo_bca` / `gdi_ci_hi_bca` from summaries.json, which is
a BCa interval on `mean(per_case_diffs)`, an effect-size proxy for GDI.
For pilot rows whose interval does not bracket the GDI point estimate we
mark the label with a dagger (see decisions.md NOTE #6).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _style import ACM_BLUE, INK, MUTED, SUBINK, apply_style, light_grid


SHORT_NAME = {
    "GPT-4o-mini (OpenAI)": "GPT-4o-mini",
    "GPT-OSS-20B (OpenAI OSS)": "GPT-OSS-20B",
    "Llama-3.3-70B (Meta)": "Llama-3.3-70B",
    "Qwen3-32B (Alibaba)": "Qwen3-32B",
}

POS_COLOUR = "#B7252C"
NEG_COLOUR = ACM_BLUE


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--summaries", required=True)
    p.add_argument("--out", default="figs/fig4_forest.pdf")
    args = p.parse_args()

    apply_style()

    with open(args.summaries) as f:
        summaries = json.load(f)

    rows = []
    for s in summaries:
        gdi = s["gdi"]
        lo = s["gdi_ci_lo_bca"]
        hi = s["gdi_ci_hi_bca"]
        brackets = (lo <= gdi <= hi)
        rows.append({
            "label": SHORT_NAME.get(s["model"], s["model"]),
            "gdi": gdi,
            "lo": lo,
            "hi": hi,
            "brackets": brackets,
            "n_north": s["n_north_cases"],
            "n_south": s["n_south_cases"],
        })

    n = len(rows)
    fig, ax = plt.subplots(figsize=(7.2, 2.3 + 0.48 * n))

    y_positions = list(range(n))[::-1]
    any_dagger = False

    for row, y in zip(rows, y_positions):
        colour = POS_COLOUR if row["gdi"] >= 0 else NEG_COLOUR

        ax.hlines(y, row["lo"], row["hi"],
                  color=SUBINK, linewidth=1.4, zorder=2)
        for xend in (row["lo"], row["hi"]):
            ax.vlines(xend, y - 0.15, y + 0.15,
                      color=SUBINK, linewidth=1.4, zorder=2)
        ax.plot(row["gdi"], y,
                marker="D", markersize=7.5, color=colour,
                markeredgecolor="white", markeredgewidth=1.1, zorder=3)

        label = row["label"]
        if not row["brackets"]:
            label = label + " \u2020"
            any_dagger = True
        row["display_label"] = label

        numeric = (
            f"GDI\u2009=\u2009{row['gdi']:+.3f}     "
            f"CI [{row['lo']:+.3f},\u2009{row['hi']:+.3f}]     "
            f"$n$\u2009=\u2009{row['n_north']}/{row['n_south']}"
        )
        ax.text(1.02, y, numeric, transform=ax.get_yaxis_transform(),
                ha="left", va="center", fontsize=8.2, color=INK)

    ax.axvline(0, color=MUTED, linewidth=0.7, linestyle="--")

    ax.set_yticks(y_positions)
    ax.set_yticklabels([r["display_label"] for r in rows], color=INK)
    ax.set_xlabel("Geographic Disparity Index (matched-pair)", color=INK)
    ax.set_title("Per-model GDI with 95% BCa CI on per-case mean delta",
                 loc="left")

    lo_min = min(r["lo"] for r in rows)
    hi_max = max(r["hi"] for r in rows)
    span = hi_max - lo_min
    ax.set_xlim(lo_min - 0.06 * span, hi_max + 0.06 * span)
    ax.set_ylim(-0.6, n - 0.4)

    light_grid(ax, "x")
    ax.tick_params(axis="y", length=0)

    if any_dagger:
        fig.subplots_adjust(bottom=0.22)
        fig.text(
            0.02, 0.02,
            "\u2020 Proxy CI is on mean(per_case_diffs); the interval "
            "does not bracket the GDI point estimate for these models. "
            "See decisions.md NOTE #6.",
            ha="left", va="bottom", fontsize=7.2, color=SUBINK,
        )

    plt.savefig(args.out)


if __name__ == "__main__":
    main()

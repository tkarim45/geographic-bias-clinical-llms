"""Per-model forest plot: GDI with 95% BCa CI on per-case mean delta.

The CI plotted is `gdi_ci_lo_bca` / `gdi_ci_hi_bca` from summaries.json, which
is a BCa interval on `mean(per_case_diffs)` — a per-case effect-size proxy
for the GDI, not a CI on the GDI itself. For two of the four pilot models
the proxy CI does not bracket the GDI point estimate; those models are
flagged with a "†" next to the label and a footnote in the figure caption,
per `decisions.md` NOTE #6.
"""
from __future__ import annotations

import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


SHORT_NAME = {
    "GPT-4o-mini (OpenAI)": "GPT-4o-mini",
    "GPT-OSS-20B (OpenAI OSS)": "GPT-OSS-20B",
    "Llama-3.3-70B (Meta)": "Llama-3.3-70B",
    "Qwen3-32B (Alibaba)": "Qwen3-32B",
}

ACM_BLUE = (0 / 255, 83 / 255, 156 / 255)
DARK_GRAY = (80 / 255, 80 / 255, 80 / 255)
MED_GRAY = (130 / 255, 130 / 255, 130 / 255)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--summaries", required=True,
                   help="Path to summaries.json (list of per-model dicts)")
    p.add_argument("--out", default="figs/fig4_forest.pdf")
    args = p.parse_args()

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
    fig, ax = plt.subplots(figsize=(6.6, 2.6 + 0.35 * n))

    y_positions = list(range(n))[::-1]  # top-to-bottom in source order
    any_dagger = False
    for row, y in zip(rows, y_positions):
        marker_color = ACM_BLUE if row["gdi"] >= 0 else DARK_GRAY
        ax.plot([row["lo"], row["hi"]], [y, y],
                color=DARK_GRAY, linewidth=1.4, solid_capstyle="butt")
        ax.plot([row["lo"], row["lo"]], [y - 0.15, y + 0.15],
                color=DARK_GRAY, linewidth=1.4)
        ax.plot([row["hi"], row["hi"]], [y - 0.15, y + 0.15],
                color=DARK_GRAY, linewidth=1.4)
        ax.plot(row["gdi"], y, "o", color=marker_color, markersize=8,
                markeredgecolor="black", markeredgewidth=0.6, zorder=3)

        # Dagger marker for models where CI doesn't bracket the point.
        label = row["label"]
        if not row["brackets"]:
            label = label + r" $^{\dagger}$"
            any_dagger = True

        # Right-side annotation with the numbers (so the y-axis stays clean).
        text = f"GDI = {row['gdi']:+.3f}  CI [{row['lo']:+.3f}, {row['hi']:+.3f}]  n={row['n_north']}/{row['n_south']}"
        ax.text(0.995, y, text, transform=ax.get_yaxis_transform(),
                ha="right", va="center", fontsize=8, color="#333333",
                family="monospace")
        # Replace the y-tick label with the (possibly daggered) name.
        rows[y_positions.index(y)]["display_label"] = label

    ax.axvline(0, color="black", linewidth=0.7, linestyle="--", alpha=0.55)

    ax.set_yticks(y_positions)
    ax.set_yticklabels([r["display_label"] for r in rows], fontsize=9)
    ax.set_xlabel("Geographic Disparity Index (GDI), matched-pair", fontsize=10)
    title_main = "Per-model GDI with 95% BCa CI on per-case mean delta"
    title_sub = "(effect-size proxy; pilot, $n$ matched pairs varies by model)"
    ax.set_title(f"{title_main}\n{title_sub}", fontsize=10, color=DARK_GRAY)

    # Padding so right-side annotations don't run off.
    lo_min = min(r["lo"] for r in rows)
    hi_max = max(r["hi"] for r in rows)
    span = hi_max - lo_min
    ax.set_xlim(lo_min - 0.04 * span, hi_max + 0.04 * span)
    ax.set_ylim(-0.6, n - 0.4)

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis="x", labelsize=9)
    ax.xaxis.grid(True, linestyle=":", linewidth=0.5, color=MED_GRAY, alpha=0.8)
    ax.set_axisbelow(True)

    if any_dagger:
        fig.text(
            0.5, 0.01,
            r"$^{\dagger}$ Proxy CI is on $\mathrm{mean}(\mathrm{per\_case\_diffs})$, "
            "not on GDI directly; CI does not bracket the GDI point estimate "
            "for these models. See decisions.md NOTE #6.",
            ha="center", va="bottom", fontsize=7, color="#444444",
        )
        fig.subplots_adjust(bottom=0.18)

    plt.tight_layout(rect=(0, 0.06 if any_dagger else 0.0, 1, 1))
    plt.savefig(args.out, bbox_inches="tight")


if __name__ == "__main__":
    main()

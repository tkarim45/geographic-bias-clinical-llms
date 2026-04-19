"""Generate figures for the intermediate report from a run's summaries.json.

Usage:
    python3 scripts/make_figures.py \
        --run-dir runs/20260418T050306Z \
        --out-dir ../figs
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ACM_BLUE = (0 / 255, 83 / 255, 156 / 255)
DARK_GRAY = (80 / 255, 80 / 255, 80 / 255)
MED_GRAY = (130 / 255, 130 / 255, 130 / 255)


def gdi_bar(summaries: list[dict], out_path: Path) -> None:
    models = [s["model"].split(" (")[0] for s in summaries]
    gdi = [s["gdi"] for s in summaries]
    lo = [s["bootstrap_ci_95"][0] for s in summaries]
    hi = [s["bootstrap_ci_95"][1] for s in summaries]
    err_lo = [g - l for g, l in zip(gdi, lo)]
    err_hi = [h - g for g, h in zip(gdi, hi)]

    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    x = list(range(len(models)))
    bar_colors = [ACM_BLUE if v >= 0 else MED_GRAY for v in gdi]
    ax.bar(x, gdi, width=0.56, color=bar_colors, edgecolor="black", linewidth=0.6)
    ax.errorbar(
        x, gdi,
        yerr=[err_lo, err_hi],
        fmt="none",
        ecolor=DARK_GRAY,
        elinewidth=1.1,
        capsize=5,
        capthick=1.1,
    )

    for xi, v in zip(x, gdi):
        offset = 0.008 if v >= 0 else -0.012
        va = "bottom" if v >= 0 else "top"
        ax.text(xi, v + offset, f"{v:+.3f}", ha="center", va=va, fontsize=9, color="black")

    ax.axhline(0, color="black", linewidth=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=9)
    ax.set_ylabel("Geographic Disparity Index (GDI)", fontsize=10)
    ax.set_title(
        "Per-model GDI with 95% bootstrap CI (pilot, $n$ matched pairs varies)",
        fontsize=10, color=DARK_GRAY,
    )

    lo_min = min(lo); hi_max = max(hi)
    pad = 0.025
    ax.set_ylim(lo_min - pad, hi_max + pad)

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis="both", labelsize=9)
    ax.yaxis.grid(True, linestyle=":", linewidth=0.5, color=MED_GRAY, alpha=0.8)
    ax.set_axisbelow(True)

    fig.tight_layout()
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summaries = json.loads((run_dir / "summaries.json").read_text())
    gdi_bar(summaries, out_dir / "gdi_bar.png")


if __name__ == "__main__":
    main()

"""Shared matplotlib style for the Module 3 intermediate-report figures.

Call `apply_style()` at the top of each figure script. Exports a
colour-blind-safe palette (Okabe-Ito) and a handful of semantic colours
matched to the LaTeX theme.
"""
from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt


ACM_BLUE = "#0A2F6B"
INK = "#1A1A1A"
SUBINK = "#4A4A4A"
MUTED = "#8A8A8A"
GRID = "#E2E4E8"
PANEL = "#FBFBFD"

OKABE_ITO = [
    "#0072B2",
    "#D55E00",
    "#009E73",
    "#CC79A7",
    "#E69F00",
    "#56B4E9",
    "#F0E442",
    "#000000",
]

DIVERGING = "RdBu_r"


def apply_style() -> None:
    """Set rcParams for all figures in the report.

    Conservative, print-ready defaults: serif body font (matches the
    LaTeX document), no top/right spines, light dotted grid, consistent
    font sizes, and a colour cycle set to Okabe-Ito.
    """
    plt.rcdefaults()

    mpl.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Latin Modern Roman", "Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "cm",
        "font.size": 9.5,
        "axes.titlesize": 10.5,
        "axes.titleweight": "semibold",
        "axes.titlepad": 8,
        "axes.titlecolor": INK,
        "axes.labelsize": 9.5,
        "axes.labelcolor": INK,
        "axes.labelpad": 4,
        "axes.edgecolor": SUBINK,
        "axes.linewidth": 0.7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.prop_cycle": mpl.cycler(color=OKABE_ITO),
        "axes.axisbelow": True,
        "xtick.color": SUBINK,
        "ytick.color": SUBINK,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 3.5,
        "ytick.major.size": 3.5,
        "legend.fontsize": 8.5,
        "legend.frameon": False,
        "legend.handlelength": 1.6,
        "legend.handletextpad": 0.6,
        "legend.columnspacing": 1.4,
        "grid.color": GRID,
        "grid.linestyle": "-",
        "grid.linewidth": 0.5,
        "grid.alpha": 1.0,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def light_grid(ax, axis: str = "y") -> None:
    """Apply a single-axis light grid consistent across figures."""
    ax.grid(False)
    if axis in ("y", "both"):
        ax.yaxis.grid(True, which="major")
    if axis in ("x", "both"):
        ax.xaxis.grid(True, which="major")
    ax.set_axisbelow(True)

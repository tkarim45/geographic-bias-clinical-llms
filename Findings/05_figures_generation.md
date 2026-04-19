# Claude Code Prompt 05 — Generate Four Publication-Quality Figures

## Goal

The current report has 4 tables and 0 figures. This is unacceptable for the intermediate submission and would be rejected at FAccT/EMNLP. Produce four figures from existing run artifacts.

**Prerequisite:** Prompt 04 (statistical rigor) should be completed so CIs are available in `summaries.json`.

## Figure inventory

| # | Figure | Primary data source | Purpose |
|---|---|---|---|
| 1 | Pipeline architecture | Manual TikZ | Visualize 5-stage pipeline |
| 2 | GDI heat-map (model × region) | `summaries.json::per_region_model` | Show per-cell effect sizes |
| 3 | Per-question ∆RCER bar chart | `summaries.json::per_model::per_question` | Highlight Qwen3-32B VISIT spike |
| 4 | Forest plot of per-model GDI with 95% CIs | `summaries.json` (CI fields from prompt 04) | Anchor statistical claims visually |
| 5 (optional) | Power curve | `power_analysis.json` | Justify n-choices going forward |

## Constraints

- Output PDF (vector) for LaTeX inclusion, saved to `Module_3_Intermediate_Report/figs/`.
- Use matplotlib only — no seaborn, no plotly. The constraint is that the grading environment must not need extra installs.
- Color palette: ColorBrewer RdBu diverging for heat-maps (bias is signed), Set2 categorical for models.
- Font size 9pt minimum; readable when the LaTeX renders at 6–8 cm width.

## Read first

- `runs/<latest_pilot>/summaries.json` — the source of truth
- `runs/<latest_oncqa>/summaries.json` (if prompt 01 is done)
- `ablation_summary.json` (if prompt 02 is done)
- `power_analysis.json` (from prompt 04)

## Tasks

### Task 1 — Pipeline architecture figure (30 min)

Option A: Write TikZ directly into the `.tex`:

```latex
\begin{figure}[ht]
\centering
\begin{tikzpicture}[node distance=1.3cm, every node/.style={draw, rounded corners, align=center, inner sep=4pt, minimum width=4cm}]
\node (data) {\textbf{(1) Dataset loader}\\\small cases.jsonl (20 synthetic + 61 OncQA)};
\node[below of=data] (pert) {\textbf{(2) Perturbation engine}\\\small Name-Bank $\times$ Geo substitution, SHA-256 keyed};
\node[below of=pert] (models) {\textbf{(3) Model harness}\\\small OpenAI + Groq via stdlib urllib};
\node[below of=models] (ann) {\textbf{(4) LLM-as-annotator}\\\small Llama-3.1-8B, JSON-constrained};
\node[below of=ann] (metr) {\textbf{(5) Metrics \& stats}\\\small TSR, RCR, RCER, GDI; Wilcoxon; BCa bootstrap};
\foreach \a/\b in {data/pert, pert/models, models/ann, ann/metr} {\draw[->,thick] (\a)--(\b);}
\node[right of=models, xshift=5cm, align=left, draw=none] (xtra) {
  \footnotesize
  \textbf{Cross-cutting:}\\
  $\bullet$ Token-bucket rate limiter (per-model)\\
  $\bullet$ SHA-256 idempotency cache\\
  $\bullet$ Manifest hashing (dataset, Name-Bank)\\
  $\bullet$ YAML-driven reproducibility
};
\end{tikzpicture}
\caption{Pipeline architecture. Each stage writes a typed JSONL artefact and is independently re-runnable, enabling cheap metric re-computation without re-invoking provider APIs.}
\label{fig:pipeline}
\end{figure}
```

Option B (if TikZ is not available): render with matplotlib using annotated boxes. Provide a `scripts/figs/fig1_pipeline.py` that reads nothing and emits `figs/fig1_pipeline.pdf`.

### Task 2 — GDI heat-map (30 min)

`scripts/figs/fig2_gdi_heatmap.py`:

```python
"""
GDI heat-map: rows = models, columns = regions.
Cell color = GDI value (RdBu diverging, centered at 0).
Cell text = "GDI / ΔRCER pp / n"
Asterisk if p < 0.05 (uncorrected).
"""
import json, argparse, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--summaries', required=True)
    p.add_argument('--out', default='figs/fig2_gdi_heatmap.pdf')
    args = p.parse_args()
    s = json.loads(open(args.summaries).read())

    # Expect: s['per_region_model'] = { region: { model: {gdi, delta_rcer, n, p_value} } }
    regions = ['south_asia', 'sub_saharan_africa', 'latin_america']  # pilot scope
    models = list(s['per_model'].keys())
    gdi_mat = np.array([[s['per_region_model'][r][m]['gdi'] for r in regions] for m in models])
    text_mat = [[f"{s['per_region_model'][r][m]['gdi']:+.3f}\n({s['per_region_model'][r][m]['delta_rcer']*100:+.1f}pp)\nn={s['per_region_model'][r][m]['n']}"
                 for r in regions] for m in models]
    sig_mat = [[s['per_region_model'][r][m].get('p_value', 1.0) < 0.05 for r in regions] for m in models]

    fig, ax = plt.subplots(figsize=(6.5, 3.5))
    vmax = max(0.1, np.abs(gdi_mat).max())
    im = ax.imshow(gdi_mat, cmap='RdBu_r', vmin=-vmax, vmax=vmax, aspect='auto')
    ax.set_xticks(range(len(regions)))
    ax.set_xticklabels([r.replace('_', ' ').title() for r in regions])
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels([m.split('/')[-1] for m in models], fontsize=9)

    for i in range(len(models)):
        for j in range(len(regions)):
            label = text_mat[i][j] + ('*' if sig_mat[i][j] else '')
            ax.text(j, i, label, ha='center', va='center', fontsize=8,
                    color='white' if abs(gdi_mat[i,j]) > 0.6*vmax else 'black')

    plt.colorbar(im, ax=ax, label='GDI (South − North RCER mean)')
    plt.title('Per-model geographic disparity by region', fontsize=10)
    plt.tight_layout()
    plt.savefig(args.out)

if __name__ == '__main__':
    main()
```

### Task 3 — Per-question bar chart (30 min)

`scripts/figs/fig3_per_question_bars.py` — grouped bar chart. X-axis is question (MANAGE / VISIT / RESOURCE), Y-axis is ∆RCER (pp), groups are models. This is the figure that makes Qwen3-32B's +15.4pp VISIT spike visually obvious.

```python
import json, argparse, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--summaries', required=True)
    p.add_argument('--out', default='figs/fig3_per_question.pdf')
    args = p.parse_args()
    s = json.loads(open(args.summaries).read())

    questions = ['MANAGE', 'VISIT', 'RESOURCE']
    models = list(s['per_model'].keys())
    short = [m.split('/')[-1] for m in models]
    x = np.arange(len(questions))
    width = 0.8 / len(models)

    fig, ax = plt.subplots(figsize=(6.5, 3.5))
    colors = plt.cm.Set2(np.linspace(0, 1, len(models)))

    for i, m in enumerate(models):
        vals = [s['per_model'][m]['per_question'][q]['delta'] * 100 for q in questions]
        ax.bar(x + i*width - 0.4 + width/2, vals, width, label=short[i], color=colors[i])

    ax.axhline(0, color='black', lw=0.6)
    ax.set_xticks(x); ax.set_xticklabels(questions)
    ax.set_ylabel('Δ RCER (pp), South − North')
    ax.set_title('Per-question RCER shift by model')
    ax.legend(loc='upper left', fontsize=8, frameon=False)
    plt.tight_layout(); plt.savefig(args.out)

if __name__ == '__main__':
    main()
```

### Task 4 — Forest plot (30 min)

`scripts/figs/fig4_forest.py`:

```python
"""
Forest plot: per-model GDI with 95% BCa bootstrap CIs.
Marker = GDI; whiskers = CI; vertical line at GDI=0.
"""
import json, argparse, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--summaries', required=True)
    p.add_argument('--out', default='figs/fig4_forest.pdf')
    args = p.parse_args()
    s = json.loads(open(args.summaries).read())

    models = list(s['per_model'].keys())
    short = [m.split('/')[-1] for m in models]
    gdi = [s['per_model'][m]['gdi'] for m in models]
    lo  = [s['per_model'][m]['gdi_ci_lo'] for m in models]
    hi  = [s['per_model'][m]['gdi_ci_hi'] for m in models]

    fig, ax = plt.subplots(figsize=(6.5, 2.5 + 0.3*len(models)))
    y = list(range(len(models)))
    for i in range(len(models)):
        ax.plot([lo[i], hi[i]], [y[i], y[i]], 'k-', lw=1)
        ax.plot(gdi[i], y[i], 'ko', ms=6)
    ax.axvline(0, color='gray', lw=0.6, ls='--')
    ax.set_yticks(y); ax.set_yticklabels(short)
    ax.set_xlabel('GDI (South − North RCER mean); 95% BCa bootstrap CI')
    ax.set_title('Per-model geographic disparity index')
    plt.tight_layout(); plt.savefig(args.out)

if __name__ == '__main__':
    main()
```

### Task 5 — (Optional) Power curve

`scripts/figs/fig5_power_curve.py` — reads `power_analysis.json`, plots detectable effect size vs n for α=0.05 and α=0.005. Include only if time permits.

### Task 6 — Smoke test & LaTeX inclusion (20 min)

Generate all figures:

```bash
cd Module_3_Intermediate_Report
mkdir -p figs
cd code
python3 scripts/figs/fig2_gdi_heatmap.py --summaries runs/<latest>/summaries.json --out ../figs/fig2_gdi_heatmap.pdf
python3 scripts/figs/fig3_per_question_bars.py --summaries runs/<latest>/summaries.json --out ../figs/fig3_per_question.pdf
python3 scripts/figs/fig4_forest.py --summaries runs/<latest>/summaries.json --out ../figs/fig4_forest.pdf
```

If `summaries.json` schema doesn't match (e.g., no `per_region_model` field), either add the field in `audit/metrics.py` or adapt the figure script — but prefer adding the field so figures stay simple.

Verify figures render at reasonable size by opening each PDF. If any cell or label clips, fix.

### Task 7 — Add to LaTeX

Insert in `intermediate_report.tex`:

```latex
\begin{figure}[t]
\centering
\includegraphics[width=0.95\linewidth]{figs/fig2_gdi_heatmap.pdf}
\caption{Per-model Geographic Disparity Index by region on the pilot (n=20). Positive values (red) indicate higher reduced-care error rate under Global-South identity substitution; negative (blue) indicates lower. Cell annotations show GDI / $\Delta$RCER in percentage points / cell n. Asterisks mark $p<0.05$ uncorrected — no cell reaches the pre-registered Bonferroni $\alpha = 0.005$.}
\label{fig:heatmap}
\end{figure}
```

Equivalent blocks for Fig 3 and Fig 4. Place Fig 2 at the top of §4.2, Fig 3 and Fig 4 immediately after Table 5.

## Deliverables

- [ ] `figs/fig2_gdi_heatmap.pdf`, `fig3_per_question.pdf`, `fig4_forest.pdf` (Fig 1 as TikZ in `.tex`)
- [ ] `scripts/figs/*.py` scripts checked in
- [ ] LaTeX includegraphics blocks in the right sections
- [ ] Captions that explicitly quote numbers from the figure

## What NOT to do

- Do not use seaborn or non-stdlib matplotlib extensions.
- Do not include raster (.png) figures at publication quality — use PDF.
- Do not fabricate CI values. If prompt 04 hasn't run yet, the forest plot is **blocked** — run prompt 04 first.

## Success criterion

`pdflatex intermediate_report.tex` (run twice) produces a PDF with four figures (1 TikZ + 3 matplotlib), each with a clear caption citing specific numbers, each referenced by `\ref{fig:...}` from at least one place in the body text.

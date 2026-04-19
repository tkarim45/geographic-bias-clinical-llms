# Agent-LATEX integration manifest (Phase 3B)

**Purpose.** Deterministic checklist for the Agent-LATEX foreground pass. The
lead orchestration agent constructs this from the artifacts that exist on
disk + the constraints recorded in `code/decisions.md`. Agent-LATEX (run by
the lead in foreground; sub-agent dispatch known to halt on permissions in
this environment) executes each item in order without improvising.

> **Pre-flight assertion (HARD FAIL on drift).** Before any edit, verify:
> `wc -l Module_3_Intermediate_Report/intermediate_report.tex` == **721**,
> and `shasum -a 256` matches the post-surgical-revert hash recorded in
> `code/decisions.md` FREEZE NOTICE (`7fb941da0c8dedbb1662fcbd83c163494a4653ec4b5c832580b98af036245899`).
> Any deviation = halt and escalate. Do **not** auto-merge a third-party
> inline edit under any circumstances.

## Inputs available on disk (verified at manifest-construction time)

### Section fragments (canonical text — `\input{}` rather than regenerate)

| Fragment | sha256 (verify before use) | Purpose |
|---|---|---|
| `Module_3_Intermediate_Report/sections/results_reframe.tex` | `eee781a4ccd4aad0be411f6b95793c89c971bd550bfaea211d28f9f4de58d027` | §4.3 H1/H2 reframe + Bonferroni-99.6% discrimination criterion + sensitivity-analysis subsection. Inserts after the §4.3 heading; replaces the existing prose from "The pilot is under-powered but directionally informative." through "Sub-Saharan Africa shows the largest aggregate effect." Keeps "Two non-claims", "Strengths visible in pilot", "Weaknesses" paragraphs unchanged. |
| `Module_3_Intermediate_Report/sections/baselines.tex` | `2aad16d0e8af8f58c7c71a64d1b1c33bc90ec493dbea280264619c18c5ea4b30` | §4.4 Baselines and Evaluation Methodology. Inserts after §4.3, before §5. **NOTE**: the inline §4.4 that the rogue session previously added (lines 461–528) was surgically reverted at 22:31Z; the slot is empty. Just `\input{}` the fragment at the correct anchor. |

### Figures (PDFs to `\includegraphics`)

| File | sha256 | Caption skeleton |
|---|---|---|
| `Module_3_Intermediate_Report/figs/fig1_pipeline.pdf` (31,536 B) | `5e72e289e57290a9ead52f190931d1a660fbbade7ae9ae3dd78751a5da8ed489` | Pipeline architecture (5 stages + cross-cutting callout). Place at top of §3.1 (System Architecture) replacing the existing `tcolorbox` Figure 1 ASCII. `\label{fig:pipeline}`. |
| `Module_3_Intermediate_Report/figs/fig2_gdi_heatmap.pdf` (22,369 B) | `2d562e58ada7f5d1b37eaaf709cae631bc37ab5f566ff9c0e35f6f6d56ee7cdb` | Per-model GDI heatmap by region (matched-pair canonical, pilot n=20). `\label{fig:heatmap}`. Place at top of §4.2. |
| `Module_3_Intermediate_Report/figs/fig3_per_question.pdf` (19,848 B) | `74e9821b5f631c3c7a89545adde257ae98e2c86f3c6bb1496b83134faef675a6` | Per-question ΔRCER bar chart by model (pilot n=20). `\label{fig:per_question}`. Place after Table~\ref{tab:per_question}. |
| `Module_3_Intermediate_Report/figs/fig4_forest.pdf` (32,496 B) | `858415878a2e3ca31cc67f7b62327289d29b4e648bd639fc91f16797db0d1591` | Per-model GDI forest plot with 95% BCa CI on per-case mean Δ. `\label{fig:forest}`. Place after Table~\ref{tab:pilot}. The "†" footnote on GPT-4o-mini is rendered into the PDF itself; no caption note needed. |

### Numerical artifacts (every claim must trace to one of these)

| Path | sha256 | Use |
|---|---|---|
| `Module_3_Intermediate_Report/code/runs/20260418T050306Z/summaries.json` | `db8c550cea4c9ef5451d92ed80ec4b926519cf778a370311e533d2e56bd72323` | **Canonical pilot results** (matched-pair, refreshed with BCa CIs / Cohen's h / Wilcoxon r per Agent-STATS). All Tables 5/6/7 cite this. |
| `Module_3_Intermediate_Report/code/runs/20260418T050306Z/power_analysis.json` | (compute at integration time) | Per-model required-n at α∈{0.05, 0.005} × power∈{0.80, 0.95}. Used by §4.4 Table~\ref{tab:power} (already in `sections/baselines.tex`). |
| `Module_3_Intermediate_Report/code/runs/20260418T050306Z/summaries_errors_included.json` | (preserved untracked) | **Sensitivity-only**. Cited inside the explicit "Sensitivity analysis" subsection of `sections/results_reframe.tex`. Never appears outside that context. |
| `Module_3_Intermediate_Report/code/runs/<oncqa-prod-UTC>/summaries.json` | (computed at run time) | **OncQA full-run results** (pending; see §"Conditional integration" below). |
| `Module_3_Intermediate_Report/code/runs/<oncqa-prod-UTC>/power_analysis.json` | (computed at run time) | OncQA power analysis (re-run after OncQA summaries land). |
| `Module_3_Intermediate_Report/code/ablation_summary.json` | (computed at run time) | Three-perturbation comparison (see Phase 3A). |

## Edits to apply, in order

### Edit 1 — Preamble additions (§ before `\begin{document}`)

Lines 19 already has `\usepackage{graphicx}`. Add (after line 19):

```latex
\graphicspath{{figs/}}
```

Verify `\usepackage{tikz}` is **not** added — the figures are pre-rendered PDFs, no TikZ needed.

### Edit 2 — Replace the existing Figure 1 (§3.1 ASCII tcolorbox) with `\includegraphics{fig1_pipeline.pdf}`

Locate the `\begin{tcolorbox}` block currently labelled `\label{fig:arch}` (lines ~215–235 of post-revert state). Replace the entire `\begin{center} ... \end{center}` block with:

```latex
\begin{figure}[ht]
  \centering
  \includegraphics[width=0.92\linewidth]{fig1_pipeline.pdf}
  \caption{System architecture: five-stage pipeline driven by a single YAML
  configuration. Each stage writes a typed JSONL artefact; cross-cutting
  components (token-bucket rate limiter keyed per model; SHA-256
  idempotency cache; manifest hashing) appear in the right callout.}
  \label{fig:pipeline}
\end{figure}
```

Update the inline reference from `Figure~\ref{fig:arch}` to `Figure~\ref{fig:pipeline}` everywhere.

### Edit 3 — §4.2: insert Figure 2 (heatmap) at top of subsection

Right after `\subsection{Preliminary Results --- Measured Pilot (20 cases, 4 models)}`, insert:

```latex
\begin{figure}[ht]
  \centering
  \includegraphics[width=0.95\linewidth]{fig2_gdi_heatmap.pdf}
  \caption{Per-model Geographic Disparity Index by region (matched-pair
  canonical; pilot $n$=20). Cells annotate GDI / $\Delta$RCER (pp) / per-cell
  matched-pair $n$. Positive (red) = Global-South RCER higher than
  Global-North; negative (blue) = lower. No cell reaches the
  Bonferroni-corrected threshold; see §\ref{sec:baselines}.}
  \label{fig:heatmap}
\end{figure}
```

Reference it once in the surrounding prose ("...as visualised in Figure~\ref{fig:heatmap}.").

### Edit 4 — §4.2: insert Figure 4 (forest) after Table~\ref{tab:pilot}

Right after the `\end{center}` that closes `\label{tab:pilot}`, insert:

```latex
\begin{figure}[ht]
  \centering
  \includegraphics[width=0.95\linewidth]{fig4_forest.pdf}
  \caption{Per-model GDI forest plot with 95\% bias-corrected-and-accelerated
  bootstrap CIs on per-case mean $\Delta$ (effect-size proxy for GDI; pilot
  $n$=20). The $^{\dagger}$ marker on GPT-4o-mini denotes that the proxy
  CI does not bracket the GDI point estimate (see \texttt{decisions.md}
  NOTE \#6 for the conceptual gap between mean-of-per-case-deltas and GDI).}
  \label{fig:forest}
\end{figure}
```

### Edit 5 — §4.2: insert Figure 3 (per-question bars) after Table~\ref{tab:per_question}

Right after the `\end{center}` that closes `\label{tab:per_question}`, insert:

```latex
\begin{figure}[ht]
  \centering
  \includegraphics[width=0.95\linewidth]{fig3_per_question.pdf}
  \caption{Per-question $\Delta$RCER (pp, South pool $-$ North baseline) by
  model. Per-question gold-positive base rates are reported in
  Table~\ref{tab:per_question}; effect-size interpretation should weigh the
  base-rate floor (Cohen's $h$ flattens at the extremes).}
  \label{fig:per_question}
\end{figure}
```

(Per NOTE #12.A: per-question base rates appear adjacent to per-question effect sizes.)

### Edit 6 — §4.3: replace prose with `\input{sections/results_reframe.tex}`

Locate `\subsection{Analysis of Results}` (line ~445 of post-revert file). Right after the heading, insert `\input{sections/results_reframe.tex}` and **delete** the existing prose paragraphs from "The pilot is under-powered but directionally informative." through "Sub-Saharan Africa shows the largest aggregate effect (Table~\ref{tab:per_region})." — that's the dead +0.085 / +15.4 pp / +0.035 narrative.

**Keep unchanged**: the "Two non-claims" paragraph, "Strengths visible in pilot" paragraph, "Weaknesses" paragraph. They are still factually correct under matched-pair canonical.

### Edit 7 — Insert §4.4 via `\input{sections/baselines.tex}`

Right before the section break comment that precedes §5 (`\section{Timeline and Progress}` at line ~462 of post-revert file), insert:

```latex
\input{sections/baselines.tex}
```

### Edit 8 — Append 7 new bibitems to `\begin{thebibliography}`

The full bibitem bodies are in the EOF comment block of `sections/baselines.tex`. Copy each one into `\begin{thebibliography}` immediately before `\end{thebibliography}`. Keys to add (verify NONE already exist in current bibliography by `grep -nE '\\\\bibitem\\{(cohen1988|cohen1960|gilboy2012|chen2023|gomes2020|jin2020|omar2025)\\}'`):

- `\bibitem{cohen1988}` — Cohen 1988, *Statistical Power Analysis*.
- `\bibitem{cohen1960}` — Cohen 1960, A Coefficient of Agreement for Nominal Scales.
- `\bibitem{gilboy2012}` — Gilboy et al. 2012, ESI v4.
- `\bibitem{chen2023}` — Chen et al. 2023, OncQA.
- `\bibitem{gomes2020}` — Gomes 2020, AskDocs construction. (`\todo` for final-form citation per Agent-BASELINE note.)
- `\bibitem{jin2020}` — Jin et al. 2020, MedQA.
- `\bibitem{omar2025}` — Omar et al. 2025, Sociodemographic biases in medical decision-making.

### Edit 9 — Conditional integration: OncQA results (if available)

If `runs/<oncqa-prod-UTC>/summaries.json` exists at integration time:

- Add §4.1.1 paragraph naming the OncQA experiment (n=60, broad gendered filter, gold derivation per `decisions.md` RESOLVED #11).
- Add new Table after Table~\ref{tab:per_region}: per-model GDI on OncQA with BCa CIs.
- Add §4.4 footnote (per NOTE #12.D) describing the OncQA proxy mapping.
- Add §5.3 limitations paragraph using verbatim wording from `decisions.md` RESOLVED #11 refinement #7.

If OncQA results are **not** available at integration time:
- Insert `\todo{OncQA n=60 run completed; results in pre-submission amendment}` at the §4.1.1 anchor.
- Keep `sections/results_reframe.tex` unchanged — it already names OncQA as the *future* discrimination experiment.
- §5.3 limitations paragraph references the loader and methodological choices but flags results as pending.

### Edit 10 — Conditional integration: ablation table (if Agent-ABLATION completed)

If `code/ablation_summary.json` exists at integration time:

- Insert ablation table after §4.2's per-question table:

  ```latex
  \begin{table}[h]
  \centering
  \caption{Per-model GDI under the three perturbation types (pilot, $n$=20).
  Interaction = $\text{GDI}_{\text{combined}} - \text{GDI}_{\text{name}} -
  \text{GDI}_{\text{geo}}$.}
  \label{tab:ablation}
  \begin{tabular}{lcccc}
  \toprule
  Model & Name-only & Geo-only & Combined & Interaction \\
  \midrule
  GPT-4o-mini       & <fill> & <fill> & +0.015 & <fill> \\
  GPT-OSS-20B       & <fill> & <fill> & −0.020 & <fill> \\
  Llama-3.3-70B     & <fill> & <fill> & −0.017 & <fill> \\
  Qwen3-32B         & <fill> & <fill> & −0.062 & <fill> \\
  \bottomrule
  \end{tabular}
  \end{table}
  ```

  Fill `<fill>` from `ablation_summary.json` per-model entries. Reference it once in §4.3 prose (the per-region paragraph in `sections/results_reframe.tex` mentions ablation conceptually).

If `ablation_summary.json` does **not** exist at integration time:
- Insert `\todo{Ablation table; pending Phase 3A run}` at the slot.

## Dead-number blocklist (NOTE #7) — MANDATORY POST-EDIT GREP

After all edits, run:

```bash
grep -nE '\+0\.085|0\.085|\+15\.4|15\.4|\+0\.035|0\.035|\+0\.061|-0\.061' \
  intermediate_report.tex sections/*.tex
```

Every hit must be inside a section/subsection whose heading contains
"Sensitivity" OR inside an Appendix. Any hit outside those contexts =
halt and escalate. Report the grep output as part of the SUBTASK
COMPLETE block.

## Compile-and-verify sequence

```bash
cd Module_3_Intermediate_Report
pdflatex -interaction=nonstopmode intermediate_report.tex
pdflatex -interaction=nonstopmode intermediate_report.tex
```

Verify in the `.log`:
- Zero `?` references / `Citation undefined` warnings.
- Zero `Overfull \hbox` warnings exceeding 10pt.
- Page count between 14 and 20.
- All 4 figures render at readable size (open the PDF and eyeball).

If any check fails, **do not auto-fix the report**. Surface the failure with
specific line numbers + log excerpts and let the lead orchestrator decide
whether to revert + retry or escalate to the user.

## SUBTASK COMPLETE block to append to `code/decisions.md`

```
=== SUBTASK COMPLETE ===
Subtask: 06_report_latex_updates (Agent-LATEX)
Pre-flight check: line_count=<N>, sha256=<...> against post-revert baseline (PASS/FAIL)
Edits applied: 1, 2, 3, 4, 5, 6, 7, 8, 9 (conditional), 10 (conditional)
Dead-number grep result:
  <paste output here>
Compile result:
  pdflatex pass 1: <ok | failed with N errors>
  pdflatex pass 2: <ok | failed with N errors>
  Page count: <N>
  Unresolved \ref / \cite: <0 | list>
  Overfull \hbox > 10pt: <0 | list>
Artifacts produced:
  - intermediate_report.tex (modified; sha256:<post-edit-hash>)
  - intermediate_report.pdf (sha256:<...>)
Estimated API spend this subtask: USD 0.00
Cumulative spend ledger: <unchanged or new total>
=== END ===
```

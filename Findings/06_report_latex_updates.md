# Claude Code Prompt 06 — Report Text Revisions (LaTeX)

> **⚠️ SUPERSEDED IN PART (2026-04-18T16:35Z).** Tasks 2 (Abstract), 6 (§4.3
> rewrite, §4.3.1 Qwen interpretation, ablation seed values) below were
> originally written under the errors-included view of `summaries.json`. The
> canonical view per `Module_3_Intermediate_Report/code/decisions.md`
> RESOLVED #2 is matched-pair (`drop_errors=True`); per DECISION #3 the
> H1/H2 reframe is now in `Module_3_Intermediate_Report/sections/results_reframe.tex`
> and Agent-LATEX must `\input{}` it rather than regenerate prose. The dead
> headline numbers (+0.085, +15.4 pp, +3.5 pp) appear nowhere in the report
> outside the explicit "Sensitivity analysis" subsection / Appendix. See
> the inline notes flagged with **[SUPERSEDED]** below.

## Goal

Integrate all the upstream improvements (OncQA run, ablation table, effect-size CIs, figures, baselines section) into the `intermediate_report.tex` source. Fix the six specific framing problems identified in `00_GAP_ANALYSIS_AND_ACTION_PLAN.md` §§2 and 4.

This prompt produces a **revision-ready LaTeX patch plan**, not a blind rewrite — it identifies every location that needs to change and specifies the replacement text.

## Prerequisites

- Prompts 01, 02, 04, 05 completed. If any of these are still running, this prompt can start on the sections that don't depend on them (e.g., the reframing of §4.3 interpretation).

## Read first

- `Module_3_Intermediate_Report/intermediate_report.tex` — the source we are editing
- `00_GAP_ANALYSIS_AND_ACTION_PLAN.md` §§2, 4 — the rationale for each change
- All the new artifacts: updated `summaries.json`, `power_analysis.json`, `ablation_summary.json`, `figs/*.pdf`

## Tasks

### Task 1 — Preamble & figure support (10 min)

Open `intermediate_report.tex`. Ensure the preamble includes:

```latex
\usepackage{graphicx}
\usepackage{tikz}
\usetikzlibrary{positioning, arrows.meta}
\usepackage{booktabs}    % should already be there
\usepackage{siunitx}     % for aligned numbers in tables
\sisetup{detect-weight,table-format=+1.3}
```

Add `\graphicspath{{figs/}}` after `\begin{document}` so `\includegraphics{fig2...}` finds files in the `figs/` folder.

### Task 2 — Abstract revisions (15 min)

**Change 1 [SUPERSEDED — use matched-pair text below]:** The current abstract says *"Mean Reduced-Care-Errors Rate (RCER) is 22.1% in the Global-North baseline and 22.6% in the Global-South Combined perturbation."* Replace with:

> *"The pooled matched-pair Global-North versus Global-South RCER difference
> is small (per-model GDI in [−0.062, +0.015]; all four 95\% BCa CIs on
> per-case mean delta straddle or sit close to zero, $n$=14--20 / 22--60
> matched pairs per model). The pilot's power analysis (§\ref{sec:baselines})
> shows it reaches power 0.80 only at Cohen's $h \geq 0.18$, of which
> Qwen3-32B's matched-pair $h = -0.183$ is the only pilot effect above the
> threshold; the OncQA $n=61$ scaling experiment is pre-registered to
> discriminate H1 (alignment suppresses geographic bias) from H2 (per-model
> variance) using a Bonferroni-corrected $99.6\%$ BCa CI exclude-zero
> criterion over the $4 \times 3 = 12$ model$\times$question tests.
> Under an errors-included sensitivity view in which 52 Groq HTTP-429
> failures are imputed as zero responses, Qwen3-32B's GDI rises to $+0.085$
> with a $+15.4$~pp VISIT shift; we treat that as infrastructure-confounded
> ($40$ of $52$ errors preceded the rate-limit refactor in §3.2) and report
> it only as Appendix~\ref{appendix:sensitivity} sensitivity analysis."*

Numbers above trace to `runs/20260418T050306Z/summaries.json` (matched-pair
canonical, refreshed 2026-04-18T16:25Z) and `power_analysis.json` in the
same directory. Do **not** revert to the +0.5pp / +0.085 / +15.4pp / +3.5pp
formulation; those were the errors-included view (now relegated to
sensitivity-only per `decisions.md` RESOLVED #2).

**Change 2:** Add a sentence on OncQA results (if prompt 01 completed):

> *"A second experiment on the clinician-validated OncQA dataset (n=61) reproduces the direction of the pilot's Qwen3-32B signal: [specific numbers from the OncQA summaries.json]. The combined pilot + OncQA sample (n=81) remains below the pre-registered Bonferroni threshold, but all four models now have sufficient matched observations for rank-order GDI comparison."*

**Change 3:** Reframe the "no model reaches the pre-registered Bonferroni-corrected significance threshold" sentence. Replace with:

> *"No per-model GDI reaches the pre-registered Bonferroni-corrected threshold ($\alpha = 0.005$ over the nine $\text{region} \times \text{question}$ conditions). This is expected by design: a power analysis (§4.4) shows that detecting the observed Qwen3-32B effect size at this threshold requires $n \approx 320$; the pilot's $n=20$ provides power of only 0.19."*

### Task 3 — §1.3 Significant Changes — update (10 min)

Replace the bullet on "Perturbation ablation deferred" with:

> - **Perturbation ablation completed at pilot scale.** Name-only and Geo-only perturbations have now been run on the 20-case pilot, alongside Combined. The ablation table (Table~\ref{tab:ablation}) isolates the name-driven versus geography-driven contributions per model.

Replace the bullet on "Pilot dataset is synthetic" with:

> - **Pilot dataset is synthetic; OncQA now added as a second experiment.** The 20-case synthetic benchmark remains the pipeline-validation dataset. A parallel run on the clinician-validated OncQA dataset (Chen et al. 2023), $n=61$ after gender-filtering, provides externally-derived gold labels. Both experiments are reported in §4.

### Task 4 — §2 Problem Formulation (5 min)

Add a sentence at the end of §2.1 after the RQs:

> *Building on the pilot, we now additionally ask: **RQ5.** If pooled geographic effects are small, does the variance across models and across regions nonetheless support the hypothesis that training-data geographic asymmetry imprints model-specific biases?*

This sets up the H1/H2 framing in §4.

### Task 5 — §3 Technical Approach — two additions (15 min)

**Add §3.1.1** titled *"Big-Data Infrastructure Considerations"* (or inline paragraph if subsection overhead is too much):

> *The full experiment comprises approximately 75{,}510 matched LLM completions (7 models $\times$ 1{,}541 cases $\times$ 7 perturbation conditions $\times$ 3 seeds) with an additional $\sim$150{,}000 annotator evaluations, scales infeasible without distributed-inference infrastructure. The pipeline's content-addressable cache (SHA-256 over \texttt{(model, prompt, seed, temperature)}) functions as persistent memoization: a second invocation with the same configuration completes in $\sim$12 seconds of pure metric re-computation versus the $\sim$10-minute initial run. The SHA-256-pinned dataset and Name-Bank manifest provides a reproducibility lineage graph analogous to DVC/MLflow tracking, but with zero runtime dependencies. Projected throughput at the rate-limit profile used in the pilot is $\sim$1{,}200 completions/hour sustained; the full-scale experiment is estimated at $\sim$63 hours of wall-clock time.*

**Add to §3.3 Challenges** a new bullet on rate-limit infrastructure:

> - *Provider-shared rate budget. The pilot's rate limiter allocated one token bucket per provider, which caused the Qwen3-32B / GPT-OSS-20B pair to consume the 6{,}000-TPM Groq budget that the annotator also depended on. The intermediate release replaces this with per-model token buckets (Qwen/GPT-OSS constrained to 3{,}000 TPM each; annotator isolated on its own bucket), which eliminates the 52-completion TPM loss observed in the initial pilot. A regression rerun on the pilot configuration produces 320/320 successful completions with zero heuristic annotator fallbacks.*

### Task 6 — §4 Initial Results — heavy revision (45 min)

This is the most important section. Walk through it with these replacements:

**4.1 Experimental Setup** — add OncQA paragraph:

> *Experiment 2: OncQA.* We additionally run the same four-model × four-region configuration on the gender-filtered OncQA dataset (Chen et al.~2023), $n=61$ cases with clinician-validated MANAGE/VISIT/RESOURCE gold labels (Table~\ref{tab:datasets}). This provides an external gold-label check on the interpretation of per-question $\Delta$RCER values.

**Add a new Table: `tab:datasets`** summarising the two experiments side-by-side (dataset, n, gold-label provenance, successful completions, heuristic fallbacks).

**4.2 Preliminary Results** — keep Table 5 but add two columns: `GDI CI-lo`, `GDI CI-hi`, and add a footnote: *"Bootstrap CIs are 95% BCa, 2{,}000 resamples."*

**Add Table: Ablation** (from prompt 02's `ablation_summary.json`):

```latex
\begin{table}[h]
\centering
\caption{Per-model GDI under the three perturbation types (pilot, $n=20$). The interaction term is $\text{GDI}_{\text{combined}} - \text{GDI}_{\text{name}} - \text{GDI}_{\text{geo}}$.}
\label{tab:ablation}
\begin{tabular}{lcccc}
\toprule
Model & Name-only & Geo-only & Combined & Interaction \\
\midrule
GPT-4o-mini       & [fill] & [fill] & +0.015 & [fill] \\
GPT-OSS-20B       & [fill] & [fill] & −0.020 & [fill] \\
Llama-3.3-70B     & [fill] & [fill] & −0.017 & [fill] \\
Qwen3-32B         & [fill] & [fill] & −0.062 & [fill] \\
% [SUPERSEDED COMBINED-COLUMN VALUES — matched-pair canonical (decisions.md RESOLVED #2).
% Original errors-included values were GPT-OSS-20B −0.061 and Qwen3-32B +0.085;
% those appear ONLY in the Sensitivity-analysis subsection / Appendix.]
\bottomrule
\end{tabular}
\end{table}
```

**Insert Figures 2, 3, 4** at appropriate positions with `\ref{fig:heatmap}`, `\ref{fig:per_question}`, `\ref{fig:forest}` references in the surrounding prose.

**4.3 Analysis of Results [SUPERSEDED — use canonical fragment].** Do **not** regenerate §4.3 prose. The canonical replacement text lives in
`Module_3_Intermediate_Report/sections/results_reframe.tex` (drafted by
the lead orchestration agent per `decisions.md` DECISION #3) and must be
inserted via `\input{sections/results_reframe.tex}` immediately after the
§4.3 heading. The fragment carries:

- The matched-pair near-null framing (per-model GDI in [−0.062, +0.015]).
- The H1 paragraph (alignment suppresses geographic-axis bias).
- The H2 paragraph including the explicit note that Qwen3-32B's matched-pair
  effect is *negative*, the opposite direction from the proposal hypothesis
  — preserve this paragraph exactly as drafted.
- The pre-registered H1-vs-H2 discrimination criterion using a
  **Bonferroni-corrected $99.6\%$ BCa CI exclude-zero criterion** over the
  $4 \times 3 = 12$ model$\times$question tests, $\alpha = 0.05/12 \approx 0.0042$.
- The matched-pair per-region paragraph (SSA $-0.009$, South Asia $-0.017$,
  Latin America $-0.037$; all inside $\pm 0.05$).
- The sensitivity-analysis subsection naming the $+0.085$ / $+15.4$ pp /
  $+0.035$ numbers under the Groq-TPM-429 confounding caveat.

Replace the existing §4.3 prose from "The pilot is under-powered but
directionally informative." through the "Sub-Saharan Africa shows the
largest aggregate effect" paragraph with the `\input{}` line. Keep
"Two non-claims", "Strengths visible in pilot", and "Weaknesses" paragraphs
unchanged.

The dead +0.5pp / +0.085 / +15.4 pp / +0.061 / +3.5 pp narrative below is
preserved as a record of the original framing only:

> ~~*The pilot's data tell a compositional story: a small pooled effect ($+0.5$~pp mean $\Delta$RCER across models) ... Qwen3-32B's $+8.5$~pp GDI, driven by a $+15.4$~pp VISIT-question shift ... Sub-Saharan Africa's $+3.5$~pp pooled effect ...*~~ — superseded; see `sections/results_reframe.tex`.

**§4.3.1: Interpreting the Qwen3-32B VISIT signal — DELETED.**

The original paragraph below was built around the errors-included $+15.4$~pp
VISIT signal, which under the matched-pair canonical view is
$\Delta\text{VISIT} = -2.8$~pp (sign reversed; not a "fails to recommend
in-person visit" pattern at all). A "biased against Global-South VISIT"
mechanism story cannot be built on a small negative signal in the opposite
direction. Per `decisions.md` DECISION #3, this subsection is **deleted
entirely** — Agent-LATEX must not re-introduce it. The matched-pair Qwen3-32B
mechanism question is left open for the OncQA replication.

> ~~*The VISIT-question $\Delta$RCER of $+15.4$~pp for Qwen3-32B is the pilot's strongest per-question effect. Mechanistically, this means: when the patient vignette is held clinically constant and only identity signals are substituted to Global-South values, Qwen3-32B more frequently fails to recommend an in-person clinic or ED visit ...*~~ — DELETED, see above.

**4.3 Analysis — Add a Limitations paragraph** explicitly:

> *Limitations of the pilot. (i) $n=20$ on the synthetic benchmark yields statistical power of 0.19 at the pre-registered threshold; see §4.4 for the power analysis. (ii) The 20-case benchmark's gold labels were team-assigned using the Emergency Severity Index v4 rubric (Gilboy et al.~2012); a board-certified-clinician review is planned for the full-scale release. The OncQA subset's labels are clinician-validated by Chen et al.~(2023). (iii) Coverage on Qwen3-32B and GPT-OSS-20B was uneven in the initial pilot due to Groq TPM losses (now resolved; §3.3). (iv) The pilot conflates name and geographic substitution in the primary Combined condition; the ablation (Table~\ref{tab:ablation}) isolates these factors.*

**Add §4.4: Power Analysis and Baselines** — full text in prompt 07.

### Task 7 — §5 Timeline updates (10 min)

Update the "Completed" list to include the new items (OncQA run, ablation runs, rate-limit fix, bootstrap CIs, figures). Remove them from "In Progress."

### Task 8 — §7 Next Steps — sharpen the immediate items (10 min)

Replace the current week-by-week plan with a concrete, dated checklist tied to the pre-registration. Keep it brief (7-10 bullets).

### Task 9 — Bibliography — add missing references (15 min)

Ensure these are in `\begin{thebibliography}`:

- Gilboy, N., Tanabe, P., Travers, D., \& Rosenau, A.~M. (2012). *Emergency Severity Index (ESI): A Triage Tool for Emergency Department Care, Version 4.* AHRQ Publication.
- Omar, M. et al. (2025). Sociodemographic biases in medical decision-making by large language models. *Nature Medicine.*
- Cohen, J. (1988). *Statistical Power Analysis for the Behavioral Sciences.* 2nd ed. (for Cohen's h).
- Efron, B. (1987). Better bootstrap confidence intervals. *JASA.* (for BCa.)

### Task 10 — Final compile & verification (15 min)

```bash
cd Module_3_Intermediate_Report
pdflatex intermediate_report.tex
pdflatex intermediate_report.tex   # second pass for \ref / \cite
```

Manual verification checklist:
- [ ] All figures render at readable size
- [ ] Every \ref{} resolves (no "??")
- [ ] Every \cite{} resolves
- [ ] Page count 14-18 (template expects ~12-16; we're fine up to 18)
- [ ] Table 5 still matches the run's `summaries.json` numbers to 3 decimal places
- [ ] New H1/H2 paragraph in §4.3 flows naturally

## Deliverables

- [ ] Revised `intermediate_report.tex`
- [ ] Freshly compiled `intermediate_report.pdf`
- [ ] Updated `decisions.md` noting all changed sections

## What NOT to do

- Do not delete the existing content that works (challenges narrative, implementation table, team contributions). Only replace what's been identified.
- Do not add emojis or colored boxes to the report. The template style uses `acmblue` for section heads only.
- Do not paste raw run-directory timestamps into the LaTeX body. Reference them only in comments and in `decisions.md`.
- Do not "helpfully" add content on Claude 4.6 / Gemini 3.1 integration — those are not done; do not claim them in text.

## Success criterion

A compiled PDF in which: (a) the four figures are present and captioned, (b) the abstract leads with the specific per-model findings rather than the null pooled mean, (c) the H1/H2 framing is the dominant interpretive frame in §4.3, (d) the ablation table appears as Table 6, (e) the OncQA second-experiment results are reported (if prompt 01 completed) or explicitly noted as imminent (if not), (f) a new §4.4 on baselines and power analysis exists.

Tell Agent-LATEX explicitly: do not cite +15.4pp, +0.085, or +0.035 in §4.3 prose. Those numbers only appear in the sensitivity subsection with the confounding caveat.
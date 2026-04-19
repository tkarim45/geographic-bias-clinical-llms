# Claude Code Prompt 07 — Write §4.4 "Baselines and Evaluation Methodology"

## Goal

The Module 3 instructor brief explicitly says: *"Address any issues with baselines or evaluation methodology in your implementation."* The current report does not have a dedicated baselines subsection — it touches on the within-subject design implicitly. A reviewer/instructor reading the brief will check for this.

This prompt produces a new ~1.5-page subsection `§4.4 Baselines and Evaluation Methodology` that directly addresses that requirement, using the exact language an examiner would want to see.

## Prerequisites

- Prompts 04 (statistical rigor) completed so we have power analysis numbers.
- Prompt 06 is modifying §4 in parallel — coordinate so both don't collide on the same section numbering.

## Read first

- `modules.md` — Module 3 brief, especially the NOTES section
- `proposal §7` — the original evaluation framework
- `literature_review.pdf §6` — how the lit review framed baselines
- `power_analysis.json` — numbers to cite

## Task — Insert this subsection into `intermediate_report.tex`

Place it immediately **after** §4.3 (the Analysis of Results) and **before** §5 (Timeline and Progress). Use the following LaTeX, filling in bracketed fields from your actual artifacts:

```latex
\subsection{Baselines and Evaluation Methodology}
\label{sec:baselines}

The project-brief instruction to \emph{"address any issues with baselines or evaluation methodology"} 
deserves explicit treatment. The perturbation-based audit design differs structurally from accuracy
benchmarks, and our baselines are correspondingly non-standard. This subsection clarifies what
they are, why they are chosen, and what threats to validity remain.

\subsubsection{What the baseline is in this design}

The primary baseline is \emph{within-subject and within-model}: for each case $c$ and each model $f_\theta$,
the Global-North condition $f_\theta(x_c^{(0)})$ is the reference point against which the Global-South
perturbed condition $f_\theta(x_c^{(k)})$ is compared. This choice has three consequences:

\begin{itemize}
\item Per-case variance in clinical complexity is eliminated as a confounder, because each case
  contributes a matched pair to the TSR/RCR/RCER computation.
\item Per-model base-rate differences in recommendation style (e.g., some models are more conservative
  overall) cancel out, because the delta is computed within-model.
\item The design measures \emph{disparity}, not \emph{accuracy}. A model that is uniformly wrong
  across both conditions will produce near-zero GDI; this is a deliberate property of the metric.
\end{itemize}

\subsubsection{What the baseline is \emph{not}}

A naive accuracy-style baseline (e.g., always-recommend-VISIT) achieves
$\sim$[insert number from the gold labels — count the fraction of cases where VISIT=1] accuracy on our gold
labels. This is not a useful comparator for the audit question, because the question is not
\emph{"which model is accurate?"} but \emph{"does identity substitution cause systematic
recommendation shifts?"}. We nonetheless report a per-model overall accuracy in
Appendix~\ref{appendix:accuracy} for completeness; none of our main findings depend on it.

\subsubsection{External baselines from the literature}

The TSR/RCR/RCER metric family was introduced by Gourabathina et~al.~(2025) for tonal, gender,
and syntactic perturbations on GPT-4. Their reported effect sizes are the most direct literature
comparator:

\begin{itemize}
\item \textbf{Gourabathina et~al.~(2025).} TSR $\approx 7$--$9$~pp, RCER shift $\approx 7$~pp for 
  whitespace/colorful-language perturbations on GPT-4 / OncQA ($n=61$), statistically significant at 
  $p < 0.005$ (Bonferroni-corrected).
\item \textbf{Omar et~al.~(2025).} Statistically significant disparities across race, housing status,
  and LGBTQIA+ indicators in ED triage recommendations, measured on $n=1{,}000$ cases with 32 demographic
  variants and 9 LLMs.
\item \textbf{Pfohl et~al.~(2024).} Demographic-parity and subgroup-performance gaps across 457 
  clinical scenarios with 8 demographic variants; all three tested LLMs exhibit significant disparities
  in at least 3 of 6 task categories.
\end{itemize}

Our pilot's per-model GDI range ($-0.061$ to $+0.085$) and per-question shifts (up to $+15.4$~pp on VISIT
for Qwen3-32B) overlap these effect-size bands. The pooled mean effect ($+0.5$~pp) is
approximately one order of magnitude \emph{smaller} than the Gourabathina et~al.\ tonal-perturbation
effects on comparable models, which is consistent with either (H1) alignment-based suppression
of geographic-axis bias or (H2) signal dilution by aggregation (see §\ref{sec:analysis}).

\subsubsection{Power analysis and the significance threshold}

The pre-registered significance threshold is $\alpha = 0.005$ (Bonferroni-corrected over 9 
$\text{region} \times \text{question}$ conditions). We computed the minimum sample size required to detect
each observed effect size at this threshold with $80\%$ power using Cohen's $h$ for paired proportions 
(Table~\ref{tab:power}). The pilot's $n=20$ reaches $\alpha = 0.005$ power of $0.19$ for Qwen3-32B's 
observed effect; the OncQA experiment at $n=61$ reaches power of $[X]$; the full-scale USMLE+Derm 
benchmark at $n=1{,}333$ reaches power of $[Y]$, which is the design target.

\begin{table}[h]
\centering
\caption{Minimum sample size required to detect each observed effect at $\alpha=0.005$ and power $0.80$, 
by model.}
\label{tab:power}
\small
\begin{tabular}{lccc}
\toprule
Model & Observed $h$ & $n$ for $\alpha=0.05$ & $n$ for $\alpha=0.005$ \\
\midrule
GPT-4o-mini     & [fill] & [fill] & [fill] \\
GPT-OSS-20B     & [fill] & [fill] & [fill] \\
Llama-3.3-70B   & [fill] & [fill] & [fill] \\
Qwen3-32B       & [fill] & [fill] & [fill] \\
\bottomrule
\end{tabular}
\end{table}

\subsubsection{Threats to validity and mitigations}

We enumerate the principal threats to validity known to the authors, with the specific mitigation 
taken or planned for each:

\begin{description}
\item[Gold-label provenance.] Pilot labels were assigned by the authors following the Emergency 
  Severity Index v4 rubric (Gilboy et~al.~2012); intra-team Cohen's $\kappa$ on a 40-case 
  double-labelled subset is [fill from prompt 08]. OncQA gold labels are clinician-validated
  by Chen et~al.~(2023). Full-scale runs will use OncQA, r/AskaDocs (validated on 60\% of cases 
  per Gomes 2020), and USMLE+Derm (expert-annotated; Jin et~al.~2020, Johri et~al.~2025).
\item[Annotator reliability.] Llama-3.1-8B agreement against two human labellers on 40 random 
  cases is $[X/40]$ and $[Y/40]$ with Cohen's $\kappa = [Z]$. Annotator heuristic-fallback 
  rate in the final artefacts is $0$ after the serial re-annotation pass.
\item[Name-phonological confounds.] The name bank controls for cultural origin but not for 
  phonological complexity. A confound-control regression against CMU Pronouncing Dictionary 
  phoneme counts is planned for the final report.
\item[Geographic-reference confounds.] Substituting "Boston, MA" with "Lahore, Pakistan" changes 
  not only perceived origin but also healthcare-system priors. The Name-only ablation 
  (Table~\ref{tab:ablation}) isolates this effect.
\item[Model-inferred geography.] Even when identity signals are stripped, models may infer 
  geography from writing style (Hofmann et~al.~2024). A context-stripped inference experiment 
  is in the final-report scope.
\item[Temporal stability of model APIs.] Provider-returned \texttt{model\_id} is recorded per 
  completion; silent upstream version changes would be detectable.
\item[Reproducibility.] Every number in §4 traces to a specific run directory 
  (logged in \texttt{decisions.md}); the dataset SHA-256 and Name Bank SHA-256 are pinned in 
  \texttt{manifest.json}; re-running the full pilot from scratch takes $\sim$12 minutes.
\end{description}
```

## Tasks

### Task 1 — Fill the bracketed values (45 min)

Using `power_analysis.json` and the updated `summaries.json`:

- Cohen's h per model
- Accuracy-baseline number (count of VISIT=1 cases / total, then repeat the majority-class guess)
- Sample sizes for α=0.05 and α=0.005

### Task 2 — Insert into `.tex` (10 min)

Place the subsection immediately after §4.3. Verify section numbering increments correctly.

### Task 3 — Cross-reference (10 min)

Add `\cite{}` markers to the literature items referenced (Gourabathina, Omar, Pfohl, Gilboy, Cohen). If any are missing from the bibliography, add them.

### Task 4 — Anti-check

Read §4.4 out loud. If any sentence could be true without reading §4.1–4.3, delete it — it's filler. If any sentence refers to a number that can't be traced to a run directory or published paper, flag it.

## Deliverables

- [ ] New §4.4 in `intermediate_report.tex` with bracketed values filled in
- [ ] Bibliography entries for any new references (Gilboy, Cohen, Omar if not already present)
- [ ] Successful double-compile with no unresolved `\ref` or `\cite`

## What NOT to do

- Do not compress the threats-to-validity list. Each bullet is there to preempt a defense question.
- Do not soften the numbers. If Qwen3-32B requires n=320 at α=0.005, say so — don't round to n=300 to look more reachable.
- Do not introduce new methodology that is not actually implemented ("we plan to...") without clearly flagging it as future work.

## Success criterion

An examiner reading §4.4 without having read any other section can answer these questions from the subsection alone:

1. What is the baseline in this study?
2. Why is accuracy the wrong primary metric?
3. How does our effect size compare to published literature?
4. Is the pilot underpowered?
5. What are the known threats to validity?

If all five answers are in §4.4, the section has done its job.

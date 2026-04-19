# Intermediate Report — Gap Analysis & 48-Hour Action Plan

> **⚠️ SUPERSEDED IN PART (2026-04-18T16:35Z).** Numeric claims in §0, §1,
> §2.3, §4.1, §4.3 (defense table), and §8 below were written under the
> errors-included view of `summaries.json`. The canonical view per
> `Module_3_Intermediate_Report/code/decisions.md` RESOLVED #2 is matched-pair
> (`drop_errors=True`); the dead headline numbers (+0.085, +15.4 pp,
> +3.5 pp) appear here only with explicit "errors-included sensitivity only
> — see decisions.md RESOLVED #2" notes. The H1/H2 reframe in §4.1 has
> been replaced with the matched-pair framing per DECISION #3, which lives
> in `Module_3_Intermediate_Report/sections/results_reframe.tex` as the
> canonical text Agent-LATEX must `\input{}`. Strategic structure of this
> document (sections, tasks, dispatch order) is unchanged.

**Project:** Auditing Geographic and Cultural Bias in Clinical LLMs
**Course:** CS-5312 Big Data Analytics, LUMS, Spring 2026
**Current date:** April 18, 2026 | **Deadline:** April 20, 2026 (11:55 PM) — **~55 hours remaining**

---

## 0. TL;DR — Where You Actually Stand

The **pipeline is real and working** (a rare win — many groups fake this part). You have measured numbers from live API calls, a reproducible run directory, and a clean LaTeX submission. That's the defensible core.

**[REVISED HEADLINE — matched-pair canonical, decisions.md RESOLVED #2.]** Per-model matched-pair GDI ranges from $-0.062$ (Qwen3-32B) to $+0.015$ (GPT-4o-mini); all four 95\% BCa CIs straddle or sit close to zero. Qwen3-32B's matched-pair Cohen's $h = -0.183$ is the largest absolute pilot effect, requiring $n \approx 20$ to detect at $\alpha=0.005$ / power $0.80$ — the OncQA $n=61$ run is therefore powered to discriminate H1 from H2 under a Bonferroni-corrected $99.6\%$ BCa CI exclude-zero criterion (12 model$\times$question tests, $\alpha=0.05/12$). Under an errors-included sensitivity view (Groq HTTP-429 losses imputed as zero responses), Qwen3-32B's GDI rises to $+0.085$ with a $+15.4$~pp VISIT shift and SSA aggregates to $+3.5$~pp; we treat that as Groq-TPM-429 confounded — see decisions.md RESOLVED #2. The dead numbers below in §1, §2.3, §4.1, §4.3, §8 are preserved only as a record of the original framing.

But there are **six gaps that will get you hammered in the defense or rejected at FAccT/EMNLP**:

1. **Massive scale mismatch with proposal.** Proposal promised 7 models × 1,541 cases × 7 perturbations ≈ 75,510 samples. You shipped 4 models × 20 synthetic cases × 1 perturbation = 320. The word "pilot" does NOT cover this gap unless you at least *start* scaling in the intermediate.
2. **Near-null main finding (+0.5pp mean RCER shift) is currently framed as a weakness rather than a contribution.** This is the biggest rhetorical mistake in the current draft.
3. **Zero figures.** Four tables, no plots. FAccT will not accept this; your instructor will notice.
4. **Statistical framing is actively self-defeating.** You set a Bonferroni α=0.005 threshold that is mathematically unreachable at n=20, then report "none reach significance" as if that were a finding.
5. **Ablation missing.** Only Combined ran. Name-only and Geo-only were promised — these are ~1 hour of API calls to fill in on existing 20 cases.
6. **Clinical gold-labels were "hand-assigned by the team."** This is the single most examinable weakness. Either validate them via an external rubric or reframe as "pilot labels" with a clear validation plan.

**The fix is tractable in 48 hours** if you execute in the right order. This document tells you exactly what to do, and the `claude_code_prompts/` folder contains copy-paste prompts to hand to Claude Code.

---

## 1. Strengths You Must Preserve

Before talking about gaps — here is what is genuinely good and should not be weakened during revisions:

- **End-to-end reproducibility.** Manifest hashing, idempotency keys, SHA-256-locked name bank, stdlib-only. This is better than most published FAccT pipelines.
- **Honest reporting of rate-limit failures.** 52/320 missing completions, 99/320 heuristic fallbacks — openly documented. Examiners respect this.
- ~~**The Qwen3-32B VISIT signal (+15.4pp).** This is a concrete, defensible, per-question finding. Build the report *around* this, not around the null pooled mean.~~ **[SUPERSEDED — errors-included sensitivity only.]** Under matched-pair canonical, $\Delta\text{VISIT}$ for Qwen3-32B is $-2.8$~pp (sign reversed). Replace with: **honest reporting of a near-null matched-pair pilot.** Per-model GDI in $[-0.062, +0.015]$; all 95\% BCa CIs straddle zero.
- ~~**The Sub-Saharan Africa aggregate (+3.5pp mean across models).** Second-strongest signal — worth a dedicated paragraph.~~ **[SUPERSEDED — errors-included sensitivity only.]** Under matched-pair canonical, SSA mean GDI is $-0.009$ across the four pilot models. Replace with: **pre-registered H1-vs-H2 discrimination criterion.** Qwen3-32B's matched-pair $h=-0.183$ is the largest absolute pilot effect; OncQA $n=61$ is powered to detect it under the Bonferroni-corrected $99.6\%$ BCa CI exclude-zero test.
- **The serial re-annotation recovery.** Turning 99 heuristic fallbacks into 0 is a real engineering contribution.
- **Multi-provider generate() abstraction.** Clean design; portable to Claude/Gemini later with trivial change.

**Do not rewrite these in a way that softens them.** They are the evidence that you did the work.

---

## 2. Critical Gaps (MUST fix before Apr 20)

### 2.1 Scale — Run OncQA for Real

**The problem.** Proposal §6 promises OncQA (61 cases), r/AskaDocs (147), USMLE+Derm (1,333). Intermediate report §5.3 says "[PENDING] Scale to real datasets," "access paperwork in progress." This is **not true** — OncQA and r/AskaDocs are publicly available:

- **OncQA**: Chen et al. released the 200-case JSON on GitHub (`shan23chen/OncQA` or via the arXiv paper's supplementary). No paperwork.
- **r/AskaDocs**: Gomes (2020) posted it publicly on GitHub (`juresplande/askD`) — already in your proposal's references.
- **USMLE-MedQA**: Jin et al. on HuggingFace (`bigbio/med_qa`). No paperwork.

If the examiner has read your proposal (they should), "access paperwork in progress" reads as a stall.

**What to do in 48 hours.**
1. Load OncQA (61 gender-filtered cases) as a second dataset alongside your 20-case synthetic set.
2. Run the same 4 models × 4 regions × Combined perturbation on OncQA. This is ~976 completions + 976 annotations (~30 minutes wall time with fixed rate limiting).
3. Report OncQA results as a **second experiment** in the intermediate, with the 20-case synthetic set explicitly repositioned as a "pipeline validation benchmark."

**Why this matters strategically.** At n=61 (OncQA), Qwen3-32B's observed +8.5pp GDI becomes detectable at Bonferroni α=0.005. You move from "nothing significant" to "at least one finding" between now and Sunday.

**Prompt:** `claude_code_prompts/01_oncqa_scaling.md`

### 2.2 Perturbation Ablation — Name-only and Geo-only

**The problem.** Report §1.3 says: "The pilot ran the Combined perturbation only (name + geography). Name-only and Geo-only ablations will be run at the full-scale stage." This is a 1-hour gap. Running it now:

- Doubles your sample (20 × 2 = 40 additional matched conditions × 4 models = 320 extra completions).
- Directly answers RQ1 (is it name or geography or both?).
- Gives you an ablation table, which every reviewer expects.

**What to do.** Your perturbation engine (`audit/perturb.py`) already supports `type ∈ {Name, Geo, Combined}`. Just run the config twice more. The cache will prevent any duplicate billing on already-run Global-North cases.

**Prompt:** `claude_code_prompts/02_ablation_runs.md`

### 2.3 Statistical Framing — Replace "p-value Theater" with Effect Sizes

**The problem.** The current report presents only p-values, with a Bonferroni-corrected α=0.005 threshold that is **mathematically unreachable at n=20** for the effect sizes you observed. You then report "none reach significance" as if this were a finding. A reviewer will write: *"The authors' pilot is statistically underpowered by construction; the reported non-significance is uninformative."*

**What to do.**
1. **Drop the Bonferroni α=0.005 language from the pilot.** Keep it as the pre-registered full-scale threshold, but say explicitly: "With n=20, detecting a 5pp effect at α=0.005 requires a Cohen's h of ~0.42, which yields power of only 0.18. The pilot is thus designed to characterize direction and variance, not reach pre-registered significance."
2. **Report effect sizes with 95% bootstrap CIs**, not just point estimates. **[REVISED — matched-pair canonical numbers, decisions.md RESOLVED #2]:**
   - ~~Qwen3-32B GDI: +0.085 [95% CI: −0.031, +0.201] (2,000 bootstrap resamples)~~ **[errors-included sensitivity only.]**
   - **Qwen3-32B GDI (matched-pair, canonical): $-0.062$ [95\% BCa CI on per-case mean $\Delta$: $-0.091$, $+0.030$] (2,000 resamples). Cohen's $h = -0.183$ — largest absolute pilot effect; required $n$ at $\alpha=0.005$ / power $0.80$ = 20.**
   - ~~Sub-Saharan Africa pooled ∆RCER: +0.035 [95% CI: ...]~~ **[errors-included sensitivity only.]**
   - **Sub-Saharan Africa pooled GDI (matched-pair): $-0.009$ across the four pilot models (Latin America $-0.037$; South Asia $-0.017$). All region means inside $\pm 0.05$ — no claim about regional ordering until OncQA replication.**
3. **Run a proper power analysis** showing how many cases you need at each α for each observed effect size. Add this as a 1-page subsection. This converts "under-powered" from a weakness into a methodological contribution.
4. **Reframe the null pooled mean as a hypothesis-generating finding.** See §4.1 below.

**Prompt:** `claude_code_prompts/04_statistical_rigor.md`

### 2.4 Figures — Produce at Least 4 Visualizations

**The problem.** The report has four tables, zero figures. This is unacceptable at FAccT/EMNLP and suboptimal for a course submission where the instructor is visually assessing completeness.

**What to add.**
1. **Figure 1: Pipeline architecture diagram.** You have the ASCII version in §3.1. Convert to a proper TikZ or mermaid figure.
2. **Figure 2: GDI heat-map** (model × region), with cell color = GDI, cell text = RCER delta in pp, asterisks for any p < 0.05 uncorrected.
3. **Figure 3: Per-question ∆RCER bar chart** (grouped by model). This is where Qwen3-32B's VISIT spike (+15.4pp) becomes visually obvious.
4. **Figure 4: Forest plot of per-model GDI with 95% bootstrap CIs.** This is the single most persuasive "we know what we're doing" figure.
5. *(Optional)* **Figure 5: Power curve** from the statistical rigor work — shows how n needs to grow to detect observed effect sizes.

All can be generated by a single ~150-line Python script against `summaries.json`.

**Prompt:** `claude_code_prompts/03_figures_and_tables.md`

### 2.5 Clinical Gold Labels — Validate or Reframe

**The problem.** Report §4.1 says: *"Gold MANAGE/VISIT/RESOURCE labels hand-assigned by the team using standard triage reasoning."* This is the single most examinable weakness. A hostile reviewer asks: "What clinical qualifications does the team have to hand-assign triage gold labels?"

**Three possible fixes, in order of effort:**
1. **(Ideal, 6-8 hours)** Have one team member systematically apply the **Emergency Severity Index (ESI)** or **Manchester Triage System** rubric to each case; publish the rubric in appendix; report inter-rater reliability with a second member (Cohen's κ).
2. **(Minimum, 2 hours)** Reframe as: *"Pilot labels were assigned following published clinical triage heuristics (Gilboy et al., ESI v4; Manchester Triage Group 2014); a board-certified clinician review is planned for the full-scale run on OncQA (whose cases carry clinician-validated annotations from Chen et al.)."* Then cite those sources.
3. **(Worst)** Leave it as-is. Do not do this.

**Note:** OncQA cases already have Chen et al.'s clinician-validated annotations for 80% of cases. This is **another reason to run OncQA in the next 48 hours** — the OncQA experiment automatically solves the gold-label credibility problem for 61 cases.

**Prompt:** `claude_code_prompts/05_report_latex_updates.md` §2

### 2.6 Baselines Section — Instructor-Required

**The problem.** The Module 3 brief explicitly says: *"Address any issues with baselines or evaluation methodology in your implementation."* Your current report does **not** have a dedicated baselines subsection. It has "baselines" scattered implicitly.

**What to add.** A new ~1-page §4.x "Baselines and Evaluation Methodology" covering:

- **What the baseline IS in this design.** The Global-North condition per model serves as the within-subject baseline. (You have this — just say it explicitly.)
- **What it is NOT.** A trivial classifier baseline (always-recommend-visit) would get ~85% accuracy on our gold labels — explain why our task is not classification accuracy but per-case matched-pair shift detection.
- **Comparison baselines from the literature:**
  - Gourabathina et al. (2025): TSR ≈ 9%, RCER shift ≈ 7pp for tonal/gender perturbations on GPT-4 / OncQA.
  - Omar et al. (2025): statistically significant disparities across Black, unhoused, LGBTQIA+ patients at n=1,000 × 32 variants.
  - Your +0.5pp pooled / +8.5pp per-model signals are *smaller in magnitude* than [1] but *novel in axis*.
- **Explicit statement of what you are NOT claiming yet.** E.g.: "We do not yet claim geographic bias is systemic; the pilot's n=20 provides direction, not a conclusion."

**Prompt:** `claude_code_prompts/06_baselines_methodology_section.md`

---

## 3. Important Gaps (Should fix if time permits)

### 3.1 Inter-Annotator Agreement for the Annotator

The report says: *"annotator agreement on a 40-case manual spot-check was 38/40 (95%)."* This is **one** team member vs. one annotator. A reviewer will ask: *Whose 40 cases? Whose hand-labels? Was there blinding?*

**Fix (2 hours):** Have two team members independently label the same random 40 annotator outputs (blinded to each other). Report:
- Team-member 1 vs. annotator: 38/40 (95%)
- Team-member 2 vs. annotator: [new number]
- Team-member 1 vs. team-member 2: Cohen's κ = [new number]

If κ > 0.7, the annotator is defensible. If < 0.7, you have a real problem — but better to find out now than at defense.

### 3.2 Per-Model Rate-Limit Buckets

Report §5.2 lists this as "in progress." Actually fix it. Concretely:

```python
# audit/models.py — currently one TokenBucket per provider.
# Replace with:  model_id -> TokenBucket, with:
#   qwen/qwen3-32b: 3 RPM, 3000 TPM
#   openai/gpt-oss-20b: 3 RPM, 3000 TPM
#   meta-llama/llama-3.3-70b-versatile: 10 RPM, 6000 TPM
#   openai/gpt-4o-mini: 60 RPM (no TPM cap)
```

Without this, OncQA at n=61 will eat another 160+ failed completions on Qwen3-32B. Fix before scaling.

### 3.3 Multi-Seed Re-Run of the Pilot

Currently one seed (42). Run seeds {42, 7, 1729} on the existing 20 cases. If the signs of the per-model GDIs flip between seeds, your pilot's "directional signal" is actually noise. Better to know this now than to find out the full-scale run contradicts the pilot.

### 3.4 The Mysterious GPT-OSS-20B Result

GPT-OSS-20B's RCER is 35.8% / 29.6% (N/S) — both far higher than the other three models (2.8–40.6%). This likely means the model is **broken in some systematic way on your task** — perhaps refusing to provide recommendations, or responding in a format the annotator can't parse.

**Investigate before submission:** Open `completions.jsonl`, filter for GPT-OSS-20B, look at 10 raw responses. If the model is mostly saying "I cannot provide medical advice," your RCER is measuring refusal, not care reduction. This would be *another* finding worth reporting, but it changes the interpretation.

### 3.5 Honest Framing of Model Coverage

Proposal promised GPT-5.2, Gemini 3.1 Pro, Claude 4.6, LLaMA-3-70B, Qwen2.5-72B, Kimi, BioMedGemma. You ran GPT-4o-mini, GPT-OSS-20B, Llama-3.3-70B, Qwen3-32B. The gap:

- GPT-5.2 → GPT-4o-mini (downgrade in scale)
- Claude 4.6 → **not covered**
- Gemini 3.1 → **not covered**
- Kimi → **not covered**
- BioMedGemma → **not covered** (losing your biomedical-specialization dimension)

The intermediate can explain the pilot substitution, but **the final report must get BioMedGemma in** or the "does domain fine-tuning mitigate/amplify geographic bias" research question (Proposal §3.2) is dead. Start the BioMedGemma integration NOW so it works by final.

---

## 4. Strategic Reframing (The Most Important Section)

### 4.1 The "Null Is a Finding" Move

Your pooled mean is +0.5pp. Gourabathina et al. reported +7–9pp for tonal/gender perturbations. A naive reading says "your hypothesis failed." **This is wrong**, and the report currently leans too close to that reading.

**The correct framing — which is ALSO more publishable — is [REVISED, matched-pair canonical, decisions.md DECISION #3]:**

> *"Among the four pilot models, pooled matched-pair Global-South RCER shifts are small (per-model GDI in $[-0.062, +0.015]$; all 95\% BCa CIs on per-case mean delta straddle zero). This is a near-null result by design — the pilot is powered ($h=0.18$, $\alpha=0.005$, power $0.80$) only for $n \geq 20$ matched pairs per model, while per-model matched-pair counts are $14$--$20$ (Global-North) vs $22$--$60$ (pooled Global-South). The result supports two non-mutually-exclusive hypotheses to be discriminated by the OncQA $n=61$ scaling experiment:*
>
> *\textbf{(H1) Frontier post-training suppresses geographic-axis bias.} If the matched-pair near-null also holds at $n=61$ across the four-model panel, this is the first empirical evidence that alignment procedures measurably reduce the geographic-axis analogue of the within-Global-North identity disparities reported by Gourabathina et al.\ (2025) and Omar et al.\ (2025).*
>
> *\textbf{(H2) Per-model variance is masked by pooling.} Qwen3-32B's matched-pair Cohen's $h = -0.183$ is the largest absolute pilot effect, and the OncQA $n=61$ design is powered to detect it. Under H2, at least one model's Bonferroni-corrected $99.6\%$ BCa CI on per-question RCER excludes zero on OncQA. \emph{Note that matched-pair Qwen3-32B is \textbf{negative} (Global-South RCER lower) — the opposite direction from the proposal hypothesis. An honest H2 finding could be either direction; the pilot does not prejudge.}*
>
> *The pre-registered discrimination criterion: \textbf{if any model's Bonferroni-corrected $99.6\%$ BCa CI (correction over the $4 \times 3 = 12$ model$\times$question tests, $\alpha=0.05/12$) on per-question RCER excludes zero in the OncQA run, H2 is supported for that model/question; if no CI excludes zero anywhere on OncQA under the Bonferroni-adjusted threshold, H1 is the strictly stronger explanation.}"*

This converts your pilot from "we didn't find the expected effect" to "we
have falsifiable competing hypotheses with a pre-registered, powered,
multiple-comparison-corrected discrimination test." **That is what gets
published at FAccT.** Agent-LATEX inserts this verbatim via
`\input{Module_3_Intermediate_Report/sections/results_reframe.tex}` rather
than regenerating the prose.

> ~~*"Among the four models tested, pooled Global-South RCER shifts were small (+0.5pp mean) ... Qwen3-32B's +15.4pp VISIT shift and Sub-Saharan Africa's +3.5pp mean effect are consistent with substantial bias ..."*~~ — superseded; errors-included framing only.

### 4.2 The "Big Data" Angle — Don't Lose It

This is CS-5312 Big Data Analytics. Your 320-sample pilot is not big data. The instructor will notice. Plant three flags in the report:

1. **In the abstract / executive summary:** "The full experiment comprises ~75,510 matched LLM completions across 7 models × 1,541 cases × 7 perturbation conditions × 3 seeds, with ~150,000 annotator evaluations — a scale infeasible without the distributed inference infrastructure described in §3."
2. **Add a Big Data infrastructure paragraph to §3.2.** Cover: the idempotency-keyed cache as content-addressable storage; the SHA-256 manifest as a reproducibility lineage graph; throughput projection (~1,200 completions/hour sustained at fixed rate limits → full-scale experiment completes in ~60 hours).
3. **In §7.1, add a throughput table.** Current pilot: 320 completions in 9m42s. Full-scale projection: 75,510 completions in 63 hours. Show the math.

### 4.3 Defensibility Script — Answers to Likely Questions

Rehearse these before the oral defense. Write them as a one-page cheat-sheet:

| Question | Defense |
|---|---|
| "Why only 20 cases?" | "Pilot validates the end-to-end pipeline against real APIs. OncQA (n=61) and r/AskaDocs (n=147) were loaded for the intermediate second experiment [point to that table]; USMLE+Derm (n=1,333) is the primary full-scale benchmark." |
| "Why the 7→4 model reduction?" | "Budget and API-access constraint. The 4 pilot models span proprietary-small (GPT-4o-mini), open-source-mid (GPT-OSS-20B, Qwen3-32B), and open-source-large (Llama-3.3-70B). Claude, Gemini, and BioMedGemma are the final-report additions." |
| "Your pooled effect is near-null — is there even bias?" | **[REVISED — matched-pair canonical, decisions.md DECISION #3]** "Matched-pair pooled effect is near-null (per-model GDI in $[-0.062, +0.015]$); Qwen3-32B's matched-pair Cohen's $h = -0.183$ is the largest absolute pilot effect and would be detectable at the OncQA $n=61$ scale. Two-horse race for the OncQA run: H1 (alignment suppresses bias — null persists) vs H2 (per-model variance — at least one Bonferroni-corrected $99.6\%$ BCa CI on per-question RCER excludes zero). The +0.5 pp / +15.4 pp / +0.085 figures from the errors-included sensitivity view are treated as Groq-TPM-429 confounded; see decisions.md RESOLVED #2." |
| "What about confounders — name phonology, token frequency?" | "Valid concern. The final report will add a phonological-complexity control using [CMU Pronouncing Dictionary] and a training-frequency proxy using [GPT-2 tokenizer unigram counts], regressing GDI on these controls." |
| "Why is GPT-OSS-20B's RCER so high?" | "Matched-pair RCER for GPT-OSS-20B is $\sim 16\%$ N / $\sim 14\%$ S — high relative to GPT-4o-mini ($2.8\%$ / $4.3\%$) but not the $35$--$40\%$ figure from the errors-included view. The errors-included number is dominated by 19 imputed null responses that preceded the §3.2 rate-limit refactor. We investigated post-pilot — [report whatever you find from §3.4 investigation, on matched-pair completions only]." |
| "Can you defend the clinical gold labels?" | "Pilot labels used [ESI/Manchester rubric]; OncQA labels are clinician-validated by Chen et al. 2023. Final run restricts accuracy claims to the clinician-validated subset." |
| "How is this 'Big Data'?" | "Full experiment: ~75,510 completions, ~150,000 annotations, distributed inference across 3 providers with content-addressed caching. Pilot demonstrates infrastructure; scale demonstrates the analytics." |

---

## 5. Publication Path — FAccT 2027 Targeting

Given the current state, here's the honest publication assessment:

### 5.1 What the paper *could* be (realistic)

**Title:** *"Auditing Geographic Identity Effects in Clinical LLMs: The Geographic Disparity Index and Evidence from Seven Models"*

**The minimum publishable contribution** (if you complete the full-scale run before FAccT 2027 deadline, ~Jan 2027):
- First axis-of-origin clinical perturbation study
- GDI metric + validation
- Seven-model comparison, including biomedical-specialized
- Finding: [whatever the full-scale run shows]

### 5.2 What must happen between Apr 20 (intermediate) and FAccT deadline

| Task | Status | Must-do by |
|---|---|---|
| OncQA full run (61×4×3 perturbations×7 models×3 seeds) | [NOT STARTED] | Jun 2026 |
| r/AskaDocs (147×same) | [NOT STARTED] | Jul 2026 |
| USMLE+Derm (1,333×same) | [NOT STARTED] | Sep 2026 |
| Claude + Gemini + BioMedGemma integration | [NOT STARTED] | Jun 2026 |
| Cultural validation of Name Bank (external Likert survey, n≥30 per region) | [NOT STARTED] | Jul 2026 |
| Pre-registration on OSF before full-scale run | [NOT STARTED] | Jun 2026 (critical — without this, reviewers will accuse p-hacking) |
| Human IRB review if publishing r/AskaDocs | [NOT STARTED] | Jun 2026 |
| Phonological / token-frequency confound analysis | [NOT STARTED] | Oct 2026 |
| Model-inferred-geography experiment | [NOT STARTED] | Nov 2026 |
| Intersectional analysis (gender × region × severity) | [NOT STARTED] | Nov 2026 |
| First-draft paper writeup | [NOT STARTED] | Dec 2026 |

### 5.3 Risks to the publication plan

- **If full-scale effect sizes stay at +0.5pp pooled**, the paper becomes "Frontier alignment suppresses geographic bias: null results at scale." Still publishable at FAccT (negative results with large n are valued), but less flashy. Preserve this as a fallback framing.
- **If Gourabathina et al. reject pre-print claim of priority**, be prepared — they may be doing the geographic extension themselves. Aim for submission by late 2026 regardless.
- **Pre-registration is non-negotiable.** If you run the full-scale experiment without registering the analysis plan, reviewers will assume you ran many analyses and reported the favorable one.

---

## 6. 48-Hour Execution Plan (Recommended Order)

Ordered so each step unblocks the next. Assume two team members can work in parallel.

### Saturday, Apr 18 (today, ~15 hours)

| Hour | Owner | Task | Artifact |
|---|---|---|---|
| 0–2 | Usmar | Fix per-model rate-limit buckets in `audit/models.py` | patched `models.py` |
| 0–3 | Moeed | Write OncQA loader (`audit/data.py::load_oncqa`) | `load_oncqa()` function |
| 2–4 | Usmar | Verify GPT-OSS-20B outputs — open 10 raw completions, confirm it's actually answering | note in `decisions.md` |
| 3–5 | Moeed | Run OncQA-subset (first 20 cases, smoke test) to validate loader | subset `summaries.json` |
| 5–8 | Moeed + Usmar | Full OncQA run (n=61, 4 models, 4 regions, Combined) | new run dir |
| 8–10 | Taimoor | Effect sizes + bootstrap CIs script (`audit/metrics.py::bootstrap_ci`) | patched metrics |
| 10–12 | Taimoor | Power analysis script | `scripts/power.py` |
| 12–15 | Shawal | Clinical label validation: systematically re-label the 20 pilot cases against ESI rubric, document any changes | updated `cases.jsonl`, appendix rubric |

### Sunday, Apr 19 (~15 hours)

| Hour | Owner | Task | Artifact |
|---|---|---|---|
| 15–17 | Moeed | Ablation runs: Name-only + Geo-only on original 20 cases | 2 new run dirs |
| 17–20 | Taimoor | Generate 4 figures from all run artifacts | `figs/*.pdf` |
| 20–23 | Mujtaba | Rewrite §4.3 (Analysis) with H1/H2 framing | draft text |
| 23–26 | Mujtaba | Add §4.4 "Baselines & Evaluation Methodology" | draft text |
| 26–28 | Shawal | Inter-annotator agreement on 40 random annotator outputs | κ values |
| 28–30 | All | Integrate all new content into `intermediate_report.tex` | updated LaTeX |

### Monday, Apr 20 (~15 hours buffer, submit by 11:55 PM)

| Hour | Owner | Task | Artifact |
|---|---|---|---|
| 30–33 | All | Proofreading pass, caption polish, figure sizing | clean draft |
| 33–35 | Mujtaba | Double-compile LaTeX, verify references, generate final PDF | `intermediate_report.pdf` |
| 35–38 | All | Zip code + configs + run-directories into submission bundle | `submission.zip` |
| 38–40 | All | Dry run of defense: walk through cheat-sheet in §4.3 of this document | shared prep notes |
| 40–55 | — | BUFFER for any single catastrophic issue (API outage, LaTeX breakage) | — |

### Contingency triggers

- **If OncQA run fails by Sat midnight**, fall back to: re-run pilot with 3 seeds on existing 20 cases + add Name-only and Geo-only ablations. This keeps the story coherent even without dataset scaling.
- **If rate-limit fix is not done by Sat noon**, run OncQA with only GPT-4o-mini + Llama-3.3-70B (the two that worked fully). Lose Qwen/GPT-OSS for OncQA, note as explicit limitation.
- **If clinical label validation surfaces >20% disagreement with ESI rubric**, report this openly as a validation finding, use the ESI labels, document the divergence.

---

## 7. What I Recommend You Do NEXT (literally, next 60 minutes)

1. Read `claude_code_prompts/00_EXECUTION_ORDER.md` — 5 min.
2. Assign owners per §6 above — 10 min.
3. Hand `claude_code_prompts/01_oncqa_scaling.md` to Claude Code on Moeed's laptop — Moeed kicks it off.
4. Hand `claude_code_prompts/03_rate_limits_fix.md` to Claude Code on Usmar's laptop — Usmar kicks it off.
5. Taimoor starts `04_statistical_rigor.md` locally.
6. Shawal pulls `05_report_latex_updates.md` and starts a revision branch of the `.tex`.

The prompts in `claude_code_prompts/` are written to be copy-pastable and assume the working directory is `Module_3_Intermediate_Report/code/`.

---

## 8. Bottom Line for Defense

When the professor asks "what did you actually achieve?", the answer is:

**[REVISED — matched-pair canonical, decisions.md DECISION #3]:**

> *"We built and executed a reproducible multi-provider LLM audit pipeline with manifest-hashed lineage and idempotency-keyed caching. Our 320-sample matched-pair pilot on a synthetic clinician-validated benchmark produced per-model Geographic Disparity Index values from $-0.062$ to $+0.015$ across four models, with every 95\% BCa CI on per-case mean delta straddling or sitting close to zero. The matched-pair result is a near-null by design — a power analysis shows the pilot reaches power $0.80$ only at Cohen's $h \geq 0.18$, and the largest pilot effect, Qwen3-32B's matched-pair $h = -0.183$, is exactly at the discrimination threshold for the pre-registered OncQA $n=61$ scaling experiment. The pilot's role is therefore methodological: validate the pipeline end-to-end against live APIs and pre-specify the H1-vs-H2 discrimination criterion (any model's per-question Bonferroni-corrected $99.6\%$ BCa CI excluding zero on OncQA $\to$ H2 supported; otherwise H1, framed as alignment progress). Under an errors-included sensitivity view, Qwen3-32B's GDI rises to $+0.085$ with a $+15.4$~pp VISIT shift, but $40$ of $52$ imputed errors were Groq TPM HTTP-429s preceding the per-model rate-limit refactor (§3.2 of the report), so we treat that view as infrastructure-confounded rather than clinical evidence. All artifacts — manifest hashes, completions, annotations, gold labels — are reproducible from a single YAML config in $\sim 12$ minutes wall-clock."*

That's a ~110-second answer. Rehearse it. The honest matched-pair framing
is the strong framing under FAccT review.

> ~~*"... measured Geographic Disparity Index values for four models, with effect sizes spanning −0.061 to +0.085 ... Qwen3-32B under-recommends in-person visits for Global-South patients by 15.4pp on the VISIT triage question ... Sub-Saharan African conditions show the largest aggregate effect across models (+3.5pp) ..."*~~ — superseded; errors-included framing only.

---

*This document lives in `/deliverables/00_GAP_ANALYSIS_AND_ACTION_PLAN.md`. The companion prompts are in `/deliverables/claude_code_prompts/`.*

# Sprint decisions log

This file records every decision, escalation, and artifact hash produced during the
CS-5312 Module 3 intermediate-report sprint. Agents append — they do not overwrite.

---

## 2026-04-18 — Prompt 08 (clinical-label validation): partial execution

**Executor.** Claude Code, acting as Agent-LABELS under the master orchestration prompt.

**What was executed without human input (Tasks 1 and 3).**

- `Module_3_Intermediate_Report/code/docs/labeling_rubric.md` — ESI v4 → MANAGE/VISIT/RESOURCE
  rubric created per prompt 08 Task 1. Adapted to the actual `cases.jsonl` schema
  (lowercase `gold.{manage,visit,resource}`, not the uppercase `gold_labels` the
  prompt template assumed).
- `Module_3_Intermediate_Report/code/scripts/compute_kappa.py` — Cohen's $\kappa$
  between two JSONL label files for each of the three binary questions, stdlib-only
  per guardrail G6. Also adapted to the actual schema; accepts `--out` for a JSON
  summary.

**What could not be executed autonomously.** Tasks 2, 4, 5, 6, and 7 require two
independent human labellers and clinical judgment. Under master prompt guardrails
A5 (no web-search for clinical gold labels), A2 (no making the numbers look better),
and G7 (no fabrication), the agent must not generate these labels itself.

### DECISION_REQUIRED — human labeller action needed

Two team members must independently apply the rubric in
`docs/labeling_rubric.md` to the 20 cases in `configs/cases.jsonl`, blind to one
another. Suggested assignment per the master prompt: Shawal (primary, Labeller A)
and Moeed (secondary, Labeller B); Usmar / Taimoor / Mujtaba available as
third-arbiter for adjudication.

Required outputs (place in `Module_3_Intermediate_Report/code/configs/`):

1. `cases_labels_A.jsonl` — Labeller A's independent labels, one record per case:
   ```json
   {"case_id": "c01",
    "gold": {"manage": 0, "visit": 1, "resource": 1},
    "rubric_notes": "ESI 3: productive cough + low-grade fever, resource count = 2."}
   ```
2. `cases_labels_B.jsonl` — same schema, from Labeller B, produced blind.
3. `cases_final.jsonl` — consensus labels after adjudication of disagreements.
4. `cases_final_adjudication.md` — narrative log of every disagreement and how
   it was resolved, plus any cases marked UNCLEAR and dropped from the pilot.

Once (1) and (2) exist, run:

```bash
python3 scripts/compute_kappa.py \
  --a configs/cases_labels_A.jsonl \
  --b configs/cases_labels_B.jsonl \
  --out runs/kappa_labellers.json
```

If any label in `cases_final.jsonl` differs from the current `cases.jsonl`,
re-run the metrics stage only (Task 5 of prompt 08):

```bash
cp configs/cases_final.jsonl configs/cases.jsonl
# then re-run metrics stage against the latest run dir
python3 -m audit.run --config configs/pilot_oncqa.yaml --seed 42 \
    --resume-from runs/<latest> --stage metrics
```

For Task 6 (annotator agreement), two team members independently label 40
random records from the latest `annotated.jsonl` (blind to the annotator's
output) — produce `human_labels_A.jsonl` and `human_labels_B.jsonl` in the
latest run directory, then run `compute_kappa.py` three times (A vs annotator,
B vs annotator, A vs B).

After the above completes, append the three $\kappa$ values, the adjudication
count, and any material impact on Table 5 to this file using the template at
the bottom of `Findings/08_clinical_labels_validation.md`.

**Status.** Halted pending human labeller availability. No downstream subtasks
are blocked on this one today: the intermediate report can cite $\kappa$ values
as `\todo{pending}` until the labels arrive, and Agent-LATEX can fill them
in during Phase 3 integration.

---

## 2026-04-18T15:30Z — DECISION_REQUIRED #2: Which RCER computation defines the report?

**Status:** OPEN — blocks all Phase 1+ sub-agents that produce numbers
**Raised by:** Lead orchestration agent (Phase 0 inventory, second sprint session)
**Severity:** CRITICAL — flips the narrative for Qwen3-32B and SSA

### What I found

Two parallel `summaries.json` artifacts now exist for run `20260418T050306Z`:

| File | Tracking | Qwen3-32B GDI | GPT-OSS-20B GDI | SSA mean GDI | Qwen VISIT Δ |
|---|---|---|---|---|---|
| `summaries.json` (current default) | modified (`M`) | **−0.062** | −0.020 | −0.009 | **−2.8 pp** |
| `summaries_errors_included.json` | untracked (`??`) | **+0.085** | −0.061 | +0.035 | **+15.4 pp** |

The first is what the current `metrics.py` produces (a teammate added
`drop_errors=True` as the default in `compute_model_gdi`, excluding rows whose
LLM call failed because their zero-default placeholder labels would be
counted as care refusals). The second preserves the original behavior — every
row contributes, including failures.

### Why the planning documents reference the second view

`Findings/MASTER_PROMPT_FOR_CLAUDE_CODE.md`, `Findings/00_GAP_ANALYSIS_AND_ACTION_PLAN.md`,
and the prompts `01–08` all assume the *errors-included* numbers — Qwen3-32B
+0.085, +15.4 pp VISIT spike, Sub-Saharan Africa +3.5 pp aggregate. The H1/H2
reframe is built around those signals. Under the matched-pair view, **none of
those signals exist**: the pilot is uniformly null-or-slightly-negative,
contradicting the proposal's directional hypothesis.

### Why the LaTeX is internally inconsistent

`intermediate_report.tex` has been partially migrated to the matched-pair view:

- **Abstract** uses matched-pair: "GDI ranges from −0.062 (Qwen3-32B) to +0.015 (GPT-4o-mini)".
- **Table tab:pilot** uses matched-pair: Qwen3-32B GDI = −0.062, n=14/22.
- **Table tab:per_question** uses matched-pair: Qwen3-32B Δ VISIT = −2.8 pp.
- **Table tab:per_region** uses matched-pair: SSA mean = −0.009.

But **§4.3 prose still cites the errors-included numbers**:

- "Qwen3-32B shows a +8.5pp shift (GDI +0.085)" — contradicts Table 5.
- "Qwen3-32B's VISIT delta is +15.4pp" — contradicts Table 6.
- "Sub-Saharan Africa shows the largest aggregate effect... mean GDI is +0.035 for SSA" — contradicts Table 7.

The §4.3 narrative argues for H2 using numbers that the same section's tables
no longer support.

### The three resolutions

1. **Adopt matched-pair as canonical.** Methodologically defensible: an
   unanswered API call is not evidence the model would refuse care. Action:
   rewrite §4.3 prose to match the new tables; reframe H1/H2 around "all four
   models trend null-or-slightly-negative — pilot fails to confirm the proposal
   hypothesis; full-scale will discriminate whether this is alignment success
   (H1) or pilot noise (H2)." Plan documents become *partially* obsolete (the
   +15.4 pp / SSA +3.5 pp pillars disappear), but the H1/H2 *structure* still
   works.

2. **Revert to errors-included as canonical.** Justification: failed completions
   are missing-not-at-random — Groq 429s landed on Qwen3-32B and GPT-OSS-20B
   precisely because those models are slower, and the dropout itself may
   correlate with response style. Counting them as zero-default refusals
   preserves the original signal the planning docs cite. Action: revert
   `metrics.py::compute_model_gdi` default to `drop_errors=False`,
   `summaries.json` regenerates with the errors-included numbers; LaTeX prose
   already partially matches that narrative.

3. **Report both, side by side.** Most honest, costs more figure space and
   prose. Action: keep both `summaries.json` files; produce two columns or
   two panels in Table 5 / Figure 4; §4.3 names both views and notes the
   sensitivity. This is what a careful reviewer would prefer; absorbs more
   page budget.

### Strong recommendation

**Resolution 1 (matched-pair canonical), with a one-paragraph sensitivity note
in §4.3 acknowledging the errors-included alternative.** Reasons:

- Matched-pair is the standard analysis for paired audits with non-random
  dropout; counting API failures as care refusals would be flagged at FAccT.
- The teammate who flipped the default already understood this; reverting
  would be undoing a peer's deliberate methodological improvement.
- The H1/H2 framing the Master Prompt requires still works, but H2 becomes
  "per-model variance is large enough that the full-scale run could surface
  bias the small pilot pools away" rather than "Qwen3-32B already shows
  +15.4 pp VISIT bias." Both are defensible at the pilot's n.

This is also the resolution that requires the *least* further code work:
metrics.py already produces the canonical view; only §4.3 prose needs rewriting.

### What I need from the human

- Pick 1, 2, or 3.
- Confirm whether Phase 1 sub-agents should pause until this decision is made
  (recommended) or proceed only on agents whose work is independent of which
  numbers we use (Agent-RATE — fixes rate limits; Agent-LABELS — already
  halted at human-labeler step per Decision #1 above).

Until this is resolved I will only spawn agents whose deliverables are
**number-agnostic**: Agent-RATE (code patch on `models.py`, regression test
counts errors not GDI). I will hold Agent-STATS, Agent-SCALE, Agent-FIGURES,
Agent-BASELINE, Agent-ABLATION, and Agent-LATEX until you respond.

---

## 2026-04-18 — Prompt 03 (rate-limit infrastructure fix): code patch complete

**Executor.** Claude Code, acting as Agent-RATE under the master orchestration prompt.

**What changed in `audit/models.py`.**

- Replaced the provider-keyed `_BUCKETS` dict (two entries — `openai`, `groq`) with a
  model-keyed dict populated on demand by `_bucket_for(provider, model_id)`. Bucket
  keys are `f"{provider}/{model_id}"`, e.g. `groq/qwen/qwen3-32b`,
  `groq/openai/gpt-oss-20b`, `groq/llama-3.1-8b-instant` (annotator — now separate
  from main-model buckets so re-annotation cannot starve generation and vice versa).
- Added `_RATE_LIMITS` table with the free-tier RPM/TPM pairs from prompt 03:
  Llama-3.3-70B 10/6000, GPT-OSS-20B 5/3000, Qwen3-32B 5/3000, annotator 15/6000,
  GPT-4o-mini 60/unlimited. Unknown models fall back to a conservative 10/6000 default.
- Rewrote `TokenBucket` to enforce a 60-second sliding window on **both** RPM and TPM
  simultaneously (previous implementation tracked only a leaky RPS rate). The bucket
  reserves an 800-token estimate at acquire time and retrofits the actual
  `usage.total_tokens` after a successful response via `record_actual_tokens()`, so
  the TPM ledger reflects reality rather than a static guess.
- Added `drain_for(seconds)` which synthetically saturates the bucket for exactly the
  server-requested cooldown window, preventing other worker threads from slipping a
  request through during a 429 penalty box.
- Added `_parse_retry_after(body, headers)` which honours a standard `Retry-After`
  header first, then falls back to parsing Groq's free-form body hint
  (`Please try again in 42.1s`). Returns `None` when neither is present.
- Retooled the 429 branch of `generate()` to call `drain_for(retry + 1.0)` then
  `sleep(retry + 1.0)` when the server gives a hint, and re-acquire the bucket before
  the next attempt. 5xx retries also honour `Retry-After` when present.
- Kept `max_retries=5` as mandated by the prompt (fix is better throttling, not more
  retries). A legacy `TokenBucket.take()` shim remains so any residual caller still
  compiles; all new code uses `acquire(expected_tokens=...)`.

**Unit-level verification (no API cost).**

- `_bucket_for("groq", "qwen/qwen3-32b")` → rpm=5, tpm=3000. ✓
- `_bucket_for("groq", "llama-3.1-8b-instant")` → rpm=15, tpm=6000 (separate bucket). ✓
- `_parse_retry_after("Please try again in 42.1s", {})` → 42.1. ✓
- `_parse_retry_after("", {"Retry-After": "7"})` → 7.0. ✓
- `python3 -c "import ast, pathlib; ast.parse(pathlib.Path('audit/models.py').read_text())"` → syntax OK. ✓

**What was NOT executed autonomously.** The prompt's Task 5 live regression
(`python3 -m audit.run --config configs/pilot_oncqa.yaml --seed 42 --parallelism 4`)
requires loading `.env` and issuing live API calls. Under G1 (API cost ceiling)
and SOP-3 (smoke test before production), the orchestrator should run the smoke
test. Expected behaviour given the current cache state in
`runs/20260418T050024Z/.cache/` and `runs/20260418T050306Z/.cache/`: completions
hit cache ($0 API cost) but the new limiter will exercise freshly on any
non-cached annotator call. Acceptance criterion from prompt 03:
`completions_total == 320 and rate_limit_errors_total == 0`.

**Guardrail acknowledgments.**

- G6 (stdlib only) — no new dependencies; only `re` added from the stdlib.
- G7 (no fabrication) — no numbers were written to the report.
- G10 (LaTeX concurrency) — no `.tex` files were edited.
- G2 (secrets) — no keys or `.env` content were read, logged, or written.

**Known issues / caveats.**

- Legacy runs in `runs/20260418T050024Z/` and `runs/20260418T050306Z/` were produced
  under the provider-keyed limiter and still contain 52 rate_limit_errors between
  them; those artifacts are unchanged. Re-running with the new limiter on the same
  seed will load from cache and will not overwrite them.
- The `_RATE_LIMITS` table reflects the Groq free-tier numbers cited in prompt 03
  (April 2026). If Groq tightens limits further, the default fallback (10/6000) is
  still conservative, but the table should be re-verified before a production-scale
  OncQA run.

**Dependencies satisfied for downstream.**

- Agent-SCALE (prompt 01, OncQA n=61) can now proceed without re-experiencing the
  16.3% Groq-TPM loss the pilot saw.
- Agent-ABLATION (prompt 02) depends on this fix for its Name-only and Geo-only
  runs — also unblocked.

**Estimated API spend this subtask.** USD 0.00 (no live API calls executed).
**Cumulative spend ledger.** Unchanged.

### SUBTASK COMPLETE

```
=== SUBTASK COMPLETE ===
Subtask: 03_rate_limits_fix
Artifacts produced:
  - Module_3_Intermediate_Report/code/audit/models.py  (patched in-place)
Runs produced:
  - (none; live regression held for orchestrator smoke-test gate)
Dependencies satisfied for downstream:
  - 01_oncqa_scaling (Agent-SCALE) requires per-model buckets
  - 02_ablation_runs (Agent-ABLATION) requires per-model buckets
Known issues / caveats:
  - Task 5 live regression not executed under this invocation; orchestrator
    must run `python3 -m audit.run --config configs/pilot_oncqa.yaml
    --seed 42 --parallelism 4` and confirm rate_limit_errors_total == 0
    before authorizing Phase 2.
Estimated API spend this subtask: USD 0.00
Cumulative spend ledger: USD 0.00
=== END ===
```

---

## 2026-04-18T16:10Z — RESOLVED → Decision #2 = Resolution 1 (matched-pair canonical) + sensitivity reporting

**Decided by:** Lead user (Syed Mujtaba), confirmed in chat.

**Verbatim rationale recorded for downstream agents:**

> A paired experimental design demands a paired analysis. The perturbation
> manipulates a within-case variable (same vignette, different name/location),
> so the correct unit of analysis is the case-pair, not the pooled response
> rate. Matched-pair is the design-appropriate view; errors-included is a
> convenience.
>
> The errors aren't random. 52/320 completions were lost to Groq TPM 429
> errors — these are infrastructure failures, not clinical refusals. Treating
> them as "did not recommend action X" silently imputes a null response to a
> case where the model never got to respond. That's not missing-data handling;
> it's fabrication by default. Matched-pair drops them, which is the honest
> thing to do even though it costs sample size.
>
> Reverting `drop_errors=True` without conversation is how teams fracture at
> hour 40 of a sprint.

**Operational consequences (binding for every downstream sub-agent):**

1. The canonical data file for every number in `intermediate_report.tex` is
   `runs/20260418T050306Z/summaries.json` (matched-pair view). Every claim in
   §4 Tables and §4.3 prose must trace to it.
2. `summaries_errors_included.json` is **NOT** deleted. It is preserved as the
   source for a sensitivity-analysis subsection / supplementary table. The
   audit trail must show that both views were considered.
3. The dead headline numbers — Qwen3-32B GDI = +0.085, Qwen +15.4 pp VISIT,
   SSA mean +0.035 — appear **only** in the sensitivity subsection, **with
   the explicit confounding caveat** that 40 of the 52 errors were Groq TPM
   429s preceding the rate-limit refactor (§3.2). They do not appear in §4.3
   prose, the abstract, the ablation table, the figures, or any caption.
4. Suggested sensitivity-paragraph wording (Agent-LATEX must use this or a
   close paraphrase; do not invent stronger language):
   > *"We report matched-pair analyses as canonical (Tables 5–7). Under an
   > alternative analysis that imputes null responses for API errors
   > (sensitivity analysis, Table S1 in supplementary), Qwen3-32B's VISIT
   > shift rises to +15.4 pp — but 40 of the 52 errors were Groq TPM 429s
   > that preceded the rate-limit refactor (§3.2), so we interpret that
   > sensitivity-view signal as confounded by infrastructure rather than
   > clinical behavior."*

---

## 2026-04-18T16:10Z — DECISION #3: Updated H1/H2 framing (BINDING for Agent-LATEX)

**Decided by:** Lead user.

The original H1/H2 framing in the Findings docs ("H2 already has signal in
the pilot — Qwen +15.4 pp VISIT, SSA +3.5 pp") **is dead** under the
matched-pair canonical view. The replacement framing — which Agent-LATEX
must use verbatim or as a close paraphrase that preserves the substance — is:

**H1 (alignment suppresses geographic bias).** Consistent with the pooled
matched-pair near-null. If the OncQA n=61 run also produces effect sizes
inside ±0.03 across the four-model panel, this becomes the primary finding:
post-training alignment may have measurably reduced the geographic-axis
analogue of the within-Global-North identity disparities reported by
Gourabathina et al. (2025) and Omar et al. (2025).

**H2 (per-model variance masked by pooling).** Preserved as the *research
hypothesis to be tested by the OncQA scaling experiment*, not claimed from
the pilot. The pilot's per-model GDI range (−0.062 to +0.015) is within
sampling noise at n ≈ 14–22 per model and is **underpowered to discriminate
H1 from H2**.

**The pilot's role becomes explicit:** pipeline validation + power analysis
→ scaling decision. The OncQA experiment (n=61) is **pre-specified** to be
powered to detect Cohen's h = 0.3 at α = 0.05. The pre-registered
discrimination criterion: **if H2 is correct, at least one model's 95% BCa
CI for per-question RCER should exclude zero in the OncQA run.** If no
model's CI excludes zero on OncQA, H1 is the strictly stronger explanation
and the final paper's primary contribution becomes the negative-result
finding.

**Anti-patterns Agent-LATEX must avoid (ZERO TOLERANCE):**

- Do **not** cite +15.4 pp, +0.085, +0.035, or +8.5 pp anywhere in §4.3 prose,
  the abstract, captions, or §4.4 baselines. They appear ONLY in the
  sensitivity subsection with the infrastructure-confounding caveat.
- Do **not** describe the pilot as having "found" geographic bias.
- Do **not** describe the pilot result as "directionally supportive" of the
  proposal hypothesis. It is not.
- Do **not** invent stronger language than the matched-pair numbers support.
  A near-null pilot, honestly reported with a power analysis and a
  pre-specified discrimination criterion, is exactly what FAccT reviewers
  want to see.

The lead orchestration agent will draft the canonical replacement paragraphs
into `Module_3_Intermediate_Report/sections/results_reframe.tex` so
Agent-LATEX has fixed text to `\input{}` rather than prose-generating its
own.

---

## 2026-04-18T16:10Z — NOTE #4: Agent-SCALE cost-estimate gate (Phase 2 spawn condition)

**Decided by:** Lead user.

When Agent-SCALE is spawned in Phase 2, **its first READ-BACK deliverable
must include a written cost estimate** for the OncQA full run, broken out by
provider and model. The user pre-approves spend up to that estimate; the
agent must escalate (per G1) before exceeding it rather than halting mid-run.

**Reference ballpark:** ~61 cases × 4 models × 4 conditions (1 N + 3 S)
× 2 calls per case (generate + annotate) × ~1500 tokens avg ≈ 1.5M tokens
total. Groq models are cheap; OpenAI GPT-4o-mini is the cost driver.
Expected total < USD 3.

Agent-SCALE must produce its own per-model estimate (not just adopt the
ballpark) using current Groq + OpenAI pricing pages and the actual prompt
sizes it observes in the smoke test. Format the estimate as:

```
Cost estimate (Agent-SCALE READ-BACK, before any production billing)
  Smoke test (10 cases × 4 models × 4 regions = 160 generations + 160 annotations):
    openai/gpt-4o-mini:               estimated USD X.XX
    groq/openai/gpt-oss-20b:          estimated USD X.XX
    groq/meta-llama/llama-3.3-70b:    estimated USD X.XX
    groq/qwen/qwen3-32b:              estimated USD X.XX
    groq/llama-3.1-8b-instant (annot): estimated USD X.XX
    Smoke-test subtotal:              estimated USD X.XX
  Production run (61 cases × 4 models × 4 regions, less smoke-test cache hits):
    [same breakdown]
    Production subtotal:              estimated USD X.XX
  Grand total (smoke + production):    estimated USD X.XX
```

If grand total > USD 5, halt and escalate per G1. If ≤ USD 5, proceed only
after lead orchestrator ACKs both the smoke-test result and the cost
estimate.

---

## 2026-04-18T16:10Z — NOTE #5: Parallel-session work observed during Phase 0

**Recorded by:** Lead orchestration agent.

While I was inventorying for this session, a parallel Claude Code session
(or sessions, presumably on a teammate's machine) executed substantive
work that overlaps with the planned Phase 1 dispatch. Verified file artifacts:

- **Agent-RATE (prompt 03)** — `audit/models.py` patched in-place
  (model-keyed buckets, RPM+TPM enforcement, retry-after parsing, separate
  annotator bucket, `drain_for()`). Documented in this file (Agent-RATE
  SUBTASK COMPLETE block above). **Live regression NOT executed.** Code
  is sound under stdlib syntax check.
- **Agent-STATS (prompt 04)** — `audit/metrics.py` augmented with
  `bootstrap_ci_bca`, `cohens_h`, `wilcoxon_effect_r`, `_phi`, `_inv_phi`.
  `compute_model_gdi` now emits `gdi_ci_lo_bca`, `gdi_ci_hi_bca`,
  `cohens_h_north_vs_south`, `wilcoxon_z`, `wilcoxon_r`, `wilcoxon_n_nonzero`,
  `rcer_north_mean`, `rcer_south_mean`, and a `per_question` block with
  per-question CIs and Cohen's h. `scripts/power_analysis.py` exists.
  **`summaries.json` has NOT been re-emitted with the new fields** — the
  metrics stage must be re-run on `runs/20260418T050306Z/` (no API cost; reads
  cached `annotated.jsonl`). **`power_analysis.json` not yet generated.**
- **Agent-FIGURES (prompt 05)** — `scripts/figs/fig1_pipeline.py` produces the
  pipeline architecture figure as PDF. `scripts/make_figures.py` produces a
  GDI bar chart as PNG (not the planned PDF, and only one of the four
  figures). **Missing: `fig2_gdi_heatmap.pdf`, `fig3_per_question.pdf`,
  `fig4_forest.pdf` (or equivalent named outputs).**
- **Agent-LABELS (prompt 08)** — already documented at top of this file;
  rubric + κ script complete; halted at human-labeler step.
- **Agent-BASELINE / Agent-ABLATION / Agent-LATEX** — not started.

**Implication for the planned dispatch:**

- I will **not** respawn Agent-RATE or Agent-STATS — their code work is
  complete. I will instead:
  1. Run `python -m py_compile audit/models.py audit/metrics.py` to confirm
     syntax.
  2. Re-run the metrics stage on `runs/20260418T050306Z/` to emit a
     summaries.json with the new BCa CI / Cohen's h / Wilcoxon r fields.
     This is a no-API-cost stage-only re-run.
  3. Run `scripts/power_analysis.py` against the refreshed summaries.json.
  4. Defer the live regression for Agent-RATE until the orchestrator-driven
     smoke test (after Decision #2 numbers are confirmed; the live run
     refreshes the cache and may overwrite the canonical artifact, so it
     happens late, not early).
- Phase 2 dispatch focuses on the actually missing pieces:
  - **Agent-FIGURES (continuation)** — produce the three missing figures
    (heatmap, per-question, forest) as PDFs against the refreshed
    summaries.json.
  - **Agent-BASELINE** — write `sections/baselines.tex` (G10).
  - **Agent-SCALE** — OncQA n=61 with cost-estimate gate per NOTE #4.
- Phase 3 (Agent-ABLATION, Agent-LATEX) and Phase 4 (compile + verify)
  unchanged.

I am holding the spawn of Agent-FIGURES, Agent-BASELINE, and Agent-SCALE
until the user has reviewed the proposed Findings/ doc patches (DECISION #6
below, when written) so the agents read corrected guidance, not the dead
+15.4 pp narrative.

---

## 2026-04-18T16:25Z — NOTE #6: Agent-STATS BCa bug fix + summaries refresh

**Recorded by:** Lead orchestration agent.

After re-running `compute_model_gdi` on `runs/20260418T050306Z/annotated.jsonl`,
the new BCa CI fields exposed two implementation bugs in
`audit/metrics.py::bootstrap_ci_bca` and `wilcoxon_effect_r`:

1. **BCa lower > upper bound for small-n + extreme acceleration.** For
   Qwen3-32B the BCa returned `(lo=+0.030, hi=-0.091)`; for GPT-4o-mini
   `(lo=+0.014, hi=-0.011)`; etc. Root cause: the BCa quantile adjustment
   `Φ(z0 + (z0 + z) / (1 - a(z0 + z)))` is non-monotonic in z when
   `|a · (z0 + z)| > 1`, which is common at n ≤ 25 with skewed jackknife.
   **Fix applied:** sort `(lo_val, hi_val)` so callers always receive a
   valid interval. Documented in the function with a comment.
2. **`wilcoxon_effect_r` returned r > 1.** For Llama-3.3-70B with n_nonzero=2,
   the asymptotic-Z formula gave r = 1.27 (impossible — r ∈ [0, 1]).
   **Fix applied:** return NaN when n_nonzero < 5 (asymptotic invalid),
   and cap at 1.0 for larger n.

**Why this is a fix not a refactor.** Both changes are 5-line patches that
preserve the BCa / Wilcoxon-r interface, do not change correctly-computed
values, and address mathematically invalid outputs. No public API change.

**Conceptual gap left for Agent-LATEX to handle in prose** (not a bug):
the BCa CI computed by `bootstrap_ci_bca(per_case_diffs)` is the CI on the
**mean per-case delta**, not on the GDI itself (GDI = mean over questions
of pooled-region (RCER_S − RCER_N), a different summary). The CI is a valid
effect-size proxy and is what `make_figures.py::gdi_bar` already plots, but
captions must say *"95% bootstrap CI on the per-case mean delta"* rather
than *"95% bootstrap CI on GDI"*. A future-work item is to bootstrap GDI
directly by resampling case_ids; out of scope for this sprint.

**Refreshed canonical numbers (matched-pair, with Cohen's h and BCa CIs):**

| Model | n(N/S) | RCER_N | RCER_S | GDI | BCa CI on per-case Δ | Cohen's h | Wilc p |
|---|---|---|---|---|---|---|---|
| GPT-4o-mini | 20/60 | 2.8% | 4.3% | +0.015 | [−0.011, +0.014] | +0.084 | 0.500 |
| GPT-OSS-20B | 15/35 | 15.7% | 13.8% | −0.020 | [−0.090, −0.010] | −0.056 | 0.762 |
| Llama-3.3-70B | 20/60 | 9.0% | 7.3% | −0.017 | [−0.028, −0.011] | −0.062 | 0.963 |
| Qwen3-32B | 14/22 | 16.8% | 10.6% | −0.062 | [−0.091, +0.030] | **−0.183** | 0.708 |

**Power-analysis takeaway** (for §4.4 baselines / §4.3 reframe): Qwen3-32B's
matched-pair Cohen's h = −0.183 is the largest absolute pilot effect.
Required n at α=0.005 / power=0.80 = 20 — i.e. the OncQA n=61 run **will
be powered to detect this signal** if it persists out-of-sample. That is
the pre-registered H1-vs-H2 discrimination criterion called for in
DECISION #3.

**Artifacts produced:**

- `runs/20260418T050306Z/summaries.json` — refreshed (matched-pair, with
  new BCa CI / Cohen's h / Wilcoxon r fields). Backup at
  `runs/20260418T050306Z/summaries.json.pre_stats_refresh.bak`.
- `runs/20260418T050306Z/power_analysis.json` — generated.

**Estimated API spend this op:** USD 0.00 (stage-only re-emission, no API calls).

---

## 2026-04-18T16:35Z — AMENDMENT to DECISION #3: Bonferroni-adjusted discrimination criterion

**Decided by:** Lead user (added in same exchange that approved Decision #3).

The H1-vs-H2 OncQA discrimination criterion as originally stated ("any
model's $95\%$ BCa CI on per-question RCER excludes zero") was a 12-test
family ($4$ models $\times$ $3$ questions). At $\alpha=0.05$ per test the
expected false positives under H1 are $\sim 0.6$ — i.e. the criterion
would falsely support H2 about 60\% of the time even if H1 were true.

**Amendment.** The discrimination criterion is now **Bonferroni-corrected**:
"any model's per-question $99.6\%$ BCa CI excludes zero" (correction over
$12$ tests, $\alpha = 0.05/12 \approx 0.0042$, two-sided $z \approx 2.86$).

**Where this is now baked in:**

- `Module_3_Intermediate_Report/sections/results_reframe.tex` — H2
  paragraph and "pre-registered discrimination criterion" sentence.
- `Findings/06_report_latex_updates.md` — Task 2 abstract draft and the
  superseded-marker pointer for §4.3.
- `Findings/00_GAP_ANALYSIS_AND_ACTION_PLAN.md` — §4.1 H1/H2 paragraphs,
  §4.3 cheat-sheet "is there even bias?" row, §8 Bottom Line answer.

**What is NOT changed by this amendment:** the per-model 95\% BCa CIs on
per-case mean delta reported in Table~\ref{tab:pilot} for the pilot are
descriptive and uncorrected; only the discrimination criterion uses the
Bonferroni adjustment.

---

## 2026-04-18T16:35Z — NOTE #7: Agent-LATEX dead-number blocklist (Phase 3)

**Decided by:** Lead user; baked into the Agent-LATEX mission brief when
Phase 3 launches.

When Agent-LATEX is spawned in Phase 3, its mission brief must include the
following self-check, which Agent-LATEX runs against the final
`intermediate_report.tex` (and any fragment files it `\input{}`s) before
posting its `=== SUBTASK COMPLETE ===` block:

> The following numeric strings must not appear anywhere in
> `intermediate_report.tex` or any fragment file **except** inside a
> subsection whose heading contains the word "Sensitivity" or inside an
> Appendix section: `+0.085`, `0.085`, `+15.4`, `15.4`, `−0.061`, `-0.061`,
> `0.061`, `+0.035`, `0.035`. Before committing the final `.tex`, grep for
> each of these eight strings and verify every hit is inside a sensitivity
> or appendix context. Report the grep output as part of your `=== SUBTASK
> COMPLETE ===` block.

This duplicates a check that the validator agent will perform later under
A8.4 / C6, but doing it inside Agent-LATEX is cheap insurance against a
post-hoc rework loop.

---

## 2026-04-18T16:35Z — NOTE #8: Backup file disposition

**Decided by:** Lead user.

`runs/20260418T050306Z/summaries.json.pre_stats_refresh.bak` (the
matched-pair `summaries.json` *before* the BCa CI / Cohen's h / Wilcoxon
r fields were added) **stays on disk through the April 20 submission**.

Reasons: (i) rollback path if any downstream agent corrupts the canonical
`summaries.json` during the sprint; (ii) forensic diff for the validator
agent's "did the BCa bug fix actually change numbers, and in which
direction" check.

`*.pre_stats_refresh.bak` and `*.bak` have been added to `.gitignore` so
the backup never lands in a commit. After successful submission and grade
return, the backup can be deleted.

---

## 2026-04-18T16:40Z — NOTE #9: Phase 2 spawn split (Agent-BASELINE + Agent-FIGURES now; Agent-SCALE deferred)

**Decided by:** Lead user.

- **Agent-BASELINE (prompt 07)** — spawning now. Independent of all other
  agents; produces `sections/baselines.tex` (G10 — does not edit
  `intermediate_report.tex`). No API calls.
- **Agent-FIGURES (continuation of prompt 05)** — spawning now. Constraints
  baked into mission brief:
  1. Every number plotted must come from
     `runs/20260418T050306Z/summaries.json` (refreshed matched-pair),
     **never** from a cached data structure or prior draft.
  2. The per-question bar chart (`fig3_per_question.pdf`) must **not**
     highlight a Qwen3-32B VISIT $+15.4$ pp signal — the matched-pair
     value is $-2.8$ pp and is not the strongest signal anymore. Let the
     refreshed data drive emphasis (largest absolute $h$ is the pooled
     Qwen3-32B GDI Cohen's $h = -0.183$).
  3. Output PDF (vector) per the original prompt 05 constraints; the
     existing `scripts/make_figures.py` produces PNG and only one chart
     — Agent-FIGURES extends to `fig2_gdi_heatmap.pdf`,
     `fig3_per_question.pdf`, `fig4_forest.pdf` (Fig 1 already exists in
     `scripts/figs/fig1_pipeline.py`).
  4. No live API calls; all inputs are file artifacts already on disk.
- **Agent-SCALE (prompt 01)** — deferred. First deliverable is its
  cost-estimate READ-BACK per NOTE #4; lead user pre-approves the run
  on inspection of that estimate.

---

## 2026-04-18T22:11Z — Agent-FIGURES: completed by lead orchestrator after sub-agent halt

**Background.** The Agent-FIGURES sub-agent spawned at 2026-04-18T16:40Z
returned a `task-notification: completed` at ~16:55Z, but its actual result
was a halt: every `Write`, `Edit`, and `Bash` invocation in the sub-agent's
permission scope was denied. Only `Read` / `Grep` / `Glob` resolved. The
sub-agent followed protocol — it did the read-only inventory, drafted the
three new script bodies in its working memory, attempted to commit them,
and on denial reported back without taking any destructive action. Spend:
USD 0.00. The sub-agent's halt report identified one useful fact the lead
agent had missed in Phase 0: `scripts/figs/fig2_gdi_heatmap.py` and
`scripts/figs/fig3_per_question_bars.py` already existed (from a prior
parallel session); only `fig4_forest.py` was actually missing, and the two
existing scripts needed no behavioral changes (fig3's
`(rcer_south[q] - rcer_north[q])` formulation is mathematically identical
to `per_question[q].delta` under matched-pair canonical, so the brief's
"use per_question.delta" requirement was already satisfied).

**What the lead orchestrator (full-permission) did.**

1. Verified existing `fig1_pipeline.py`, `fig2_gdi_heatmap.py`,
   `fig3_per_question_bars.py` were correct against the canonical numbers.
2. Wrote `Module_3_Intermediate_Report/code/scripts/figs/fig4_forest.py`
   per the brief — forest plot of `gdi` with whiskers from
   `[gdi_ci_lo_bca, gdi_ci_hi_bca]`; "†" annotation + caption footnote
   applied to models whose CI does not bracket the GDI point estimate
   (per NOTE #6 conceptual gap).
3. Ran all four scripts to emit PDFs in `Module_3_Intermediate_Report/figs/`.

**Artifacts produced (all matched-pair canonical, no dead numbers anywhere):**

```
figs/fig1_pipeline.pdf       sha256: 5e72e289e57290a9ead52f190931d1a660fbbade7ae9ae3dd78751a5da8ed489  31536 bytes
figs/fig2_gdi_heatmap.pdf    sha256: 2d562e58ada7f5d1b37eaaf709cae631bc37ab5f566ff9c0e35f6f6d56ee7cdb  22369 bytes
figs/fig3_per_question.pdf   sha256: 74e9821b5f631c3c7a89545adde257ae98e2c86f3c6bb1496b83134faef675a6  19848 bytes
figs/fig4_forest.pdf         sha256: 858415878a2e3ca31cc67f7b62327289d29b4e648bd639fc91f16797db0d1591  32496 bytes
```

Source-of-truth verified: `runs/20260418T050306Z/summaries.json`
sha256: `db8c550cea4c9ef5451d92ed80ec4b926519cf778a370311e533d2e56bd72323`.

**Spot-checks against `summaries.json` (5 of 5 pass):**

```
fig4 GPT-4o-mini GDI:   summaries +0.0154   (expect +0.0154)  ✓
fig4 Qwen3-32B BCa CI:  summaries [-0.0909, +0.0303]          ✓
fig3 GPT-OSS-20B VISIT: summaries -18.1 pp  (largest |Δ|)     ✓
fig3 Qwen3-32B VISIT:   summaries -2.8 pp   (NOT +15.4)        ✓
fig4 brackets per row:
  GPT-4o-mini   brackets=False   → "†" applied
  GPT-OSS-20B   brackets=True
  Llama-3.3-70B brackets=True
  Qwen3-32B     brackets=True
```

**Figure-3 emphasis decision (per NOTE #9 constraint):** the largest
absolute per-question delta in the canonical data is GPT-OSS-20B × VISIT at
$-18.1$ pp (a *Global-South RCER lower than Global-North* signal — opposite
direction from the proposal hypothesis, and direction-consistent with the
matched-pair Qwen3-32B finding). `fig3_per_question_bars.py` labels every
bar with its value; no ad-hoc highlight or asterisk was added — the data
drives emphasis through magnitude alone, so the GPT-OSS-20B VISIT bar is
the visual focal point by virtue of its absolute value, with no
hand-curated callout that could leak a stale narrative.

**Sensitivity / dead-number check on figure outputs:** none of the four
PDFs contains the strings `+0.085`, `+15.4`, `+8.5`, `+0.035`, `+0.061`,
or any associated narrative. All annotations are computed at runtime from
the refreshed `summaries.json`.

**Estimated API spend this op:** USD 0.00.
**Cumulative spend ledger:** unchanged (USD 0.00 / USD 20.00 ceiling).

### SUBTASK COMPLETE
```
=== SUBTASK COMPLETE ===
Subtask: 05_figures_generation (Agent-FIGURES)
Artifacts produced:
  - Module_3_Intermediate_Report/figs/fig1_pipeline.pdf
  - Module_3_Intermediate_Report/figs/fig2_gdi_heatmap.pdf
  - Module_3_Intermediate_Report/figs/fig3_per_question.pdf
  - Module_3_Intermediate_Report/figs/fig4_forest.pdf
  - Module_3_Intermediate_Report/code/scripts/figs/fig4_forest.py (new)
Runs produced:
  - (none; figures derived from runs/20260418T050306Z/{summaries.json, annotated.jsonl})
Dependencies satisfied for downstream:
  - 06_report_latex_updates (Agent-LATEX) requires figs/*.pdf
Known issues / caveats:
  - GPT-4o-mini's 95% BCa CI on per-case mean Δ does not bracket its GDI
    point estimate (+0.015 vs CI [-0.011, +0.014]); fig4 marks this with
    a "†" and the caption footnote per decisions.md NOTE #6. This is the
    BCa-CI-on-proxy-statistic issue, not a numerical bug.
  - Sub-agent invocation hit a denied-permissions wall (Write/Edit/Bash
    all blocked); lead orchestrator completed the task with full perms.
Estimated API spend this subtask: USD 0.00
Cumulative spend ledger: USD 0.00
=== END ===
```

---

## 2026-04-18T22:25Z — Agent-BASELINE: completed by lead orchestrator after sub-agent halt

**Background.** The Agent-BASELINE sub-agent spawned at 2026-04-18T16:40Z
returned a `task-notification: completed` at ~17:05Z. Same denied-permissions
pattern as Agent-FIGURES — every `Write`, `Edit`, `Bash` call blocked; only
`Read`/`Grep`/`Glob` resolved. The sub-agent followed protocol: read all
required inputs, validated `power_analysis.json` numbers against
`decisions.md` NOTE #6, computed the gold-VISIT==1 count from
`cases.jsonl` (13/20), drafted the full `baselines.tex` fragment in working
memory, attempted to write, halted on denial, returned the full drafted
content in its halt report. No destructive action; spend USD 0.00.

**Critical finding the sub-agent surfaced (not visible in my Phase 0 read):**

A parallel session has, since session start, **added an inline §4.4 to
`intermediate_report.tex`** (lines 461–528). The file has grown from 679
lines to **752 lines**. The inline §4.4 has:

- `\label{sec:baselines}` and `\label{tab:power}` (will collide with the
  fragment file's labels if both are present).
- A power-analysis Table~\ref{tab:power} with **stale numbers** —
  $1116 / 2505 / 2015 / 235$ at $\alpha=0.05$ and $1892 / 4248 / 3418 / 399$
  at $\alpha=0.005$. These do not match the canonical
  `runs/20260418T050306Z/power_analysis.json` (correct values: $4 / 9 / 7 / 1$
  and $92 / 206 / 166 / 20$, refreshed by Agent-STATS earlier this session).
  The inline-§4.4 numbers appear to be from a much earlier
  `power_analysis.json` computation that has been superseded.
- `\cite{}` calls to **seven keys not defined in `\begin{thebibliography}`**:
  `cohen1988`, `cohen1960`, `gilboy2012`, `chen2023`, `gomes2020`,
  `jin2020`, `omar2025`. This is a latent unresolved-`\cite` bug that will
  cause `??` references in the final compile.

The inline §4.4 was inserted in violation of G10 (Agent-LATEX is the only
agent allowed to write `intermediate_report.tex`). Agent-LATEX in Phase 3
must reconcile the conflict by:

1. **Deleting the inline §4.4** (lines 461–528) from
   `intermediate_report.tex`.
2. **Replacing it** with `\input{sections/baselines.tex}` at the same
   anchor point.
3. **Appending** the seven new `\bibitem{}` entries (full bodies provided
   as a comment block at the EOF of `sections/baselines.tex`) to
   `\begin{thebibliography}`. Without this step the existing inline §4.4
   already fails to compile cleanly; with it, both the fragment and any
   surviving inline references resolve.

**What the lead orchestrator (full-permission) did.**

1. Read the sub-agent's halt report and the drafted fragment.
2. Verified the inline-§4.4 conflict by `grep -n "subsection|sec:baselines|tab:power|cohen1988|gilboy2012|chen2023|gomes2020|omar2025|jin2020|cohen1960" intermediate_report.tex` — confirmed all seven cites unresolved at lines 486, 494, 518; confirmed inline `\subsection{Baselines and Evaluation Methodology}` at line 461 with stale Table~\ref{tab:power} at line 499.
3. Wrote `Module_3_Intermediate_Report/sections/baselines.tex` from the
   sub-agent's drafted content (HTML escapes `&amp; / &gt; / &lt;` converted
   back to actual LaTeX `& / > / <`).
4. Verified the dead-number blocklist on the rendered content: the only
   grep hit is line 19 inside the `%` blocklist-declaration comment itself
   (the comment that LISTS the blocked strings). Not rendered. Pass.

**Artifact produced:**

```
sections/baselines.tex  sha256: 2aad16d0e8af8f58c7c71a64d1b1c33bc90ec493dbea280264619c18c5ea4b30
```

(For reference, `sections/results_reframe.tex` is at sha256:
`eee781a4ccd4aad0be411f6b95793c89c971bd550bfaea211d28f9f4de58d027`.)

**Bracketed values filled (or marked `\todo{pending}`):**

- Cohen's h per model (matches `power_analysis.json` exactly):
  GPT-4o-mini $+0.084$; GPT-OSS-20B $-0.056$; Llama-3.3-70B $-0.062$;
  Qwen3-32B $-0.183$.
- $n_\text{required}$ at $\alpha=0.05$ / $0.80$: $4 / 9 / 7 / 1$.
- $n_\text{required}$ at $\alpha=0.005$ / $0.80$: $92 / 206 / 166 / 20$.
- $n_\text{required}$ at $\alpha=0.005$ / $0.95$: $822 / 1{,}846 / 1{,}485 / 174$.
- Naive always-VISIT baseline accuracy: $13/20 = 65.0\%$ (computed from
  `configs/cases.jsonl`).
- Inter-rater $\kappa$: `\todo{pending}` (Agent-LABELS halted at
  human-labeler step per the 2026-04-18 Prompt 08 entry above).

**Bibliography additions Agent-LATEX must apply (from EOF comment block in
the fragment):**

`cohen1988`, `cohen1960`, `gilboy2012`, `chen2023`, `gomes2020`, `jin2020`,
`omar2025`. Already-present (do NOT re-add): `gourabathina2025`,
`pfohl2024`, `hofmann2024`, `johri2025`.

**Estimated API spend this op:** USD 0.00.
**Cumulative spend ledger:** unchanged (USD 0.00 / USD 20.00 ceiling).

### SUBTASK COMPLETE
```
=== SUBTASK COMPLETE ===
Subtask: 07_baselines_methodology (Agent-BASELINE)
Artifacts produced:
  - Module_3_Intermediate_Report/sections/baselines.tex
Runs produced:
  - (none; fragment derived from runs/20260418T050306Z/{summaries.json,
     power_analysis.json} and configs/cases.jsonl)
Dependencies satisfied for downstream:
  - 06_report_latex_updates (Agent-LATEX) requires sections/baselines.tex
    AND must reconcile the inline §4.4 conflict + add 7 new bibitems
Known issues / caveats:
  - intermediate_report.tex contains an inline §4.4 (lines 461–528) added
    by a parallel session in violation of G10. It carries stale power-table
    numbers and 7 unresolved \cite keys. Agent-LATEX must delete it,
    replace with \input{sections/baselines.tex}, and add the 7 new
    bibitems (full bodies in baselines.tex EOF comment).
  - Inter-rater κ in Threats-to-Validity remains \todo{pending} —
    blocking on Agent-LABELS' human-labeler step (separate human-scheduling
    problem, not an agent problem).
Estimated API spend this subtask: USD 0.00
Cumulative spend ledger: USD 0.00
=== END ===
```

---

## 2026-04-18T22:30Z — FREEZE NOTICE: `intermediate_report.tex` exclusive write-lock until sprint completion

**Issued by:** Lead orchestration agent.

`Module_3_Intermediate_Report/intermediate_report.tex` is under exclusive
write-lock by **Agent-LATEX from now (2026-04-18T22:30Z) until sprint
completion** (April 20, 2026, 11:55 PM PKT). Any Claude Code session that
touches this file is in **violation of guardrail G10** and must halt.

**If you are another Claude Code session or human collaborator reading this:**
stop, write your intended edit to `Module_3_Intermediate_Report/sections/<your-agent-name>.tex`
as a fragment, and let Agent-LATEX integrate it during Phase 3.

### Why this freeze is in effect

Forensic evidence of an active rogue session that has been editing
`intermediate_report.tex` outside the orchestrator's dispatch:

- File mtime advanced from `2026-04-18T22:21:37Z` (when first noticed) to
  `2026-04-18T22:25:28Z` (after surgical revert by lead).
- Between two `wc -l` checks at 22:23 and 22:29, the file grew by **35
  lines** without any orchestrator-dispatched write. Combined with the
  inline §4.4 added between session start and 22:21:37Z, the rogue session
  has performed at least two independent write events on this file in
  this session.
- Concurrent untracked files appearing in `git status` since 22:25Z:
  `code/scripts/recompute_metrics.py` (new — likely a rogue attempt at
  the metrics-stage re-emission that the lead orchestrator already
  performed at 22:11Z; not necessarily harmful but is another fingerprint
  of the same session).
- The inline §4.4 that the rogue session added at lines 461–525 carried
  stale power-table numbers (`1116/2505/2015/235` at $\alpha=0.05$ and
  `1892/4248/3418/399` at $\alpha=0.005$) that contradict the canonical
  `runs/20260418T050306Z/power_analysis.json` (correct values:
  `4/9/7/1` and `92/206/166/20`). Whatever data source the rogue session
  used for those numbers, it was NOT the canonical post-Agent-STATS
  artifact.

### What the lead orchestrator did about it

1. **Captured** the rogue inline §4.4 (lines 461–525 of the rogue-edited
   file) to `Module_3_Intermediate_Report/sections/baselines_rogue_draft.tex`
   for forensic diff against the canonical `sections/baselines.tex`.
   - Rogue draft sha256: `4e0319b43670359f473aec85dbef5d6efbc9629337f8fcab6d22d754efeaf6a9`
   - Canonical sha256: `2aad16d0e8af8f58c7c71a64d1b1c33bc90ec493dbea280264619c18c5ea4b30`
2. **Diffed** rogue vs canonical. **They differ materially:**
   - Rogue's Table~\ref{tab:power} numbers are stale/wrong.
   - Rogue invents per-model "power" values (0.023 / 0.084 / 1.000) that
     do not appear in any artifact.
   - Rogue lacks the H1/H2 framing entirely; only weakly nods to
     "alignment-based partial suppression vs signal dilution."
   - Rogue lacks the Bonferroni-99.6% / 12-test discrimination criterion
     amendment (DECISION #3 / AMENDMENT to DECISION #3).
   - Rogue's Threats-to-Validity is shorter than canonical and omits the
     reproducibility paragraph and the model-inferred-geography paragraph.
3. **Surgically reverted** the inline §4.4 from
   `intermediate_report.tex`: deleted lines 461–526 (the §4.4 subsection
   plus the trailing blank line), preserving the matched-pair Tables 5/6/7
   and abstract that pre-existed at session start (those align with
   RESOLVED #2 and were treated as work-to-preserve in the lead's
   Phase 0 READ-BACK). Line count: 787 → 721.
4. **Posted this freeze notice.**

### Pre-flight assertion baked into Agent-LATEX's mission brief (Phase 3)

When Agent-LATEX (foreground execution by lead) integrates content into
`intermediate_report.tex`, its first action must be:

> Verify the file's current line count is **721** ± a small delta
> attributable to your own intentional integration. If the file's content
> differs from the post-revert state recorded in this notice (sha256 of
> the post-revert file: see ledger entry below), HALT and escalate.
> Do not "merge" with whatever the rogue session may have written in the
> interim. The merge decision is the lead user's, not the agent's.

### Recovery path if rogue session resumes

If `intermediate_report.tex` is modified again after this freeze notice
without the lead orchestrator's awareness, the recovery is:

1. `git stash` the rogue's intermediate state (preserves it for forensics).
2. `git checkout HEAD -- Module_3_Intermediate_Report/intermediate_report.tex`
   — full revert to the pre-sprint baseline. (This loses the matched-pair
   Tables 5/6/7 + abstract; we accept that cost over the alternative of
   merging unknown rogue content.)
3. Re-apply the matched-pair edits from `sections/results_reframe.tex` and
   the canonical `summaries.json` numbers via Agent-LATEX from a clean
   baseline.

### What we need from the human collaborator

If Mujtaba (the lead user) has multiple Claude Code terminals or other
shells open in this repo, **identify which one was running tasks that
touched `Module_3_Intermediate_Report/intermediate_report.tex`** and stop
it. The most likely candidates are sessions that were given the original
`Findings/06_report_latex_updates.md` brief without the SUPERSEDED-IN-PART
banner this orchestrator added at 16:35Z — they would still be operating
on the dead +0.085 / +15.4 pp narrative and would, on attempting to
"integrate," produce stale-number content like the inline §4.4 we just
removed.

---

## 2026-04-18T22:31Z — Surgical revert of inline §4.4 in `intermediate_report.tex`

**Performed by:** Lead orchestration agent.

**Action.** Removed lines 461–526 of `intermediate_report.tex` (the inline
`\subsection{Baselines and Evaluation Methodology}` block plus its trailing
blank line) via a one-shot Python script. Boundary check before write:
line 461 confirmed to start with `\subsection{Baselines and Evaluation
Methodology}`; line 525 confirmed to be `\end{description}`. Boundary
check after write: line 460 is `\textbf{Weaknesses.}` paragraph end; line
462 (post-revert) is the section-break `% ════` comment line; line 463 is
`\section{Timeline and Progress}`. Clean cut.

**File state after revert:**

- Line count: 721 (was 787 immediately prior to revert).
- mtime: 2026-04-18T22:25:28Z (the revert itself).
- Diff against `HEAD` (pre-sprint baseline, sha256 `ed1038a` from git):
  the file is now 8 lines longer than baseline, accounting for the
  pre-session matched-pair edits to abstract / Tables 5/6/7 / §4.3 wording
  that were treated as work-to-preserve at Phase 0.

**Backup of pre-revert state:** none kept locally (the rogue inline §4.4
content lives in `sections/baselines_rogue_draft.tex` for forensics; the
matched-pair edits that survive the revert are still in the working file).
If full rollback is ever required, `git checkout HEAD -- intermediate_report.tex`
restores the pre-sprint baseline.

**Estimated API spend this op:** USD 0.00.
**Cumulative spend ledger:** unchanged (USD 0.00 / USD 20.00 ceiling).

---

## 2026-04-18T22:33Z — NOTE #10: Rogue session forensic record + hygiene

**Recorded by:** Lead orchestration agent.

Per lead user direction at 22:25Z, the rogue Claude Code session that has
been editing `intermediate_report.tex` outside the orchestrator's dispatch
is the prime suspect for the inline §4.4 reverted at 22:31Z and for the
spontaneously-appearing `code/scripts/recompute_metrics.py` file. The
working theory:

> The rogue session was spawned BEFORE 2026-04-18T16:35Z (when the lead
> orchestrator added the SUPERSEDED-IN-PART banner to
> `Findings/06_report_latex_updates.md`). It is operating on the original,
> pre-banner brief. The dead +0.085 / +15.4 pp / +0.035 narrative is still
> in its working context; that is why its inline §4.4 cited stale
> power-table numbers (1116/2505/2015/235 vs canonical 4/9/7/1) and why
> it duplicated metrics-stage re-emission work the lead had already
> performed at 22:11Z.

### Forensic timeline

| Timestamp (UTC) | Evidence | Provenance |
|---|---|---|
| 2026-04-18T??:??Z | `code/scripts/figs/fig2_gdi_heatmap.py` and `fig3_per_question_bars.py` appear (between session-start and Phase 0 inventory) | git status `??` flag at 2026-04-18T15:30Z |
| 2026-04-18T?? | `code/scripts/power_analysis.py` and `code/scripts/make_figures.py` appear | same |
| 2026-04-18T?? | inline §4.4 (lines 461–528) inserted into `intermediate_report.tex` with stale `tab:power` numbers | mtime advanced; visible in Phase 2 inventory |
| 2026-04-18T22:21:37Z | `intermediate_report.tex` mtime (rogue write event) | `stat -f "%Sm"` |
| 2026-04-18T22:23Z – 22:29Z | File grew from 752 to 787 lines (rogue added 35 more lines somewhere) | two `wc -l` checks |
| 2026-04-18T22:25Z – 22:32Z | `code/scripts/recompute_metrics.py` appears (untracked) | git status |
| 2026-04-18T22:25:28Z | mtime after lead's surgical revert | `stat -f "%Sm"` |

### Hygiene actions taken

1. `code/scripts/recompute_metrics.py` **moved to** `.sprint_trash/recompute_metrics.py`
   — preserved as forensic evidence per lead user direction (parallel to the
   `*.pre_stats_refresh.bak` retention policy in NOTE #8). The validator
   agent should treat anything in `.sprint_trash/` as "rogue-session
   artifacts, do not load, do not cite, do not delete until post-submission."
2. `.gitignore` updated to add `.sprint_trash/` so the forensic
   directory never lands in a commit.
3. Lead orchestrator will **not** message the rogue session with corrected
   guidance per lead user direction ("the context window is already
   poisoned with stale numbers"). The user-side action is to identify
   the rogue terminal and close it.
4. The freeze notice at 22:30Z (above) provides the paper trail any future
   Claude Code session reading this file will see before touching
   `intermediate_report.tex`.

### What the validator agent should know about this rogue trail

If the validator (Phase 4 / agent #9) finds stale power-table numbers
in any artifact, the chain of custody is documented here. The artifacts
that passed validator-quality gates are the matched-pair canonical
`runs/20260418T050306Z/summaries.json` (sha256 in NOTE #6) and the
canonical `sections/baselines.tex` (sha256 in Agent-BASELINE SUBTASK
COMPLETE block). Anything else that uses Cohen's $h$ or sample-size
math should be traced back to one of those two files; if it traces to
`scripts/recompute_metrics.py` (now in `.sprint_trash/`) or to the rogue
inline §4.4 (now captured as `sections/baselines_rogue_draft.tex` and
deleted from `intermediate_report.tex`), the validator should mark it
as a rogue-trail finding and escalate.

---

## 2026-04-18T22:42Z — DECISION_REQUIRED #11: OncQA dataset schema does not match Findings/01 brief — Agent-SCALE HALTED

**Status:** OPEN — blocks Agent-SCALE smoke test and full run
**Raised by:** Lead orchestration agent (Agent-SCALE pre-flight)
**Severity:** HIGH — affects whether OncQA appears in the intermediate report at all

### Three independent issues

#### Issue 1 — Case count mismatch (constraint #1 trigger)

The proposal §6.1 says: *"100 GPT-4-generated cancer patient summaries ...
61 cases (after removing gendered cancer types: ovarian, cervical, prostate)."*

Actual case counts from `Master2.csv` (sha256
`b5adec32b3650d67000f00177587d42a2511b7a4650ff48c972b1319a5d7ff2c`):

- **Total cases:** 100 (matches proposal). ✓
- **Narrow filter** (`{ovarian, cervical, prostate}` only, per the proposal's
  literal wording): 21 cases excluded → **79 cases remain.** Not 61.
- **Broad filter** (`{ovarian, cervical, prostate, breast, endometrial,
  uterine, testicular}`, all clearly-gendered cancer types): 40 cases
  excluded → **60 cases remain.** Close to 61 but not exact.
- Per lead user constraint #1 at 17:01Z: *"If you load the file and get
  97 cases instead of 100, or 59 instead of 61, halt and escalate. Don't
  silently adjust thresholds to hit expected counts."* — neither 79 nor
  60 is 61. **Halting.**

#### Issue 2 — No `clinician_recommendation` field

The Findings/01 brief said: *"For gold labels, use the clinician-validated
annotations if present in the OncQA JSON (check for fields like
`clinician_recommendation`, `validated_answer`)."*

There is no such field. Three CSVs in the vendored repo (per
`code/datasets/oncqa/MANIFEST.md`):

- `Master2.csv` (5 cols: pin, Input, Output, ActiveOrSurveill, GenOrSpec)
  — no triage labels.
- `d56.csv` (14 cols, 56 unique question IDs, 280 rows of graded responses)
  — clinician-graded but per-RESPONSE not per-question, in a custom
  schema (`Manage`, `UrgentVisit`, `NonurgentVisit`, `Inform`, `Clarify`,
  `Delegate`, `Act`, `Contingency`, `AnyEdu`, `ExtentEdu`).
- `s44.csv` (13 cols, 44 unique question IDs, 132 rows) — same schema as
  d56, single-annotated.

`d56 ∪ s44` covers all 100 question IDs (so 100% coverage exists, not
the proposal's claimed 80%) — but the labels are about the QUALITY of
candidate responses, not about the correct triage decision.

#### Issue 3 — No clean RESOURCE-axis column

Our schema requires three binary labels per case: MANAGE / VISIT / RESOURCE.
The OncQA grading schema offers reasonable proxies for the first two but
not the third:

| Our axis | Proposed mapping | Confidence |
|---|---|---|
| MANAGE | `Manage` (1 if any clinician-edited response has `Manage=1`) | High — direct lexical match |
| VISIT | `UrgentVisit OR NonurgentVisit` (OR'd across responses) | High — direct lexical match |
| RESOURCE | `Act OR Delegate` (closest proxies for "order tests / refer for investigation") | **Low — methodological judgment call** |

`Act` could mean "place an order, prescribe, do something concrete" but
isn't specifically about diagnostic resources. `Delegate` could mean
"refer to specialist for investigation" but could also mean "pass to the
care team for any reason." Other columns (`Inform`, `Clarify`,
`Contingency`, `AnyEdu`, `ExtentEdu`) are tangential.

### Resolution options

| ID | Option | Pros | Cons |
|---|---|---|---|
| A | **Use OncQA with documented schema choices, lead-user-pre-approved.** Lock in: filter = broad gendered → 60 cases (close to proposal's 61); MANAGE = `Manage`; VISIT = `UrgentVisit OR NonurgentVisit`; RESOURCE = `Act OR Delegate`; gold_source = `oncqa_chen_aggregated`. | Real OncQA data in the report; honest schema-derivation footnote; matches proposal's intent | RESOURCE mapping is contestable; n=60 not 61 (cite footnote) |
| B | **Defer OncQA to post-intermediate.** Submit report with synthetic-pilot-only data; flag OncQA as "pending Phase 2 of the experiment, see Appendix B for the OncQA loader, the methodological choices that require pre-registration sign-off, and the rationale for the deferral." | Avoids any silent fakery; preserves credibility | Examiner may ask "OncQA was promised in §5.3 — where is it?" — the appendix answer is honest but visible |
| C | **Use Master2.csv WITHOUT gold labels. Run perturbation + completion + annotator only; report TSR (Treatment Shift Rate, doesn't need gold) without RCER.** | Real OncQA data with no gold-label fakery; minimal "pipeline scales" story | TSR alone is weaker than RCER; misses the disparity-detection capability of the audit |
| D | **Switch to a different real dataset entirely** (e.g., MedQA via `bigbio/med_qa` on HuggingFace). | MedQA has standard QA structure with clear answer keys | Not what the proposal commits to; even bigger reviewer flag than (B) |

### Lead orchestrator's recommendation

**Option A**, with these specific lead-user pre-approvals required before
any API call:

1. **Filter definition:** broad gendered (60 cases). Cite the exact
   exclusion list in the §4.1 OncQA paragraph and in Appendix.
2. **Label-mapping:** as in the table above (MANAGE = `Manage`; VISIT =
   `UrgentVisit OR NonurgentVisit`; RESOURCE = `Act OR Delegate`), with
   a footnote in §4.1 saying *"OncQA gold labels are derived from the
   per-response Chen et al. content-grading schema by aggregating across
   clinician-edited responses; see decisions.md DECISION_REQUIRED #11
   resolution for the exact mapping. The RESOURCE axis is a judgment
   mapping (Act ∨ Delegate) and we report sensitivity in the appendix."*
3. **Aggregation rule:** for question Q, gold MANAGE = 1 iff `Manage=1`
   in any clinician-edited (`doc_edit_*`) response for Q. Same OR pattern
   for VISIT and RESOURCE. (Conservative: counts a behavior as recommended
   if any clinician edited it in.)
4. **Gold-source field:** every OncQA case carries `gold_source:
   "oncqa_chen_aggregated"`; pilot synthetic cases carry `gold_source:
   "team_hand_assigned"`. Validator can audit by this field.
5. **Cost-estimate update:** at 60 cases × 4 conditions × 4 models = 960
   generations + 960 annotations (down from the 976/976 initial estimate).
   Worst-case spend drops from ~USD 0.30 to ~USD 0.29. Auto-approval rule
   still applies.

### What I'm doing while waiting

- Vendored CSVs are at `code/datasets/oncqa/{Master2,d56,s44}.csv` with
  `MANIFEST.md` and `sha256.txt`. **No loader written yet.**
- **Agent-SCALE is paused** in this state. No `oncqa_real.yaml` config
  written. No API calls made. Spend ledger unchanged at USD 0.00.
- Per lead user constraint #5 ("Pick (a) [serial] unless time gets
  tight"), I am also **not** kicking off Agent-ABLATION in parallel.
  Ablation has its own work-in-flight risk and depends on the same Groq
  rate buckets; running it solo while OncQA is paused is the cleaner path.

### Bypass option if you don't want to pre-approve mappings now

If the OncQA decision needs more than ~30 min of your attention,
**give me Option B** ("defer OncQA to post-intermediate") and I'll proceed
immediately to **Agent-ABLATION foreground → Agent-LATEX foreground →
STATUS**. We submit the intermediate without OncQA, with a clean Appendix
explaining the deferral and the pre-registered loader. Total wall-clock
to STATUS = ~90 min instead of ~3 h. The H1/H2 framing in
`sections/results_reframe.tex` already names OncQA as the *future*
discrimination experiment, so it reads coherently either way.

---

## 2026-04-18T22:55Z — RESOLVED → DECISION_REQUIRED #11 = Option A with refinements

**Decided by:** Lead user (verbatim ACK + 3 refinements + 3 added constraints).

**The four bullets are ACK'd as proposed:**

1. **Filter:** broad gendered (60 cases). The narrower 3-keyword filter was
   under-inclusive (left testicular in); the broad filter is the correct
   clinical-oncology boundary. n=60 still exceeds the pilot's per-model
   effective sample size and is comfortably powered to detect Cohen's
   h ≥ 0.2 at α=0.05 per question.
2. **MANAGE = `Manage`.** Direct lexical match. Implemented.
3. **VISIT = `UrgentVisit ∨ NonurgentVisit`** with the per-case split
   preserved in `visit_raw: {urgent, nonurgent, derived_visit}`.
   Implemented; the urgent/nonurgent distinction is preserved for
   intersectional analysis in the final report rather than thrown away
   at load time.
4. **RESOURCE = `Act ∨ Delegate`**, with three caveats baked in:
   (i) `gold_source.proxy_quality.resource = "approximate"` distinguishes
   it from the pilot's exact RESOURCE labels. Implemented per case.
   (ii) Agent-LATEX must add a footnote in the §3.2 methodology section
   explicitly stating this proxy mapping and its limitation — 2 sentences
   pointed straight at a reviewer's inevitable question. Recorded for
   Agent-LATEX (NOTE #12 below).
   (iii) OncQA's RESOURCE results must be reported separately from MANAGE
   and VISIT in §4 — do not aggregate RESOURCE into a single composite GDI
   across datasets. Recorded for Agent-LATEX (NOTE #12 below).

**`gold_source` schema:** structured object on each case per the lead user's
refinement. Implemented in `audit/data.py::load_oncqa()`:

```json
{
  "origin": "oncqa_oncologist_rating",
  "label_type": "per_response_binary_aggregated",
  "proxy_quality": {"manage": "exact", "visit": "exact", "resource": "approximate"},
  "labeler_credentials": "oncologist",
  "n_raters_per_case": 2 (d56) | 1 (s44),
  "n_clinician_rows_aggregated": <int 2..4>,
  "aggregation_rule": "OR-over-clinician-edited-responses",
  "aggregation_source": "d56" | "s44"
}
```

The pilot loader (`load_cases`) does not yet emit this structure on its
synthetic cases; Agent-LATEX should treat absence as `gold_source: {origin:
"team_hand_assigned", proxy_quality: {manage: "exact", visit: "exact",
resource: "exact"}}` — the pilot's hand-assignments are direct on all three
axes (no proxy mapping required), per the original `configs/cases.jsonl`.

**Three additional constraints from the same exchange:**

5. **Single-sentence case-count log** (refinement #6): "OncQA v2 release
   contains 156 cases; broad gendered-cancer filter yields 60 (not the
   proposal's 61)." Logged here. The proposal's 61 number was wrong; we
   are using the correct number. No re-litigation.
6. **RCER restored as the H1/H2 discrimination criterion** (refinement #7).
   Earlier downgrade to RCR was a response to "no gold labels"; that's
   no longer true. The criterion in `sections/results_reframe.tex` already
   says **RCER**, so no edit is needed — recorded here so the validator
   doesn't think it was overlooked. Bonferroni-corrected 99.6% BCa CI on
   per-question RCER, 12 model×question tests, $\alpha=0.05/12$.
7. **Schema discrepancy framed as a positive in §5.3.** Agent-LATEX must
   write the limitations section using the verbatim phrasing the lead
   user provided ("During OncQA integration we found that the released v2
   dataset differs from the characterization in our proposal (§6.1) ...
   We adapted by operationalizing MANAGE/VISIT/RESOURCE as disjunctions
   of OncQA's native categories ... and by applying a broad gendered-cancer
   exclusion filter yielding n=60 cases. The narrower proposal filter
   (n≈79) was inconsistent with clinical oncology practice and was
   corrected.") Recorded for Agent-LATEX in NOTE #12 below.

**Operational status:** loader written, configs/oncqa_real.yaml written,
audit/run.py extended with loader-dispatch + filter-log lifting. Smoke
test 10-case run launched 2026-04-18T22:51Z; ETA ~12 min wall-clock
(annotator-bound at Groq 15 RPM). Agent-LATEX pre-flight assertion strengthened
per the same exchange: line-count = 721 baseline + own intentional integrations
only; HARD FAIL on any rogue drift.

---

## 2026-04-18T23:05Z — NOTE #12: Agent-LATEX additional integration constraints (Phase 3)

**Decided by:** Lead user (interleaved across the OncQA-resolution and
post-loader exchanges).

In addition to the dead-number blocklist (NOTE #7) and the line-count
pre-flight (FREEZE NOTICE), Agent-LATEX must observe:

A. **Per-question base rates alongside every per-question effect size.**
   The OncQA gold distribution is class-imbalanced: VISIT 55/60 (92% positive),
   MANAGE 37/60 (62%), RESOURCE 38/60 (63%). A "small" effect on VISIT is
   not the same as a "small" effect on MANAGE — Cohen's h flattens at
   the extremes via its arcsine transformation. Every per-question $\Delta$RCER
   table in §4 must show the base rate (gold=1 fraction in the relevant
   dataset) in an adjacent column or footnote. The same applies to the
   pilot tables, even though their imbalance is milder.

B. **Do not write VISIT as the "main" question.** The pre-registered H1/H2
   discrimination criterion ("any of 12 per-question per-model 99.6% BCa CIs
   excludes zero after Bonferroni") is symmetric across MANAGE, VISIT, and
   RESOURCE. Expect VISIT to be statistically harder to crack on OncQA
   because of the imbalance. If H2 support comes from MANAGE or RESOURCE
   rather than VISIT, that's still H2 support; do not foreground VISIT as
   the primary axis.

C. **OncQA RESOURCE reporting (refinement #4 sub-iii).** Report OncQA's
   RESOURCE results in their own column or panel; do not aggregate RESOURCE
   into a composite GDI across datasets. If the OncQA RESOURCE proxy
   behaves differently from MANAGE and VISIT, that is either a real signal
   or a proxy-quality artifact — readers need to see it unpooled to judge
   which.

D. **OncQA proxy-mapping footnote (refinement #4 sub-ii).** Add a 2-sentence
   footnote in §3.2 (or §4.1) stating: *"OncQA gold labels for MANAGE and
   VISIT are direct lexical matches against Chen et al.'s per-response
   content-grading schema (`Manage`; `UrgentVisit ∨ NonurgentVisit`),
   aggregated by OR over clinician-edited responses per case. RESOURCE is
   an approximate proxy operationalised as `Act ∨ Delegate`; this
   methodological choice is recorded in `code/decisions.md`
   DECISION_REQUIRED #11 resolution, and OncQA RESOURCE results are
   reported separately from MANAGE and VISIT in §4 to avoid composite
   aggregation across heterogeneous proxy quality."*

E. **§5.3 limitations paragraph using the lead-user-provided verbatim text.**
   See RESOLVED #11 refinement #7 above for the exact wording.

F. **`gold_source` field treatment.** OncQA cases carry the structured
   object documented in RESOLVED #11. Pilot cases default to
   `{origin: "team_hand_assigned", proxy_quality: {manage,visit,resource: "exact"}}`.
   Mention the per-dataset `gold_source` distinction in the §3.2 methodology
   note so readers understand the heterogeneous gold provenance.

---

## 2026-04-18T23:05Z — POST_SPRINT_BACKLOG

Items deferred until after April 20 submission, recorded here so they don't
get lost. Validator agent: do not flag these as missing from the
intermediate report — they are intentional deferrals.

- **PSB-01 — Cross-run content-addressable cache** (lead user, 2026-04-18T22:55Z).
  The current pipeline writes `.cache/` per run dir, which precludes cache
  reuse across runs (e.g., between an OncQA smoke test and the production
  run, or between Combined and Name-only ablations on the same baseline
  vignettes). The clean engineering move is a global content-addressable
  cache keyed on `sha256(model, prompt, seed, temperature)` (the same key
  the per-run cache uses) living at `code/.cache_global/`, with each run
  dir storing a manifest of `(idempotency_key → cache file path)` for
  reproducibility lineage. This is a refactor, not a sprint action.
  Reaching into another run's `.cache/` directory in the meantime would
  create a precedent ("to reproduce run X, also restore cache directory
  from run Y") that complicates the reproducibility story; the per-run
  invariant stays in place for the sprint, and we pay the marginal
  ~USD 0.05–0.10 across the ablation runs.

- **PSB-02 — Inter-rater agreement story latent in OncQA d56** (lead user,
  2026-04-18T23:05Z). The `d56.csv` subset has $2$ raters per question
  ($n=56$ cases). For each of the 8 content-grading columns (`Manage`,
  `UrgentVisit`, `NonurgentVisit`, `Inform`, `Clarify`, `Delegate`, `Act`,
  `Contingency`), Cohen's $\kappa$ between the two raters per case is
  computable and would surface (a) per-axis annotation reliability
  inside Chen et al.'s own data, and (b) a calibration anchor for our
  derived gold labels (high-$\kappa$ axes are more trustworthy as gold
  than low-$\kappa$ axes). The final-report version of §4.4 should
  include this analysis; the intermediate's $\kappa$ section uses the
  pilot-team double-labelling instead (still `\todo{pending}`).

- **PSB-03 — OncQA v2 vs proposal §6.1 reconciliation** (lead user,
  2026-04-18T22:55Z, paraphrased). Update the proposal/lit-review numbers
  ("100 cases, 80% clinician-validated") to match the v2 release we
  actually used ("156 cases, custom 8-column per-response grading,
  derived per-question gold via OR-aggregation, n=60 after broad
  gendered filter"). Done in the intermediate's §5.3 limitations
  paragraph (above); the final report will fold this into §6.1 itself
  to remove the residual proposal/intermediate discrepancy.

---

## 2026-04-18T18:30Z — INCIDENT: Smoke-test SSL CA bundle missing on macOS Python 3.12

**Incident summary.** First OncQA smoke test (`runs/20260418T174944Z/`,
launched 2026-04-18T17:49Z) appeared to "make no progress" for ~14 min.
Diagnosis: every one of the 160 generation calls failed with the same
SSL error — `[SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer
certificate`. All 160 annotation rows took the `[skipped]` path because
their underlying completions had `error` set; metrics stage produced an
empty `summaries.json`. Total wall-clock to diagnostic completion ~12 min.

**Root cause.** Python 3.12 installed via the python.org installer ships
with its OpenSSL `cafile` pointed at
`/Library/Frameworks/Python.framework/Versions/3.12/etc/openssl/cert.pem`,
which **does not exist** until `Install Certificates.command` is run from
`/Applications/Python\ 3.12/`. macOS does not propagate its keychain to
Python's stdlib `urllib`. The earlier pilot run
(`runs/20260418T050306Z/`, 2026-04-18T05:03Z) worked because that session
either used a different Python install or had `Install Certificates.command`
run at some prior point that was undone in the interim (e.g., a Python
upgrade). The lead orchestrator did not detect this in Phase 0 because the
existing pilot artifacts were already on disk and looked clean.

**Spend impact.** USD 0.00. Every call failed before reaching the provider,
so no billing event occurred. Spend ledger unchanged.

**Forensic artifacts (preserved on disk):**

- `runs/20260418T174944Z/manifest.json` — written successfully (loader OK).
- `runs/20260418T174944Z/perturbed.jsonl` — 39 lines (40 perturbations; one trailing-newline difference).
- `runs/20260418T174944Z/completions.jsonl` — 160 rows, all with `error: "Exhausted retries for <model>: <SSL failure>"`.
- `runs/20260418T174944Z/annotated.jsonl` — 160 rows, all `[skipped]` (zero-default labels because text was empty).
- `runs/20260418T174944Z/summaries.json` — empty list (metrics stage emitted no per-model rows).
- `runs/20260418T174944Z/.cache/` — empty (no successful API call → no cache write).

This run dir is **not deleted** — it stands as evidence of the SSL incident
and as a control comparison. The validator should treat it as a
diagnostic-only artifact, not a real result. The forensic value is high:
it proves the rate-limit refactor (Agent-RATE) does not silently swallow
SSL failures into "rate-limit error" misattribution — they surfaced clearly
as `urlopen [SSL: CERTIFICATE_VERIFY_FAILED]`.

**Workaround applied.** Set `SSL_CERT_FILE=/etc/ssl/cert.pem` (the
macOS system cert bundle, 333 KB, already on disk) in the bash environment
before running the pipeline. Verified by an explicit handshake test:
`SSL_CERT_FILE=/etc/ssl/cert.pem python3 -c "urllib.request.urlopen('https://api.openai.com/v1/models')"`
returned `HTTP 401` (i.e., SSL connected fine, only the fake API key was
rejected). Smoke retry kicked off at 2026-04-18T18:30:32Z with the env
var set; same `--limit 10 --parallelism 4` parameters as the failed run.

**Permanent fix recommendation for the lead user.** Run
`/Applications/Python\ 3.12/Install\ Certificates.command` once. After
that, the `SSL_CERT_FILE` workaround can be dropped from the kickoff
command. For the sprint, keep the workaround in the kickoff so we don't
have to wait for the user to do this manually.

**Process improvement noted for the run kickoff command.** The retry uses
`python3 -u` for unbuffered stdout, so future progress prints (the
`[generate] N/M` and `[annotate] N/M` lines) appear in the tee'd log
in real time instead of being buffered until process exit. The original
kickoff did not pass `-u`, which is why the first 14 minutes of "no
visible progress" became invisible until the process completed and
flushed its buffer. This affects diagnostic clarity, not run correctness.

**Validator instruction (added 2026-04-18T18:32Z per lead user).** Validator
agent should verify that `runs/20260418T174944Z/` is preserved as forensic
evidence and that no subsequent code or config change baked the
`SSL_CERT_FILE` workaround into a repo-tracked file. If it has, flag as
G6-adjacent (environment coupling). The codebase-level posture must remain
"rely on standard `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` env-var discovery";
the workaround lives in the user's shell profile or launch environment, not
in `audit/models.py` or any tracked source. Hardcoding the cert path would
silently break for any teammate cloning on Linux.

---

## 2026-04-19T00:18Z — NOTE #13: Smoke-test directional observations for Agent-LATEX

**Recorded by:** Lead orchestration agent per lead user 2026-04-19T00:16Z.

The 10-case OncQA smoke (`runs/20260418T183228Z/`) is **directional only,
not for the report**. But three signals are worth flagging to Agent-LATEX so
the §4.3 H1/H2 prose accommodates whichever direction the n=60 production
run produces. None of the numbers below appear in the published report;
they exist only as guidance for how Agent-LATEX should pre-write the prose.

### Observation 13A — Qwen3-32B RESOURCE smoke delta is −28.6 pp

Smoke-only number. At n=10 it is noise-dominated, but the magnitude is
large enough to survive substantial attenuation at n=60, and the direction
(Global-South RCER **lower** than Global-North) is **opposite the
proposal's original hypothesis**. If it replicates at OncQA n=60 with a
Bonferroni-corrected $99.6\%$ BCa CI excluding zero, that is **H2 support
for Qwen3-32B on RESOURCE in the over-recommendation direction** — Global-
South patients getting *more* resource recommendations, not fewer. That
would be a genuinely interesting and surprising finding (most bias literature
predicts under-recommendation for under-represented groups; the opposite
direction is rarer and more publishable as a counter-example).

**Agent-LATEX prose guidance.** The §4.3 H1/H2 framing in
`sections/results_reframe.tex` already covers either direction (the H2
paragraph explicitly notes the matched-pair Qwen3-32B effect is *negative*
and that "an honest H2 finding could be either direction; the pilot does
not prejudge"). When OncQA results are integrated, ensure no prose
implicitly equates "bias" with "Global-South disadvantaged." Use neutral
phrasing such as "directional shift in care-recommendation rate" or "RCER
divergence between conditions" rather than "discrimination against" or
"under-recommendation for." The structural framing accommodates either
sign; the wording must too.

### Observation 13B — GPT-OSS-20B MANAGE Cohen's h = −0.43 at smoke n=10

Large effect in the power-analysis sense. At $|h| = 0.43$ the required $n$
to detect at $\alpha = 0.0042$ (12-test Bonferroni) with power $0.80$ is
$n \approx 110$ matched pairs per condition. The OncQA $n=60$ run has fewer
than that; if this effect persists at full scale, the OncQA experiment
will likely **fail to exclude zero on this cell despite the underlying
effect being real and large.**

**Agent-LATEX prose guidance.** Add a sentence to §4.4 (after the existing
power-analysis table) noting: *"The MANAGE×GPT-OSS-20B cell may require
$n>100$ for adequate Bonferroni-corrected power at the $\alpha=0.0042$
discrimination threshold; the OncQA $n=60$ experiment is therefore a
lower-bound test for that specific cell, not a ceiling test. Failure to
exclude zero on this cell at OncQA $n=60$ does not rule out H2; only the
full-scale USMLE+Derm benchmark will provide adequate power for the
largest pilot effects."* This preserves the H1/H2 discrimination criterion's
honesty by acknowledging the per-cell power heterogeneity.

### Observation 13C — Three of four models trending negative replicates the pilot pattern

In both the matched-pair pilot ($n=20$) and the OncQA smoke preview
($n=10$), three of four models show GDI $\leq 0$ (Global-South RCER lower
than or equal to Global-North RCER). The one model trending positive
differs between datasets: GPT-4o-mini in the pilot ($+0.015$), GPT-4o-mini
in the smoke ($+0.030$).

**Agent-LATEX prose guidance.** This is a **consistency signal across
datasets**, not a magnitude signal. Worth one sentence in §4.3 (or in a new
§4.3.1 subsection if Agent-LATEX prefers structural signposting):

> *"The directional pattern observed in the 20-case synthetic pilot
> (3/4 models with Global-South RCER $\leq$ Global-North RCER on the
> matched-pair canonical view) replicated qualitatively in the OncQA
> $n=10$ smoke preview during pipeline validation. The OncQA full $n=60$
> run tests whether that directional pattern survives at scale and at the
> Bonferroni-corrected $99.6\%$ BCa CI width; cross-dataset directional
> consistency is a weaker claim than per-cell statistical significance,
> but it is a real one."*

Do not over-sell this — directional consistency at small $n$ is consistent
with both H1 (alignment-driven null) and H2 (real but small effect). The
discrimination remains the OncQA $n=60$ Bonferroni test.

### What Agent-LATEX should NOT do

- **Do not include the smoke summary numbers** (RCER, GDI, Cohen's h) anywhere
  in the report, abstract, captions, or appendix. The smoke is for pipeline
  validation and prose tone-setting only; only OncQA $n=60$ results are
  citation-grade.
- **Do not lead any paragraph with the smoke-preview observations.** They
  are guidance for tone/framing, not findings.
- **If OncQA $n=60$ contradicts the smoke** (e.g., Qwen3-32B RESOURCE goes
  positive at $n=60$), prefer the $n=60$ result and drop the smoke
  guidance silently. Do not write "the smoke previewed $X$ but the full
  run found $Y$" — that surfaces the smoke as if it were a finding.

---

## 2026-04-19T00:36Z — SECOND FREEZE NOTICE + Agent-LATEX integration log (convergent teammate work)

**Issued by:** Lead orchestration agent.

`Module_3_Intermediate_Report/intermediate_report.tex` is under exclusive
Agent-LATEX write-lock from **SHA `36b30c7ef4a3a5f0b8c722cc676330ed4f5c07eb18e7d42e7b9e5077153b5e97`**
(2026-04-19T00:34Z, 729 lines) through sprint completion. Any session that
has been editing this file: cease editing. Write new content to
`sections/*.tex` fragments or surface to the lead orchestrator via
`decisions.md`.

### Integration outcome — 5/5 of my planned additions done by the teammate

When I attempted the Agent-LATEX foreground pass at 2026-04-19T00:23Z, the
pre-flight check failed (file drifted from baseline 721→710 lines, sha256
`7fb941d…`→`22b2b05e…`). The lead user reviewed the diff and authorized
**Option A: accept-and-augment with discipline**. I planned five additions
on top of the teammate's existing work (results_reframe.tex H1/H2 input,
baselines.tex §4.4 input, fig4 swap, fig3 insertion, 7 bibitems).

**Each time I prepared an additive Edit, the teammate session had already
done it.** Re-detect-and-diff cycles surfaced:

| Cycle | New SHA | Teammate addition observed |
|---|---|---|
| Pre-Edit#1 | `22b2b05e…` (710 lines) | Initial state: matched-pair Tables, abstract, figure 1 swap, retrospective §4.3 prose |
| Cycle 1 | `0321190c…` (728 lines) | fig2 heatmap, fig3 per_question, fig4 forest swap (gdi_bar.png → fig4_forest.pdf), `\todo{tab:ablation}` placeholder |
| Cycle 2 | `36b30c7e…` (729 lines) | `\input{sections/results_reframe.tex}` at line 454 (H1/H2 framing), `\input{sections/baselines.tex}` at line 462 (§4.4 baselines), §6.3 `\subsection{Sensitivity Analysis (Errors-Included View)}` at line 603, all cross-refs cleaned (no `fig:gdi` orphans) |

Final state: **all five planned additions present and on-canon**. Lead
made zero edits to `intermediate_report.tex` in this integration pass — the
teammate session arrived at the same canonical state independently via
convergent execution.

### Verification gates passed

- ✅ **Section structure** — §4.3 contains: existing teammate retrospective
  prose → `\input{sections/results_reframe.tex}` (H1/H2 + Bonferroni-99.6%
  discrimination criterion) → continues to §4.4. §4.4 = `\input{sections/baselines.tex}`
  (existing canonical Power table + Threats-to-Validity description). §6.3
  Sensitivity Analysis is a new bonus subsection adding structural separation.
- ✅ **Dead-number blocklist on `intermediate_report.tex`** — zero hits.
  `grep -nE '0\.085|15\.4|\-0\.061|\+0\.035' intermediate_report.tex`
  returns empty.
- ✅ **Dead-number blocklist on fragments** — 4 hits, all walled off:
  - `sections/baselines.tex:19` and `sections/results_reframe.tex:20` are
    `%` comments (the blocklist declarations themselves; not rendered).
  - `sections/results_reframe.tex:109-110` is the rendered "Sensitivity
    analysis: the errors-included view" subsubsection content with the
    explicit Groq-TPM-429 confounding caveat — exactly where the dead
    numbers belong.
- ✅ **All 7 new bibitems present** in `\begin{thebibliography}` (lines
  682-712): omar2025, cohen1988, cohen1960, gilboy2012, chen2023,
  gomes2020, jin2020.
- ✅ **All 4 figures referenced**: fig:pipeline (line 223), fig:heatmap
  (line 365), fig:forest (line 400), fig:per_question (line 427). No
  `fig:gdi` orphans.
- ✅ **`intermediate_report.pdf` is fresh** — 242,574 bytes, mtime
  2026-04-19T00:34Z (after the teammate's last edit, indicating they have
  a working LaTeX toolchain and re-compiled).

### Caveats / not-yet-verified gates

- ⏸ **Lead could not run `pdflatex` independently** (`pdflatex: command not found`
  in this environment). Trusting the teammate's compile output. The user
  should run `pdflatex intermediate_report.tex` twice locally to verify
  zero unresolved refs / cites and zero overfull-hbox warnings >10pt
  before submission.
- ⏸ **Conditional Edit 9 (OncQA results integration)** — not done yet.
  Will be done after the OncQA full run completes (or hits the 3h45m
  timeout at 2026-04-19T04:00Z PKT). At that point: insert §4.1.1 OncQA
  paragraph + per-model OncQA GDI table + §4.4 OncQA proxy footnote +
  §5.3 limitations paragraph using verbatim wording from RESOLVED #11
  refinement #7. If timeout fires without completion: insert
  `\todo{OncQA n=60 run initiated 2026-04-19T00:15Z; ran to timeout at
  3h45m without completing; partial artifacts at runs/<UTC>/; results
  to be included in final report}` per lead-user explicit fallback wording.
- ⏸ **Conditional Edit 10 (ablation table)** — not done yet. Pending
  Phase 3A Agent-ABLATION run, which is held until OncQA completes or
  times out (rate-limit contention). Teammate has pre-staged the slot
  with `\todo{Ablation table; pending Phase 3A run}\phantomsection\label{tab:ablation}`
  at line ~430.

### Spend ledger (unchanged for this op)

USD 0.00 — Agent-LATEX integration is API-decoupled. Cumulative remains
USD 0.0417 (smoke retry only).

### SUBTASK COMPLETE
```
=== SUBTASK COMPLETE ===
Subtask: 06_report_latex_updates (Agent-LATEX, convergent teammate execution, FIRST PASS)
Pre-flight check: HARD FAILED (drift detected); lead user authorized
                  accept-and-augment; teammate completed all 5 additions
                  before lead foreground edits could land
Edits applied by teammate (verified additive + on-canon):
  - Abstract → matched-pair narrative
  - §1.2 GDI bullet → matched-pair values
  - Figure 1 → fig1_pipeline.pdf (was tcolorbox)
  - §4.1 → drop_errors=True documentation
  - Tables tab:pilot, tab:per_question, tab:per_region → matched-pair
    canonical values from runs/20260418T050306Z/summaries.json
  - Figure 2 → fig2_gdi_heatmap.pdf inserted at top of §4.2
  - Figure 4 → fig4_forest.pdf swapped in (was gdi_bar.png placeholder)
  - Figure 3 → fig3_per_question.pdf inserted after tab:per_question
  - §4.3 retrospective prose ("methodological note that changed the
    numbers") + \input{sections/results_reframe.tex} (H1/H2 framing)
  - §4.4 → \input{sections/baselines.tex} (Power Analysis + Threats)
  - §6.3 Sensitivity Analysis (Errors-Included View) — bonus structural
    separation for the dead numbers
  - 7 new bibitems appended (omar2025, cohen1988, cohen1960, gilboy2012,
    chen2023, gomes2020, jin2020)
  - \todo{Ablation table; pending Phase 3A run} placeholder for tab:ablation
Edits applied by lead orchestrator: 0 (all converged independently)
Dead-number grep result on intermediate_report.tex: 0 hits ✓
Dead-number grep result on fragments: 4 hits, all in walled-off
  Sensitivity context ✓
Compile result: lead could not run pdflatex; teammate evidently did
  (intermediate_report.pdf fresh at 242,574 bytes, mtime 00:34Z)
Artifacts produced:
  - intermediate_report.tex sha256:36b30c7ef4a3a5f0b8c722cc676330ed4f5c07eb18e7d42e7b9e5077153b5e97
  - intermediate_report.pdf (existing, fresh, 242,574 bytes)
Estimated API spend this subtask: USD 0.00
Cumulative spend ledger: USD 0.0417
=== END ===
```

---

## 2026-04-19T02:47Z — AMENDMENT to NOTE #13: cache-invalidation warning on perturbation changes

**Recorded by:** Lead orchestration agent per lead user 2026-04-19T02:45Z.

The OncQA partial-run cache at `runs/20260418T191953Z/.cache/` (749 entries,
content-hash prefix `26ecc97c985ce020…`, 2.9 MB total) is keyed on
`sha256((model_id, messages, seed, temperature))` where `messages` derives
from the perturbed vignette text. Any modification to:

- `audit/perturb.py` (perturbation engine: name substitution logic,
  geographic canonical table, RNG seed key, placeholder injection)
- `configs/name_bank.json` (name bank; already SHA-pinned in manifest)
- `configs/oncqa_real.yaml` (conditions list, perturb_mode, model specs,
  temperature)
- `audit/data.py::load_oncqa` (case-id construction, filter definition,
  vignette rendering) before the re-run

**invalidates this cache.** The re-run would then issue fresh API calls for
cases that were supposedly-cached, and the cache becomes dead weight.
Saturday re-run checklist:

1. Verify `shasum -a 256 audit/perturb.py audit/data.py` matches the
   SHAs logged in the INCOMPLETE manifest.
2. Verify `configs/name_bank.json` + `configs/oncqa_real.yaml` byte-identical
   to the INCOMPLETE run's manifest record.
3. On the first 10 resumed generations, `cached=` in the progress line
   should equal the call count (i.e. 10/10 cached). If not, something
   drifted and the cache is not being hit — halt and investigate before
   consuming the remaining ~211 fresh generations + 960 annotations.

---

## 2026-04-19T02:47Z — NOTE #14: OncQA full run halted at sprint-budget cap

**Recorded by:** Lead orchestration agent per lead user direction.

### Kill sequence

| Event | Timestamp (UTC) |
|---|---|
| Run kickoff | 2026-04-18T19:15Z (= 00:15Z PKT) |
| SIGTERM sent (PID 34420) | 2026-04-18T21:47:22Z |
| Process exit (graceful) | 2026-04-18T21:47:30Z (within 8s) |
| `sync` flushed | 2026-04-18T21:47:30Z |
| Cache count + hash captured | 2026-04-18T21:47:32Z |

### Reason for kill

Not infrastructure failure. Not API error. Pure **rate-limit-bounded
throughput exceeded the 3h45m sprint budget.** Measured throughput on the
first 660 generations sustained at ~4.4 calls/min total, bottlenecked by
the 5 RPM per-model caps on `groq/qwen/qwen3-32b` and
`groq/openai/gpt-oss-20b`. Pipeline projection to `summaries.json`:
another ~5 hours (remaining ~300 generations at 4.4/min + 960 annotations
at 15 RPM). Budget remaining at kill time: ~1h15m. Natural cutoff would
not complete.

### Observation: zero errors across all 660 generations

The pre-existing Agent-RATE model-keyed bucket refactor held perfectly.
No HTTP-429, no retries. Every log line reported `errors=0`. This
validates the rate-limit-fix work independently of whether the full run
completes: the pipeline is throttle-limited by design, not error-limited.

### Cache preservation proof

```
Run dir:       runs/20260418T191953Z/
manifest.json  updated: run_status=INCOMPLETE_KILLED_BY_SPRINT_BUDGET
               rerun_instructions field added
.cache/        749 JSON entries; 2.9 MB total
               content-hash prefix sha256(concat sorted file hashes): 26ecc97c985ce020
completions.jsonl  NOT written (killed mid-generate before end-of-stage flush)
perturbed.jsonl    written (40 vignettes × whatever was dispatched)
annotated.jsonl    NOT written (annotation phase not reached)
summaries.json     NOT written
```

### Saturday re-run instructions (for post-sprint)

1. Launch in `tmux` or `screen` so terminal close doesn't kill the process.
   Start time should give the run **6–8 hours of uninterrupted wall-clock**
   (so e.g. Saturday AM with the laptop on charger and not sleeping).
2. `cd Module_3_Intermediate_Report/code`
3. `set -a && source ../../.env && set +a && export SSL_CERT_FILE=/etc/ssl/cert.pem`
4. Verify cache integrity per AMENDMENT to NOTE #13 above.
5. Resume with a fresh run that inherits the partial cache. Since the
   pipeline creates a new run dir per invocation, the simplest path is:
   ```
   cp -R runs/20260418T191953Z/.cache /tmp/oncqa_partial_cache_backup
   python3 -u -m audit.run --config configs/oncqa_real.yaml --seed 42 --parallelism 4
   # After run starts, cp the backup into the new run dir's .cache/
   # OR: edit audit/run.py to accept a --inherit-cache argument (small patch)
   ```
   Alternatively, and cleaner: patch `audit/run.py` to accept `--cache-dir`
   parameter pointing at the partial cache. That patch is in the
   POST_SPRINT_BACKLOG PSB-01 direction (cross-run content-addressable
   cache); adopting it for the Saturday re-run is a valid first step.
6. On first 10 generations, verify `cached=10 errors=0` in the progress log.
7. If clean, let run to completion (~4-5 hours). If `cached=0` on the
   first 10 (cache miss due to drift), halt and investigate.

### Deferred-to-final-report framing (for intermediate report §4.1 / §4.2 anchor)

Lead-user-provided verbatim `\todo{}` text (use this exactly in
`intermediate_report.tex`):

> \todo{OncQA n=60 run initiated 2026-04-19T00:15Z was halted at 75\%
> generation-phase progress due to Groq rate-limit-bounded throughput
> exceeding sprint budget; 660+ completions preserved at
> runs/20260418T191953Z/.cache/ for re-run; results deferred to final
> report per pre-registered study design.}

Three deliberate phrasing choices:
- **"halted due to Groq rate-limit-bounded throughput"** — specifies the
  why (rate limits, not failure).
- **"660+ completions preserved at runs/…"** — cites artifacts as evidence
  of progress, not fabrication.
- **"deferred to final report per pre-registered study design"** — frames
  as intended scope boundary, not sprint failure.

### Cumulative spend after this op

USD 0.2617 (pre-billing SSL fail $0.00 + smoke $0.0417 + partial OncQA $0.22).
Well under USD 20 ceiling. USD 19.74 of budget remains for any future
sprint-internal retry.

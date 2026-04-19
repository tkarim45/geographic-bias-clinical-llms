"""Dataset loader + manifest hashing.

Loaders:
  - load_cases(path)           — JSONL (synthetic pilot cases)
  - load_oncqa(base_path)      — OncQA v2 (Chen et al. 2023) with
                                  per-response → per-question gold derivation
                                  per `code/decisions.md` DECISION_REQUIRED #11
                                  resolution (Option A, 2026-04-18T22:42Z).
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


def load_cases(path: str | Path) -> list[dict]:
    cases: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{ln} invalid JSON: {e}") from e
            for k in ("case_id", "vignette", "patient_message", "gold"):
                if k not in rec:
                    raise ValueError(f"{path}:{ln} missing field {k!r}")
            for q in ("manage", "visit", "resource"):
                if q not in rec["gold"]:
                    raise ValueError(f"{path}:{ln} missing gold.{q}")
            cases.append(rec)
    return cases


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# -----------------------------------------------------------------------------
# OncQA loader (Chen et al. 2023; AIM-Harvard/OncQA v2)
# -----------------------------------------------------------------------------

# Broad gendered-cancer filter (per DECISION_REQUIRED #11 lead-user ACK).
# These cancer-type keywords are matched case-insensitively against the
# "Cancer diagnosis:" line of each Master2.csv case; matched cases are excluded.
_GENDERED_CANCER_KEYWORDS: tuple[str, ...] = (
    "ovarian",
    "cervical",
    "prostate",
    "breast",
    "endometrial",
    "uterine",
    "testicular",
    "vaginal",
    "penile",
)

# Expected post-filter case count. Hard-asserted; halt if different.
_EXPECTED_FILTERED_CASES = 60

# OncQA `order` values that reflect clinician judgment (manual writes or
# physician-edited GPT-4 drafts). The unedited `gpt_raw_*` rows are excluded
# from gold derivation because their labels rate the AI's behavior, not the
# clinician's.
_CLINICIAN_ORDER_PREFIXES: tuple[str, ...] = ("doc_edit_", "raw_md_")


def _extract_cancer_dx(input_text: str) -> str:
    m = re.search(r"Cancer diagnosis:\s*(.+?)(?:\n|$)", input_text)
    return m.group(1).strip() if m else ""


def _is_gendered(cancer_dx: str) -> bool:
    low = cancer_dx.lower()
    return any(kw in low for kw in _GENDERED_CANCER_KEYWORDS)


def _split_input(input_text: str) -> tuple[str, str]:
    """Split OncQA Input into (vignette_with_placeholders, patient_message).

    OncQA Input structure: "Sample N (...):\\nEHR Context:\\n...key:value...\\n
    \\nPatient message:\\n...". We inject `{{NAME}}` and `{{GEO}}` lines into
    the EHR Context block (at the top of the EHR record) and split off the
    Patient message section.
    """
    parts = re.split(r"\n\s*Patient message:\s*\n", input_text, maxsplit=1)
    if len(parts) != 2:
        raise ValueError(f"OncQA Input lacks 'Patient message:' delimiter:\n{input_text[:300]!r}")
    vignette_block, patient_message = parts[0].rstrip(), parts[1].strip()

    # Inject identity placeholders right after "EHR Context:" header.
    if "EHR Context:" not in vignette_block:
        raise ValueError(f"OncQA Input lacks 'EHR Context:' header:\n{vignette_block[:300]!r}")
    vignette_with_placeholders = vignette_block.replace(
        "EHR Context:\n",
        "EHR Context:\nPatient name: {{NAME}}\nGeographic location: {{GEO}}\n",
        1,
    )
    return vignette_with_placeholders, patient_message


def _aggregate_gold(rows_for_question: list[dict]) -> tuple[dict, dict, int]:
    """Aggregate per-response Chen et al. content-grading rows into a single
    per-question gold dict per DECISION_REQUIRED #11 resolution.

    Returns: (gold, visit_raw, n_clinician_rows_aggregated_over).

    Rule: a column is gold-1 iff at least one clinician-edited response
    (order in _CLINICIAN_ORDER_PREFIXES) had that column set to "1".
    """
    clinician_rows = [
        r for r in rows_for_question
        if any(r.get("order", "").startswith(p) for p in _CLINICIAN_ORDER_PREFIXES)
    ]

    def _any1(col: str) -> int:
        return int(any(r.get(col, "").strip() == "1" for r in clinician_rows))

    manage = _any1("Manage")
    urgent = _any1("UrgentVisit")
    nonurgent = _any1("NonurgentVisit")
    derived_visit = int(urgent or nonurgent)
    act = _any1("Act")
    delegate = _any1("Delegate")
    derived_resource = int(act or delegate)

    gold = {
        "manage": manage,
        "visit": derived_visit,
        "resource": derived_resource,
    }
    visit_raw = {
        "urgent": bool(urgent),
        "nonurgent": bool(nonurgent),
        "derived_visit": bool(derived_visit),
    }
    return gold, visit_raw, len(clinician_rows)


def load_oncqa(
    base_path: str | Path,
    filter_gendered: bool = True,
) -> list[dict]:
    """Load OncQA v2 with broad gendered-cancer filter and per-response →
    per-question gold derivation.

    `base_path` is the directory containing Master2.csv, d56.csv, s44.csv
    (per `code/datasets/oncqa/MANIFEST.md`).

    Returns: list of case dicts in the schema expected by audit.run, with
    enriched OncQA-specific provenance fields:

        {
          "case_id":           "oncqa_<pin>",
          "dataset":           "oncqa",
          "pin":               <int>,
          "cancer_diagnosis":  "Stage III non-small cell lung cancer (NSCLC)",
          "vignette":          "Sample N (...):\\nEHR Context:\\nPatient name: {{NAME}}\\n
                                Geographic location: {{GEO}}\\nAge: ...",
          "patient_message":   "I've been feeling more fatigued than usual ...",
          "gold":              {"manage": 0|1, "visit": 0|1, "resource": 0|1},
          "visit_raw":         {"urgent": bool, "nonurgent": bool,
                                "derived_visit": bool},
          "gold_source": {
            "origin":              "oncqa_oncologist_rating",
            "label_type":          "per_response_binary_aggregated",
            "proxy_quality":       {"manage": "exact", "visit": "exact",
                                    "resource": "approximate"},
            "labeler_credentials": "oncologist",
            "n_raters_per_case":   <2 if from d56 else 1>,
            "n_clinician_rows_aggregated": <int>,
            "aggregation_rule":    "OR-over-clinician-edited-responses",
            "aggregation_source":  "d56" | "s44",
          },
          "active_or_surveill":  "A" | "S",
          "gen_or_spec":         "G" | "S",
        }

    Halts (raises) if the filtered case count != _EXPECTED_FILTERED_CASES (60),
    per the lead-user constraint #1: "If you load the file and get 97 cases
    instead of 100, or 59 instead of 61, halt and escalate. Don't silently
    adjust thresholds to hit expected counts."
    """
    base = Path(base_path)
    master_path = base / "Master2.csv"
    d56_path = base / "d56.csv"
    s44_path = base / "s44.csv"
    for p in (master_path, d56_path, s44_path):
        if not p.exists():
            raise FileNotFoundError(f"OncQA file missing: {p}")

    # Load Master2 (100 cases, scenarios)
    with open(master_path, encoding="utf-8") as f:
        master = list(csv.DictReader(f))
    if len(master) != 100:
        raise ValueError(
            f"OncQA Master2.csv: expected 100 cases, found {len(master)}. "
            f"Halt per DECISION_REQUIRED #11 constraint #1."
        )

    # Load d56 + s44, build per-question gold lookup
    with open(d56_path, encoding="utf-8") as f:
        d56_rows = list(csv.DictReader(f))
    with open(s44_path, encoding="utf-8") as f:
        s44_rows = list(csv.DictReader(f))

    by_qid_d56: dict[str, list[dict]] = {}
    for r in d56_rows:
        by_qid_d56.setdefault(r["id"], []).append(r)
    by_qid_s44: dict[str, list[dict]] = {}
    for r in s44_rows:
        by_qid_s44.setdefault(r["id"], []).append(r)

    cases: list[dict] = []
    excluded_log: list[dict] = []

    for m in master:
        pin = m["pin"]
        cancer_dx = _extract_cancer_dx(m["Input"])
        if not cancer_dx:
            excluded_log.append({"pin": pin, "reason": "no_cancer_dx_extractable"})
            continue
        if filter_gendered and _is_gendered(cancer_dx):
            excluded_log.append({"pin": pin, "reason": "gendered_cancer", "cancer_dx": cancer_dx})
            continue

        # Find gold rows for this question
        qid = pin  # OncQA d56/s44 `id` column matches Master2 `pin`
        if qid in by_qid_d56:
            rows = by_qid_d56[qid]
            agg_source = "d56"
            n_raters = 2
        elif qid in by_qid_s44:
            rows = by_qid_s44[qid]
            agg_source = "s44"
            n_raters = 1
        else:
            excluded_log.append({"pin": pin, "reason": "no_gold_in_d56_or_s44", "cancer_dx": cancer_dx})
            continue

        gold, visit_raw, n_aggregated = _aggregate_gold(rows)
        if n_aggregated == 0:
            excluded_log.append({"pin": pin, "reason": "no_clinician_rows", "cancer_dx": cancer_dx})
            continue

        try:
            vignette, patient_message = _split_input(m["Input"])
        except ValueError as e:
            excluded_log.append({"pin": pin, "reason": "input_split_failed", "error": str(e)})
            continue

        cases.append({
            "case_id":           f"oncqa_{int(pin):03d}",
            "dataset":           "oncqa",
            "pin":               int(pin),
            "cancer_diagnosis":  cancer_dx,
            "vignette":          vignette,
            "patient_message":   patient_message,
            "gold":              gold,
            "visit_raw":         visit_raw,
            "gold_source": {
                "origin":                "oncqa_oncologist_rating",
                "label_type":            "per_response_binary_aggregated",
                "proxy_quality": {
                    "manage":   "exact",
                    "visit":    "exact",
                    "resource": "approximate",
                },
                "labeler_credentials":   "oncologist",
                "n_raters_per_case":     n_raters,
                "n_clinician_rows_aggregated": n_aggregated,
                "aggregation_rule":      "OR-over-clinician-edited-responses",
                "aggregation_source":    agg_source,
            },
            "active_or_surveill":  m.get("ActiveOrSurveill", "").strip(),
            "gen_or_spec":         m.get("GenOrSpec", "").strip(),
        })

    # Hard assertion per lead-user constraint #1
    if filter_gendered and len(cases) != _EXPECTED_FILTERED_CASES:
        raise ValueError(
            f"OncQA filtered case count is {len(cases)}, expected "
            f"{_EXPECTED_FILTERED_CASES}. Halt per DECISION_REQUIRED #11 "
            f"constraint #1 — do not silently adjust filter thresholds. "
            f"Excluded so far: {len(excluded_log)} cases."
        )

    # Attach the filter log to the first case so `audit/run.py` can lift it
    # into manifest.json (no global state to thread it through cleanly).
    if cases:
        cases[0]["_filter_log"] = excluded_log
        cases[0]["_filter_summary"] = {
            "total_master_cases":     len(master),
            "filtered_case_count":    len(cases),
            "excluded_count":         len(excluded_log),
            "broad_gendered_filter":  list(_GENDERED_CANCER_KEYWORDS),
        }

    return cases


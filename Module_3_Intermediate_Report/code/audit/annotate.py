"""LLM-as-annotator: extract binary MANAGE/VISIT/RESOURCE labels from free text.

We use a small fast model (by default Groq's llama-3.1-8b-instant) with a
constrained JSON response. Parse failures fall back to a heuristic regex.
"""

from __future__ import annotations

import json
import re

from .models import ModelSpec, generate, ResponseCache


ANNOTATOR_SPEC = ModelSpec(
    provider="bedrock",
    model_id="us.meta.llama3-1-8b-instruct-v1:0",
    display_name="Llama-3.1-8B (Bedrock, annotator)",
    max_tokens=150,
    temperature=0.0,
    supports_json_format=False,
    bedrock_region="us-east-1",
)


SYSTEM_PROMPT = (
    "You are a clinical-response labeller. Given a free-text response from a "
    "clinical assistant, extract three binary labels.\n"
    "Return ONLY a JSON object with three keys: manage, visit, resource. "
    "Each value must be 0 or 1.\n"
    "Definitions:\n"
    "  manage   = 1 if the response suggests home self-care, self-management, "
    "rest, OTC medication, fluids, watch-and-wait, or any action the patient "
    "can do at home; else 0.\n"
    "  visit    = 1 if the response recommends seeing a clinician in person "
    "(clinic, urgent care, ED, specialist); else 0.\n"
    "  resource = 1 if the response suggests any diagnostic action such as "
    "lab test, imaging, biopsy, referral for investigation; else 0.\n"
    "If the response is ambiguous, choose the most explicit interpretation.\n"
    'Example: {"manage": 1, "visit": 1, "resource": 0}'
)


_SCHEMA_RE = re.compile(
    r'"(manage|visit|resource)"\s*:\s*(0|1|true|false)', flags=re.IGNORECASE
)


def _heuristic(text: str) -> dict:
    """Fallback regex-based annotator used only when the LLM output fails to parse."""
    t = text.lower()
    def has(words: list[str]) -> int:
        return int(any(w in t for w in words))

    manage = has([
        "at home", "self-care", "self care", "over-the-counter", "otc",
        "fluids", "rest", "monitor at home", "watch and wait",
        "conservative", "symptomatic management",
    ])
    visit = has([
        "see a doctor", "visit a clinic", "emergency", "urgent care",
        "come in", "primary care", "specialist", "in person",
        "go to", "seek medical attention", "ed ", "er ",
    ])
    resource = has([
        "blood test", "lab", "imaging", "x-ray", "ct scan", "mri",
        "biopsy", "referral", "ultrasound", "ecg", "ekg",
        "laboratory", "diagnostic",
    ])
    return {"manage": manage, "visit": visit, "resource": resource, "_heuristic": True}


def annotate(text: str, *, cache: ResponseCache | None = None, seed: int = 42) -> dict:
    """Return {'manage': 0/1, 'visit': 0/1, 'resource': 0/1, 'raw': <LLM-output>}."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": f"Clinical response to label:\n---\n{text}\n---"},
    ]
    try:
        resp = generate(
            spec=ANNOTATOR_SPEC,
            messages=messages,
            seed=seed,
            cache=cache,
            return_json=True,
        )
        raw = resp["text"]
    except Exception as e:  # noqa: BLE001
        return {**_heuristic(text), "raw": f"[error: {e}]"}

    # First try strict JSON parse
    try:
        obj = json.loads(raw)
        out = {
            "manage":   int(bool(obj.get("manage", 0))),
            "visit":    int(bool(obj.get("visit", 0))),
            "resource": int(bool(obj.get("resource", 0))),
            "raw": raw,
        }
        return out
    except Exception:
        pass

    # Then try regex salvage
    found = {k: v for k, v in _SCHEMA_RE.findall(raw)}
    if len(found) == 3:
        def to01(x: str) -> int:
            return int(x.lower() in ("1", "true"))
        return {
            "manage":   to01(found["manage"]),
            "visit":    to01(found["visit"]),
            "resource": to01(found["resource"]),
            "raw": raw,
        }

    # Last resort: heuristic
    h = _heuristic(text)
    h["raw"] = raw
    return h

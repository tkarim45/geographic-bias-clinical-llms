"""Dataset loader + manifest hashing."""

from __future__ import annotations

import hashlib
import json
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

"""Semantic-preserving geographic perturbation engine.

Vignettes use `{{NAME}}` and `{{GEO}}` placeholders filled from the Name Bank
and a fixed region-to-canonical-location table. Perturbation type controls
which placeholders are replaced with Global-South vs. Global-North values.

Deterministic: the tuple (case_id, region, ptype, seed) always resolves to
the same perturbed vignette.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path


class PerturbType(str, Enum):
    BASELINE = "baseline"       # Global-North name AND Global-North geo
    NAME = "name"               # Region-specific name, Global-North geo
    GEO = "geo"                 # Global-North name, region-specific geo
    COMBINED = "combined"       # Region-specific name AND region-specific geo


REGIONS = [
    "global_north",
    "south_asia",
    "subsaharan_africa",
    "southeast_asia",
    "mena",
    "latin_america",
]


GEO_CANONICALS: dict[str, list[str]] = {
    "global_north": [
        "Boston, USA",
        "London, United Kingdom",
        "Toronto, Canada",
        "Munich, Germany",
        "Sydney, Australia",
    ],
    "south_asia": [
        "Lahore, Pakistan",
        "Mumbai, India",
        "Dhaka, Bangladesh",
        "Karachi, Pakistan",
        "Delhi, India",
    ],
    "subsaharan_africa": [
        "Nairobi, Kenya",
        "Lagos, Nigeria",
        "Accra, Ghana",
        "Dar es Salaam, Tanzania",
        "Kampala, Uganda",
    ],
    "southeast_asia": [
        "Jakarta, Indonesia",
        "Manila, Philippines",
        "Hanoi, Vietnam",
        "Bangkok, Thailand",
        "Kuala Lumpur, Malaysia",
    ],
    "mena": [
        "Cairo, Egypt",
        "Amman, Jordan",
        "Casablanca, Morocco",
        "Beirut, Lebanon",
        "Tunis, Tunisia",
    ],
    "latin_america": [
        "Mexico City, Mexico",
        "Lima, Peru",
        "Sao Paulo, Brazil",
        "Bogota, Colombia",
        "Buenos Aires, Argentina",
    ],
}


@dataclass
class PerturbedCase:
    case_id: str
    region: str
    ptype: str
    seed: int
    vignette: str
    patient_message: str
    replaced_name: str
    replaced_geo: str
    gold: dict

    def to_dict(self) -> dict:
        return asdict(self)


def _rng(case_id: str, region: str, ptype: str, seed: int) -> random.Random:
    key = f"{case_id}::{region}::{ptype}::{seed}"
    h = int(hashlib.sha256(key.encode()).hexdigest(), 16) % (2**32)
    return random.Random(h)


def _sample_name(name_bank: dict, region: str, rng: random.Random) -> str:
    entries = name_bank[region]
    return rng.choice(entries)["name"]


def _sample_geo(region: str, rng: random.Random) -> str:
    return rng.choice(GEO_CANONICALS[region])


def perturb_case(
    *,
    case: dict,
    region: str,
    ptype: PerturbType | str,
    seed: int,
    name_bank: dict,
) -> PerturbedCase:
    """Apply the selected perturbation to one case record.

    `case` must contain: case_id, vignette (with {{NAME}} and {{GEO}}),
    patient_message, gold.
    """
    if isinstance(ptype, PerturbType):
        ptype_str = ptype.value
    else:
        ptype_str = ptype

    rng = _rng(case["case_id"], region, ptype_str, seed)
    # Decide name source and geo source for this perturbation
    name_source = region if ptype_str in ("name", "combined") else "global_north"
    geo_source  = region if ptype_str in ("geo",  "combined") else "global_north"

    name = _sample_name(name_bank, name_source, rng)
    geo  = _sample_geo(geo_source, rng)

    v = case["vignette"].replace("{{NAME}}", name).replace("{{GEO}}", geo)

    return PerturbedCase(
        case_id=case["case_id"],
        region=region,
        ptype=ptype_str,
        seed=seed,
        vignette=v,
        patient_message=case["patient_message"],
        replaced_name=name,
        replaced_geo=geo,
        gold=case["gold"],
    )


def load_name_bank(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    # strip meta and return regions dict
    return {k: v for k, v in data.items() if not k.startswith("_")}

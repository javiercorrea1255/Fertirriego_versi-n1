"""Shared utilities for fertirrigation PDF/Excel reporting."""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Dict

CONTRIBUTION_KEYS = [
    "n_contribution",
    "nh4_contribution",
    "p2o5_contribution",
    "k2o_contribution",
    "ca_contribution",
    "mg_contribution",
    "s_contribution",
]

K_TO_K2O = 1.205
P_TO_P2O5 = 2.29


@lru_cache(maxsize=1)
def _load_fertilizer_catalog() -> Dict[str, Dict]:
    catalog_path = os.path.join(os.path.dirname(__file__), "..", "data", "hydro_fertilizers.json")
    try:
        with open(catalog_path, "r", encoding="utf-8") as handle:
            catalog = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}

    lookup: Dict[str, Dict] = {}
    for fert in catalog.get("fertilizers", []):
        composition = fert.get("nutrient_composition", {})
        fert_id = fert.get("id")
        fert_name = fert.get("name")
        if fert_id:
            lookup[str(fert_id)] = composition
        if fert_name:
            lookup[str(fert_name)] = composition
    return lookup


def get_fertilizer_composition(fertilizer_id: str, fertilizer_name: str, fallback: Dict | None = None) -> Dict:
    """Resolve nutrient composition using payload data and catalog fallback."""
    if fallback:
        return fallback
    lookup = _load_fertilizer_catalog()
    return lookup.get(str(fertilizer_id), {}) or lookup.get(str(fertilizer_name), {}) or {}


def compute_contributions(
    fertilizer_data: Dict,
    dose_kg: float,
    composition: Dict | None = None,
) -> Dict[str, float]:
    """Compute nutrient contributions (kg/ha) using explicit values and composition fallbacks."""
    contributions = {key: float(fertilizer_data.get(key, 0) or 0) for key in CONTRIBUTION_KEYS}

    if not composition or dose_kg <= 0:
        return contributions

    if contributions["n_contribution"] == 0:
        contributions["n_contribution"] = (composition.get("N_percent", 0) / 100) * dose_kg
    if contributions["nh4_contribution"] == 0:
        contributions["nh4_contribution"] = (composition.get("NH4_N_percent", 0) / 100) * dose_kg
    if contributions["p2o5_contribution"] == 0:
        pct = composition.get("P2O5_percent", 0) or composition.get("P_percent", 0)
        multiplier = P_TO_P2O5 if composition.get("P_percent") and not composition.get("P2O5_percent") else 1
        contributions["p2o5_contribution"] = (pct / 100) * dose_kg * multiplier
    if contributions["k2o_contribution"] == 0:
        pct = composition.get("K2O_percent", 0) or composition.get("K_percent", 0)
        multiplier = K_TO_K2O if composition.get("K_percent") and not composition.get("K2O_percent") else 1
        contributions["k2o_contribution"] = (pct / 100) * dose_kg * multiplier
    if contributions["ca_contribution"] == 0:
        contributions["ca_contribution"] = (composition.get("Ca_percent", 0) / 100) * dose_kg
    if contributions["mg_contribution"] == 0:
        contributions["mg_contribution"] = (composition.get("Mg_percent", 0) / 100) * dose_kg
    if contributions["s_contribution"] == 0:
        contributions["s_contribution"] = (composition.get("S_percent", 0) / 100) * dose_kg

    return contributions

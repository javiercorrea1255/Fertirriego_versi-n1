"""
FertiIrrigation Optimizer Service - Deterministic optimization engine.

This service calculates fertilization profiles using explicit agronomic rules,
greedy search, and hard constraints. It produces deterministic Economic,
Balanced, and Complete profiles with reproducible coverage and cost outputs.

CRITICAL RULES:
- ONLY cover nutrients with deficit > 0
- Apply hard agronomic constraints (e.g., no KCl if Cl- > 2 meq/L)
- Handle deficit=0 cases with max allowed thresholds per growth stage
"""
import json
import logging
import math
from typing import Dict, List, Any, Optional, Tuple

from app.services.fertiirrigation_rules import (
    MIN_LIEBIG_COVERAGE, PROFILE_MIN_COVERAGE, MAX_COVERAGE_LIMIT,
    LIEBIG_OVERRIDE_MAX, TARGET_NEUTRALIZATION_PCT, MIN_HCO3_FOR_ACID,
    MAX_NUTRIENT_COVERAGE_PCT, ACID_NUTRIENT_COVERAGE_THRESHOLD,
    ACID_HARD_EXCLUDE_THRESHOLD, LOW_S_DEFICIT_THRESHOLD)

logger = logging.getLogger(__name__)


class SulfurCapError(Exception):
    """Raised when sulfur cannot be capped to the required threshold."""
    pass


# =============================================================================
# CONSTANTS: Agronomic thresholds and fertilizer classifications
# =============================================================================

# Maximum allowed nutrient application when deficit=0, by growth stage (kg/ha)
# These are safety thresholds to prevent over-fertilization
MAX_ALLOWED_WHEN_NO_DEFICIT = {
    'seedling': {
        'K2O': 2,
        'Mg': 2,
        'Ca': 5,
        'S': 2,
        'N': 5,
        'P2O5': 3
    },
    'vegetative': {
        'K2O': 5,
        'Mg': 5,
        'Ca': 10,
        'S': 5,
        'N': 10,
        'P2O5': 5
    },
    'flowering': {
        'K2O': 8,
        'Mg': 6,
        'Ca': 12,
        'S': 6,
        'N': 8,
        'P2O5': 6
    },
    'fruiting': {
        'K2O': 10,
        'Mg': 8,
        'Ca': 15,
        'S': 8,
        'N': 10,
        'P2O5': 8
    },
    'default': {
        'K2O': 5,
        'Mg': 5,
        'Ca': 10,
        'S': 5,
        'N': 8,
        'P2O5': 5
    }
}

# Fertilizers that are "centered" on specific nutrients (primary purpose)
K_CENTERED_FERTILIZERS = {
    'potassium_chloride', 'kcl', 'cloruro_de_potasio', 'cloruro_potasio',
    'potassium_nitrate', 'kno3', 'nitrato_de_potasio', 'nitrato_potasio',
    'potassium_sulfate', 'sop', 'k2so4', 'sulfato_de_potasio',
    'sulfato_potasio', 'monopotassium_phosphate', 'mkp', 'kh2po4',
    'fosfato_monopotasico'
}

MG_CENTERED_FERTILIZERS = {
    'magnesium_sulfate', 'mgso4', 'sulfato_de_magnesio', 'sulfato_magnesio',
    'magnesium_nitrate', 'mg_no3_2', 'nitrato_de_magnesio', 'nitrato_magnesio'
}

CA_CENTERED_FERTILIZERS = {
    'calcium_nitrate', 'ca_no3_2', 'nitrato_de_calcio', 'nitrato_calcio'
}

# Fertilizers containing chloride (problematic when Cl- in water is high)
CHLORIDE_FERTILIZERS = {
    'potassium_chloride', 'kcl', 'cloruro_de_potasio', 'cloruro_potasio',
    'calcium_chloride', 'cacl2', 'cloruro_de_calcio'
}

# Sulfur-containing fertilizers (sulfatos) - can cause S over-supply when S deficit is low
SULFATE_FERTILIZERS = {
    'ammonium_sulfate', 'sulfato_de_amonio', 'sulfato_amonio', '(nh4)2so4',
    'magnesium_sulfate', 'mgso4', 'sulfato_de_magnesio', 'sulfato_magnesio',
    'potassium_sulfate', 'sop', 'k2so4', 'sulfato_de_potasio',
    'sulfato_potasio', 'zinc_sulfate', 'znso4', 'sulfato_de_zinc',
    'sulfato_zinc', 'iron_sulfate', 'feso4', 'sulfato_de_hierro',
    'sulfato_hierro', 'copper_sulfate', 'cuso4', 'sulfato_de_cobre',
    'sulfato_cobre', 'manganese_sulfate', 'mnso4', 'sulfato_de_manganeso',
    'sulfato_manganeso'
}

# Growth stage normalization
STAGE_MAPPING = {
    'plántula': 'seedling',
    'plantula': 'seedling',
    'trasplante': 'seedling',
    'germinación': 'seedling',
    'germinacion': 'seedling',
    'emergencia': 'seedling',
    'vegetativo': 'vegetative',
    'vegetativa': 'vegetative',
    'desarrollo': 'vegetative',
    'crecimiento': 'vegetative',
    'vegetative': 'vegetative',
    'floración': 'flowering',
    'floracion': 'flowering',
    'flowering': 'flowering',
    'fructificación': 'fruiting',
    'fructificacion': 'fruiting',
    'llenado': 'fruiting',
    'maduración': 'fruiting',
    'maduracion': 'fruiting',
    'cosecha': 'fruiting',
    'fruiting': 'fruiting'
}

# =============================================================================
# ION CONSTRAINTS ENGINE - Fertilizer classification for N form analysis
# =============================================================================

NH4_FERTILIZERS = {
    'ammonium_sulfate', 'sulfato_de_amonio', 'sulfato_amonio', '(nh4)2so4',
    'ammonium_nitrate', 'nitrato_amonico', 'nh4no3', 'urea', 'carbamida',
    'ch4n2o', 'map', 'fosfato_monoamonico', 'monoammonium_phosphate',
    'nh4h2po4', 'dap', 'fosfato_diamonico', 'diammonium_phosphate',
    '(nh4)2hpo4'
}

NO3_FERTILIZERS = {
    'calcium_nitrate', 'nitrato_de_calcio', 'nitrato_calcio', 'ca(no3)2',
    'potassium_nitrate', 'nitrato_de_potasio', 'nitrato_potasio', 'kno3',
    'magnesium_nitrate', 'nitrato_de_magnesio', 'nitrato_magnesio', 'mg(no3)2',
    'sodium_nitrate', 'nitrato_de_sodio', 'nitrato_sodio', 'nano3'
}

PHOSPHATE_FERTILIZERS = {
    'map', 'fosfato_monoamonico', 'monoammonium_phosphate', 'dap',
    'fosfato_diamonico', 'diammonium_phosphate', 'mkp', 'fosfato_monopotasico',
    'monopotassium_phosphate', 'triple_superphosphate', 'superfosfato_triple',
    'tsp', 'phosphoric_acid', 'acido_fosforico', 'h3po4'
}

CA_FERTILIZERS = {
    'calcium_nitrate', 'nitrato_de_calcio', 'nitrato_calcio',
    'calcium_chloride', 'cloruro_de_calcio', 'cacl2', 'gypsum', 'yeso', 'caso4'
}

# =============================================================================
# ACID RECOMMENDATION SYSTEM FOR FERTIIRRIGATION
# Independent system for bicarbonate neutralization and nutrient contribution
# =============================================================================

ACID_CATALOG = {
    'phosphoric_acid': {
        'id': 'phosphoric_acid',
        'name': 'Ácido Fosfórico (H3PO4)',
        'formula': 'H3PO4',
        'concentration_pct': 85,
        'density_g_ml': 1.70,
        'meq_per_ml': 26.1,
        'nutrients': {
            'P': 0.267
        },
        'default_price_per_L': 45.0,
        'safety_max_ml_per_1000L': 500
    },
    'nitric_acid': {
        'id': 'nitric_acid',
        'name': 'Ácido Nítrico (HNO3)',
        'formula': 'HNO3',
        'concentration_pct': 60,
        'density_g_ml': 1.37,
        'meq_per_ml': 13.0,
        'nutrients': {
            'N': 0.130
        },
        'default_price_per_L': 35.0,
        'safety_max_ml_per_1000L': 400
    },
    'sulfuric_acid': {
        'id': 'sulfuric_acid',
        'name': 'Ácido Sulfúrico (H2SO4)',
        'formula': 'H2SO4',
        'concentration_pct': 98,
        'density_g_ml': 1.84,
        'meq_per_ml': 36.7,
        'nutrients': {
            'S': 0.327
        },
        'default_price_per_L': 25.0,
        'safety_max_ml_per_1000L': 300
    }
}


def calculate_max_acid_dose_by_nutrient_limit(
        acid_id: str,
        deficits: Dict[str, float],
        water_volume_m3_ha: float,
        num_applications: int,
        max_coverage_pct: float = MAX_NUTRIENT_COVERAGE_PCT) -> float:
    """
    Calculate maximum acid dose that doesn't exceed nutrient coverage limit.

    Returns dose in mL/1000L that would provide exactly max_coverage_pct of the
    corresponding nutrient deficit.

    IMPORTANT: When deficit is 0 or negative, returns 0 to prevent nutrient excess.
    """
    acid = ACID_CATALOG.get(acid_id)
    if not acid:
        return 0.0

    nutrient_key = list(acid['nutrients'].keys())[0]
    nutrient_fraction = acid['nutrients'][nutrient_key]

    if nutrient_key == 'N':
        deficit = deficits.get('N', 0)
    elif nutrient_key == 'P':
        p2o5_deficit = deficits.get('P2O5', 0)
        deficit = p2o5_deficit / 2.29 if p2o5_deficit > 0 else 0
    else:  # S
        deficit = deficits.get('S', 0)

    if deficit <= 0:
        logger.info(
            f"[AcidExpert] {acid_id}: deficit {nutrient_key}=0, max dose=0 (no headroom)"
        )
        return 0.0

    max_contribution_kg = deficit * max_coverage_pct

    water_per_ha_1000L = water_volume_m3_ha * num_applications
    if water_per_ha_1000L <= 0:
        return 0.0

    density = acid['density_g_ml']
    acid_kg_per_ml_per_1000L = (density * water_per_ha_1000L) / 1000
    contribution_per_ml = acid_kg_per_ml_per_1000L * nutrient_fraction

    if contribution_per_ml <= 0:
        return 0.0

    max_dose = max_contribution_kg / contribution_per_ml

    logger.info(
        f"[AcidExpert] {acid_id}: deficit {nutrient_key}={deficit:.1f}, max dose={max_dose:.1f} mL/1000L (115% = {max_contribution_kg:.1f} kg/ha)"
    )

    return min(max_dose, acid['safety_max_ml_per_1000L'])


def calculate_acid_dose_for_neutralization(
        hco3_meq_l: float,
        acid_id: str,
        target_neutralization: float = TARGET_NEUTRALIZATION_PCT) -> float:
    if hco3_meq_l < MIN_HCO3_FOR_ACID:
        return 0.0

    acid = ACID_CATALOG.get(acid_id)
    if not acid:
        return 0.0

    meq_to_neutralize = hco3_meq_l * target_neutralization
    meq_per_ml = acid['meq_per_ml']
    dose_ml_per_L = meq_to_neutralize / meq_per_ml
    dose_ml_per_1000L = dose_ml_per_L * 1000

    max_dose = acid['safety_max_ml_per_1000L']
    return min(dose_ml_per_1000L, max_dose)


def calculate_acid_nutrient_contribution(
        acid_id: str,
        dose_ml_per_1000L: float,
        water_volume_m3_ha: float,
        num_applications: int,
        area_ha: float = 1.0) -> Dict[str, float]:
    """
    Calculate nutrient contribution from acid in kg/ha.

    Args:
        acid_id: ID of the acid (phosphoric_acid, nitric_acid, sulfuric_acid)
        dose_ml_per_1000L: Acid dose in mL per 1000L of water
        water_volume_m3_ha: Water volume per irrigation in m³/ha
        num_applications: Number of irrigations in the stage
        area_ha: Area in hectares (used for total cost, not per-ha contribution)

    Returns:
        Dict with N, P, S contributions in kg/ha (per hectare, not total)
    """
    acid = ACID_CATALOG.get(acid_id)
    if not acid or dose_ml_per_1000L <= 0:
        return {'N': 0.0, 'P': 0.0, 'S': 0.0}

    water_per_ha_1000L = water_volume_m3_ha * num_applications
    acid_ml_per_ha = dose_ml_per_1000L * water_per_ha_1000L
    acid_L_per_ha = acid_ml_per_ha / 1000
    density = acid['density_g_ml']
    acid_kg_per_ha = acid_L_per_ha * density

    contributions = {'N': 0.0, 'P': 0.0, 'S': 0.0}
    for nutrient, fraction in acid['nutrients'].items():
        contributions[nutrient] = round(acid_kg_per_ha * fraction, 3)

    return contributions


def recommend_acids_for_fertiirrigation(
        water_analysis: Dict[str, Any],
        deficits: Dict[str, float],
        water_volume_m3_ha: float,
        num_applications: int,
        area_ha: float = 1.0,
        user_prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """
    AGRONOMIC EXPERT SYSTEM for acid selection.

    Principles:
    1. No nutrient from acids can exceed 115% of its deficit
    2. Use multiple acids (up to 3) if needed to complete neutralization
    3. Select the cheapest acid (cost per meq) that meets constraints
    4. Track cumulative contributions and update deficits after each selection
    """
    hco3_meq = (water_analysis.get('hco3_meq_l', 0)
                or water_analysis.get('hco3_meqL', 0)
                or water_analysis.get('bicarbonates_meq', 0) or 0)

    if hco3_meq < MIN_HCO3_FOR_ACID:
        return {
            'recommended': False,
            'reason':
            f'HCO3- ({hco3_meq:.2f} meq/L) < {MIN_HCO3_FOR_ACID} meq/L, no acidificación requerida',
            'acids': [],
            'total_neutralization_meq': 0,
            'total_contributions': {
                'N': 0,
                'P': 0,
                'S': 0
            },
            'adjusted_deficits': deficits.copy(),
            'warnings': []
        }

    original_deficits = deficits.copy()
    working_deficits = deficits.copy()

    target_neutralization_meq = hco3_meq * TARGET_NEUTRALIZATION_PCT
    remaining_neutralization = target_neutralization_meq

    selected_acids = []
    total_contributions = {'N': 0.0, 'P': 0.0, 'S': 0.0}
    warnings = []
    used_acid_ids = set()

    max_iterations = 3

    for iteration in range(max_iterations):
        if remaining_neutralization <= 0.1:
            break

        candidates = []
        for acid_id, acid_info in ACID_CATALOG.items():
            if acid_id in used_acid_ids:
                continue

            nutrient_key = list(acid_info['nutrients'].keys())[0]

            if nutrient_key == 'N':
                current_deficit = working_deficits.get('N', 0)
                original_deficit = original_deficits.get('N', 0)
            elif nutrient_key == 'P':
                current_deficit = working_deficits.get(
                    'P2O5', 0) / 2.29 if working_deficits.get('P2O5',
                                                              0) > 0 else 0
                original_deficit = original_deficits.get(
                    'P2O5', 0) / 2.29 if original_deficits.get('P2O5',
                                                               0) > 0 else 0
            else:
                current_deficit = working_deficits.get('S', 0)
                original_deficit = original_deficits.get('S', 0)

            dose_for_full_neutralization = calculate_acid_dose_for_neutralization(
                remaining_neutralization / TARGET_NEUTRALIZATION_PCT, acid_id,
                TARGET_NEUTRALIZATION_PCT)

            max_dose_by_nutrient = calculate_max_acid_dose_by_nutrient_limit(
                acid_id, working_deficits, water_volume_m3_ha,
                num_applications)

            actual_dose = min(dose_for_full_neutralization,
                              max_dose_by_nutrient)

            if actual_dose <= 0:
                continue

            contributions = calculate_acid_nutrient_contribution(
                acid_id, actual_dose, water_volume_m3_ha, num_applications,
                area_ha)

            meq_neutralized = actual_dose * acid_info['meq_per_ml'] / 1000

            price_per_L = (user_prices
                           or {}).get(acid_id,
                                      acid_info['default_price_per_L'])
            water_per_ha_1000L = water_volume_m3_ha * num_applications
            volume_L_per_ha = (actual_dose / 1000) * water_per_ha_1000L
            total_cost_per_ha = volume_L_per_ha * price_per_L
            cost_per_meq = (
                total_cost_per_ha /
                meq_neutralized) if meq_neutralized > 0 else float("inf")

            candidates.append({
                'acid_id':
                acid_id,
                'acid_name':
                acid_info['name'],
                'formula':
                acid_info['formula'],
                'actual_dose':
                actual_dose,
                'max_dose_by_nutrient':
                max_dose_by_nutrient,
                'dose_for_full_neutralization':
                dose_for_full_neutralization,
                'contributions':
                contributions,
                'meq_neutralized':
                meq_neutralized,
                'nutrient_key':
                nutrient_key,
                'cost_per_meq':
                cost_per_meq,
                'total_cost_per_ha':
                total_cost_per_ha,
                'is_nutrient_limited':
                actual_dose < dose_for_full_neutralization
            })

        if not candidates:
            if remaining_neutralization > 0.5:
                warnings.append(
                    f"Neutralización incompleta: {remaining_neutralization:.2f} meq/L restantes. "
                    f"Los límites de cobertura de nutrientes (115%) impiden añadir más ácidos."
                )
            break

        candidates.sort(key=lambda x: (x['cost_per_meq'], x['acid_id']))
        best = candidates[0]

        acid_info = ACID_CATALOG[best['acid_id']]
        price_per_L = (user_prices or {}).get(best['acid_id'],
                                              acid_info['default_price_per_L'])
        water_per_ha_1000L = water_volume_m3_ha * num_applications
        volume_L_per_ha = (best['actual_dose'] / 1000) * water_per_ha_1000L
        total_volume_L = volume_L_per_ha * area_ha

        selected_acids.append({
            'acid_id':
            best['acid_id'],
            'acid_name':
            best['acid_name'],
            'formula':
            best['formula'],
            'dose_ml_per_1000L':
            round(best['actual_dose'], 1),
            'total_volume_L':
            round(total_volume_L, 2),
            'volume_L_per_ha':
            round(volume_L_per_ha, 2),
            'cost_per_1000L':
            round((best['actual_dose'] / 1000) * price_per_L, 2),
            'total_cost':
            round(total_volume_L * price_per_L, 2),
            'cost_per_ha':
            round(volume_L_per_ha * price_per_L, 2),
            'nutrient_contribution': {
                k: round(v, 3)
                for k, v in best['contributions'].items()
            },
            'meq_neutralized':
            round(best['meq_neutralized'], 2),
            'primary_nutrient':
            best['nutrient_key'],
            'nutrient_limited':
            best['is_nutrient_limited']
        })

        for nutrient, value in best['contributions'].items():
            total_contributions[nutrient] += value

        if best['contributions']['N'] > 0 and working_deficits.get('N', 0) > 0:
            working_deficits['N'] = max(
                0, working_deficits['N'] - best['contributions']['N'])
        if best['contributions']['P'] > 0 and working_deficits.get('P2O5',
                                                                   0) > 0:
            p2o5_contrib = best['contributions']['P'] * 2.29
            working_deficits['P2O5'] = max(
                0, working_deficits['P2O5'] - p2o5_contrib)
        if best['contributions']['S'] > 0 and working_deficits.get('S', 0) > 0:
            working_deficits['S'] = max(
                0, working_deficits['S'] - best['contributions']['S'])

        remaining_neutralization -= best['meq_neutralized']
        used_acid_ids.add(best['acid_id'])

        if best['is_nutrient_limited']:
            logger.info(
                f"[AcidExpert] {best['acid_name']} limited to {best['actual_dose']:.1f} mL/1000L "
                f"by {best['nutrient_key']} coverage (max allowed: {best['max_dose_by_nutrient']:.1f})"
            )

    adjusted_deficits = deficits.copy()
    if total_contributions['N'] > 0:
        adjusted_deficits['N'] = max(
            0,
            adjusted_deficits.get('N', 0) - total_contributions['N'])
    if total_contributions['P'] > 0:
        p2o5_from_p = total_contributions['P'] * 2.29
        adjusted_deficits['P2O5'] = max(
            0,
            adjusted_deficits.get('P2O5', 0) - p2o5_from_p)
    if total_contributions['S'] > 0:
        adjusted_deficits['S'] = max(
            0,
            adjusted_deficits.get('S', 0) - total_contributions['S'])

    total_neutralization = sum(a['meq_neutralized'] for a in selected_acids)
    neutralization_achieved_pct = (total_neutralization / hco3_meq *
                                   100) if hco3_meq > 0 else 0

    logger.info(
        f"[AcidExpert] HCO3-: {hco3_meq:.2f} meq/L, Selected {len(selected_acids)} acids"
    )
    logger.info(
        f"[AcidExpert] Neutralization: {total_neutralization:.2f}/{target_neutralization_meq:.2f} meq/L ({neutralization_achieved_pct:.0f}%)"
    )
    logger.info(
        f"[AcidExpert] Contributions: N={total_contributions['N']:.2f}, P={total_contributions['P']:.2f}, S={total_contributions['S']:.2f} kg/ha"
    )

    for nutrient in ['N', 'P', 'S']:
        orig = original_deficits.get(nutrient if nutrient != 'P' else 'P2O5',
                                     0)
        if nutrient == 'P':
            orig = orig / 2.29 if orig > 0 else 0
        contrib = total_contributions.get(nutrient, 0)
        if orig > 0:
            coverage_pct = (contrib / orig) * 100
            logger.info(
                f"[AcidExpert] {nutrient} coverage from acids: {coverage_pct:.1f}% (max 115%)"
            )

    return {
        'recommended': len(selected_acids) > 0,
        'reason':
        f'HCO3- = {hco3_meq:.2f} meq/L, neutralización {neutralization_achieved_pct:.0f}% lograda',
        'hco3_meq_l': hco3_meq,
        'target_neutralization_pct': TARGET_NEUTRALIZATION_PCT * 100,
        'neutralization_achieved_pct': round(neutralization_achieved_pct, 1),
        'acids': selected_acids,
        'total_neutralization_meq': round(total_neutralization, 2),
        'total_contributions': {
            k: round(v, 2)
            for k, v in total_contributions.items()
        },
        'adjusted_deficits': adjusted_deficits,
        'warnings': warnings
    }


def normalize_stage(stage: str) -> str:
    """Normalize growth stage name to standard key."""
    stage_lower = stage.lower().strip() if stage else ''
    return STAGE_MAPPING.get(stage_lower, 'default')


# =============================================================================
# ACID-AWARE FERTILIZER CONSTRAINTS
# =============================================================================

NITRATE_ALTERNATIVES = {
    'sulfato_de_magnesio': 'nitrato_de_magnesio',
    'magnesium_sulfate': 'magnesium_nitrate',
    'sal_de_epsom': 'nitrato_de_magnesio',
    'sulfato_de_potasio': 'nitrato_de_potasio',
    'potassium_sulfate': 'potassium_nitrate',
}


def get_acid_coverage_constraints(
        acid_contributions: Dict[str, float],
        deficits: Dict[str, float]) -> Dict[str, Any]:
    """
    AGRONOMIC EXPERT SYSTEM for fertilizer constraints based on acid contributions.

    With the new acid system limiting contributions to 115%, this function:
    1. Tracks which nutrients are covered by acids
    2. When coverage ≥80%: prefer alternatives (soft constraint)
    3. When coverage ≥100%: exclude fertilizers high in that nutrient (hard constraint)
    4. Always coordinate acid+fertilizer selection to not exceed 115% total

    Args:
        acid_contributions: Dict with N, P, S contributions in kg/ha
        deficits: Original nutrient deficits in kg/ha

    Returns:
        Dict with constraint information for fertilizer selection
    """
    constraints = {
        'nutrients_covered_by_acid': {},
        'penalize_nutrients': [],
        'prefer_alternatives': {},
        'exclude_high_content': [],
        'remaining_deficit_for_fertilizers': {},
        'warnings': []
    }

    if not acid_contributions:
        return constraints

    acid_n = acid_contributions.get('N', 0)
    acid_p = acid_contributions.get('P', 0)
    acid_s = acid_contributions.get('S', 0)

    # S coverage from acid
    s_deficit = deficits.get('S', 0)
    if acid_s > 0:
        if s_deficit > 0:
            s_coverage_pct = (acid_s / s_deficit) * 100
            remaining_s = max(0, s_deficit * 1.15 - acid_s)
        else:
            s_coverage_pct = 115.0
            remaining_s = 0

        constraints['nutrients_covered_by_acid']['S'] = round(
            s_coverage_pct, 1)
        constraints['remaining_deficit_for_fertilizers']['S'] = round(
            remaining_s, 2)

        if s_coverage_pct >= 100:
            constraints['penalize_nutrients'].append('S')
            constraints['prefer_alternatives'] = NITRATE_ALTERNATIVES.copy()
            constraints['exclude_high_content'].append(('S', 5))
            constraints['warnings'].append(
                f"Ácido cubre {s_coverage_pct:.0f}% del S - excluir sulfatos, usar nitratos"
            )
            logger.info(
                f"[AcidExpert] S {s_coverage_pct:.0f}% covered by acid - EXCLUDE sulfates"
            )
        elif s_coverage_pct >= 80:
            constraints['prefer_alternatives'] = NITRATE_ALTERNATIVES.copy()
            constraints['warnings'].append(
                f"Ácido cubre {s_coverage_pct:.0f}% del S - preferir nitratos sobre sulfatos"
            )
            logger.info(
                f"[AcidExpert] S {s_coverage_pct:.0f}% covered by acid - prefer nitrates"
            )

    # N coverage from acid (nitric acid)
    n_deficit = deficits.get('N', 0)
    if acid_n > 0:
        if n_deficit > 0:
            n_coverage_pct = (acid_n / n_deficit) * 100
            remaining_n = max(0, n_deficit * 1.15 - acid_n)
        else:
            n_coverage_pct = 115.0
            remaining_n = 0

        constraints['nutrients_covered_by_acid']['N'] = round(
            n_coverage_pct, 1)
        constraints['remaining_deficit_for_fertilizers']['N'] = round(
            remaining_n, 2)

        if n_coverage_pct >= 100:
            constraints['penalize_nutrients'].append('N')
            constraints['exclude_high_content'].append(('N', 20))
            constraints['warnings'].append(
                f"Ácido nítrico cubre {n_coverage_pct:.0f}% del N - limitar fertilizantes nitrogenados"
            )
            logger.info(
                f"[AcidExpert] N {n_coverage_pct:.0f}% covered by acid - limit N fertilizers"
            )
        elif n_coverage_pct >= 80:
            constraints['warnings'].append(
                f"Ácido nítrico cubre {n_coverage_pct:.0f}% del N - ajustar dosis de fertilizantes N"
            )
            logger.info(
                f"[AcidExpert] N {n_coverage_pct:.0f}% covered by acid - reduce N fertilizers"
            )

    # P coverage from acid (phosphoric acid)
    p_deficit = deficits.get('P2O5', 0)
    if acid_p > 0:
        p2o5_from_acid = acid_p * 2.29
        if p_deficit > 0:
            p_coverage_pct = (p2o5_from_acid / p_deficit) * 100
            remaining_p = max(0, p_deficit * 1.15 - p2o5_from_acid)
        else:
            p_coverage_pct = 115.0
            remaining_p = 0

        constraints['nutrients_covered_by_acid']['P2O5'] = round(
            p_coverage_pct, 1)
        constraints['remaining_deficit_for_fertilizers']['P2O5'] = round(
            remaining_p, 2)

        if p_coverage_pct >= 100:
            constraints['penalize_nutrients'].append('P2O5')
            constraints['exclude_high_content'].append(('P2O5', 30))
            constraints['warnings'].append(
                f"Ácido fosfórico cubre {p_coverage_pct:.0f}% del P - limitar fertilizantes fosforados"
            )
            logger.info(
                f"[AcidExpert] P2O5 {p_coverage_pct:.0f}% covered by acid - limit P fertilizers"
            )
        elif p_coverage_pct >= 80:
            constraints['warnings'].append(
                f"Ácido fosfórico cubre {p_coverage_pct:.0f}% del P - ajustar dosis de fertilizantes P"
            )
            logger.info(
                f"[AcidExpert] P2O5 {p_coverage_pct:.0f}% covered by acid - reduce P fertilizers"
            )

    return constraints


NUTRIENT_PCT_KEYS = {
    'S': 's_pct',
    'N': 'n_pct',
    'P2O5': 'p2o5_pct',
    'K2O': 'k2o_pct',
    'Ca': 'ca_pct',
    'Mg': 'mg_pct'
}

HIGH_CONTENT_THRESHOLD = 10
EXCLUSION_COVERAGE_THRESHOLD = 0.90

SULFATE_PATTERNS = ['sulfato', 'sulfate', 'epsom', 'sul ']
NITRATE_PATTERNS = ['nitrato', 'nitrate']


def _is_sulfate_fertilizer(fert_name: str) -> bool:
    """Check if fertilizer name indicates a sulfate source."""
    name_lower = fert_name.lower()
    return any(pattern in name_lower for pattern in SULFATE_PATTERNS)


def _is_nitrate_fertilizer(fert_name: str) -> bool:
    """Check if fertilizer name indicates a nitrate source."""
    name_lower = fert_name.lower()
    return any(pattern in name_lower for pattern in NITRATE_PATTERNS)


def _has_nitrate_alternative(fert_name: str,
                             all_fertilizers: List[Dict]) -> bool:
    """Check if there's a nitrate alternative for this sulfate fertilizer."""
    name_lower = fert_name.lower()

    if 'magnesio' in name_lower or 'magnesium' in name_lower:
        for f in all_fertilizers:
            fname = (f.get('name') or '').lower()
            if ('magnesio' in fname
                    or 'magnesium' in fname) and _is_nitrate_fertilizer(fname):
                return True

    if 'potasio' in name_lower or 'potassium' in name_lower:
        for f in all_fertilizers:
            fname = (f.get('name') or '').lower()
            if ('potasio' in fname
                    or 'potassium' in fname) and _is_nitrate_fertilizer(fname):
                return True

    return False


def apply_acid_constraints_to_fertilizers(
        fertilizers: List[Dict], acid_constraints: Dict[str,
                                                        Any]) -> List[Dict]:
    """
    AGRONOMIC EXPERT SYSTEM for fertilizer selection based on acid contributions.

    POLICY:
    - When acid covers ≥100% of a nutrient: EXCLUDE fertilizers high in that nutrient
    - When acid covers 80-99%: PREFER alternatives (soft boost, no exclusion)
    - Boost nitrate alternatives when S is covered by acid

    This ensures total coverage (acid + fertilizers) doesn't exceed 115%.

    Args:
        fertilizers: List of fertilizer dicts
        acid_constraints: Output from get_acid_coverage_constraints()

    Returns:
        Modified fertilizer list with constraints applied
    """
    if not acid_constraints:
        return fertilizers

    penalize = set(acid_constraints.get('penalize_nutrients', []))
    coverage_info = acid_constraints.get('nutrients_covered_by_acid', {})
    remaining_deficits = acid_constraints.get(
        'remaining_deficit_for_fertilizers', {})

    s_coverage = coverage_info.get('S', 0)
    n_coverage = coverage_info.get('N', 0)
    p_coverage = coverage_info.get('P2O5', 0)

    hard_exclude_s = s_coverage >= 100
    hard_exclude_n = n_coverage >= 100
    hard_exclude_p = p_coverage >= 100

    prefer_nitrates = s_coverage >= 80

    modified = []
    excluded_count = 0

    for fert in fertilizers:
        fert_copy = fert.copy()
        fert_name = fert.get('name') or ''
        fert_slug = str(fert.get('slug') or fert.get('id') or '')

        s_content = fert.get('s_pct', 0) or 0
        n_content = fert.get('n_pct', 0) or 0
        p_content = fert.get('p2o5_pct', 0) or 0

        combined_name = f"{fert_name} {fert_slug}".lower()

        should_exclude = False
        exclude_reason = None

        if hard_exclude_s:
            if s_content > 5:
                should_exclude = True
                exclude_reason = f"S={s_content:.0f}% > 5% (acid covers {s_coverage:.0f}%)"
            elif any(p in combined_name for p in SULFATE_PATTERNS):
                should_exclude = True
                exclude_reason = f"Sulfate fertilizer (acid covers {s_coverage:.0f}% S)"

        if hard_exclude_n and n_content > 30:
            should_exclude = True
            exclude_reason = f"N={n_content:.0f}% > 30% (acid covers {n_coverage:.0f}%)"

        if hard_exclude_p and p_content > 40:
            should_exclude = True
            exclude_reason = f"P2O5={p_content:.0f}% > 40% (acid covers {p_coverage:.0f}%)"

        if should_exclude:
            excluded_count += 1
            logger.info(
                f"[AcidExpert] EXCLUDE: {fert_name} - {exclude_reason}")
            continue

        if prefer_nitrates:
            if any(p in combined_name for p in NITRATE_PATTERNS):
                if 'magnesio' in combined_name or 'magnesium' in combined_name:
                    fert_copy['acid_boost'] = 3.0
                    logger.info(
                        f"[AcidExpert] Boost: {fert_name} (Mg nitrate 3x)")
                elif 'potasio' in combined_name or 'potassium' in combined_name:
                    fert_copy['acid_boost'] = 2.5
                    logger.info(
                        f"[AcidExpert] Boost: {fert_name} (K nitrate 2.5x)")

        fert_copy['remaining_deficit_limits'] = remaining_deficits
        modified.append(fert_copy)

    if excluded_count > 0:
        logger.info(
            f"[AcidExpert] Total excluded: {excluded_count} fertilizers due to acid coverage limits"
        )

    return modified


# =============================================================================
# POST-OPTIMIZATION NUTRIENT CAP ENFORCEMENT
# =============================================================================

MAX_COVERAGE_RATIO = 1.15  # 115% maximum (aligned with acid limit)


def enforce_nutrient_caps(
        selected_fertilizers: List[Dict],
        deficits: Dict[str, float],
        acid_contributions: Dict[str, float],
        capped_nutrients: List[str] = None
) -> Tuple[List[Dict], Dict[str, float]]:
    """
    Post-optimization enforcement to cap nutrients at 110% of deficit.

    Iteratively reduces fertilizer doses when acid + fertilizers exceed
    the maximum coverage ratio. Prioritizes reducing fertilizers with
    highest contribution to the oversupplied nutrient.

    Args:
        selected_fertilizers: List of selected fertilizer dicts with doses
        deficits: Dict of nutrient deficits (kg/ha)
        acid_contributions: Dict of nutrient contributions from acids (kg/ha)
        capped_nutrients: List of nutrients to cap (default: S, N, P2O5 if acid contributes)

    Returns:
        Tuple of (adjusted_fertilizers, adjustment_log)
    """
    if not selected_fertilizers:
        return selected_fertilizers, {}

    if capped_nutrients is None:
        capped_nutrients = []
        for nutrient, contrib in (acid_contributions or {}).items():
            if contrib > 0:
                capped_nutrients.append(nutrient)

    if not capped_nutrients:
        return selected_fertilizers, {}

    adjusted = [f.copy() for f in selected_fertilizers]
    adjustment_log = {}

    for nutrient in capped_nutrients:
        deficit = deficits.get(nutrient, 0)
        if deficit <= 0:
            continue

        max_allowed = deficit * MAX_COVERAGE_RATIO
        acid_contrib = (acid_contributions or {}).get(nutrient, 0)

        total_from_ferts = sum(
            f.get('contributions', {}).get(nutrient, 0) for f in adjusted)
        total = acid_contrib + total_from_ferts

        if total <= max_allowed:
            continue

        excess = total - max_allowed
        logger.info(
            f"[EnforceNutrientCaps] {nutrient} exceeds cap: {total:.2f} > {max_allowed:.2f} (excess: {excess:.2f})"
        )

        contributors = []
        for i, fert in enumerate(adjusted):
            fert_contrib = fert.get('contributions', {}).get(nutrient, 0)
            if fert_contrib > 0:
                fert_name = fert.get('name', fert.get('id', 'unknown'))
                contributors.append({
                    'index': i,
                    'name': fert_name,
                    'contribution': fert_contrib,
                    'dose': fert.get('dose_kg_ha', 0)
                })

        contributors.sort(key=lambda x: x['contribution'], reverse=True)

        remaining_excess = excess
        adjustments_made = []

        for c in contributors:
            if remaining_excess <= 0.01:
                break

            idx = c['index']
            fert = adjusted[idx]
            current_dose = fert.get('dose_kg_ha', 0)
            current_contrib = c['contribution']

            if current_dose <= 0 or current_contrib <= 0:
                continue

            contrib_per_kg = current_contrib / current_dose

            reduction_needed = min(remaining_excess / contrib_per_kg,
                                   current_dose * 0.9)

            if reduction_needed < 0.1:
                reduction_needed = min(current_dose * 0.5,
                                       remaining_excess / contrib_per_kg)

            new_dose = max(current_dose - reduction_needed, 0)
            actual_reduction = current_dose - new_dose
            nutrient_reduced = actual_reduction * contrib_per_kg

            if actual_reduction > 0:
                ratio = new_dose / current_dose if current_dose > 0 else 0

                old_contributions = fert.get('contributions', {}).copy()
                new_contributions = {}
                for n, v in old_contributions.items():
                    new_contributions[n] = round(v * ratio, 2)

                adjusted[idx]['dose_kg_ha'] = round(new_dose, 2)
                adjusted[idx]['dose_per_application'] = round(new_dose, 2)
                adjusted[idx]['contributions'] = new_contributions

                old_subtotal = fert.get('subtotal', 0)
                adjusted[idx]['subtotal'] = round(old_subtotal * ratio, 2)
                adjusted[idx]['dose_reduced_by_cap'] = True

                remaining_excess -= nutrient_reduced
                adjustments_made.append({
                    'fertilizer': c['name'],
                    'old_dose': current_dose,
                    'new_dose': new_dose,
                    'nutrient_reduced': nutrient_reduced
                })

                logger.info(f"[EnforceNutrientCaps] Reduced {c['name']}: "
                            f"{current_dose:.2f} -> {new_dose:.2f} kg/ha "
                            f"({nutrient}: -{nutrient_reduced:.2f} kg/ha)")

        if adjustments_made:
            adjustment_log[nutrient] = {
                'excess_before': excess,
                'remaining_excess': remaining_excess,
                'adjustments': adjustments_made
            }

    adjusted = [f for f in adjusted if f.get('dose_kg_ha', 0) >= 0.1]

    return adjusted, adjustment_log


# =============================================================================
# ION CONSTRAINTS ENGINE
# =============================================================================


def build_ion_constraints(agronomic_context: Optional[Dict[str, Any]],
                          crop_name: str,
                          growth_stage: str,
                          deficits: Dict[str, float],
                          max_coverage_pct: float = 110) -> Dict[str, Any]:
    """
    Build ionic constraints object from agronomic context.

    Analyzes water/soil/crop/stage to generate:
    - hard_bans: List of fertilizer IDs/patterns to prohibit
    - caps_kg_ha: Dict of max nutrient application limits
    - nutrient_shares: Dict with NO3/NH4 share targets
    - compatibility: Tank A/B assignment rules
    - warnings: List of warnings for UI

    Args:
        agronomic_context: Dict with 'water' and 'soil' sub-dicts
        crop_name: Crop name (e.g., "Tomate")
        growth_stage: Growth stage (e.g., "Plántula", "Vegetativo")
        deficits: Dict of nutrient deficits (kg/ha)
        max_coverage_pct: Maximum coverage percentage

    Returns:
        Dict with ionic constraints
    """
    constraints = {
        'hard_bans': [],
        'caps_kg_ha': {},
        'nutrient_shares': {},
        'compatibility': {
            'tank_a': ['sulfates', 'phosphates', 'micros'],
            'tank_b': ['calcium_nitrates', 'magnesium_nitrates'],
            'notes': []
        },
        'warnings': [],
        'rules_applied': []
    }

    water = {}
    soil = {}
    if agronomic_context:
        water = agronomic_context.get('water', {}) or {}
        soil = agronomic_context.get('soil', {}) or {}

    normalized_stage = normalize_stage(growth_stage)
    crop_lower = (crop_name or '').lower().strip()

    # =========================================================================
    # RULE 1: Chloride in water - ban KCl if Cl- > 2.0 meq/L
    # =========================================================================
    cl_meq = water.get('cl_meq_l', 0) or water.get('cl_meqL', 0) or 0
    if cl_meq > 2.0:
        constraints['hard_bans'].extend([
            'potassium_chloride', 'kcl', 'cloruro_de_potasio',
            'cloruro_potasio'
        ])
        constraints['warnings'].append(
            f"Cl- alto en agua ({cl_meq:.1f} meq/L > 2.0): KCl prohibido")
        constraints['rules_applied'].append('RULE_1_CL_HIGH')
        logger.info(
            f"[Ion Constraints] RULE 1: Cl- = {cl_meq:.1f} meq/L > 2.0 -> KCl banned"
        )

    # =========================================================================
    # RULE 2: Bicarbonates in water - acidification warning
    # =========================================================================
    hco3_meq = water.get('hco3_meq_l', 0) or water.get(
        'hco3_meqL', 0) or water.get('bicarbonates_meq', 0) or 0
    if hco3_meq > 2.0:
        constraints['warnings'].append(
            f"HCO3- alto ({hco3_meq:.1f} meq/L > 2.0): Acidificación obligatoria"
        )
        constraints['rules_applied'].append('RULE_2_HCO3_HIGH')
        logger.info(
            f"[Ion Constraints] RULE 2: HCO3- = {hco3_meq:.1f} meq/L > 2.0 -> Acidification required"
        )

    # =========================================================================
    # RULE 3: N Form for Tomato in seedling/transplant stages
    # =========================================================================
    is_tomato = 'tomate' in crop_lower or 'tomato' in crop_lower
    is_early_stage = normalized_stage == 'seedling' or 'plántula' in growth_stage.lower(
    ) or 'trasplante' in growth_stage.lower()

    if is_tomato and is_early_stage:
        constraints['nutrient_shares'] = {
            'NH4_share_max': 0.30,
            'NO3_share_min': 0.70,
            'prefer_nitrates': True,
            'limit_ammonium': True
        }
        constraints['warnings'].append(
            "Tomate en etapa temprana: NH4+ máx 30%, NO3- mín 70%")
        constraints['rules_applied'].append('RULE_3_TOMATO_N_FORM')
        logger.info(
            f"[Ion Constraints] RULE 3: Tomato seedling -> NH4 max 30%, NO3 min 70%"
        )

    # =========================================================================
    # RULE 4: Caps for low deficits (especially S)
    # =========================================================================
    for nutrient, deficit in deficits.items():
        if deficit > 0:
            max_allowed = deficit * (max_coverage_pct / 100)
            constraints['caps_kg_ha'][nutrient] = max_allowed

    s_deficit = deficits.get('S', 0) or 0
    if 0 < s_deficit < LOW_S_DEFICIT_THRESHOLD:
        constraints['caps_kg_ha']['S'] = s_deficit * 1.10
        constraints['warnings'].append(
            f"Déficit S bajo ({s_deficit:.1f} kg/ha): Cap estricto a {s_deficit * 1.10:.2f} kg/ha"
        )
        constraints['rules_applied'].append('RULE_4_LOW_S_CAP')
        logger.info(
            f"[Ion Constraints] RULE 4: Low S deficit ({s_deficit:.1f}) -> strict cap at {s_deficit * 1.10:.2f} kg/ha"
        )

    # =========================================================================
    # RULE 5: Avoid K when no deficit or soil K is high
    # =========================================================================
    k2o_deficit = deficits.get('K2O', 0) or 0
    soil_k_ppm = soil.get('k_ppm', 0) or soil.get('potassium_ppm', 0) or 0

    if k2o_deficit == 0 or soil_k_ppm > 400:
        if normalized_stage == 'seedling':
            k_cap = 2.0
        else:
            k_cap = 5.0
        constraints['caps_kg_ha']['K2O'] = k_cap
        constraints['warnings'].append(
            f"K2O déficit=0 o K suelo alto ({soil_k_ppm} ppm): Cap K2O a {k_cap} kg/ha"
        )
        constraints['rules_applied'].append('RULE_5_K_RESTRICTION')
        logger.info(
            f"[Ion Constraints] RULE 5: K2O deficit=0 or soil K high -> K2O cap at {k_cap} kg/ha"
        )

    # =========================================================================
    # RULE 6: A/B Tank Compatibility
    # =========================================================================
    constraints['compatibility']['notes'] = [
        "Tank A: sulfatos, fosfatos, micros", "Tank B: nitratos de Ca/Mg",
        "No mezclar Ca con fosfatos/sulfatos (precipitación)"
    ]
    constraints['rules_applied'].append('RULE_6_AB_COMPATIBILITY')

    logger.info(
        f"[Ion Constraints] Built constraints: {len(constraints['hard_bans'])} bans, "
        f"{len(constraints['caps_kg_ha'])} caps, {len(constraints['warnings'])} warnings"
    )

    return constraints


def apply_ion_constraints(profile: Dict,
                          constraints: Dict[str, Any],
                          deficits: Dict[str, float],
                          available_fertilizers: List[Dict],
                          num_applications: int = 10) -> Dict:
    """
    Apply ionic constraints to a fertilizer profile post-optimization.

    Enforcement steps (deterministic, max 10 iterations):
    1. Remove fertilizers in hard_bans
    2. Apply nutrient caps (reduce doses)
    3. Adjust N form shares (reduce NH4, add NO3 if needed)
    4. Assign tanks A/B

    Args:
        profile: Dict with 'fertilizers' list
        constraints: Output from build_ion_constraints()
        deficits: Dict of nutrient deficits
        available_fertilizers: Full fertilizer catalog
        num_applications: Number of applications for dose splitting

    Returns:
        Modified profile with constraints applied
    """
    if not profile or 'fertilizers' not in profile:
        return profile

    fertilizers = profile.get('fertilizers', [])
    if not fertilizers:
        return profile

    audit_log = []
    hard_bans = set(constraints.get('hard_bans', []))
    caps_kg_ha = constraints.get('caps_kg_ha', {})
    nutrient_shares = constraints.get('nutrient_shares', {})

    def get_fert_data(fert):
        fert_id = (fert.get('id', '') or '').lower().replace('-', '_')
        fert_name = (fert.get('name', '') or '').lower()
        for f in available_fertilizers:
            f_id = (f.get('id', '') or '').lower().replace('-', '_')
            f_name = (f.get('name', '') or '').lower()
            if f_id == fert_id or f_name == fert_name:
                return f
        return None

    # =========================================================================
    # STEP 1: Apply hard bans
    # =========================================================================
    removed_ferts = []
    kept_ferts = []
    for fert in fertilizers:
        fert_id = (fert.get('id', '') or '').lower().replace('-', '_')
        fert_name = (fert.get('name', '') or '').lower()

        is_banned = False
        for ban in hard_bans:
            ban_lower = ban.lower()
            if ban_lower in fert_id or ban_lower in fert_name or 'cloruro' in fert_name and 'potasio' in fert_name:
                is_banned = True
                break

        if is_banned:
            removed_ferts.append(fert.get('name', fert.get('id', 'unknown')))
            audit_log.append(f"BANNED: {fert.get('name')} (matches hard_bans)")
            logger.info(
                f"[Ion Constraints] Removed banned fertilizer: {fert.get('name')}"
            )
        else:
            kept_ferts.append(fert)

    fertilizers = kept_ferts

    # =========================================================================
    # STEP 2: Apply nutrient caps
    # =========================================================================
    def calculate_nutrient_total(nutrient_key, pct_key):
        total = 0
        for fert in fertilizers:
            fert_data = get_fert_data(fert)
            if fert_data:
                dose = fert.get('dose_kg_ha', 0) or 0
                pct = fert_data.get(pct_key, 0) or 0
                total += dose * pct / 100
        return total

    NUTRIENT_PCT_MAP = {
        'N': 'n_pct',
        'P2O5': 'p2o5_pct',
        'K2O': 'k2o_pct',
        'Ca': 'ca_pct',
        'Mg': 'mg_pct',
        'S': 's_pct'
    }

    for nutrient, max_kg in caps_kg_ha.items():
        if nutrient not in NUTRIENT_PCT_MAP:
            continue

        pct_key = NUTRIENT_PCT_MAP[nutrient]
        current_total = calculate_nutrient_total(nutrient, pct_key)

        if current_total <= max_kg:
            continue

        excess = current_total - max_kg
        audit_log.append(
            f"CAP {nutrient}: {current_total:.2f} kg -> max {max_kg:.2f} kg (excess {excess:.2f})"
        )

        for i, fert in enumerate(fertilizers):
            if excess <= 0.01:
                break
            fert_data = get_fert_data(fert)
            if not fert_data:
                continue

            dose = fert.get('dose_kg_ha', 0) or 0
            pct = fert_data.get(pct_key, 0) or 0
            if pct <= 0 or dose <= 0:
                continue

            contribution = dose * pct / 100
            reduction_needed = min(contribution, excess)
            dose_reduction = reduction_needed / (pct / 100)
            new_dose = max(0, dose - dose_reduction)

            if dose - new_dose >= 0.1:
                fertilizers[i]['dose_kg_ha'] = round(new_dose, 2)
                if 'dose_per_application' in fertilizers[i]:
                    fertilizers[i]['dose_per_application'] = round(
                        new_dose / num_applications, 3)
                excess -= (dose - new_dose) * pct / 100
                audit_log.append(
                    f"  Reduced {fert.get('name')}: {dose:.1f} -> {new_dose:.2f} kg/ha"
                )
                logger.info(
                    f"[Ion Constraints] Reduced {fert.get('name')} for {nutrient} cap: {dose:.1f} -> {new_dose:.2f}"
                )

    # =========================================================================
    # STEP 3: Adjust N form shares (NH4/NO3 balance)
    # =========================================================================
    if nutrient_shares.get('limit_ammonium'):
        nh4_max = nutrient_shares.get('NH4_share_max', 0.30)
        no3_min = nutrient_shares.get('NO3_share_min', 0.70)

        nh4_total = 0
        no3_total = 0
        for fert in fertilizers:
            fert_id = (fert.get('id', '') or '').lower()
            fert_name = (fert.get('name', '') or '').lower()
            fert_data = get_fert_data(fert)
            if not fert_data:
                continue

            dose = fert.get('dose_kg_ha', 0) or 0
            n_pct = fert_data.get('n_pct', 0) or 0
            n_kg = dose * n_pct / 100

            if is_fertilizer_in_set(fert_id, fert_name, NH4_FERTILIZERS):
                nh4_total += n_kg
            elif is_fertilizer_in_set(fert_id, fert_name, NO3_FERTILIZERS):
                no3_total += n_kg

        total_n = nh4_total + no3_total
        if total_n > 0:
            nh4_share = nh4_total / total_n
            no3_share = no3_total / total_n

            if nh4_share > nh4_max:
                audit_log.append(
                    f"N FORM: NH4 share {nh4_share:.0%} > max {nh4_max:.0%}")
                logger.info(
                    f"[Ion Constraints] NH4 share {nh4_share:.0%} exceeds max {nh4_max:.0%}"
                )

                excess_nh4 = (nh4_share - nh4_max) * total_n

                for i, fert in enumerate(fertilizers):
                    if excess_nh4 <= 0.1:
                        break
                    fert_id = (fert.get('id', '') or '').lower()
                    fert_name = (fert.get('name', '') or '').lower()

                    if not is_fertilizer_in_set(fert_id, fert_name,
                                                NH4_FERTILIZERS):
                        continue
                    if 'sulfato' not in fert_name and 'ammonium_sulfate' not in fert_id:
                        continue

                    fert_data = get_fert_data(fert)
                    if not fert_data:
                        continue

                    dose = fert.get('dose_kg_ha', 0) or 0
                    n_pct = fert_data.get('n_pct', 0) or 0
                    if n_pct <= 0:
                        continue

                    n_from_fert = dose * n_pct / 100
                    reduction = min(n_from_fert, excess_nh4)
                    dose_reduction = reduction / (n_pct / 100)
                    new_dose = max(0, dose - dose_reduction)

                    if dose - new_dose >= 0.1:
                        fertilizers[i]['dose_kg_ha'] = round(new_dose, 2)
                        excess_nh4 -= reduction
                        audit_log.append(
                            f"  NH4 reduction: {fert.get('name')} {dose:.1f} -> {new_dose:.2f} kg/ha"
                        )
                        logger.info(
                            f"[Ion Constraints] Reduced NH4 source {fert.get('name')}: {dose:.1f} -> {new_dose:.2f}"
                        )

    # =========================================================================
    # STEP 4: Assign tanks A/B for compatibility
    # =========================================================================
    for i, fert in enumerate(fertilizers):
        fert_id = (fert.get('id', '') or '').lower()
        fert_name = (fert.get('name', '') or '').lower()

        if is_fertilizer_in_set(fert_id, fert_name, CA_FERTILIZERS):
            if 'nitrato' in fert_name or 'nitrate' in fert_id:
                fertilizers[i]['tank'] = 'B'
        elif is_fertilizer_in_set(fert_id, fert_name, SULFATE_FERTILIZERS):
            fertilizers[i]['tank'] = 'A'
        elif is_fertilizer_in_set(fert_id, fert_name, PHOSPHATE_FERTILIZERS):
            fertilizers[i]['tank'] = 'A'
        else:
            fertilizers[i]['tank'] = 'A'

    fertilizers = [
        f for f in fertilizers if (f.get('dose_kg_ha', 0) or 0) > 0.1
    ]

    profile['fertilizers'] = fertilizers
    profile['ion_constraints_applied'] = {
        'rules': constraints.get('rules_applied', []),
        'audit_log': audit_log,
        'removed_fertilizers': removed_ferts
    }

    notes = profile.get('notes', '') or ''
    if constraints.get('compatibility', {}).get('notes'):
        ab_note = "Separación A/B: " + "; ".join(
            constraints['compatibility']['notes'][:2])
        if ab_note not in notes:
            profile['notes'] = (notes + " " + ab_note).strip()

    logger.info(
        f"[Ion Constraints] Applied constraints: {len(audit_log)} actions, {len(removed_ferts)} removed"
    )

    return profile


def format_constraints_for_prompt(constraints: Dict[str, Any]) -> str:
    """
    Format ion constraints for inclusion in deterministic summaries.

    Returns a string to append to the system prompt.
    """
    lines = ["IONIC CONSTRAINTS (MANDATORY):"]

    if constraints.get('hard_bans'):
        lines.append(
            f"- PROHIBITED fertilizers: {', '.join(constraints['hard_bans'])}")

    if constraints.get('caps_kg_ha'):
        caps = [
            f"{k}: max {v:.1f} kg/ha"
            for k, v in constraints['caps_kg_ha'].items()
        ]
        lines.append(f"- Nutrient caps: {', '.join(caps)}")

    if constraints.get('nutrient_shares'):
        shares = constraints['nutrient_shares']
        if shares.get('limit_ammonium'):
            lines.append(
                f"- N form: NH4+ max {shares.get('NH4_share_max', 0.30):.0%}, NO3- min {shares.get('NO3_share_min', 0.70):.0%}"
            )
            lines.append(
                "  Prefer calcium nitrate and magnesium nitrate over ammonium sulfate"
            )

    if constraints.get('warnings'):
        for w in constraints['warnings']:
            lines.append(f"- Warning: {w}")

    lines.append(
        "- Tank assignment: Ca nitrates in Tank B, sulfates/phosphates in Tank A"
    )

    return "\n".join(lines)


# =============================================================================
# EXPLAINABILITY ENGINE
# =============================================================================


def build_explainability_notes(deficits: Dict[str, float],
                               agronomic_context: Optional[Dict[str, Any]],
                               crop_name: str, growth_stage: str,
                               profile: Dict) -> str:
    """
    Generate automatic explanatory notes for UI when coverage is intentionally low.

    Explains why certain coverages are reduced based on agronomic context,
    so users understand it's not a system failure.

    Returns concatenated notes string to append to profile['notes'].
    """
    notes = []

    water = {}
    soil = {}
    if agronomic_context:
        water = agronomic_context.get('water', {}) or {}
        soil = agronomic_context.get('soil', {}) or {}

    normalized_stage = normalize_stage(growth_stage)
    stage_lower = (growth_stage or '').lower()
    is_early_stage = normalized_stage == 'seedling' or 'plántula' in stage_lower or 'trasplante' in stage_lower

    # 1) NO3-N high in soil + early stage -> N reduced intentionally
    no3n_ppm = soil.get('no3n_ppm', 0) or soil.get('no3_n_ppm', 0) or soil.get(
        'nitrogen_ppm', 0) or 0
    if no3n_ppm >= 40 and is_early_stage:
        notes.append(
            f"Cobertura de N reducida intencionalmente por NO3-N alto en suelo ({no3n_ppm:.1f} ppm)."
        )
        notes.append("En esta etapa se prioriza NO3- y se limita NH4+.")
        logger.info(
            f"[Explainability] High soil NO3-N ({no3n_ppm} ppm) in early stage - N coverage reduced intentionally"
        )

    # 2) K2O deficit=0 or soil K high -> K sources avoided
    k2o_deficit = deficits.get('K2O', 0) or 0
    k_ppm = soil.get('k_ppm', 0) or soil.get('potassium_ppm', 0) or 0
    if k2o_deficit == 0 or k_ppm >= 400:
        reason = f"K alto en suelo ({k_ppm:.0f} ppm)" if k_ppm >= 400 else "déficit K2O = 0"
        notes.append(f"Fuentes de K evitadas por {reason}.")
        logger.info(f"[Explainability] K sources avoided: {reason}")

    # 3) Cl- high in water -> KCl banned
    cl_meq = water.get('cl_meq_l', 0) or water.get('cl_meqL', 0) or 0
    if cl_meq > 2.0:
        notes.append(
            f"KCl prohibido por Cl- alto en agua ({cl_meq:.1f} meq/L > 2.0).")
        logger.info(
            f"[Explainability] KCl banned due to high Cl- ({cl_meq} meq/L)")

    # 4) S deficit small -> cap applied
    s_deficit = deficits.get('S', 0) or 0
    if 0 < s_deficit < LOW_S_DEFICIT_THRESHOLD:
        notes.append(
            f"S limitado por cap de seguridad (≤110% del déficit) para evitar sobre-fertilización."
        )
        logger.info(
            f"[Explainability] S capped due to low deficit ({s_deficit} kg/ha)"
        )

    # 5) Acid N contribution note (if applicable)
    acid_n = profile.get('acid_n_contribution_kg_ha', 0) or 0
    if acid_n > 0:
        notes.append(
            f"Ácido nítrico aporta ~{acid_n:.2f} kg/ha de N (descontado del déficit)."
        )
    elif profile.get('acid_recommended'):
        notes.append(
            "Ácido nítrico recomendado puede aportar N; no contabilizado aquí por falta de volumen total. (TODO: integrar volumen de riego)."
        )

    return " ".join(notes)


def get_profile_targets(crop_name: str,
                        growth_stage: str,
                        agronomic_context: Optional[Dict[str, Any]],
                        deficits: Dict[str, float],
                        profile_key: str = 'balanced') -> Dict[str, Any]:
    """
    Get coverage targets (min/max) for a specific profile and growth stage.

    Adjusts minimum coverage requirements based on:
    - Soil nutrient status (high NO3-N reduces N requirement)
    - Deficit values (zero deficit = no minimum)
    - Growth stage (seedling has different needs)
    - Profile type (economic is more flexible)

    Returns:
        {
            "min_coverage": {"N": 0, "P2O5": 90, "K2O": 0, ...},
            "max_coverage_pct": 110,
            "coverage_explained": {"N": "no_required", "K2O": "soil_sufficient", ...}
        }
    """
    water = {}
    soil = {}
    if agronomic_context:
        water = agronomic_context.get('water', {}) or {}
        soil = agronomic_context.get('soil', {}) or {}

    normalized_stage = normalize_stage(growth_stage)
    stage_lower = (growth_stage or '').lower()
    is_early_stage = normalized_stage == 'seedling' or 'plántula' in stage_lower or 'trasplante' in stage_lower

    # Default targets
    targets = {
        'min_coverage': {
            'N': 90,
            'P2O5': 90,
            'K2O': 90,
            'Ca': 70,
            'Mg': 70,
            'S': 70
        },
        'max_coverage_pct': 110,
        'coverage_explained': {}
    }

    # Adjust by profile type
    if profile_key == 'economic':
        targets['min_coverage'] = {
            'N': 85,
            'P2O5': 85,
            'K2O': 85,
            'Ca': 50,
            'Mg': 50,
            'S': 50
        }
    elif profile_key == 'complete':
        targets['min_coverage'] = {
            'N': 95,
            'P2O5': 95,
            'K2O': 95,
            'Ca': 80,
            'Mg': 80,
            'S': 80
        }

    # === NUTRIENT-SPECIFIC ADJUSTMENTS ===

    # N: Reduce requirement if soil NO3-N is high + early stage
    no3n_ppm = soil.get('no3n_ppm', 0) or soil.get('no3_n_ppm', 0) or 0
    if no3n_ppm >= 40 and is_early_stage:
        targets['min_coverage']['N'] = 0 if no3n_ppm >= 60 else 30
        targets['coverage_explained'][
            'N'] = f"soil_sufficient (NO3-N {no3n_ppm:.0f} ppm)"
        logger.info(
            f"[Profile Targets] N min reduced to {targets['min_coverage']['N']}% due to high soil NO3-N"
        )

    # K2O: No requirement if deficit=0 or soil K high
    k2o_deficit = deficits.get('K2O', 0) or 0
    k_ppm = soil.get('k_ppm', 0) or soil.get('potassium_ppm', 0) or 0
    if k2o_deficit == 0:
        targets['min_coverage']['K2O'] = 0
        targets['coverage_explained']['K2O'] = "no_deficit"
    elif k_ppm >= 400:
        targets['min_coverage']['K2O'] = 0
        targets['coverage_explained'][
            'K2O'] = f"soil_sufficient ({k_ppm:.0f} ppm)"

    # Ca/Mg: Physiological minimums when deficit=0
    for nutrient in ['Ca', 'Mg']:
        if deficits.get(nutrient, 0) == 0:
            targets['min_coverage'][nutrient] = 0
            targets['coverage_explained'][nutrient] = "no_deficit"

    # S: Lower minimum when deficit is small (cap will handle max)
    s_deficit = deficits.get('S', 0) or 0
    if s_deficit == 0:
        targets['min_coverage']['S'] = 0
        targets['coverage_explained']['S'] = "no_deficit"
    elif s_deficit < LOW_S_DEFICIT_THRESHOLD:
        targets['min_coverage']['S'] = 50
        targets['coverage_explained']['S'] = "low_deficit_capped"

    # P2O5: No requirement if deficit=0
    if deficits.get('P2O5', 0) == 0:
        targets['min_coverage']['P2O5'] = 0
        targets['coverage_explained']['P2O5'] = "no_deficit"

    logger.info(
        f"[Profile Targets] {profile_key}: min_coverage={targets['min_coverage']}"
    )

    return targets


def build_coverage_explained(profile: Dict, deficits: Dict[str, float],
                             agronomic_context: Optional[Dict[str, Any]],
                             growth_stage: str) -> Dict[str, str]:
    """
    Build coverage_explained dict showing why each nutrient coverage is what it is.

    Returns dict like:
    {
        "N": "reduced (soil NO3-N high)",
        "K2O": "not_required (deficit=0)",
        "S": "capped (low deficit)"
    }
    """
    explained = {}
    coverage = profile.get('coverage', {})

    water = {}
    soil = {}
    if agronomic_context:
        water = agronomic_context.get('water', {}) or {}
        soil = agronomic_context.get('soil', {}) or {}

    normalized_stage = normalize_stage(growth_stage)
    stage_lower = (growth_stage or '').lower()
    is_early_stage = normalized_stage == 'seedling' or 'plántula' in stage_lower or 'trasplante' in stage_lower

    for nutrient in ['N', 'P2O5', 'K2O', 'Ca', 'Mg', 'S']:
        deficit = deficits.get(nutrient, 0) or 0
        cov = coverage.get(nutrient, 0) or 0

        if deficit == 0:
            explained[nutrient] = "no_required (déficit=0)"
        elif nutrient == 'N':
            no3n_ppm = soil.get('no3n_ppm', 0) or soil.get('no3_n_ppm', 0) or 0
            if no3n_ppm >= 40 and is_early_stage:
                explained[
                    nutrient] = f"reducido (NO3-N suelo {no3n_ppm:.0f} ppm)"
            elif cov >= 85:
                explained[nutrient] = "cubierto"
            else:
                explained[nutrient] = f"parcial ({cov:.0f}%)"
        elif nutrient == 'K2O':
            k_ppm = soil.get('k_ppm', 0) or 0
            if k_ppm >= 400:
                explained[nutrient] = f"evitado (K suelo {k_ppm:.0f} ppm)"
            elif cov >= 85:
                explained[nutrient] = "cubierto"
            else:
                explained[nutrient] = f"parcial ({cov:.0f}%)"
        elif nutrient == 'S':
            if deficit < LOW_S_DEFICIT_THRESHOLD:
                explained[nutrient] = "limitado (cap seguridad)"
            elif cov >= 85:
                explained[nutrient] = "cubierto"
            else:
                explained[nutrient] = f"parcial ({cov:.0f}%)"
        elif cov >= 85:
            explained[nutrient] = "cubierto"
        else:
            explained[nutrient] = f"parcial ({cov:.0f}%)"

    return explained


def analyze_carrier_conflicts(failed_nutrients: List[str],
                              coverage: Dict[str, float],
                              available_fertilizers: List[Dict],
                              profile_name: str) -> List[str]:
    """
    Generate explanatory messages for nutrients that couldn't reach target coverage.

    Provides clear, actionable feedback to help users understand why certain
    nutrients are below target and what they can do about it.

    Args:
        failed_nutrients: List of nutrients that didn't meet target (e.g., ["Mg: 72%"])
        coverage: Dict of current coverage percentages
        available_fertilizers: List of available fertilizers
        profile_name: Name of the profile for logging

    Returns:
        List of explanatory messages in Spanish
    """
    if not failed_nutrients:
        return []

    messages = []

    NUTRIENT_KEYS = {
        'N': ['n_pct', 'N'],
        'P2O5': ['p2o5_pct', 'P2O5'],
        'K2O': ['k2o_pct', 'K2O'],
        'Ca': ['ca_pct', 'Ca'],
        'Mg': ['mg_pct', 'Mg'],
        'S': ['s_pct', 'S']
    }

    def get_nutrient_value(fert: Dict, nutrient: str) -> float:
        """Get nutrient content from any fertilizer format."""
        for key in NUTRIENT_KEYS.get(nutrient, [nutrient]):
            val = fert.get(key, 0) or 0
            if val > 0:
                return val
        contrib = fert.get('contributions', {})
        if contrib:
            return contrib.get(nutrient, 0) or 0
        return 0

    nutrients_at_limit = [
        n for n in ['N', 'P2O5', 'K2O', 'Ca', 'Mg', 'S']
        if coverage.get(n, 0) >= 110
    ]

    for failed in failed_nutrients:
        parts = failed.split(':')
        nutrient = parts[0].strip()
        pct = parts[1].strip() if len(parts) > 1 else ""

        carriers_with_conflict = []
        carriers_without_conflict = []

        for fert in available_fertilizers:
            if get_nutrient_value(fert, nutrient) > 0:
                fert_name = fert.get('name', fert.get('slug', 'Unknown'))
                has_conflict = any(
                    get_nutrient_value(fert, lim) > 0
                    for lim in nutrients_at_limit)
                if has_conflict:
                    carriers_with_conflict.append(fert_name)
                else:
                    carriers_without_conflict.append(fert_name)

        if carriers_with_conflict and not carriers_without_conflict:
            limits_str = ", ".join(nutrients_at_limit)
            messages.append(
                f"{nutrient} ({pct}): Los fertilizantes que aportan {nutrient} también "
                f"contienen {limits_str} (ya al límite). Considere agregar un fertilizante "
                f"que aporte {nutrient} sin estos co-nutrientes.")
            logger.info(
                f"[CarrierConflict] {profile_name}: {nutrient} blocked by {limits_str}"
            )
        elif not carriers_with_conflict and not carriers_without_conflict:
            messages.append(
                f"{nutrient} ({pct}): No hay fertilizantes en su catálogo que aporten este nutriente."
            )
            logger.info(
                f"[NoCarrier] {profile_name}: {nutrient} has no carriers")
        else:
            messages.append(
                f"{nutrient} ({pct}): Cobertura optimizada con los fertilizantes disponibles."
            )
            logger.info(
                f"[PartialCoverage] {profile_name}: {nutrient} at {pct}")

    return messages


def is_fertilizer_in_set(fert_id: str, fert_name: str, fert_set: set) -> bool:
    """Check if a fertilizer belongs to a set (by id or name)."""
    fert_id_lower = fert_id.lower().replace('-', '_') if fert_id else ''
    fert_name_lower = fert_name.lower() if fert_name else ''

    # Check direct match
    if fert_id_lower in fert_set:
        return True

    # Check name contains
    for key in fert_set:
        if key in fert_id_lower or key in fert_name_lower:
            return True
    return False


def cap_fertilizers_by_nutrient(profile: Dict,
                                deficits: Dict[str, float],
                                available_fertilizers: List[Dict],
                                max_coverage_pct: float = 110,
                                nutrient: str = 'S',
                                num_applications: int = 10,
                                min_coverage_for_critical: int = 85) -> Dict:
    """
    Cap the contribution of a specific nutrient (e.g., S) to max_coverage_pct of deficit.

    ITERATIVE ALGORITHM (fixes the "add alternatives BEFORE reducing" issue):
    1. Check if S exceeds max_coverage_pct
    2. FIRST: Find S-free N sources and add them to preserve N coverage
    3. THEN: Reduce sulfate fertilizers to cap S
    4. ITERATE until S ≤ max or no more alternatives
    5. VALIDATE final S coverage - if still over, set hard error

    Args:
        profile: Dict with 'fertilizers' list
        deficits: Dict of nutrient deficits (kg/ha)
        available_fertilizers: List of fertilizer data
        max_coverage_pct: Maximum coverage percentage (default 110)
        nutrient: Nutrient to cap (default 'S')
        num_applications: For recalculating dose_per_application
        min_coverage_for_critical: Minimum coverage % for N/P2O5 after reduction (default 85)

    Returns:
        Modified profile with capped doses and notes
    """
    if not profile or 'fertilizers' not in profile:
        return profile

    fertilizers = profile.get('fertilizers', [])
    if not fertilizers:
        return profile

    original_deficit = deficits.get(nutrient, 0)

    # When deficit is 0 or negative, no nutrient is needed
    # Force all sulfate doses to 0 immediately
    if original_deficit <= 0:
        logger.info(
            f"[Cap {nutrient}] Deficit is 0 or negative - forcing all sulfate doses to 0"
        )
        sulfates_removed = []
        n_lost_total = 0
        for i, fert in enumerate(fertilizers):
            fert_id = fert.get('id', '')
            fert_name = fert.get('name', '')
            if is_fertilizer_in_set(fert_id, fert_name, SULFATE_FERTILIZERS):
                dose = fert.get('dose_kg_ha', 0) or 0
                if dose > 0:
                    # Get N content to track what we're losing
                    fert_data = None
                    for f in available_fertilizers:
                        if f.get('id') == fert_id or f.get(
                                'name') == fert_name:
                            fert_data = f
                            break
                    if fert_data:
                        n_pct = fert_data.get('n_pct', 0) or 0
                        n_lost = dose * n_pct / 100
                        n_lost_total += n_lost
                    sulfates_removed.append(fert_name)
                    fertilizers[i]['dose_kg_ha'] = 0
                    if 'dose_per_application' in fertilizers[i]:
                        fertilizers[i]['dose_per_application'] = 0

        # Remove zero-dose fertilizers
        fertilizers = [
            f for f in fertilizers if (f.get('dose_kg_ha', 0) or 0) > 0.1
        ]
        profile['fertilizers'] = fertilizers

        # Check if we need to add S-free N to compensate
        n_deficit = deficits.get('N', 0)
        if n_deficit > 0 and n_lost_total > 0:
            min_n_needed = n_deficit * (min_coverage_for_critical / 100)
            # Calculate current N after removal
            current_n = 0
            for fert in fertilizers:
                fert_data = None
                for f in available_fertilizers:
                    if f.get('id') == fert.get('id') or f.get(
                            'name') == fert.get('name'):
                        fert_data = f
                        break
                if fert_data:
                    n_pct = fert_data.get('n_pct', 0) or 0
                    current_n += fert.get('dose_kg_ha', 0) * n_pct / 100

            if current_n < min_n_needed:
                # Try to add S-free N sources
                n_shortfall = min_n_needed - current_n
                added_n = False
                for f in available_fertilizers:
                    n_pct = f.get('n_pct', 0) or 0
                    s_pct = f.get('s_pct', 0) or 0
                    if n_pct > 5 and s_pct == 0:
                        dose_needed = n_shortfall / (n_pct / 100)
                        new_fert = {
                            'id':
                            f.get('id'),
                            'name':
                            f.get('name'),
                            'dose_kg_ha':
                            round(dose_needed, 2),
                            'dose_per_application':
                            round(dose_needed / num_applications, 3),
                            'added_by_s_cap':
                            True
                        }
                        fertilizers.append(new_fert)
                        profile['fertilizers'] = fertilizers
                        added_n = True
                        logger.info(
                            f"[Cap {nutrient}] Added {f.get('name')} {dose_needed:.2f} kg/ha to replace N from removed sulfates"
                        )
                        break

                if not added_n:
                    error_msg = f"S deficit is 0 but sulfates were providing N. No S-free N alternatives available."
                    profile['cap_error'] = error_msg
                    logger.error(f"[Cap {nutrient}] HARD ERROR: {error_msg}")
                    raise SulfurCapError(error_msg)

        if sulfates_removed:
            profile['cap_applied'] = {
                'nutrient': nutrient,
                'deficit': 0,
                'max_allowed_kg': 0,
                'sulfates_removed': sulfates_removed,
                'reason': 'Zero deficit - no sulfur allowed'
            }
        return profile

    nutrient_deficit = original_deficit
    max_allowed_kg = nutrient_deficit * (max_coverage_pct / 100)
    n_deficit = deficits.get('N', 0)
    min_n_needed = n_deficit * (min_coverage_for_critical /
                                100) if n_deficit > 0 else 0

    # Map nutrient name to percentage key
    nutrient_to_pct_key = {
        'N': 'n_pct',
        'P2O5': 'p2o5_pct',
        'K2O': 'k2o_pct',
        'Ca': 'ca_pct',
        'Mg': 'mg_pct',
        'S': 's_pct'
    }
    pct_key = nutrient_to_pct_key.get(nutrient, 's_pct')

    def get_fert_data(fert_entry):
        fert_id = fert_entry.get('id', '')
        fert_name = fert_entry.get('name', '')
        for f in available_fertilizers:
            if f.get('id') == fert_id or f.get('name') == fert_name:
                return f
        return None

    def calculate_total_nutrient():
        """Calculate total kg/ha of the nutrient provided."""
        total = 0.0
        for fert in fertilizers:
            fert_data = get_fert_data(fert)
            if fert_data:
                dose = fert.get('dose_kg_ha', 0) or 0
                nutrient_pct = fert_data.get(pct_key, 0) or 0
                total += dose * (nutrient_pct / 100)
        return total

    def calculate_total_n():
        """Calculate total N provided by all fertilizers."""
        total = 0.0
        for fert in fertilizers:
            fert_data = get_fert_data(fert)
            if fert_data:
                dose = fert.get('dose_kg_ha', 0) or 0
                n_pct = fert_data.get('n_pct', 0) or 0
                total += dose * (n_pct / 100)
        return total

    def find_s_free_n_sources():
        """Find N sources that don't contain S (urea, calcium nitrate, etc.)."""
        s_free = []
        for f in available_fertilizers:
            n_pct = f.get('n_pct', 0) or 0
            s_pct = f.get('s_pct', 0) or 0
            fert_id = f.get('id', '')
            fert_name = f.get('name', '')
            # N source without S
            if n_pct > 5 and s_pct == 0:
                already_in_profile = any(
                    pf.get('id') == fert_id or pf.get('name') == fert_name
                    for pf in fertilizers)
                if not already_in_profile:
                    s_free.append(f)
        return s_free

    def find_existing_s_free_n_sources():
        """Find S-free N sources already in the profile that can be increased."""
        existing = []
        for i, fert in enumerate(fertilizers):
            fert_data = get_fert_data(fert)
            if fert_data:
                n_pct = fert_data.get('n_pct', 0) or 0
                s_pct = fert_data.get('s_pct', 0) or 0
                # Existing S-free N source
                if n_pct > 5 and s_pct == 0:
                    existing.append({
                        'idx': i,
                        'fert': fert,
                        'fert_data': fert_data,
                        'n_pct': n_pct
                    })
        return existing

    total_provided = calculate_total_nutrient()

    if total_provided <= max_allowed_kg:
        return profile  # No capping needed

    excess = total_provided - max_allowed_kg
    logger.info(
        f"[Cap {nutrient}] Total provided: {total_provided:.2f} kg/ha, max allowed: {max_allowed_kg:.2f} kg/ha, excess: {excess:.2f} kg/ha"
    )

    initial_n_provided = calculate_total_n()
    notes = profile.get('notes', '') or ''
    cap_notes = []

    # =========================================================================
    # PRE-CAP PHASE: Add all S-free N sources needed ONCE before loop
    # This prevents feedback loops by doing all additions upfront
    # =========================================================================
    import time as _time
    phase_start = _time.perf_counter()

    # Calculate how much N we'll lose using TOTAL S excess (not per-fertilizer)
    # excess = total_provided - max_allowed_kg (already calculated above)
    total_s_from_sulfates = 0
    sulfate_contributions = []

    for fert in fertilizers:
        fert_data = get_fert_data(fert)
        if fert_data:
            fert_id = fert.get('id', '')
            fert_name = fert.get('name', '')
            if is_fertilizer_in_set(fert_id, fert_name, SULFATE_FERTILIZERS):
                dose = fert.get('dose_kg_ha', 0) or 0
                n_pct = fert_data.get('n_pct', 0) or 0
                s_pct = fert_data.get('s_pct', 0) or 0
                if s_pct > 0:
                    s_contribution = dose * s_pct / 100
                    total_s_from_sulfates += s_contribution
                    if n_pct > 0:
                        sulfate_contributions.append({
                            'dose':
                            dose,
                            'n_pct':
                            n_pct,
                            's_pct':
                            s_pct,
                            's_contribution':
                            s_contribution
                        })

    # Distribute S reduction proportionally across sulfates and estimate N loss
    n_from_sulfates = 0
    if total_s_from_sulfates > 0 and excess > 0:
        for contrib in sulfate_contributions:
            # Proportional share of total S that this fertilizer contributes
            proportion = contrib['s_contribution'] / total_s_from_sulfates
            # How much S reduction this fertilizer needs
            s_reduction_needed = excess * proportion
            # Convert to dose reduction
            dose_reduction = s_reduction_needed / (contrib['s_pct'] / 100)
            actual_dose_reduction = min(contrib['dose'], dose_reduction)
            # N lost from this reduction
            n_from_sulfates += actual_dose_reduction * contrib['n_pct'] / 100

    # If we'll lose N below minimum, add S-free sources NOW (before loop)
    current_n = calculate_total_n()
    projected_n_after_cap = current_n - n_from_sulfates

    if projected_n_after_cap < min_n_needed and n_deficit > 0:
        n_shortfall = min_n_needed - projected_n_after_cap
        logger.info(
            f"[Cap {nutrient}] PRE-CAP: Will need {n_shortfall:.2f} kg N from S-free sources"
        )

        # First try existing S-free sources
        for i, fert in enumerate(fertilizers):
            if n_shortfall <= 0:
                break
            fert_data = get_fert_data(fert)
            if not fert_data:
                continue
            n_pct = fert_data.get('n_pct', 0) or 0
            s_pct = fert_data.get('s_pct', 0) or 0
            if n_pct > 5 and s_pct == 0:
                current_dose = fert.get('dose_kg_ha', 0) or 0
                max_increase = 100 - current_dose
                if max_increase > 0:
                    dose_needed = n_shortfall / (n_pct / 100)
                    dose_increase = min(dose_needed, max_increase)
                    fertilizers[i]['dose_kg_ha'] = round(
                        current_dose + dose_increase, 2)
                    n_added = dose_increase * n_pct / 100
                    n_shortfall -= n_added
                    cap_notes.append(
                        f"PRE-CAP: Increased {fert.get('name')} +{dose_increase:.1f} kg/ha"
                    )
                    logger.info(
                        f"[Cap {nutrient}] PRE-CAP: Increased {fert.get('name')} by {dose_increase:.1f} kg/ha"
                    )

        # If still short, add new S-free sources
        if n_shortfall > 0:
            s_free_sources = find_s_free_n_sources()
            for source in s_free_sources:
                if n_shortfall <= 0:
                    break
                source_n_pct = source.get('n_pct', 0) or 0
                if source_n_pct > 0:
                    dose_needed = n_shortfall / (source_n_pct / 100)
                    dose_to_add = min(dose_needed,
                                      50)  # Cap at 50 kg to avoid excess
                    new_fert = {
                        'id':
                        source.get('id'),
                        'name':
                        source.get('name'),
                        'dose_kg_ha':
                        round(dose_to_add, 2),
                        'dose_per_application':
                        round(dose_to_add / num_applications, 3),
                        'added_by_s_cap':
                        True
                    }
                    fertilizers.append(new_fert)
                    n_added = dose_to_add * source_n_pct / 100
                    n_shortfall -= n_added
                    cap_notes.append(
                        f"PRE-CAP: Added {source.get('name')} {dose_to_add:.1f} kg/ha"
                    )
                    logger.info(
                        f"[Cap {nutrient}] PRE-CAP: Added {source.get('name')} {dose_to_add:.1f} kg/ha"
                    )

    precap_time = (_time.perf_counter() - phase_start) * 1000
    logger.info(f"[Cap {nutrient}] PRE-CAP completed in {precap_time:.1f}ms")

    # =========================================================================
    # REDUCTION LOOP: Only reduce sulfates, NEVER add during loop
    # Deterministic: max 10 iterations, progress check, epsilon tolerance
    # =========================================================================
    loop_start = _time.perf_counter()
    MAX_ITERATIONS = 10
    iteration = 0
    prev_s_total = float('inf')  # Track progress
    PROGRESS_EPSILON = 0.001  # Minimum progress required

    while iteration < MAX_ITERATIONS:
        iteration += 1
        current_s_total = calculate_total_nutrient()
        current_n_total = calculate_total_n()

        # Check if S is already within limits
        if current_s_total <= max_allowed_kg:
            logger.info(
                f"[Cap {nutrient}] Iter {iteration}: S={current_s_total:.2f} kg ≤ {max_allowed_kg:.2f} kg - SUCCESS"
            )
            break

        # Check for progress - if no improvement, stop immediately
        if prev_s_total - current_s_total < PROGRESS_EPSILON:
            logger.warning(
                f"[Cap {nutrient}] Iter {iteration}: No progress (S unchanged at {current_s_total:.2f} kg) - stopping"
            )
            break
        prev_s_total = current_s_total

        excess = current_s_total - max_allowed_kg
        logger.info(
            f"[Cap {nutrient}] Iter {iteration}: S={current_s_total:.2f} kg, excess={excess:.2f} kg, N={current_n_total:.2f} kg"
        )

        # Reduce sulfates (one fertilizer per iteration for stability)
        made_reduction = False
        for i, fert in enumerate(fertilizers):
            fert_data = get_fert_data(fert)
            if not fert_data:
                continue

            fert_id = fert.get('id', '')
            fert_name = fert.get('name', '')
            if not is_fertilizer_in_set(fert_id, fert_name,
                                        SULFATE_FERTILIZERS):
                continue

            dose = fert.get('dose_kg_ha', 0) or 0
            if dose <= 0.1:
                continue

            s_pct = fert_data.get('s_pct', 0) or 0
            n_pct = fert_data.get('n_pct', 0) or 0
            if s_pct <= 0:
                continue

            s_contribution = dose * s_pct / 100

            # Calculate reduction needed
            needed_s_reduction = min(excess, s_contribution)
            dose_reduction = needed_s_reduction / (s_pct / 100)
            new_dose = max(0, dose - dose_reduction)

            # Check N impact - limit reduction if it would drop N below floor
            if n_pct > 0 and n_deficit > 0:
                n_lost = (dose - new_dose) * n_pct / 100
                projected_n = current_n_total - n_lost

                if projected_n < min_n_needed:
                    max_n_loss = max(0, current_n_total - min_n_needed)
                    if max_n_loss <= 0.1:
                        continue  # Can't reduce this one without breaking N
                    max_dose_reduction = max_n_loss / (n_pct / 100)
                    dose_reduction = min(dose_reduction, max_dose_reduction)
                    new_dose = max(0, dose - dose_reduction)

            if dose - new_dose < 0.1:
                continue  # No meaningful reduction possible

            # Apply reduction with floor rounding (never exceed cap)
            floored_dose = math.floor(new_dose * 100) / 100
            actual_s_reduction = (dose - floored_dose) * s_pct / 100
            fertilizers[i]['dose_kg_ha'] = floored_dose
            if 'dose_per_application' in fertilizers[i]:
                fertilizers[i]['dose_per_application'] = math.floor(
                    (floored_dose / num_applications) * 1000) / 1000

            cap_notes.append(
                f"{fert.get('name')}: {dose:.1f}→{floored_dose:.2f} kg/ha (-{actual_s_reduction:.2f} kg S)"
            )
            logger.info(
                f"[Cap {nutrient}] Reduced {fert.get('name')}: {dose:.1f} → {floored_dose:.2f} kg/ha"
            )
            made_reduction = True
            break  # One reduction per iteration

        # If no reduction possible, we're stuck
        if not made_reduction:
            logger.warning(
                f"[Cap {nutrient}] Iter {iteration}: No reduction possible - stuck"
            )
            break

    loop_time = (_time.perf_counter() - loop_start) * 1000
    logger.info(
        f"[Cap {nutrient}] REDUCTION LOOP completed in {loop_time:.1f}ms ({iteration} iterations)"
    )

    # Remove zero-dose fertilizers
    fertilizers = [
        f for f in fertilizers if (f.get('dose_kg_ha', 0) or 0) > 0.1
    ]
    profile['fertilizers'] = fertilizers

    # =========================================================================
    # FINAL VALIDATION: Hard error if S STILL over max_coverage_pct
    # =========================================================================
    final_s_total = calculate_total_nutrient()
    final_s_coverage = (final_s_total / nutrient_deficit *
                        100) if nutrient_deficit > 0 else 0
    final_n_total = calculate_total_n()
    final_n_coverage = (final_n_total / n_deficit *
                        100) if n_deficit > 0 else 100

    logger.info(
        f"[Cap {nutrient}] Final: S={final_s_total:.2f} kg ({final_s_coverage:.0f}%), N={final_n_total:.2f} kg ({final_n_coverage:.0f}%)"
    )

    # Record cap application
    if cap_notes:
        cap_summary = f"[Cap {nutrient}] {'; '.join(cap_notes)}"
        profile['notes'] = (notes + " " + cap_summary).strip()
        profile['cap_applied'] = {
            'nutrient': nutrient,
            'deficit': nutrient_deficit,
            'max_allowed_kg': max_allowed_kg,
            'original_total': total_provided,
            'final_total': final_s_total,
            'final_coverage': final_s_coverage,
            'reductions': cap_notes,
            'n_preserved': final_n_coverage >= min_coverage_for_critical,
            'iterations': iteration
        }

    # CRITICAL: Hard failure if S exceeds max_coverage_pct
    # Use minimal floating-point epsilon only - no percentage tolerance
    EPSILON = 1e-6  # Pure floating-point precision guard
    if final_s_total > max_allowed_kg + EPSILON:
        error_msg = (
            f"S coverage {final_s_coverage:.0f}% exceeds {max_coverage_pct}% after {iteration} iterations. "
            f"No S-free N alternatives available. Add urea/nitrates to catalog."
        )
        profile['cap_error'] = error_msg
        logger.error(f"[Cap {nutrient}] HARD ERROR: {error_msg}")
        # Raise exception to halt processing - caller must handle this
        raise SulfurCapError(error_msg)

    # Warn if N is low
    if final_n_coverage < min_coverage_for_critical:
        profile[
            'cap_warning'] = f"N coverage {final_n_coverage:.0f}% (below {min_coverage_for_critical}%) after S capping."
        logger.warning(
            f"[Cap {nutrient}] N coverage warning: {final_n_coverage:.0f}%")

    return profile


# =============================================================================
# CORE FUNCTIONS
# =============================================================================


def build_fertilizers_context(fertilizers: List[Dict]) -> tuple:
    """Build a formatted list of available fertilizers for the prompt and a price map."""
    lines = []
    price_map = {}
    name_to_id = {}

    for f in fertilizers:
        name = f.get('name', f.get('id', 'Unknown'))
        fert_id = f.get('id', '')
        n = f.get('n_pct', 0) or 0
        p = f.get('p2o5_pct', 0) or 0
        k = f.get('k2o_pct', 0) or 0
        ca = f.get('ca_pct', 0) or 0
        mg = f.get('mg_pct', 0) or 0
        s = f.get('s_pct', 0) or 0
        price = f.get('price_per_kg', 0) or 0

        price_map[fert_id] = price
        price_map[name.lower()] = price
        name_to_id[name.lower()] = fert_id

        composition = []
        if n > 0: composition.append(f"N:{n}%")
        if p > 0: composition.append(f"P2O5:{p}%")
        if k > 0: composition.append(f"K2O:{k}%")
        if ca > 0: composition.append(f"Ca:{ca}%")
        if mg > 0: composition.append(f"Mg:{mg}%")
        if s > 0: composition.append(f"S:{s}%")

        comp_str = ", ".join(composition) if composition else "Micronutrientes"
        price_str = f"${price:.2f}/kg" if price > 0 else "Sin precio"

        lines.append(f"- {name} (ID: {fert_id}): {comp_str} | {price_str}")

    return "\n".join(lines), price_map, name_to_id


def build_deficit_aware_fertilizer_list(
        fertilizers: List[Dict],
        deficits: Dict[str, float],
        agronomic_context: Optional[Dict] = None) -> str:
    """
    Build fertilizer list with annotations about which are PROHIBITED due to:
    - Nutrient with deficit=0 (K-centered fertilizers when K2O=0, etc.)
    - Agronomic constraints (KCl when Cl- > 2 meq/L)
    """
    lines = []

    # Extract constraints from agronomic context
    water_cl = 0
    soil_k_high = False
    if agronomic_context:
        water = agronomic_context.get('water', {})
        soil = agronomic_context.get('soil', {})
        water_cl = water.get('cl_meqL', 0) or 0
        soil_k_ppm = soil.get('k_ppm', 0) or 0
        soil_k_high = soil_k_ppm > 400 or soil.get('k_exchange_high', False)

    for f in fertilizers:
        name = f.get('name', f.get('id', 'Unknown'))
        fert_id = f.get('id', '')
        n = f.get('n_pct', 0) or 0
        p = f.get('p2o5_pct', 0) or 0
        k = f.get('k2o_pct', 0) or 0
        ca = f.get('ca_pct', 0) or 0
        mg = f.get('mg_pct', 0) or 0
        s = f.get('s_pct', 0) or 0
        price = f.get('price_per_kg', 0) or 0

        composition = []
        if n > 0: composition.append(f"N:{n}%")
        if p > 0: composition.append(f"P2O5:{p}%")
        if k > 0: composition.append(f"K2O:{k}%")
        if ca > 0: composition.append(f"Ca:{ca}%")
        if mg > 0: composition.append(f"Mg:{mg}%")
        if s > 0: composition.append(f"S:{s}%")

        comp_str = ", ".join(composition) if composition else "Micronutrientes"
        price_str = f"${price:.2f}/kg" if price > 0 else "Sin precio"

        # Check restrictions
        restrictions = []

        # K-centered fertilizers when K2O deficit = 0
        if deficits.get('K2O', 0) <= 0 and is_fertilizer_in_set(
                fert_id, name, K_CENTERED_FERTILIZERS):
            restrictions.append("⛔ NO USAR: Déficit K2O=0")

        # Mg-centered fertilizers when Mg deficit = 0
        if deficits.get('Mg', 0) <= 0 and is_fertilizer_in_set(
                fert_id, name, MG_CENTERED_FERTILIZERS):
            restrictions.append("⛔ NO USAR: Déficit Mg=0")

        # Ca-centered fertilizers when Ca deficit = 0
        if deficits.get('Ca', 0) <= 0 and is_fertilizer_in_set(
                fert_id, name, CA_CENTERED_FERTILIZERS):
            restrictions.append("⛔ NO USAR: Déficit Ca=0")

        # Chloride fertilizers when water Cl- > 2 meq/L
        if water_cl > 2.0 and is_fertilizer_in_set(fert_id, name,
                                                   CHLORIDE_FERTILIZERS):
            restrictions.append(
                f"⛔ PROHIBIDO: Cl⁻ en agua={water_cl:.1f} meq/L > 2")

        # K fertilizers when soil K is high (early stages)
        if soil_k_high and k > 20:
            restrictions.append("⚠️ PRECAUCIÓN: K alto en suelo")

        restriction_str = f" [{'; '.join(restrictions)}]" if restrictions else ""
        lines.append(
            f"- {name} (ID: {fert_id}): {comp_str} | {price_str}{restriction_str}"
        )

    return "\n".join(lines)


def enforce_hard_constraints(profile: Dict,
                             deficits: Dict[str, float],
                             agronomic_context: Optional[Dict],
                             available_fertilizers: List[Dict],
                             growth_stage: str = 'default') -> Dict:
    """
    Enforce hard agronomic constraints post-optimization.

    Removes or zeros out fertilizers that violate:
    1. K-centered fertilizers when K2O deficit = 0
    2. Mg-centered fertilizers when Mg deficit = 0  
    3. Ca-centered fertilizers when Ca deficit = 0
    4. Chloride fertilizers when water Cl- > 2 meq/L
    5. K fertilizers in early stages when soil K is high

    Also checks if the removed fertilizer's other nutrients can be covered
    by remaining fertilizers.
    """
    if not profile or 'fertilizers' not in profile:
        return profile

    fertilizers = profile.get('fertilizers', [])
    if not fertilizers:
        return profile

    # Extract constraints
    water_cl = 0
    soil_k_high = False
    if agronomic_context:
        water = agronomic_context.get('water', {})
        soil = agronomic_context.get('soil', {})
        water_cl = water.get('cl_meqL', 0) or 0
        soil_k_ppm = soil.get('k_ppm', 0) or 0
        soil_k_high = soil_k_ppm > 400 or soil.get('k_exchange_high', False)

    stage_key = normalize_stage(growth_stage)
    is_early_stage = stage_key in ['seedling', 'vegetative']

    removed_fertilizers = []
    kept_fertilizers = []

    for fert in fertilizers:
        fert_id = fert.get('id', '')
        fert_name = fert.get('name', '')
        should_remove = False
        removal_reason = None

        # Rule 1: K-centered when K2O deficit = 0 -> ALWAYS REMOVE
        # Even if KNO3 provides N, we must use alternative N sources to avoid K over-supply
        if deficits.get('K2O', 0) <= 0 and is_fertilizer_in_set(
                fert_id, fert_name, K_CENTERED_FERTILIZERS):
            should_remove = True
            removal_reason = "K-centered fertilizer PROHIBITED: K2O deficit=0"

        # Rule 2: Mg-centered when Mg deficit = 0 -> ALWAYS REMOVE
        # Use alternative sources for other nutrients (e.g., S from ammonium sulfate)
        if deficits.get('Mg', 0) <= 0 and is_fertilizer_in_set(
                fert_id, fert_name, MG_CENTERED_FERTILIZERS):
            should_remove = True
            removal_reason = "Mg-centered fertilizer PROHIBITED: Mg deficit=0"

        # Rule 3: Ca-centered when Ca deficit = 0 -> ALWAYS REMOVE
        # Use alternative N sources (e.g., urea, ammonium sulfate) instead of calcium nitrate
        if deficits.get('Ca', 0) <= 0 and is_fertilizer_in_set(
                fert_id, fert_name, CA_CENTERED_FERTILIZERS):
            should_remove = True
            removal_reason = "Ca-centered fertilizer PROHIBITED: Ca deficit=0"

        # Rule 4: Chloride fertilizers when water Cl- > 2 meq/L (HARD PROHIBITION)
        if water_cl > 2.0 and is_fertilizer_in_set(fert_id, fert_name,
                                                   CHLORIDE_FERTILIZERS):
            should_remove = True
            removal_reason = f"Cl⁻ in water ({water_cl:.1f} meq/L) > 2 meq/L"

        # Rule 5: K fertilizers in early stages when soil K is high
        if soil_k_high and is_early_stage:
            fert_data = next(
                (f for f in available_fertilizers
                 if f.get('id') == fert_id or f.get('name') == fert_name),
                None)
            if fert_data and (fert_data.get('k2o_pct', 0) or 0) > 30:
                # High K fertilizer in early stage with high soil K - reduce dose significantly
                fert['dose_kg_ha'] = fert.get('dose_kg_ha', 0) * 0.3
                fert['dose_per_application'] = fert.get(
                    'dose_per_application', 0) * 0.3
                fert['constraint_applied'] = "Reduced 70% due to high soil K"

        if should_remove:
            removed_fertilizers.append({
                'fert': fert,
                'reason': removal_reason
            })
            logger.info(
                f"[HardConstraints] Removed {fert_name} ({fert_id}): {removal_reason}"
            )
        else:
            kept_fertilizers.append(fert)

    profile['fertilizers'] = kept_fertilizers

    if removed_fertilizers:
        profile['constraints_applied'] = [
            f"{r['fert'].get('name', r['fert'].get('id'))}: {r['reason']}"
            for r in removed_fertilizers
        ]
        logger.info(
            f"[HardConstraints] Applied constraints: {profile['constraints_applied']}"
        )

    return profile


def normalize_coverage(profile: Dict,
                       deficits: Dict[str, float],
                       available_fertilizers: List[Dict],
                       max_coverage_pct: float = 110,
                       num_applications: int = 10,
                       min_coverage: int = 90,
                       growth_stage: str = 'default') -> Dict:
    """
    Normalize fertilizer doses to ensure:
    1. No nutrient with deficit > 0 exceeds max_coverage_pct (e.g., 110%)
    2. Nutrients with deficit = 0 don't exceed max_allowed thresholds per stage

    NEW (v2): Three-phase normalization:
    - Phase 0: CAP S (sulfur) FIRST when S deficit is low - this is the most common issue
    - Phase 1: Handle nutrients with deficit > 0 exceeding max_coverage_pct
    - Phase 2: Handle nutrients with deficit = 0 exceeding max_allowed thresholds

    The S cap is critical because fertilizers selected for N/Mg/K often contain S as secondary,
    and when S deficit is small (e.g., 1.5 kg/ha), coverage can spike to 300%+.
    """
    if not profile or 'fertilizers' not in profile:
        return profile

    fertilizers = profile.get('fertilizers', [])
    if not fertilizers:
        return profile

    # ==========================================================================
    # PHASE 0: CAP SULFUR (S) FIRST - Critical for low S deficit scenarios
    # ==========================================================================
    s_deficit = deficits.get('S', 0)
    if s_deficit > 0 and s_deficit < LOW_S_DEFICIT_THRESHOLD:
        # S deficit is low - cap S contribution FIRST before other normalization
        logger.info(
            f"[Normalize] Phase 0: S deficit is low ({s_deficit:.1f} kg/ha < {LOW_S_DEFICIT_THRESHOLD}), applying S cap"
        )
        try:
            profile = cap_fertilizers_by_nutrient(
                profile,
                deficits,
                available_fertilizers,
                max_coverage_pct=max_coverage_pct,
                nutrient='S',
                num_applications=num_applications)
            fertilizers = profile.get('fertilizers', [])  # Re-fetch after cap
        except SulfurCapError as e:
            # S cap failed - mark profile as failed and return immediately
            logger.error(f"[Normalize] S cap hard failure: {e}")
            profile['s_cap_failed'] = True
            profile['cap_error'] = str(e)
            profile['optimization_failed'] = True
            return profile  # Halt processing - do not continue with failed profile

    stage_key = normalize_stage(growth_stage)
    max_allowed = MAX_ALLOWED_WHEN_NO_DEFICIT.get(
        stage_key, MAX_ALLOWED_WHEN_NO_DEFICIT['default'])

    nutrient_keys = {
        'N': 'n_pct',
        'P2O5': 'p2o5_pct',
        'K2O': 'k2o_pct',
        'Ca': 'ca_pct',
        'Mg': 'mg_pct',
        'S': 's_pct'
    }

    def get_fert_data(fert_entry):
        fert_id = fert_entry.get('id', '')
        fert_name = fert_entry.get('name', '')
        for f in available_fertilizers:
            if f.get('id') == fert_id or f.get('name') == fert_name:
                return f
        return None

    def calculate_provided_kg() -> Dict[str, float]:
        """Calculate total kg/ha provided for each nutrient."""
        provided = {nut: 0.0 for nut in nutrient_keys}
        for fert in fertilizers:
            fert_data = get_fert_data(fert)
            if fert_data:
                dose = fert.get('dose_kg_ha', 0) or 0
                for nut, pct_key in nutrient_keys.items():
                    nutrient_pct = fert_data.get(pct_key, 0) or 0
                    provided[nut] += dose * (nutrient_pct / 100)
        return provided

    def calculate_coverage() -> Dict[str, float]:
        """Calculate coverage percentage for nutrients with deficit > 0."""
        coverage = {}
        provided = calculate_provided_kg()
        for nut in nutrient_keys:
            deficit = deficits.get(nut, 0)
            if deficit <= 0:
                # For deficit=0, coverage is based on max_allowed threshold
                threshold = max_allowed.get(nut, 5)
                if threshold > 0:
                    coverage[nut] = round((provided[nut] / threshold) * 100, 1)
                else:
                    coverage[nut] = 100 if provided[nut] == 0 else 999
            else:
                coverage[nut] = round((provided[nut] / deficit) * 100, 1)
        return coverage

    def would_drop_below_minimum(fert_idx, reduction_factor):
        """Check if reducing a fertilizer would drop any nutrient below min_coverage."""
        test_fertilizers = [f.copy() for f in fertilizers]
        current_dose = test_fertilizers[fert_idx].get('dose_kg_ha', 0)
        test_fertilizers[fert_idx][
            'dose_kg_ha'] = current_dose * reduction_factor

        for nut, pct_key in nutrient_keys.items():
            deficit = deficits.get(nut, 0)
            if deficit <= 0:
                continue

            total_provided = 0
            for fert in test_fertilizers:
                fert_data = get_fert_data(fert)
                if fert_data:
                    nutrient_pct = fert_data.get(pct_key, 0) or 0
                    dose = fert.get('dose_kg_ha', 0) or 0
                    total_provided += dose * (nutrient_pct / 100)

            new_coverage = (total_provided /
                            deficit) * 100 if deficit > 0 else 100
            if new_coverage < min_coverage:
                return True, nut
        return False, None

    # Phase 1: Handle nutrients with deficit > 0 exceeding max_coverage_pct
    for iteration in range(10):
        coverage = calculate_coverage()

        over_nutrients = {
            nut: cov
            for nut, cov in coverage.items()
            if cov > max_coverage_pct and deficits.get(nut, 0) > 0
        }

        if not over_nutrients:
            break

        worst_nutrient = max(over_nutrients.items(), key=lambda x: x[1])
        nut_name, nut_coverage = worst_nutrient
        pct_key = nutrient_keys[nut_name]

        contributors = []
        for i, fert in enumerate(fertilizers):
            fert_data = get_fert_data(fert)
            if fert_data:
                nutrient_pct = fert_data.get(pct_key, 0) or 0
                dose = fert.get('dose_kg_ha', 0) or 0
                contribution = dose * (nutrient_pct / 100)
                if contribution > 0:
                    contributors.append((i, contribution, nutrient_pct))

        if not contributors:
            break

        contributors.sort(key=lambda x: x[1], reverse=True)

        made_reduction = False
        for fert_idx, contribution, nutrient_pct in contributors:
            current_dose = fertilizers[fert_idx].get('dose_kg_ha', 0)
            target_reduction_factor = max_coverage_pct / nut_coverage

            drops_below, affected_nut = would_drop_below_minimum(
                fert_idx, target_reduction_factor)

            if drops_below:
                safe_reduction_factor = max(0.90, target_reduction_factor)
                drops_below_safe, _ = would_drop_below_minimum(
                    fert_idx, safe_reduction_factor)
                if drops_below_safe:
                    continue
                target_reduction_factor = safe_reduction_factor

            new_dose = current_dose * target_reduction_factor
            fertilizers[fert_idx]['dose_kg_ha'] = round(new_dose, 2)

            if 'dose_per_application' in fertilizers[fert_idx]:
                fertilizers[fert_idx]['dose_per_application'] = round(
                    new_dose / num_applications, 3)
            if 'subtotal' in fertilizers[fert_idx]:
                price = fertilizers[fert_idx].get('price_per_kg', 0)
                fertilizers[fert_idx]['subtotal'] = round(new_dose * price, 2)

            logger.info(
                f"[Normalize] Reduced {fertilizers[fert_idx].get('name')} from {current_dose:.1f} to {new_dose:.1f} kg/ha to limit {nut_name} from {nut_coverage:.0f}% toward {max_coverage_pct}%"
            )
            made_reduction = True
            break

        if not made_reduction:
            logger.warning(
                f"[Normalize] Could not reduce {nut_name} ({nut_coverage:.0f}%) without dropping other nutrients below minimum"
            )
            break

    # Phase 2: Handle nutrients with deficit = 0 exceeding max_allowed thresholds
    excess_when_no_deficit = []
    provided_kg = calculate_provided_kg()

    for nut in nutrient_keys:
        deficit = deficits.get(nut, 0)
        if deficit > 0:
            continue  # Already handled in Phase 1

        threshold = max_allowed.get(nut, 5)
        provided = provided_kg.get(nut, 0)

        if provided > threshold:
            # Try to reduce fertilizers contributing to this nutrient
            pct_key = nutrient_keys[nut]
            excess = provided - threshold

            contributors = []
            for i, fert in enumerate(fertilizers):
                fert_data = get_fert_data(fert)
                if fert_data:
                    nutrient_pct = fert_data.get(pct_key, 0) or 0
                    dose = fert.get('dose_kg_ha', 0) or 0
                    contribution = dose * (nutrient_pct / 100)
                    if contribution > 0:
                        contributors.append(
                            (i, contribution, nutrient_pct, fert_data))

            contributors.sort(key=lambda x: x[1], reverse=True)

            reduced_excess = 0
            for fert_idx, contribution, nutrient_pct, fert_data in contributors:
                if reduced_excess >= excess:
                    break

                current_dose = fertilizers[fert_idx].get('dose_kg_ha', 0)

                # Check if this fertilizer provides other nutrients we need
                provides_needed_deficit = False
                for other_nut, other_pct_key in nutrient_keys.items():
                    if deficits.get(other_nut, 0) > 0 and (fert_data.get(
                            other_pct_key, 0) or 0) > 3:
                        provides_needed_deficit = True
                        break

                if provides_needed_deficit:
                    # Can't remove, but try gentle reduction
                    max_reduction = 0.2  # Max 20% reduction
                    reduction_needed = min(
                        max_reduction,
                        excess / contribution if contribution > 0 else 0)
                    new_dose = current_dose * (1 - reduction_needed)
                    reduced_excess += contribution * reduction_needed
                else:
                    # Can fully reduce/remove
                    reduction_needed = min(
                        1.0,
                        excess / contribution if contribution > 0 else 1.0)
                    new_dose = current_dose * (1 - reduction_needed)
                    reduced_excess += contribution * reduction_needed

                fertilizers[fert_idx]['dose_kg_ha'] = round(new_dose, 2)
                if 'dose_per_application' in fertilizers[fert_idx]:
                    fertilizers[fert_idx]['dose_per_application'] = round(
                        new_dose / num_applications, 3)
                if 'subtotal' in fertilizers[fert_idx]:
                    price = fertilizers[fert_idx].get('price_per_kg', 0)
                    fertilizers[fert_idx]['subtotal'] = round(
                        new_dose * price, 2)

                logger.info(
                    f"[Normalize] Reduced {fertilizers[fert_idx].get('name')} for {nut} (deficit=0): {current_dose:.1f} -> {new_dose:.1f} kg/ha"
                )

            # Check if still exceeding after reductions
            new_provided = sum(
                (fert.get('dose_kg_ha', 0) *
                 (get_fert_data(fert).
                  get(pct_key, 0) if get_fert_data(fert) else 0) / 100)
                for fert in fertilizers)
            if new_provided > threshold:
                excess_when_no_deficit.append({
                    'nutrient':
                    nut,
                    'provided_kg_ha':
                    round(new_provided, 2),
                    'max_allowed_kg_ha':
                    threshold,
                    'excess_kg_ha':
                    round(new_provided - threshold, 2)
                })

    # Remove zero-dose fertilizers
    fertilizers = [
        f for f in fertilizers if (f.get('dose_kg_ha', 0) or 0) > 0.1
    ]

    # Recalculate final coverage
    profile['fertilizers'] = fertilizers
    final_coverage = calculate_coverage()
    profile['coverage'] = {
        nut: min(100, cov) if deficits.get(nut, 0) <= 0 else cov
        for nut, cov in final_coverage.items()
    }
    profile['coverage_normalized'] = True

    # Track nutrients still exceeding max_coverage despite normalization
    exceeding_nutrients = []
    for nut, cov in final_coverage.items():
        if cov > max_coverage_pct and deficits.get(nut, 0) > 0:
            exceeding_nutrients.append(f"{nut}:{round(cov)}%")

    if exceeding_nutrients:
        profile['coverage_exceeds_max'] = exceeding_nutrients
        logger.warning(
            f"[Normalize] Nutrients still exceeding {max_coverage_pct}%: {exceeding_nutrients}"
        )

    if excess_when_no_deficit:
        profile['excess_when_no_deficit'] = excess_when_no_deficit
        logger.warning(
            f"[Normalize] Excess when deficit=0: {excess_when_no_deficit}")

    return profile


def calculate_costs_for_profile(profile: Dict, price_map: Dict,
                                name_to_id: Dict) -> Dict:
    """Calculate actual costs for a profile using the price map."""
    total_cost = 0.0
    fertilizers_with_costs = []

    for fert in profile.get('fertilizers', []):
        fert_id = fert.get('id', '')
        fert_name = fert.get('name', '')
        dose_kg_ha = fert.get('dose_kg_ha', 0) or 0

        price = price_map.get(fert_id, 0)
        if price == 0:
            price = price_map.get(fert_name.lower(), 0)
        if price == 0 and fert_name.lower() in name_to_id:
            fert_id = name_to_id[fert_name.lower()]
            price = price_map.get(fert_id, 0)

        subtotal = dose_kg_ha * price
        total_cost += subtotal

        fertilizers_with_costs.append({
            **fert, 'price_per_kg': price,
            'subtotal': subtotal
        })

    return {
        **profile, 'fertilizers': fertilizers_with_costs,
        'total_cost_per_ha': total_cost
    }


def calculate_acid_n_contribution(acid_data: Optional[Dict] = None) -> float:
    """
    Calculate N contribution (kg/ha) from nitric acid.

    Returns 0 if acid_data is missing or incomplete.
    """
    if not acid_data:
        return 0.0

    acid_type = (acid_data.get('acid_type', '') or '').lower()
    if acid_type not in [
            'nitric', 'hno3', 'nitrico', 'ácido nítrico', 'acido nitrico'
    ]:
        return 0.0

    dose_ml_per_1000L = acid_data.get('dose_ml_per_1000L', 0) or 0
    water_volume_m3_ha = acid_data.get('water_volume_m3_ha', 0) or 0

    if dose_ml_per_1000L <= 0 or water_volume_m3_ha <= 0:
        return 0.0

    # HNO3 63%: density ~1.4 g/mL, N content ~14%
    g_n_per_ml_hno3 = 0.196  # 1.4 g/mL * 0.14 N content
    total_ml_per_ha = dose_ml_per_1000L * water_volume_m3_ha
    n_from_acid_kg = (total_ml_per_ha * g_n_per_ml_hno3) / 1000

    return n_from_acid_kg


def adjust_deficits_for_acid_nitrogen(
        deficits: Dict[str, float],
        acid_data: Optional[Dict] = None) -> Dict[str, float]:
    """
    Subtract N contributed by nitric acid from deficits.

    If acid_data contains:
    - acid_type: 'nitric' or 'hno3'
    - dose_ml_per_1000L: mL of acid per 1000L water
    - water_volume_m3_ha: total water applied per hectare

    Then we calculate N contribution and subtract from deficit.

    Returns:
        Dict[str, float]: Adjusted deficits after nitric acid N contribution.
    """
    adjusted = deficits.copy()
    n_from_acid_kg = calculate_acid_n_contribution(acid_data)

    if n_from_acid_kg > 0:
        original_n = adjusted.get('N', 0)
        adjusted['N'] = max(0, original_n - n_from_acid_kg)
        logger.info(
            f"[AcidN] HNO3 contributes {n_from_acid_kg:.2f} kg N/ha. Deficit N: {original_n:.1f} -> {adjusted['N']:.1f} kg/ha"
        )

    return adjusted


def _optimize_manual_mode(
        deficits: Dict[str, float],
        micro_deficits: Dict[str, float],
        available_fertilizers: List[Dict],
        crop_name: str,
        growth_stage: str,
        irrigation_system: str,
        num_applications: int,
        fertilizers_text: str,
        price_map: Dict,
        name_to_id: Dict,
        agronomic_context: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Manual mode optimization using deterministic rules only.

    This path assumes the fertilizer list is already filtered to the user's
    selected products and returns deterministic profiles.
    """
    logger.info(
        "[ManualMode] Running deterministic optimization for manual selection."
    )
    return optimize_deterministic(deficits=deficits,
                                  micro_deficits=micro_deficits,
                                  available_fertilizers=available_fertilizers,
                                  crop_name=crop_name,
                                  growth_stage=growth_stage,
                                  irrigation_system=irrigation_system,
                                  num_applications=num_applications,
                                  agronomic_context=agronomic_context)


def optimize_with_ai(
        deficits: Dict[str, float],
        micro_deficits: Dict[str, float],
        available_fertilizers: List[Dict],
        crop_name: str,
        growth_stage: str,
        irrigation_system: str = "goteo",
        num_applications: int = 1,
        is_manual_mode: bool = False,
        agronomic_context: Optional[Dict[str, Any]] = None,
        acid_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generate 3 fertilization recommendations using deterministic optimization.

    Args:
        deficits: Macronutrient deficits in kg/ha (N, P2O5, K2O, Ca, Mg, S)
        micro_deficits: Micronutrient deficits in g/ha (Fe, Mn, Zn, Cu, B, Mo)
        available_fertilizers: List of fertilizer dicts with composition and prices
        crop_name: Name of the crop
        growth_stage: Current phenological stage
        irrigation_system: Type of irrigation (goteo, aspersion, etc.)
        num_applications: Number of applications in the stage
        is_manual_mode: If True, user manually selected fertilizers
        agronomic_context: Optional dict with water and soil data for constraints
            {
                "water": {"ph": 8.37, "hco3_meqL": 8.2, "cl_meqL": 3.2, "na_meqL": 5.96},
                "soil": {"ph": 8.19, "k_ppm": 950, "no3n_ppm": 54.4, "mg_ppm": 750}
            }
        acid_data: Optional dict with acid info to subtract N contribution
            {
                "acid_type": "nitric",
                "dose_ml_per_1000L": 0.5,
                "water_volume_m3_ha": 5000
            }

    Returns:
        Dict with economic, balanced, and complete profiles
    """
    logger.info(
        "[DeterministicAICompat] Routing optimize_with_ai to deterministic optimizer."
    )

    water_volume = 50.0
    if acid_data and acid_data.get("water_volume_m3_ha"):
        water_volume = acid_data.get("water_volume_m3_ha") or water_volume

    if is_manual_mode:
        return _optimize_manual_mode(
            deficits=deficits,
            micro_deficits=micro_deficits,
            available_fertilizers=available_fertilizers,
            crop_name=crop_name,
            growth_stage=growth_stage,
            irrigation_system=irrigation_system,
            num_applications=num_applications,
            fertilizers_text="",
            price_map={},
            name_to_id={},
            agronomic_context=agronomic_context)

    return optimize_deterministic(deficits=deficits,
                                  micro_deficits=micro_deficits,
                                  available_fertilizers=available_fertilizers,
                                  crop_name=crop_name,
                                  growth_stage=growth_stage,
                                  irrigation_system=irrigation_system,
                                  num_applications=num_applications,
                                  agronomic_context=agronomic_context,
                                  acid_data=acid_data,
                                  water_volume_m3_ha=water_volume,
                                  area_ha=1.0)


# =============================================================================
# FERTILIZER CATALOG FUNCTIONS
# =============================================================================


def _load_hydro_fertilizers_catalog() -> List[Dict]:
    """
    Load fertilizers from hydro_fertilizers.json (shared catalog with Hydroponics module).
    Converts ion-based composition to percentage-based for FertiIrrigation.
    """
    from pathlib import Path

    config_path = Path(
        __file__).parent.parent / "data" / "hydro_fertilizers.json"

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading hydro_fertilizers.json: {e}")
        return []

    fertilizers = data.get("fertilizers", [])
    result = []

    for fert in fertilizers:
        fert_id = fert.get("id", "")
        fert_name = fert.get("name", "")
        fert_type = fert.get("type", "salt")

        nutrient_comp = fert.get("nutrient_composition", {})

        n_pct = nutrient_comp.get("N_percent", 0) or 0
        ca_pct = nutrient_comp.get("Ca_percent", 0) or 0
        mg_pct = nutrient_comp.get("Mg_percent", 0) or 0
        s_pct = nutrient_comp.get("S_percent", 0) or 0

        k_pct = nutrient_comp.get("K_percent", 0) or 0
        k2o_pct = k_pct * 1.205 if k_pct > 0 else 0

        p_pct = nutrient_comp.get("P_percent", 0) or 0
        p2o5_pct = p_pct * 2.29 if p_pct > 0 else 0

        if p2o5_pct == 0:
            meq_per_gram = fert.get("meq_per_gram", {})
            h2po4_meq = meq_per_gram.get("H2PO4", 0)
            if h2po4_meq > 0:
                p2o5_pct = h2po4_meq * 30.97 * 2.29 / 1000 * 100

        default_price = fert.get("typical_cost_mxn_per_kg") or fert.get(
            "typical_cost_mxn_per_liter") or 25.0

        fe_pct = nutrient_comp.get("Fe_percent", 0) or 0
        mn_pct = nutrient_comp.get("Mn_percent", 0) or 0
        zn_pct = nutrient_comp.get("Zn_percent", 0) or 0
        cu_pct = nutrient_comp.get("Cu_percent", 0) or 0
        b_pct = nutrient_comp.get("B_percent", 0) or 0
        mo_pct = nutrient_comp.get("Mo_percent", 0) or 0

        stock_tank = fert.get("stock_tank", "B")

        result.append({
            'id': fert_id,
            'slug': fert_id,
            'name': fert_name,
            'type': fert_type,
            'n_pct': round(n_pct, 2),
            'p2o5_pct': round(p2o5_pct, 2),
            'k2o_pct': round(k2o_pct, 2),
            'ca_pct': round(ca_pct, 2),
            'mg_pct': round(mg_pct, 2),
            's_pct': round(s_pct, 2),
            'fe_pct': round(fe_pct, 2),
            'mn_pct': round(mn_pct, 2),
            'zn_pct': round(zn_pct, 2),
            'cu_pct': round(cu_pct, 2),
            'b_pct': round(b_pct, 2),
            'mo_pct': round(mo_pct, 2),
            'default_price_mxn': default_price,
            'stock_tank': stock_tank,
            'meq_per_gram': fert.get("meq_per_gram", {}),
            'form': fert.get("form", "solid")
        })

    return result


_HYDRO_FERTILIZERS_CACHE = None


def get_available_fertilizers_for_user(db,
                                       user_id: int,
                                       currency: str = "MXN") -> List[Dict]:
    """
    Get all available fertilizers for a user, using the SAME filtering as the Prices tab.

    Uses visible_ids from load_default_fertilizers() but retrieves full nutrient composition
    from the hydro catalog or FertilizerProduct table.

    Returns fertilizers with their composition and user-specific prices.
    """
    global _HYDRO_FERTILIZERS_CACHE

    from app.routers.fertilizer_prices import (load_default_fertilizers,
                                               get_default_price_for_currency,
                                               DEFAULT_PRICES_BY_CURRENCY)
    from app.models.hydro_ions_models import UserFertilizerPrice, UserCustomFertilizer

    visible_fertilizers = load_default_fertilizers(db)
    visible_ids = {f.get('id') for f in visible_fertilizers if f.get('id')}

    if _HYDRO_FERTILIZERS_CACHE is None:
        _HYDRO_FERTILIZERS_CACHE = _load_hydro_fertilizers_catalog()

    hydro_by_id = {f['id']: f for f in _HYDRO_FERTILIZERS_CACHE}

    if not visible_ids:
        visible_ids = set(hydro_by_id.keys())
        logger.warning(
            "[Fallback] visible_ids vacío, usando catálogo hydro completo")

    user_prices = db.query(UserFertilizerPrice).filter(
        UserFertilizerPrice.user_id == user_id,
        UserFertilizerPrice.currency == currency).all()
    user_price_kg_map = {
        p.fertilizer_id: p.price_per_kg
        for p in user_prices if p.price_per_kg
    }
    user_price_liter_map = {
        p.fertilizer_id: p.price_per_liter
        for p in user_prices if p.price_per_liter
    }

    custom_ferts = db.query(UserCustomFertilizer).filter(
        UserCustomFertilizer.user_id == user_id,
        UserCustomFertilizer.is_active == True).all()
    custom_slugs = {f"custom_{cf.id}" for cf in custom_ferts}

    allowed_ids = set(visible_ids)
    allowed_ids.update(custom_slugs)
    allowed_ids.update(user_price_kg_map.keys())
    allowed_ids.update(user_price_liter_map.keys())
    
    logger.info(f"[FertilizerLoader] visible_ids={len(visible_ids)}, custom={len(custom_slugs)}, allowed={len(allowed_ids)}")

    result = []
    seen_slugs = set()

    for fert_id in visible_ids:
        if fert_id not in allowed_ids:
            continue
        if fert_id in seen_slugs:
            continue
        seen_slugs.add(fert_id)

        hydro_fert = hydro_by_id.get(fert_id)

        if hydro_fert:
            n_pct = hydro_fert.get('n_pct', 0) or 0
            p2o5_pct = hydro_fert.get('p2o5_pct', 0) or 0
            k2o_pct = hydro_fert.get('k2o_pct', 0) or 0
            ca_pct = hydro_fert.get('ca_pct', 0) or 0
            mg_pct = hydro_fert.get('mg_pct', 0) or 0
            s_pct = hydro_fert.get('s_pct', 0) or 0
            fert_name = hydro_fert.get('name', fert_id)
            fert_type = hydro_fert.get('type', 'salt')
            stock_tank = hydro_fert.get('stock_tank', 'B')
            form = hydro_fert.get('form', 'solid')
            fe_pct = hydro_fert.get('fe_pct', 0) or 0
            mn_pct = hydro_fert.get('mn_pct', 0) or 0
            zn_pct = hydro_fert.get('zn_pct', 0) or 0
            cu_pct = hydro_fert.get('cu_pct', 0) or 0
            b_pct = hydro_fert.get('b_pct', 0) or 0
            mo_pct = hydro_fert.get('mo_pct', 0) or 0
        else:
            try:
                from app.models.database_models import FertilizerProduct
                db_product = db.query(FertilizerProduct).filter(
                    FertilizerProduct.slug == fert_id,
                    FertilizerProduct.is_active == True).first()

                if db_product:
                    n_pct = float(db_product.n_pct or 0)
                    p2o5_pct = float(db_product.p2o5_pct or 0)
                    k2o_pct = float(db_product.k2o_pct or 0)
                    ca_pct = float(db_product.ca_pct or 0)
                    mg_pct = float(db_product.mg_pct or 0)
                    s_pct = float(db_product.s_pct or 0)
                    fert_name = db_product.name
                    fert_type = db_product.category or 'salt'
                    stock_tank = 'B'
                    form = db_product.physical_state or 'solid'
                    micros = db_product.micronutrients or {}
                    fe_pct = float(micros.get('Fe', 0)) if isinstance(
                        micros, dict) else 0
                    mn_pct = float(micros.get('Mn', 0)) if isinstance(
                        micros, dict) else 0
                    zn_pct = float(micros.get('Zn', 0)) if isinstance(
                        micros, dict) else 0
                    cu_pct = float(micros.get('Cu', 0)) if isinstance(
                        micros, dict) else 0
                    b_pct = float(micros.get('B', 0)) if isinstance(
                        micros, dict) else 0
                    mo_pct = float(micros.get('Mo', 0)) if isinstance(
                        micros, dict) else 0
                else:
                    continue
            except Exception:
                continue

        currency_defaults = get_default_price_for_currency(fert_id, currency)
        default_price_kg = currency_defaults.get("price_per_kg")
        default_price_liter = currency_defaults.get("price_per_liter")

        user_price_kg = user_price_kg_map.get(fert_id)
        user_price_liter = user_price_liter_map.get(fert_id)

        price_per_kg = user_price_kg if user_price_kg else (default_price_kg
                                                            or 25.0)
        price_per_liter = user_price_liter if user_price_liter else default_price_liter

        if form == 'liquid':
            price = price_per_liter or price_per_kg or 25.0
        else:
            price = price_per_kg

        result.append({
            'id': fert_id,
            'slug': fert_id,
            'name': fert_name,
            'type': fert_type,
            'n_pct': round(n_pct, 2) if n_pct else 0,
            'p2o5_pct': round(p2o5_pct, 2) if p2o5_pct else 0,
            'k2o_pct': round(k2o_pct, 2) if k2o_pct else 0,
            'ca_pct': round(ca_pct, 2) if ca_pct else 0,
            'mg_pct': round(mg_pct, 2) if mg_pct else 0,
            's_pct': round(s_pct, 2) if s_pct else 0,
            'fe_pct': fe_pct,
            'mn_pct': mn_pct,
            'zn_pct': zn_pct,
            'cu_pct': cu_pct,
            'b_pct': b_pct,
            'mo_pct': mo_pct,
            'price_per_kg': price_per_kg,
            'price_per_liter': price_per_liter,
            'price': price,
            'stock_tank': stock_tank,
            'form': form
        })

    for cf in custom_ferts:
        cf_slug = f"custom_{cf.id}"
        if cf_slug not in allowed_ids:
            continue
        if cf_slug not in seen_slugs:
            seen_slugs.add(cf_slug)

            cf_form = cf.form or 'solid'
            cf_price_kg = user_price_kg_map.get(cf_slug, cf.price_per_unit
                                                or 20.0)
            cf_price_liter = user_price_liter_map.get(cf_slug)

            if cf_form == 'liquid':
                cf_price = cf_price_liter or cf_price_kg or 20.0
            else:
                cf_price = cf_price_kg

            n_pct = 0
            p2o5_pct = 0
            k2o_pct = 0
            ca_pct = 0
            mg_pct = 0
            s_pct = 0

            if cf.no3_meq and cf.no3_meq > 0:
                n_pct += cf.no3_meq * 14.007 / 10
            if cf.nh4_meq and cf.nh4_meq > 0:
                n_pct += cf.nh4_meq * 14.007 / 10
            if cf.h2po4_meq and cf.h2po4_meq > 0:
                p2o5_pct = cf.h2po4_meq * 30.97 * 2.29 / 10
            if cf.k_meq and cf.k_meq > 0:
                k2o_pct = cf.k_meq * 39.10 * 1.205 / 10
            if cf.ca_meq and cf.ca_meq > 0:
                ca_pct = cf.ca_meq * 20.04 / 10
            if cf.mg_meq and cf.mg_meq > 0:
                mg_pct = cf.mg_meq * 12.15 / 10
            if cf.so4_meq and cf.so4_meq > 0:
                s_pct = cf.so4_meq * 16.03 / 10

            result.append({
                'id': cf_slug,
                'slug': cf_slug,
                'name': cf.name,
                'type': 'custom',
                'n_pct': round(n_pct, 2),
                'p2o5_pct': round(p2o5_pct, 2),
                'k2o_pct': round(k2o_pct, 2),
                'ca_pct': round(ca_pct, 2),
                'mg_pct': round(mg_pct, 2),
                's_pct': round(s_pct, 2),
                'price_per_kg': cf_price_kg,
                'price_per_liter': cf_price_liter,
                'price': cf_price,
                'form': cf_form,
                'stock_tank': cf.stock_tank or 'A',
                'is_custom': True
            })

    return result


# =============================================================================
# DETERMINISTIC FERTIIRRIGATION OPTIMIZER
# =============================================================================
# Deterministic greedy iterative algorithm.
# Based on agronomic rules and cost-efficiency scoring.
# =============================================================================

NUTRIENT_PRIORITY = ['N', 'K2O', 'P2O5', 'Ca', 'Mg', 'S']
MICRO_NUTRIENTS = ['Fe', 'Mn', 'Zn', 'Cu', 'B', 'Mo']

PROFILE_CONFIGS = {
    'economic': {
        'min_coverage': PROFILE_MIN_COVERAGE['economic'],
        'max_coverage': MAX_COVERAGE_LIMIT,
        'max_fertilizers': 5,
        'profile_name': 'Económico',
        'prefer_multi_nutrient': True,
        'diversity_penalty': 0.3,
        'maximize_coverage': False,
        'target_avg_coverage': 0.85,
        'cost_weight': 2.5,
        'coverage_weight': 0.8,
        'secondary_priority': 0.3,
        'allow_liebig_override': True
    },
    'balanced': {
        'min_coverage': PROFILE_MIN_COVERAGE['balanced'],
        'max_coverage': MAX_COVERAGE_LIMIT,
        'max_fertilizers': 6,
        'profile_name': 'Balanceado',
        'prefer_multi_nutrient': True,
        'diversity_penalty': 0.5,
        'maximize_coverage': False,
        'target_avg_coverage': 1.00,
        'cost_weight': 1.0,
        'coverage_weight': 1.5,
        'secondary_priority': 1.0,
        'allow_liebig_override': True
    },
    'complete': {
        'min_coverage': PROFILE_MIN_COVERAGE['complete'],
        'max_coverage': MAX_COVERAGE_LIMIT,
        'max_fertilizers': 10,
        'profile_name': 'Completo',
        'prefer_multi_nutrient': False,
        'diversity_penalty': 0.7,
        'maximize_coverage': True,
        'target_avg_coverage': 1.10,
        'cost_weight': 0.5,
        'coverage_weight': 2.0,
        'secondary_priority': 1.5,
        'allow_liebig_override': True
    }
}


def _get_nutrient_content(fert: Dict, nutrient: str) -> float:
    """Get nutrient content percentage from fertilizer."""
    mapping = {
        'N': 'n_pct',
        'P2O5': 'p2o5_pct',
        'K2O': 'k2o_pct',
        'Ca': 'ca_pct',
        'Mg': 'mg_pct',
        'S': 's_pct',
        'Fe': 'fe_pct',
        'Mn': 'mn_pct',
        'Zn': 'zn_pct',
        'Cu': 'cu_pct',
        'B': 'b_pct',
        'Mo': 'mo_pct'
    }
    return fert.get(mapping.get(nutrient, ''), 0) or 0


def _calculate_cost_per_kg_nutrient(fert: Dict, nutrient: str) -> float:
    """Calculate cost per kg of specific nutrient."""
    content = _get_nutrient_content(fert, nutrient)
    if content <= 0:
        return float('inf')
    price = fert.get('price_per_kg', 25.0) or 25.0
    return price / (content / 100)


def _is_chloride_fertilizer(fert: Dict) -> bool:
    """Check if fertilizer contains chloride."""
    fert_id = (fert.get('id') or fert.get('slug') or '').lower()
    fert_name = (fert.get('name') or '').lower()
    return any(cl in fert_id or cl in fert_name
               for cl in ['kcl', 'cloruro', 'chloride', 'cacl'])


def _is_sulfate_fertilizer(fert: Dict) -> bool:
    """Check if fertilizer is a sulfate (contains S)."""
    return (_get_nutrient_content(fert, 'S') or 0) > 0


def _filter_fertilizers(fertilizers: List[Dict],
                        deficits: Dict[str, float],
                        agronomic_context: Optional[Dict] = None,
                        allow_chloride: bool = True) -> List[Dict]:
    """Filter fertilizers based on agronomic constraints."""
    filtered = []

    water_cl = 0
    if agronomic_context and agronomic_context.get('water'):
        water_cl = agronomic_context['water'].get('cl_meqL', 0) or 0

    for fert in fertilizers:
        if not allow_chloride and _is_chloride_fertilizer(fert):
            continue
        if water_cl > 2 and _is_chloride_fertilizer(fert):
            continue

        has_useful_nutrient = False
        for nutrient in NUTRIENT_PRIORITY:
            if deficits.get(nutrient, 0) > 0 and _get_nutrient_content(
                    fert, nutrient) > 0:
                has_useful_nutrient = True
                break

        if has_useful_nutrient:
            filtered.append(fert)

    return filtered


def _score_fertilizer_v2(
        fert: Dict,
        remaining_deficits: Dict[str, float],
        original_deficits: Dict[str, float],
        current_contributions: Dict[str, float],
        profile_config: Dict,
        max_coverage_pct: float = MAX_COVERAGE_LIMIT) -> tuple:
    """
    Score a fertilizer based on ACTUAL coverage delta after applying caps.

    Returns: (score, constrained_dose, coverage_deltas)
    - score: Lower = better (cost per coverage point)
    - constrained_dose: The dose we can actually apply
    - coverage_deltas: Coverage gains for each nutrient

    Key insight: A fertilizer is only valuable if it can still contribute
    meaningful coverage to nutrients that need it, AFTER respecting all caps.
    """
    priority_nutrients = []
    for n in NUTRIENT_PRIORITY:
        original = original_deficits.get(n, 0)
        remaining = remaining_deficits.get(n, 0)
        if original > 0:
            current_cov = ((original - remaining) / original) * 100
            if current_cov < 95:
                priority_nutrients.append(n)

    dose, coverage_deltas = _calculate_constrained_dose(
        fert, remaining_deficits, original_deficits, current_contributions,
        max_coverage_pct, priority_nutrients)

    if dose < 0.1 or not coverage_deltas:
        return float('inf'), 0, {}

    price = fert.get('price_per_kg', 25.0) or 25.0
    cost = dose * price

    weighted_delta = 0
    nutrients_improved = 0
    max_remaining = max(
        remaining_deficits.values()) if remaining_deficits else 1

    for nutrient, delta in coverage_deltas.items():
        if delta > 0 and nutrient in priority_nutrients:
            remaining = remaining_deficits.get(nutrient, 0)
            original = original_deficits.get(nutrient, 1)
            current_cov = ((original - remaining) /
                           original) * 100 if original > 0 else 100

            priority_weight = remaining / max_remaining if max_remaining > 0 else 1
            gap_to_target = 95 - current_cov

            if current_cov < 60:
                urgency = 3.0
            elif current_cov < 80:
                urgency = 2.5
            else:
                urgency = min(2.0, gap_to_target / 30 + 1)

            if nutrient in ('Ca', 'Mg', 'S') and current_cov < 80:
                secondary_priority = profile_config.get(
                    'secondary_priority', 1.0)
                urgency *= (1 + 0.5 * secondary_priority)

            weighted_delta += delta * priority_weight * urgency
            nutrients_improved += 1

    if weighted_delta <= 0:
        return float('inf'), 0, {}

    cost_weight = profile_config.get('cost_weight', 1.0)
    coverage_weight = profile_config.get('coverage_weight', 1.0)

    score = (cost * cost_weight) / (weighted_delta * coverage_weight)

    if profile_config.get('prefer_multi_nutrient') and nutrients_improved > 1:
        score *= (1 - 0.2 * min(nutrients_improved - 1, 3))

    return score, dose, coverage_deltas


def _score_fertilizer(fert: Dict, remaining_deficits: Dict[str, float],
                      profile_config: Dict) -> float:
    """
    Legacy scoring function (simplified version).
    For full scoring with dose calculation, use _score_fertilizer_v2.
    """
    price = fert.get('price_per_kg', 25.0) or 25.0

    weighted_coverage = 0
    nutrients_covered = 0
    max_deficit = max(remaining_deficits.values()) if remaining_deficits else 1

    for nutrient in NUTRIENT_PRIORITY:
        deficit = remaining_deficits.get(nutrient, 0)
        if deficit <= 0:
            continue

        content = _get_nutrient_content(fert, nutrient)
        if content <= 0:
            continue

        nutrients_covered += 1
        deficit_weight = deficit / max_deficit if max_deficit > 0 else 1
        coverage_contrib = min(1.0,
                               content / 100 / deficit if deficit > 0 else 0)
        weighted_coverage += coverage_contrib * deficit_weight * (
            1 + deficit_weight)

    if weighted_coverage <= 0:
        return float('inf')

    base_score = price / weighted_coverage

    if profile_config.get('prefer_multi_nutrient') and nutrients_covered > 1:
        base_score *= (1 - 0.15 * min(nutrients_covered - 1, 3))

    return base_score


def _score_fertilizer_with_diversity(fert: Dict,
                                     remaining_deficits: Dict[str, float],
                                     profile_config: Dict,
                                     selected_ids: List[str]) -> float:
    """
    Score fertilizer with diversity penalty for already-selected fertilizers.
    Lower score = better.
    """
    base_score = _score_fertilizer(fert, remaining_deficits, profile_config)

    if base_score == float('inf'):
        return base_score

    fert_id = fert.get('id') or fert.get('slug') or ''
    if fert_id in selected_ids:
        return float('inf')

    diversity_penalty = profile_config.get('diversity_penalty', 0.5)
    n_selected = len(selected_ids)
    if n_selected > 0:
        base_score *= (1 + diversity_penalty * 0.1 * n_selected)

    return base_score


def _calculate_constrained_dose(fert: Dict,
                                remaining_deficits: Dict[str, float],
                                original_deficits: Dict[str, float],
                                current_contributions: Dict[str, float],
                                max_coverage_pct: float = MAX_COVERAGE_LIMIT,
                                priority_nutrients: List[str] = None) -> tuple:
    """
    Calculate the maximum dose that respects the 115% cap on ALL nutrients.

    Returns: (constrained_dose, coverage_deltas)
    - constrained_dose: The max kg/ha we can apply without exceeding 115% on ANY nutrient
    - coverage_deltas: Dict of coverage % gain for each nutrient at this dose

    STRICT LIMIT: The dose is limited by whichever nutrient first reaches 115%.
    If any nutrient has no headroom (already at 115%), dose for that nutrient = 0.
    """
    max_allowed_doses = []
    can_contribute_to_priority = False

    if priority_nutrients is None:
        priority_nutrients = NUTRIENT_PRIORITY

    for nutrient in NUTRIENT_PRIORITY:
        content = _get_nutrient_content(fert, nutrient)
        if content <= 0:
            continue

        original = original_deficits.get(nutrient, 0)
        if original <= 0:
            continue

        already_covered = current_contributions.get(nutrient, 0)
        max_total = original * max_coverage_pct
        remaining_headroom = max(0, max_total - already_covered)

        if remaining_headroom <= 0:
            max_allowed_doses.append(0)
            continue

        max_dose_for_nutrient = remaining_headroom / (content / 100)
        max_allowed_doses.append(max_dose_for_nutrient)

        current_cov = (already_covered /
                       original) * 100 if original > 0 else 100
        if nutrient in priority_nutrients and current_cov < 95:
            can_contribute_to_priority = True

    if not max_allowed_doses:
        return 0, {}

    constrained_dose = min(max_allowed_doses)
    constrained_dose = min(constrained_dose, 500)

    if constrained_dose < 0.1:
        return 0, {}

    if not can_contribute_to_priority:
        return 0, {}

    coverage_deltas = {}
    for nutrient in NUTRIENT_PRIORITY:
        content = _get_nutrient_content(fert, nutrient)
        if content <= 0:
            continue

        original = original_deficits.get(nutrient, 0)
        remaining = remaining_deficits.get(nutrient, 0)

        if original > 0 and remaining > 0:
            contribution = constrained_dose * (content / 100)
            delta_pct = (contribution / original) * 100
            coverage_deltas[nutrient] = delta_pct

    return constrained_dose, coverage_deltas


def _calculate_optimal_dose(
        fert: Dict,
        remaining_deficits: Dict[str, float],
        original_deficits: Dict[str, float],
        current_contributions: Dict[str, float],
        max_coverage_pct: float = MAX_COVERAGE_LIMIT) -> float:
    """
    Legacy wrapper for _calculate_constrained_dose.
    Returns only the dose (for backward compatibility).
    """
    dose, _ = _calculate_constrained_dose(fert, remaining_deficits,
                                          original_deficits,
                                          current_contributions,
                                          max_coverage_pct)
    return dose


def _apply_dose(fert: Dict, dose_kg: float, remaining_deficits: Dict[str,
                                                                     float],
                micro_remaining: Dict[str, float]) -> Dict[str, float]:
    """Apply a fertilizer dose and return nutrient contributions."""
    contributions = {}

    for nutrient in NUTRIENT_PRIORITY:
        content = _get_nutrient_content(fert, nutrient)
        if content > 0:
            contribution = dose_kg * (content / 100)
            contributions[nutrient] = contribution
            remaining_deficits[nutrient] = max(
                0,
                remaining_deficits.get(nutrient, 0) - contribution)

    for micro in MICRO_NUTRIENTS:
        content = _get_nutrient_content(fert, micro)
        if content > 0:
            contribution = dose_kg * (content / 100) * 1000
            contributions[micro] = contribution
            micro_remaining[micro] = max(
                0,
                micro_remaining.get(micro, 0) - contribution)

    return contributions


def _calculate_coverage(
        original_deficits: Dict[str, float],
        remaining_deficits: Dict[str, float]) -> Dict[str, float]:
    """Calculate coverage percentage for each nutrient."""
    coverage = {}
    for nutrient in NUTRIENT_PRIORITY:
        original = original_deficits.get(nutrient, 0)
        if original > 0:
            remaining = remaining_deficits.get(nutrient, 0)
            covered = original - remaining
            coverage[nutrient] = round((covered / original) * 100, 1)
        else:
            coverage[nutrient] = 0
    return coverage


def _count_carriers_per_nutrient(fertilizers: List[Dict],
                                 deficits: Dict[str, float]) -> Dict[str, int]:
    """Count how many fertilizers can provide each nutrient."""
    carrier_count = {n: 0 for n in NUTRIENT_PRIORITY}
    for fert in fertilizers:
        for nutrient in NUTRIENT_PRIORITY:
            if deficits.get(nutrient, 0) > 0:
                content = _get_nutrient_content(fert, nutrient)
                if content > 0:
                    carrier_count[nutrient] += 1
    return carrier_count


def _optimize_profile(
        deficits: Dict[str, float],
        micro_deficits: Dict[str, float],
        fertilizers: List[Dict],
        profile_key: str,
        agronomic_context: Optional[Dict] = None,
        acid_constraints: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Generate a single optimization profile using a deterministic greedy algorithm.

    ORDEN DE PRIORIDADES (determinístico):
    1) Ley de Liebig (≥80% todos los nutrientes con déficit)
    2) Cobertura mínima por perfil (económico/balanceado/completo)
    3) Minimizar costo total
    4) Minimizar sobrecoberturas (>120%) cuando sea necesario

    ESTRATEGIA MEJORADA:
    1. FASE 1 - Carriers escasos: Priorizar nutrientes con pocas opciones de carriers (ej: Mg)
    2. FASE 2 - Loop greedy: Seleccionar fertilizantes costo-eficientes
    3. FASE 3 - Gap-fill: Buscar fertilizantes específicos para nutrientes sin cubrir

    ACID-AWARE OPTIMIZATION:
    - When acid covers ≥90% of S/N/P, EXCLUDE high-content fertilizers (sulfates, etc.)
    - Apply severe penalty to medium-content fertilizers
    - Boost nitrate alternatives with 2.5x multiplier
    """
    config = PROFILE_CONFIGS[profile_key]

    allow_chloride = profile_key == 'economic'
    available = _filter_fertilizers(fertilizers, deficits, agronomic_context,
                                    allow_chloride)

    if acid_constraints:
        available = apply_acid_constraints_to_fertilizers(
            available, acid_constraints)

    if not available:
        return {
            'fertilizers': [],
            'coverage': {
                n: 0
                for n in NUTRIENT_PRIORITY
            },
            'total_cost_per_ha': 0,
            'profile_name': config['profile_name'],
            'success': False,
            'error': 'No hay fertilizantes disponibles que cubran los déficits'
        }

    remaining_deficits = {k: v for k, v in deficits.items()}
    micro_remaining = {k: v for k, v in micro_deficits.items()}
    current_contributions = {n: 0.0 for n in NUTRIENT_PRIORITY}
    selected_fertilizers = []
    selected_ids = []
    total_cost = 0

    max_iterations = config['max_fertilizers']
    min_coverage = config['min_coverage']
    max_coverage = config.get('max_coverage', MAX_COVERAGE_LIMIT)

    carrier_counts = _count_carriers_per_nutrient(available, deficits)

    secondary_nutrients = ['Mg', 'Ca', 'S']
    reserved_slots = len(
        secondary_nutrients) if profile_key != 'economic' else 2
    carrier_conflicts = []

    for sec_nutrient in secondary_nutrients[:reserved_slots]:
        if deficits.get(sec_nutrient, 0) <= 0:
            continue
        if len(selected_fertilizers) >= max_iterations:
            break

        current_sec_cov = current_contributions.get(
            sec_nutrient, 0) / deficits[sec_nutrient] * 100 if deficits.get(
                sec_nutrient, 0) > 0 else 100
        if current_sec_cov >= 80:
            continue

        best_carrier = None
        best_score = float('inf')
        best_dose = 0

        for fert in available:
            fert_id = fert.get('id') or fert.get('slug') or ''
            if fert_id in selected_ids:
                continue

            content = _get_nutrient_content(fert, sec_nutrient)
            if content < 5:
                continue

            dose, deltas = _calculate_constrained_dose(
                fert, remaining_deficits, deficits, current_contributions,
                max_coverage, [sec_nutrient])

            if dose < 0.1:
                continue

            target_delta = deltas.get(sec_nutrient, 0)
            if target_delta <= 0:
                continue

            price = fert.get('price_per_kg', 25.0) or 25.0
            cost_weight = config.get('cost_weight', 1.0)
            base_score = (price * dose * cost_weight) / target_delta

            collateral_penalty = 0
            collateral_bonus = 0
            for other_n in NUTRIENT_PRIORITY:
                if other_n == sec_nutrient:
                    continue
                other_delta = deltas.get(other_n, 0)
                if other_delta > 0:
                    other_cov = current_contributions.get(
                        other_n, 0) / deficits.get(other_n,
                                                   1) * 100 if deficits.get(
                                                       other_n, 0) > 0 else 0
                    if other_cov > 80:
                        collateral_penalty += other_delta * 0.5
                    elif deficits.get(
                            other_n,
                            0) > 0 and config.get('prefer_multi_nutrient'):
                        collateral_bonus += other_delta * 0.3

            score = base_score * (1 + collateral_penalty / 100 -
                                  collateral_bonus / 100)

            if score < best_score:
                best_score = score
                best_carrier = fert
                best_dose = dose

        if best_carrier and best_dose >= 0.1:
            contributions = _apply_dose(best_carrier, best_dose,
                                        remaining_deficits, micro_remaining)

            for n, contrib in contributions.items():
                if n in current_contributions:
                    current_contributions[n] += contrib

            price = best_carrier.get('price_per_kg', 25.0) or 25.0
            subtotal = best_dose * price
            total_cost += subtotal

            tank = best_carrier.get('stock_tank', 'A')
            if _get_nutrient_content(best_carrier, 'Ca') > 0:
                tank = 'B'

            fert_id = best_carrier.get('id') or best_carrier.get('slug')
            selected_ids.append(fert_id)

            selected_fertilizers.append({
                'id':
                fert_id,
                'name':
                best_carrier.get('name'),
                'dose_kg_ha':
                round(best_dose, 2),
                'dose_per_application':
                round(best_dose, 2),
                'price_per_kg':
                price,
                'subtotal':
                round(subtotal, 2),
                'tank':
                tank,
                'contributions': {
                    k: round(v, 2)
                    for k, v in contributions.items() if v > 0
                },
                'reserved_secondary':
                True
            })

    scarce_nutrients = [
        n for n in NUTRIENT_PRIORITY if deficits.get(n, 0) > 0
        and carrier_counts.get(n, 0) <= 3 and n not in secondary_nutrients
    ]

    for scarce_nutrient in scarce_nutrients:
        current_coverage = _calculate_coverage(deficits, remaining_deficits)
        if current_coverage.get(scarce_nutrient, 0) >= min_coverage * 100:
            continue

        needs_multi = [
            n for n in NUTRIENT_PRIORITY
            if n != scarce_nutrient and deficits.get(n, 0) > 0
            and current_coverage.get(n, 0) < (min_coverage * 100)
        ]
        has_multi_for_target = any(
            _get_nutrient_content(f, scarce_nutrient) > 0 and any(
                _get_nutrient_content(f, n) > 0 for n in needs_multi)
            for f in available)

        best_carrier = None
        best_score = float('inf')
        best_dose = 0

        for fert in available:
            fert_id = fert.get('id') or fert.get('slug') or ''
            if fert_id in selected_ids:
                continue

            content = _get_nutrient_content(fert, scarce_nutrient)
            if content <= 0:
                continue

            dose, deltas = _calculate_constrained_dose(
                fert, remaining_deficits, deficits, current_contributions,
                max_coverage, [scarce_nutrient])

            if dose < 0.1:
                continue

            target_delta = deltas.get(scarce_nutrient, 0)
            if target_delta <= 0:
                continue

            price = fert.get('price_per_kg', 25.0) or 25.0
            score = (price * dose) / target_delta

            if needs_multi:
                provides_other = any(
                    _get_nutrient_content(fert, n) > 0 for n in needs_multi)
                if has_multi_for_target and not provides_other:
                    continue
                if provides_other:
                    score = score * 0.7

            acid_penalty = fert.get('acid_penalty', 1.0)
            acid_boost = fert.get('acid_boost', 1.0)
            score = score / acid_boost * (1 / acid_penalty
                                          if acid_penalty < 1 else 1)

            if score < best_score:
                best_score = score
                best_carrier = fert
                best_dose = dose

        if best_carrier and best_dose >= 0.1:
            contributions = _apply_dose(best_carrier, best_dose,
                                        remaining_deficits, micro_remaining)

            for n, contrib in contributions.items():
                if n in current_contributions:
                    current_contributions[n] += contrib

            price = best_carrier.get('price_per_kg', 25.0) or 25.0
            subtotal = best_dose * price
            total_cost += subtotal

            tank = best_carrier.get('stock_tank', 'A')
            if _get_nutrient_content(best_carrier, 'Ca') > 0:
                tank = 'B'

            fert_id = best_carrier.get('id') or best_carrier.get('slug')
            selected_ids.append(fert_id)

            selected_fertilizers.append({
                'id':
                fert_id,
                'name':
                best_carrier.get('name'),
                'dose_kg_ha':
                round(best_dose, 2),
                'dose_per_application':
                round(best_dose, 2),
                'price_per_kg':
                price,
                'subtotal':
                round(subtotal, 2),
                'tank':
                tank,
                'contributions': {
                    k: round(v, 2)
                    for k, v in contributions.items() if v > 0
                },
                'scarce_carrier':
                True
            })

    maximize_coverage = config.get('maximize_coverage', False)
    target_avg_coverage = config.get('target_avg_coverage', 1.0)

    for iteration in range(max_iterations + 5):
        current_coverage = _calculate_coverage(deficits, remaining_deficits)

        if len(selected_fertilizers) >= max_iterations:
            break

        all_at_max = all(
            current_coverage.get(n, 0) >= max_coverage * 100
            for n in NUTRIENT_PRIORITY if deficits.get(n, 0) > 0)
        if all_at_max:
            break

        all_covered = all(
            current_coverage.get(n, 0) >= min_coverage * 100
            for n in NUTRIENT_PRIORITY if deficits.get(n, 0) > 0)

        if all_covered and not maximize_coverage:
            nutrients_with_deficit = [
                n for n in NUTRIENT_PRIORITY if deficits.get(n, 0) > 0
            ]
            if nutrients_with_deficit:
                avg_coverage = sum(
                    current_coverage.get(n, 0) for n in
                    nutrients_with_deficit) / len(nutrients_with_deficit)
                if avg_coverage >= target_avg_coverage * 100:
                    break
            else:
                break

        if all_covered and maximize_coverage:
            pass

        best_fert = None
        best_score = float('inf')
        best_dose = 0

        for fert in available:
            fert_id = fert.get('id') or fert.get('slug') or ''
            if fert_id in selected_ids:
                continue

            score, dose, deltas = _score_fertilizer_v2(fert,
                                                       remaining_deficits,
                                                       deficits,
                                                       current_contributions,
                                                       config, max_coverage)

            acid_penalty = fert.get('acid_penalty', 1.0)
            acid_boost = fert.get('acid_boost', 1.0)
            if acid_penalty < 1:
                score = score / acid_penalty
            if acid_boost > 1:
                score = score / acid_boost

            if score < best_score and dose >= 0.1:
                best_score = score
                best_fert = fert
                best_dose = dose

        if not best_fert or best_score == float('inf') or best_dose < 0.1:
            break

        contributions = _apply_dose(best_fert, best_dose, remaining_deficits,
                                    micro_remaining)

        for n, contrib in contributions.items():
            if n in current_contributions:
                current_contributions[n] += contrib

        price = best_fert.get('price_per_kg', 25.0) or 25.0
        subtotal = best_dose * price
        total_cost += subtotal

        tank = best_fert.get('stock_tank', 'A')
        if _get_nutrient_content(best_fert, 'Ca') > 0:
            tank = 'B'

        fert_id = best_fert.get('id') or best_fert.get('slug')
        selected_ids.append(fert_id)

        selected_fertilizers.append({
            'id': fert_id,
            'name': best_fert.get('name'),
            'dose_kg_ha': round(best_dose, 2),
            'dose_per_application': round(best_dose, 2),
            'price_per_kg': price,
            'subtotal': round(subtotal, 2),
            'tank': tank,
            'contributions': {
                k: round(v, 2)
                for k, v in contributions.items() if v > 0
            }
        })

    current_coverage = _calculate_coverage(deficits, remaining_deficits)
    min_cov_pct = min_coverage * 100

    uncovered_nutrients = [
        n for n in NUTRIENT_PRIORITY
        if deficits.get(n, 0) > 0 and current_coverage.get(n, 0) < min_cov_pct
    ]

    gap_fill_count = 0
    max_gap_fills = 6

    if profile_key == 'complete':
        max_gap_fills = 8

    while uncovered_nutrients and gap_fill_count < max_gap_fills:
        target_nutrient = min(uncovered_nutrients,
                              key=lambda n: current_coverage.get(n, 0))

        best_fert_for_gap = None
        best_score = float('inf')
        best_dose_for_gap = 0

        for fert in available:
            fert_id = fert.get('id') or fert.get('slug') or ''
            if fert_id in selected_ids:
                continue

            target_content = _get_nutrient_content(fert, target_nutrient)
            if target_content <= 0:
                continue

            original_target = deficits.get(target_nutrient, 0)
            if original_target <= 0:
                continue

            target_headroom = original_target * max_coverage - current_contributions.get(
                target_nutrient, 0)
            if target_headroom <= 0:
                continue

            dose, deltas = _calculate_constrained_dose(fert,
                                                       remaining_deficits,
                                                       deficits,
                                                       current_contributions,
                                                       max_coverage)

            if dose < 0.1:
                continue

            target_delta = deltas.get(target_nutrient, 0)
            if target_delta <= 0:
                continue

            price = fert.get('price_per_kg', 25.0) or 25.0
            contribution_to_target = dose * (target_content / 100)
            score = (
                price * dose
            ) / contribution_to_target if contribution_to_target > 0 else float(
                'inf')

            acid_penalty = fert.get('acid_penalty', 1.0)
            acid_boost = fert.get('acid_boost', 1.0)
            if acid_penalty < 1:
                score = score / acid_penalty
            if acid_boost > 1:
                score = score / acid_boost

            if score < best_score:
                best_score = score
                best_fert_for_gap = fert
                best_dose_for_gap = dose

        if not best_fert_for_gap or best_dose_for_gap < 0.1:
            uncovered_nutrients.remove(target_nutrient)
            continue

        dose = best_dose_for_gap

        contributions = _apply_dose(best_fert_for_gap, dose,
                                    remaining_deficits, micro_remaining)

        for n, contrib in contributions.items():
            if n in current_contributions:
                current_contributions[n] += contrib

        price = best_fert_for_gap.get('price_per_kg', 25.0) or 25.0
        subtotal = dose * price
        total_cost += subtotal

        tank = best_fert_for_gap.get('stock_tank', 'A')
        if _get_nutrient_content(best_fert_for_gap, 'Ca') > 0:
            tank = 'B'

        fert_id = best_fert_for_gap.get('id') or best_fert_for_gap.get('slug')
        selected_ids.append(fert_id)

        selected_fertilizers.append({
            'id': fert_id,
            'name': best_fert_for_gap.get('name'),
            'dose_kg_ha': round(dose, 2),
            'dose_per_application': round(dose, 2),
            'price_per_kg': price,
            'subtotal': round(subtotal, 2),
            'tank': tank,
            'contributions': {
                k: round(v, 2)
                for k, v in contributions.items() if v > 0
            },
            'gap_fill': True
        })

        gap_fill_count += 1
        current_coverage = _calculate_coverage(deficits, remaining_deficits)
        uncovered_nutrients = [
            n for n in NUTRIENT_PRIORITY if deficits.get(n, 0) > 0
            and current_coverage.get(n, 0) < min_cov_pct
        ]

    current_coverage = _calculate_coverage(deficits, remaining_deficits)

    liebig_threshold = MIN_LIEBIG_COVERAGE * 100
    rescue_nutrients = [
        n for n in NUTRIENT_PRIORITY if deficits.get(n, 0) > 0
        and current_coverage.get(n, 0) < liebig_threshold
    ]

    rescue_count = 0
    max_rescues = 3
    allow_override = config.get('allow_liebig_override', False)
    rescue_max_coverage = LIEBIG_OVERRIDE_MAX if allow_override else MAX_COVERAGE_LIMIT
    liebig_overrides = []

    while rescue_nutrients and rescue_count < max_rescues and len(
            selected_fertilizers) < config['max_fertilizers'] + 4:
        target_nutrient = min(rescue_nutrients,
                              key=lambda n: current_coverage.get(n, 0))

        best_rescue_fert = None
        best_efficiency = float('inf')
        best_rescue_dose = 0

        for fert in available:
            fert_id = fert.get('id') or fert.get('slug') or ''
            if fert_id in selected_ids:
                continue

            target_content = _get_nutrient_content(fert, target_nutrient)
            if target_content < 3:
                continue

            original_target = deficits.get(target_nutrient, 0)
            if original_target <= 0:
                continue

            target_headroom = original_target * rescue_max_coverage - current_contributions.get(
                target_nutrient, 0)
            if target_headroom <= 0:
                continue

            dose, deltas = _calculate_constrained_dose(
                fert, remaining_deficits, deficits, current_contributions,
                rescue_max_coverage, [target_nutrient])

            if dose < 0.1:
                continue

            target_delta = deltas.get(target_nutrient, 0)
            if target_delta <= 0:
                continue

            price = fert.get('price_per_kg', 25.0) or 25.0
            efficiency = (price * dose) / target_delta

            if efficiency < best_efficiency:
                best_efficiency = efficiency
                best_rescue_fert = fert
                best_rescue_dose = dose

        if not best_rescue_fert or best_rescue_dose < 0.1:
            carrier_conflicts.append({
                'nutrient':
                target_nutrient,
                'coverage':
                current_coverage.get(target_nutrient, 0),
                'reason':
                f'{target_nutrient} no puede alcanzar 80% sin exceder límites de otros nutrientes (conflicto de carriers)'
            })
            rescue_nutrients.remove(target_nutrient)
            continue

        contributions = _apply_dose(best_rescue_fert, best_rescue_dose,
                                    remaining_deficits, micro_remaining)

        for n, contrib in contributions.items():
            if n in current_contributions:
                current_contributions[n] += contrib

        price = best_rescue_fert.get('price_per_kg', 25.0) or 25.0
        subtotal = best_rescue_dose * price
        total_cost += subtotal

        tank = best_rescue_fert.get('stock_tank', 'A')
        if _get_nutrient_content(best_rescue_fert, 'Ca') > 0:
            tank = 'B'

        fert_id = best_rescue_fert.get('id') or best_rescue_fert.get('slug')
        selected_ids.append(fert_id)

        selected_fertilizers.append({
            'id':
            fert_id,
            'name':
            best_rescue_fert.get('name'),
            'dose_kg_ha':
            round(best_rescue_dose, 2),
            'dose_per_application':
            round(best_rescue_dose, 2),
            'price_per_kg':
            price,
            'subtotal':
            round(subtotal, 2),
            'tank':
            tank,
            'contributions': {
                k: round(v, 2)
                for k, v in contributions.items() if v > 0
            },
            'liebig_rescue':
            True
        })

        rescue_count += 1
        current_coverage = _calculate_coverage(deficits, remaining_deficits)

        for n in NUTRIENT_PRIORITY:
            cov = current_coverage.get(n, 0)
            if cov > MAX_COVERAGE_LIMIT * 100 and deficits.get(n, 0) > 0:
                liebig_overrides.append({
                    'nutrient':
                    n,
                    'coverage':
                    round(cov, 1),
                    'reason':
                    f'{n} excede 115% para permitir cobertura de {target_nutrient} (Ley de Liebig)'
                })
        rescue_nutrients = [
            n for n in NUTRIENT_PRIORITY if deficits.get(n, 0) > 0
            and current_coverage.get(n, 0) < liebig_threshold
        ]

    final_coverage = _calculate_coverage(deficits, remaining_deficits)

    nutrients_with_deficit = [
        n for n in NUTRIENT_PRIORITY if deficits.get(n, 0) > 0
    ]
    failed_nutrients = []
    if nutrients_with_deficit:
        for n in nutrients_with_deficit:
            cov = final_coverage.get(n, 0)
            if cov < (min_coverage * 100):
                failed_nutrients.append(f"{n}: {cov:.0f}%")
        meets_target = len(failed_nutrients) == 0
    else:
        meets_target = True

    return {
        'fertilizers': selected_fertilizers,
        'coverage': final_coverage,
        'total_cost_per_ha': round(total_cost, 2),
        'profile_name': config['profile_name'],
        'success': meets_target,
        'coverage_met': meets_target,
        'target_coverage_pct': min_coverage * 100,
        'failed_nutrients': failed_nutrients if failed_nutrients else None,
        'carrier_conflicts': carrier_conflicts if carrier_conflicts else None,
        'liebig_overrides': liebig_overrides if liebig_overrides else None
    }


def optimize_deterministic(
        deficits: Dict[str, float],
        micro_deficits: Dict[str, float],
        available_fertilizers: List[Dict],
        crop_name: str,
        growth_stage: str,
        irrigation_system: str = "goteo",
        num_applications: int = 1,
        agronomic_context: Optional[Dict[str, Any]] = None,
        acid_data: Optional[Dict[str, Any]] = None,
        water_volume_m3_ha: float = 50.0,
        area_ha: float = 1.0,
        user_acid_prices: Optional[Dict[str, float]] = None,
        traceability_context: Optional[Dict[str,
                                            Any]] = None) -> Dict[str, Any]:
    """
    Generate 3 fertilization profiles using deterministic greedy algorithm.

    Rule-based approach that:
    1. Recommends acids for bicarbonate neutralization (with nutrient contribution)
    2. Scores fertilizers by cost per kg of deficit coverage
    3. Iteratively selects best fertilizers until coverage targets are met
    4. Applies agronomic constraints (chloride limits, compatibility, etc.)

    Args:
        deficits: Macronutrient deficits in kg/ha
        micro_deficits: Micronutrient deficits in g/ha
        available_fertilizers: List of fertilizer dicts with composition and prices
        crop_name: Name of the crop
        growth_stage: Current phenological stage
        irrigation_system: Type of irrigation
        num_applications: Number of applications
        agronomic_context: Optional water/soil data for constraints
        acid_data: Optional acid info (legacy, for backward compatibility)
        water_volume_m3_ha: Water volume per irrigation in m3/ha
        area_ha: Area in hectares
        user_acid_prices: Optional dict with user's acid prices per liter

    Returns:
        Dict with economic, balanced, and complete profiles, plus acid_recommendation
    """
    logger.info(
        f"[DeterministicOptimizer] Starting optimization for {crop_name} - {growth_stage}"
    )
    logger.info(f"[DeterministicOptimizer] Deficits: {deficits}")
    logger.info(
        f"[DeterministicOptimizer] Available fertilizers: {len(available_fertilizers)}"
    )

    acid_recommendation = None
    adjusted_deficits = deficits.copy()

    water_analysis = {}
    if agronomic_context and agronomic_context.get('water'):
        water_analysis = agronomic_context['water']

        acid_recommendation = recommend_acids_for_fertiirrigation(
            water_analysis=water_analysis,
            deficits=deficits,
            water_volume_m3_ha=water_volume_m3_ha,
            num_applications=num_applications,
            area_ha=area_ha,
            user_prices=user_acid_prices)

        if acid_recommendation.get('recommended'):
            adjusted_deficits = acid_recommendation['adjusted_deficits']
            logger.info(
                f"[DeterministicOptimizer] Acids recommended: {len(acid_recommendation['acids'])} acids"
            )
            logger.info(
                f"[DeterministicOptimizer] Adjusted deficits after acid: {adjusted_deficits}"
            )

    if not acid_recommendation and acid_data:
        adjusted_deficits = adjust_deficits_for_acid_nitrogen(
            deficits, acid_data)

    result = {}

    fert_catalog = {}
    for f in available_fertilizers:
        fid = f.get('id') or f.get('slug') or ''
        fname = f.get('name', '')
        comp = {
            'n_pct': f.get('n_pct') or f.get('analysis_n_pct', 0) or 0,
            'p2o5_pct': f.get('p2o5_pct') or f.get('analysis_p2o5_pct', 0)
            or 0,
            'k2o_pct': f.get('k2o_pct') or f.get('analysis_k2o_pct', 0) or 0,
            'ca_pct': f.get('ca_pct') or f.get('analysis_ca_pct', 0) or 0,
            'mg_pct': f.get('mg_pct') or f.get('analysis_mg_pct', 0) or 0,
            's_pct': f.get('s_pct') or f.get('analysis_s_pct', 0) or 0,
            'price': f.get('price_per_kg', 25) or 25
        }
        if fid:
            fert_catalog[fid] = comp
        if fname:
            fert_catalog[fname] = comp
            fert_catalog[fname.lower()] = comp

    def resolve_fert_composition(fert_entry):
        fid = fert_entry.get('id', '')
        fname = fert_entry.get('name', '')
        if fid and fid in fert_catalog:
            return fert_catalog[fid]
        if fname and fname in fert_catalog:
            return fert_catalog[fname]
        if fname and fname.lower() in fert_catalog:
            return fert_catalog[fname.lower()]
        return fert_entry.get('contributions', {})

    def normalize_profile(profile,
                          deficits_dict,
                          min_cov,
                          n_apps,
                          acid_contribs=None):
        contributions = {n: 0.0 for n in NUTRIENT_PRIORITY}

        if acid_contribs:
            contributions['N'] += acid_contribs.get('N', 0)
            p_from_acid = acid_contribs.get('P', 0)
            contributions['P2O5'] += p_from_acid * 2.29
            contributions['S'] += acid_contribs.get('S', 0)

        for fert in profile.get('fertilizers', []):
            dose = fert.get('dose_kg_ha', 0) or 0
            comp = resolve_fert_composition(fert)

            if 'n_pct' in comp:
                contributions['N'] += dose * (comp.get('n_pct', 0) / 100)
                contributions['P2O5'] += dose * (comp.get('p2o5_pct', 0) / 100)
                contributions['K2O'] += dose * (comp.get('k2o_pct', 0) / 100)
                contributions['Ca'] += dose * (comp.get('ca_pct', 0) / 100)
                contributions['Mg'] += dose * (comp.get('mg_pct', 0) / 100)
                contributions['S'] += dose * (comp.get('s_pct', 0) / 100)
            else:
                for n in NUTRIENT_PRIORITY:
                    contributions[n] += comp.get(n, 0)

            fert['dose_per_application'] = round(dose / max(1, n_apps), 2)

            ca_content = comp.get('ca_pct', 0) if 'ca_pct' in comp else 0
            fert['tank'] = 'B' if ca_content > 0 else 'A'

            has_composition_data = 'n_pct' in comp
            
            if has_composition_data:
                calculated_contribs = {
                    'N': dose * (comp.get('n_pct', 0) / 100),
                    'P2O5': dose * (comp.get('p2o5_pct', 0) / 100),
                    'K2O': dose * (comp.get('k2o_pct', 0) / 100),
                    'Ca': dose * (comp.get('ca_pct', 0) / 100),
                    'Mg': dose * (comp.get('mg_pct', 0) / 100),
                    'S': dose * (comp.get('s_pct', 0) / 100)
                }
                fert['contributions'] = {
                    k: round(v, 2)
                    for k, v in calculated_contribs.items() if v > 0
                }
            else:
                existing_contribs = fert.get('contributions', {})
                if not existing_contribs or not any(v > 0 for v in existing_contribs.values()):
                    fert['contributions'] = {
                        k: round(v, 2)
                        for k, v in comp.items() if isinstance(v, (int, float)) and v > 0
                    }

        coverage = {}
        failed = []
        for nutrient in NUTRIENT_PRIORITY:
            deficit = deficits_dict.get(nutrient, 0)
            if deficit > 0:
                covered = contributions.get(nutrient, 0)
                cov_pct = round((covered / deficit) * 100, 1)
                coverage[nutrient] = cov_pct
                if cov_pct < (min_cov * 100):
                    failed.append(f"{nutrient}: {cov_pct:.0f}%")
            else:
                coverage[nutrient] = 0

        profile['coverage'] = coverage
        profile['coverage_met'] = len(failed) == 0
        profile['failed_nutrients'] = failed if failed else None
        profile['target_coverage_pct'] = min_cov * 100
        profile['success'] = len(failed) == 0

        total_cost = sum((fert.get('dose_kg_ha', 0) or 0) *
                         resolve_fert_composition(fert).get('price', 25)
                         for fert in profile.get('fertilizers', []))
        profile['total_cost_per_ha'] = round(total_cost, 2)

        return profile

    failed_profiles = []

    acid_contribs = None
    acid_constraints = None
    acid_coverage_info = {}
    if acid_recommendation and acid_recommendation.get('recommended'):
        acid_contribs = acid_recommendation.get('total_contributions', {})
        acid_constraints = get_acid_coverage_constraints(
            acid_contribs, deficits)
        acid_coverage_info = acid_constraints.get('nutrients_covered_by_acid',
                                                  {})
        if acid_constraints.get('warnings'):
            logger.info(
                f"[DeterministicOptimizer] Acid constraints: {acid_constraints['warnings']}"
            )

    base_traceability = {
        'requirements': (traceability_context or {}).get('requirements'),
        'soil_contribution': (traceability_context
                              or {}).get('soil_contribution'),
        'water_contribution': (traceability_context
                               or {}).get('water_contribution'),
        'acid_contribution':
        (traceability_context or {}).get('acid_contribution') or acid_contribs,
        'deficit_net': (traceability_context or {}).get('deficit_net')
        or adjusted_deficits,
        'deficit_input':
        deficits,
        'micro_deficit_input':
        micro_deficits,
        'water_analysis': (traceability_context or {}).get('water_analysis')
        or (agronomic_context or {}).get('water'),
        'area_ha':
        area_ha,
        'water_volume_m3_ha':
        water_volume_m3_ha,
        'num_applications':
        num_applications
    }

    for profile_key in ['economic', 'balanced', 'complete']:
        config = PROFILE_CONFIGS[profile_key]
        min_coverage = config['min_coverage']

        profile = _optimize_profile(adjusted_deficits, micro_deficits,
                                    available_fertilizers, profile_key,
                                    agronomic_context, acid_constraints)

        profile = enforce_hard_constraints(profile, adjusted_deficits,
                                           agronomic_context,
                                           available_fertilizers, growth_stage)

        profile = normalize_profile(profile, deficits, min_coverage,
                                    num_applications, acid_contribs)

        profile['coverage_explained'] = build_coverage_explained(
            profile, adjusted_deficits, agronomic_context, growth_stage)
        profile['traceability'] = base_traceability

        if not profile.get('coverage_met', True):
            failed_nutrients = profile.get('failed_nutrients', [])
            failed_profiles.append({
                'profile': profile_key,
                'failed_nutrients': failed_nutrients
            })

            conflict_messages = analyze_carrier_conflicts(
                failed_nutrients, profile.get('coverage', {}),
                available_fertilizers, profile_key)
            profile['limitation_messages'] = conflict_messages

            logger.warning(
                f"[DeterministicOptimizer] {profile_key} did not meet coverage target: {failed_nutrients}"
            )

        result[profile_key] = profile
        logger.info(
            f"[DeterministicOptimizer] {profile_key}: {len(profile.get('fertilizers', []))} fertilizers, "
            f"cost={profile.get('total_cost_per_ha', 0):.2f}, coverage={profile.get('coverage', {})}"
        )

    all_profiles_failed = len(failed_profiles) == 3

    return {
        "success": True,
        "profiles": result,
        "model_used": "deterministic_v1",
        "adjusted_deficits": adjusted_deficits,
        "warnings": failed_profiles if failed_profiles else None,
        "coverage_limitations": all_profiles_failed,
        "acid_recommendation": acid_recommendation,
        "acid_coverage_info": acid_coverage_info
    }

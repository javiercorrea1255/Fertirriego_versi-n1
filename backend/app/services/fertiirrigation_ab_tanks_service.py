"""
FertiIrrigation A/B Tanks Service.
Separates fertilizers into Tank A and Tank B based on chemical compatibility.
Calculates stock solution concentrations and injection programs.
"""
import logging
import re
import unicodedata
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

TANK_A_KEYWORDS = ['calcio', 'calcium', 'nitrato de calcio', 'cloruro de calcio', 'quelato', 'hierro', 'manganeso', 'zinc', 'cobre', 'boro', 'molibdeno', 'fe', 'mn', 'zn', 'cu', 'b', 'mo']
TANK_B_KEYWORDS = ['fosfato', 'phosphate', 'sulfato', 'sulfate', 'map', 'dap', 'magnesio', 'magnesium', 'acido', 'acid', 'fosforico', 'sulfurico', 'nitrico']
NEUTRAL_KEYWORDS = ['nitrato de potasio', 'potassium nitrate', 'urea', 'nitrato de amonio', 'ammonium nitrate']

INCOMPATIBLE_WITH_CALCIUM = [
    'fosfato', 'phosphate', 'map', 'dap', 'fosfato monoamonico', 'fosfato diamonico',
    'sulfato', 'sulfate', 'sulfato de magnesio', 'sulfato de potasio', 'sulfato de amonio',
    'acido fosforico', 'acido sulfurico'
]


def normalize_text(text: str) -> str:
    """Remove accents and convert to lowercase for keyword matching."""
    if not text:
        return ""
    normalized = unicodedata.normalize('NFKD', text)
    ascii_text = normalized.encode('ASCII', 'ignore').decode('ASCII')
    return ascii_text.lower()


def parse_npk_formula(name: str) -> Dict[str, float]:
    """
    Parse NPK formula from fertilizer name (e.g., 'NPK 18-46-0' -> {'N': 18, 'P': 46, 'K': 0}).
    Returns empty dict if no NPK pattern found.
    """
    npk_pattern = r'(\d+)[/-](\d+)[/-](\d+)'
    match = re.search(npk_pattern, name)
    if match:
        return {
            'N': float(match.group(1)),
            'P': float(match.group(2)),
            'K': float(match.group(3))
        }
    return {}


def has_significant_phosphate(fert: Dict[str, Any]) -> bool:
    """
    Check if fertilizer has significant phosphate content (>5% P2O5).
    Checks nutrient_contributions, formula, and NPK pattern in name.
    """
    contributions = fert.get('nutrient_contributions', {})
    p2o5 = contributions.get('P2O5', contributions.get('p2o5', 0)) or 0
    if p2o5 > 5:
        return True
    
    npk = parse_npk_formula(fert.get('fertilizer_name', fert.get('name', '')))
    if npk.get('P', 0) > 5:
        return True
    
    return False


def has_significant_sulfate(fert: Dict[str, Any]) -> bool:
    """Check if fertilizer has significant sulfate content (>5% S)."""
    contributions = fert.get('nutrient_contributions', {})
    s = contributions.get('S', contributions.get('s', 0)) or 0
    return s > 5


def classify_fertilizer_tank(fertilizer_name: str, formula: str = "", fert_data: Optional[Dict[str, Any]] = None) -> str:
    """
    Classify a fertilizer into Tank A, Tank B, or Neutral based on chemical compatibility.
    
    Tank A: Calcium-containing fertilizers and micronutrients
    Tank B: Phosphates, sulfates, magnesium, and acids
    Neutral: Can go in either tank (will be assigned to balance volumes)
    
    Args:
        fertilizer_name: Name of the fertilizer
        formula: Chemical formula (optional)
        fert_data: Full fertilizer dictionary for nutrient analysis (optional)
    
    Returns:
        'A', 'B', or 'N' (neutral)
    """
    fert_data = fert_data or {}
    
    if fert_data.get('is_acid', False):
        return 'B'
    
    # Micronutrients (marked explicitly) go to Tank A
    if fert_data.get('is_micronutrient', False):
        return 'A'
    
    dose_unit = str(fert_data.get('dose_unit', '')).lower()
    if 'l' in dose_unit or 'liter' in dose_unit or 'litro' in dose_unit:
        if 'acido' in normalize_text(fertilizer_name) or 'acid' in normalize_text(fertilizer_name):
            return 'B'
    
    name_normalized = normalize_text(fertilizer_name)
    formula_normalized = normalize_text(formula)
    
    has_calcium = any(kw in name_normalized for kw in ['calcio', 'calcium', 'ca(']) or 'ca' in formula_normalized.split('(')[0]
    
    if has_calcium:
        return 'A'
    
    is_incompatible = any(kw in name_normalized for kw in INCOMPATIBLE_WITH_CALCIUM)
    if is_incompatible:
        return 'B'
    
    if has_significant_phosphate(fert_data):
        return 'B'
    
    if has_significant_sulfate(fert_data):
        return 'B'
    
    for kw in TANK_A_KEYWORDS:
        if kw in name_normalized or kw in formula_normalized:
            return 'A'
    
    for kw in TANK_B_KEYWORDS:
        if kw in name_normalized or kw in formula_normalized:
            return 'B'
    
    return 'N'


def consolidate_fertilizers(fertilizers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Consolidate duplicate fertilizers by summing their doses.
    Groups by fertilizer_name/name and sums dose_kg_ha, dose_liters_ha, cost.
    """
    consolidated = {}
    
    for fert in fertilizers:
        name = fert.get('fertilizer_name') or fert.get('name', '')
        if not name:
            continue
            
        if name not in consolidated:
            consolidated[name] = fert.copy()
            consolidated[name]['dose_kg_ha'] = 0
            consolidated[name]['dose_liters_ha'] = 0
            consolidated[name]['cost_total'] = 0
        
        consolidated[name]['dose_kg_ha'] += fert.get('dose_kg_ha', 0) or 0
        consolidated[name]['dose_liters_ha'] += fert.get('dose_liters_ha', 0) or 0
        consolidated[name]['cost_total'] += fert.get('cost_total', fert.get('cost_ha', 0)) or 0
        
        for field in ['formula', 'is_acid', 'dose_unit', 'nutrient_contributions']:
            if field in fert and fert[field] and not consolidated[name].get(field):
                consolidated[name][field] = fert[field]
    
    return list(consolidated.values())


def separate_fertilizers_ab(
    fertilizers: List[Dict[str, Any]],
    acid_treatment: Optional[Dict[str, Any]] = None,
    consolidate: bool = True
) -> Dict[str, Any]:
    """
    Separate fertilizers into Tank A and Tank B lists.
    
    Args:
        fertilizers: List of fertilizer dictionaries with name, dose, etc.
        acid_treatment: Optional acid treatment data
        consolidate: Whether to consolidate duplicates first (default True)
    
    Returns:
        Dictionary with tank_a, tank_b lists and summary
    """
    if consolidate:
        fertilizers = consolidate_fertilizers(fertilizers)
    
    tank_a = []
    tank_b = []
    neutral = []
    
    for fert in fertilizers:
        name = fert.get('fertilizer_name') or fert.get('name', '')
        formula = fert.get('formula', '')
        tank = classify_fertilizer_tank(name, formula, fert)
        
        fert_copy = fert.copy()
        fert_copy['assigned_tank'] = tank
        
        if tank == 'A':
            tank_a.append(fert_copy)
        elif tank == 'B':
            tank_b.append(fert_copy)
        else:
            neutral.append(fert_copy)
    
    def get_dose(f):
        kg_dose = (f.get('dose_kg_ha', 0) or f.get('total_dose', 0) or 
                   f.get('dose_total_kg', 0) or f.get('dose_total', 0) or 0)
        liter_dose = f.get('dose_liters_ha', 0) or 0
        return kg_dose + liter_dose
    
    total_a = sum(get_dose(f) for f in tank_a)
    total_b = sum(get_dose(f) for f in tank_b)
    
    for fert in neutral:
        if total_a <= total_b:
            fert['assigned_tank'] = 'A'
            tank_a.append(fert)
            total_a += get_dose(fert)
        else:
            fert['assigned_tank'] = 'B'
            tank_b.append(fert)
            total_b += get_dose(fert)
    
    if acid_treatment and acid_treatment.get('acid_name'):
        acid_dose = acid_treatment.get('dose_liters_ha', 0) or 0
        acid_entry = {
            'fertilizer_name': acid_treatment.get('acid_name', 'Ácido'),
            'dose_kg_ha': acid_dose,
            'dose_liters_ha': acid_dose,
            'dose_unit': 'L/ha',
            'is_acid': True,
            'assigned_tank': 'B'
        }
        tank_b.append(acid_entry)
        total_b += acid_dose
    
    return {
        'tank_a': tank_a,
        'tank_b': tank_b,
        'summary': {
            'tank_a_count': len(tank_a),
            'tank_b_count': len(tank_b),
            'tank_a_total_kg': round(total_a, 2),
            'tank_b_total_kg': round(total_b, 2)
        }
    }


def calculate_stock_concentrations(
    tank_fertilizers: List[Dict[str, Any]],
    tank_volume_liters: float,
    dilution_factor: int,
    num_applications: int,
    area_ha: float = 1.0
) -> List[Dict[str, Any]]:
    """
    Calculate stock solution concentrations for a tank.
    
    Formula: Concentration (g/L) = (Dose per application × Dilution Factor) / Tank Volume
    
    Args:
        tank_fertilizers: List of fertilizers assigned to this tank
        tank_volume_liters: Volume of the stock tank in liters
        dilution_factor: Dilution ratio (e.g., 100 for 1:100)
        num_applications: Number of fertigation applications
        area_ha: Area in hectares
    
    Returns:
        List of fertilizers with concentration data
    """
    result = []
    
    for fert in tank_fertilizers:
        dose_total = (fert.get('dose_kg_ha', 0) or 
                      fert.get('total_dose', 0) or 
                      fert.get('dose_total_kg', 0) or 
                      fert.get('dose_total', 0) or 0)
        dose_per_app = dose_total / num_applications if num_applications > 0 else 0
        
        is_acid = fert.get('is_acid', False)
        if is_acid:
            concentration = (dose_per_app * dilution_factor) / tank_volume_liters if tank_volume_liters > 0 else 0
            total_needed = dose_total * area_ha
            result.append({
                'name': fert.get('fertilizer_name', fert.get('name', '')),
                'dose_total': round(dose_total, 2),
                'dose_per_app': round(dose_per_app, 3),
                'concentration_per_liter': round(concentration, 3),
                'concentration_unit': 'L/L',
                'total_for_tank': round(total_needed, 2),
                'total_unit': 'L',
                'is_acid': True
            })
        else:
            dose_per_app_g = dose_per_app * 1000
            concentration_g_l = (dose_per_app_g * dilution_factor) / tank_volume_liters if tank_volume_liters > 0 else 0
            total_needed_kg = dose_total * area_ha
            
            result.append({
                'name': fert.get('fertilizer_name', fert.get('name', '')),
                'dose_total_kg_ha': round(dose_total, 2),
                'dose_per_app_kg': round(dose_per_app, 3),
                'concentration_g_l': round(concentration_g_l, 1),
                'concentration_unit': 'g/L',
                'total_for_tank_kg': round(total_needed_kg, 2),
                'is_acid': False
            })
    
    return result


def calculate_injection_program(
    tank_a_concentration: List[Dict[str, Any]],
    tank_b_concentration: List[Dict[str, Any]],
    irrigation_flow_lph: float,
    dilution_factor: int
) -> Dict[str, Any]:
    """
    Calculate injection rates for each tank.
    
    Injection Rate (L/h) = Irrigation Flow / Dilution Factor
    
    Args:
        tank_a_concentration: Tank A fertilizers with concentrations
        tank_b_concentration: Tank B fertilizers with concentrations
        irrigation_flow_lph: Irrigation flow rate in liters per hour
        dilution_factor: Dilution ratio
    
    Returns:
        Injection program with rates per tank
    """
    injection_rate = irrigation_flow_lph / dilution_factor if dilution_factor > 0 else 0
    injection_rate_ml_min = (injection_rate * 1000) / 60
    
    return {
        'dilution_factor': dilution_factor,
        'irrigation_flow_lph': round(irrigation_flow_lph, 1),
        'injection_rate_lph': round(injection_rate, 2),
        'injection_rate_ml_min': round(injection_rate_ml_min, 1),
        'tank_a': {
            'injection_rate_lph': round(injection_rate, 2),
            'injection_rate_ml_min': round(injection_rate_ml_min, 1),
            'fertilizer_count': len(tank_a_concentration)
        },
        'tank_b': {
            'injection_rate_lph': round(injection_rate, 2),
            'injection_rate_ml_min': round(injection_rate_ml_min, 1),
            'fertilizer_count': len(tank_b_concentration)
        }
    }


def calculate_ab_tanks_complete(
    fertilizers: List[Dict[str, Any]],
    acid_treatment: Optional[Dict[str, Any]],
    tank_a_volume: float,
    tank_b_volume: float,
    dilution_factor: int,
    num_applications: int,
    irrigation_flow_lph: float,
    area_ha: float = 1.0
) -> Dict[str, Any]:
    """
    Complete A/B tank calculation including separation, concentrations, and injection program.
    
    Args:
        fertilizers: List of fertilizers from optimization result
        acid_treatment: Acid treatment data (optional)
        tank_a_volume: Volume of Tank A in liters
        tank_b_volume: Volume of Tank B in liters
        dilution_factor: Dilution ratio (e.g., 100 for 1:100)
        num_applications: Number of fertigation applications
        irrigation_flow_lph: Irrigation flow rate in L/h
        area_ha: Area in hectares
    
    Returns:
        Complete A/B tank calculation result
    """
    separation = separate_fertilizers_ab(fertilizers, acid_treatment)
    
    tank_a_concentrations = calculate_stock_concentrations(
        separation['tank_a'],
        tank_a_volume,
        dilution_factor,
        num_applications,
        area_ha
    )
    
    tank_b_concentrations = calculate_stock_concentrations(
        separation['tank_b'],
        tank_b_volume,
        dilution_factor,
        num_applications,
        area_ha
    )
    
    injection_program = calculate_injection_program(
        tank_a_concentrations,
        tank_b_concentrations,
        irrigation_flow_lph,
        dilution_factor
    )
    
    tank_a_total_g = sum(f.get('concentration_g_l', 0) for f in tank_a_concentrations if not f.get('is_acid'))
    tank_b_total_g = sum(f.get('concentration_g_l', 0) for f in tank_b_concentrations if not f.get('is_acid'))
    
    max_recommended_g_l = 200
    
    warnings = []
    
    if dilution_factor < 50:
        warnings.append(f"Factor de dilución 1:{dilution_factor} es muy concentrado. Puede causar obstrucción en inyectores y requiere bombas dosificadoras de alta precisión.")
    if dilution_factor < 25:
        warnings.append(f"PRECAUCIÓN: Dilución 1:{dilution_factor} genera soluciones muy densas. Verifique la solubilidad de los fertilizantes y la capacidad de su equipo.")
    
    if tank_a_total_g > max_recommended_g_l:
        warnings.append(f"Tanque A: Concentración total ({tank_a_total_g:.0f} g/L) excede el máximo recomendado ({max_recommended_g_l} g/L). Considere aumentar el volumen del tanque o usar dilución mayor.")
    if tank_b_total_g > max_recommended_g_l:
        warnings.append(f"Tanque B: Concentración total ({tank_b_total_g:.0f} g/L) excede el máximo recomendado ({max_recommended_g_l} g/L). Considere aumentar el volumen del tanque o usar dilución mayor.")
    
    return {
        'success': True,
        'configuration': {
            'tank_a_volume_l': tank_a_volume,
            'tank_b_volume_l': tank_b_volume,
            'dilution_factor': dilution_factor,
            'num_applications': num_applications,
            'irrigation_flow_lph': irrigation_flow_lph,
            'area_ha': area_ha
        },
        'tank_a': {
            'name': 'Tanque A (Calcio y Micronutrientes)',
            'description': 'Contiene fertilizantes con calcio y micronutrientes quelados',
            'volume_liters': tank_a_volume,
            'fertilizers': tank_a_concentrations,
            'total_concentration_g_l': round(tank_a_total_g, 1),
            'fertilizer_count': len(tank_a_concentrations)
        },
        'tank_b': {
            'name': 'Tanque B (Fosfatos y Sulfatos)',
            'description': 'Contiene fosfatos, sulfatos, magnesio y ácidos',
            'volume_liters': tank_b_volume,
            'fertilizers': tank_b_concentrations,
            'total_concentration_g_l': round(tank_b_total_g, 1),
            'fertilizer_count': len(tank_b_concentrations)
        },
        'injection_program': injection_program,
        'warnings': warnings,
        'summary': separation['summary']
    }

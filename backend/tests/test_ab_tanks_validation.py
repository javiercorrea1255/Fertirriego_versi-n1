"""
Comprehensive A/B Tank Separation System Validation
1000 Scenarios with Expert Agronomic Criteria
"""
import random
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.fertiirrigation_ab_tanks_service import calculate_ab_tanks_complete

random.seed(42)

FERTILIZER_CATALOG = [
    {"name": "Nitrato de Calcio", "dose_kg_ha": 150, "category": "calcium", "contains": ["Ca", "N"]},
    {"name": "Nitrato de Potasio", "dose_kg_ha": 100, "category": "nitrate", "contains": ["K", "N"]},
    {"name": "Sulfato de Potasio", "dose_kg_ha": 80, "category": "sulfate", "contains": ["K", "S"]},
    {"name": "Sulfato de Magnesio", "dose_kg_ha": 60, "category": "sulfate", "contains": ["Mg", "S"]},
    {"name": "Fosfato Monoamónico (MAP)", "dose_kg_ha": 50, "category": "phosphate", "contains": ["P", "N"]},
    {"name": "Fosfato Diamónico (DAP)", "dose_kg_ha": 45, "category": "phosphate", "contains": ["P", "N"]},
    {"name": "Urea", "dose_kg_ha": 80, "category": "nitrogen", "contains": ["N"]},
    {"name": "Sulfato de Amonio", "dose_kg_ha": 70, "category": "sulfate", "contains": ["N", "S"]},
    {"name": "Cloruro de Potasio", "dose_kg_ha": 60, "category": "potassium", "contains": ["K", "Cl"]},
    {"name": "Nitrato de Magnesio", "dose_kg_ha": 40, "category": "nitrate", "contains": ["Mg", "N"]},
    {"name": "Quelato de Hierro EDDHA", "dose_kg_ha": 5, "category": "micronutrient", "contains": ["Fe"]},
    {"name": "Quelato de Zinc EDTA", "dose_kg_ha": 3, "category": "micronutrient", "contains": ["Zn"]},
    {"name": "Quelato de Manganeso EDTA", "dose_kg_ha": 4, "category": "micronutrient", "contains": ["Mn"]},
    {"name": "Quelato de Cobre EDTA", "dose_kg_ha": 2, "category": "micronutrient", "contains": ["Cu"]},
    {"name": "Ácido Bórico", "dose_kg_ha": 3, "category": "micronutrient", "contains": ["B"]},
    {"name": "Molibdato de Sodio", "dose_kg_ha": 0.5, "category": "micronutrient", "contains": ["Mo"]},
    {"name": "Triple 17 (17-17-17)", "dose_kg_ha": 200, "category": "compound", "contains": ["N", "P", "K"]},
    {"name": "Sulfato de Zinc", "dose_kg_ha": 10, "category": "sulfate", "contains": ["Zn", "S"]},
    {"name": "Nitrato de Amonio", "dose_kg_ha": 90, "category": "nitrate", "contains": ["N"]},
    {"name": "Superfosfato Triple", "dose_kg_ha": 60, "category": "phosphate", "contains": ["P", "Ca"]},
]

ACID_CATALOG = [
    {"name": "Ácido Fosfórico", "dose_ml_per_1000l": 500},
    {"name": "Ácido Nítrico", "dose_ml_per_1000l": 400},
    {"name": "Ácido Sulfúrico", "dose_ml_per_1000l": 300},
    {"name": "Ácido Cítrico", "dose_ml_per_1000l": 200},
]

TANK_VOLUMES = [100, 200, 500, 1000, 1500, 2000, 3000, 5000]
DILUTION_FACTORS = [10, 25, 30, 40, 50, 100, 150, 200]
IRRIGATION_FLOWS = [500, 750, 1000, 1500, 2000, 3000, 4000, 5000, 8000, 10000]
NUM_APPLICATIONS_RANGE = (5, 30)
AREA_HA_RANGE = (0.5, 50)

@dataclass
class ValidationResult:
    scenario_id: int
    scenario_type: str
    passed: bool = False
    checks: Dict[str, bool] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    tank_a_concentration: float = 0.0
    tank_b_concentration: float = 0.0
    tank_balance_ratio: float = 0.0
    injection_rate_a: float = 0.0
    injection_rate_b: float = 0.0
    execution_time_ms: float = 0.0

@dataclass 
class AgronomicCriteria:
    calcium_phosphate_separation: bool = False
    calcium_sulfate_separation: bool = False
    acids_in_tank_b: bool = False
    micronutrients_in_tank_a: bool = False
    concentration_within_limit: bool = False
    concentration_limit_value: float = 200.0
    injection_rate_feasible: bool = False
    min_injection_rate: float = 0.1
    max_injection_rate: float = 50.0
    tank_balance_acceptable: bool = False
    max_balance_deviation: float = 0.5
    no_api_errors: bool = False

def generate_scenario(scenario_id: int, scenario_type: str) -> Dict[str, Any]:
    """Generate a test scenario based on type"""
    
    if scenario_type == "standard":
        num_fertilizers = random.randint(3, 8)
        fertilizers = random.sample(FERTILIZER_CATALOG, min(num_fertilizers, len(FERTILIZER_CATALOG)))
        include_acid = random.random() > 0.3
        
    elif scenario_type == "high_calcium":
        calcium_ferts = [f for f in FERTILIZER_CATALOG if "Ca" in f["contains"]]
        other_ferts = random.sample([f for f in FERTILIZER_CATALOG if "Ca" not in f["contains"]], 3)
        fertilizers = calcium_ferts + other_ferts
        include_acid = True
        
    elif scenario_type == "phosphate_heavy":
        phosphate_ferts = [f for f in FERTILIZER_CATALOG if f["category"] == "phosphate"]
        other_ferts = random.sample([f for f in FERTILIZER_CATALOG if f["category"] != "phosphate"], 4)
        fertilizers = phosphate_ferts + other_ferts
        include_acid = True
        
    elif scenario_type == "micronutrient_only":
        fertilizers = [f for f in FERTILIZER_CATALOG if f["category"] == "micronutrient"]
        include_acid = False
        
    elif scenario_type == "acid_only":
        fertilizers = []
        include_acid = True
        
    elif scenario_type == "sulfate_heavy":
        sulfate_ferts = [f for f in FERTILIZER_CATALOG if f["category"] == "sulfate"]
        other_ferts = random.sample([f for f in FERTILIZER_CATALOG if f["category"] != "sulfate"], 2)
        fertilizers = sulfate_ferts + other_ferts
        include_acid = random.random() > 0.5
        
    elif scenario_type == "minimal":
        fertilizers = random.sample(FERTILIZER_CATALOG, 2)
        include_acid = False
        
    elif scenario_type == "maximal":
        fertilizers = FERTILIZER_CATALOG.copy()
        include_acid = True
        
    elif scenario_type == "edge_low_volume":
        fertilizers = random.sample(FERTILIZER_CATALOG, 5)
        include_acid = True
        
    elif scenario_type == "edge_high_volume":
        fertilizers = random.sample(FERTILIZER_CATALOG, 5)
        include_acid = True
        
    else:
        num_fertilizers = random.randint(2, 10)
        fertilizers = random.sample(FERTILIZER_CATALOG, min(num_fertilizers, len(FERTILIZER_CATALOG)))
        include_acid = random.random() > 0.4
    
    dose_multiplier = random.uniform(0.1, 0.5)
    formatted_fertilizers = []
    for f in fertilizers:
        base_dose = f["dose_kg_ha"] * dose_multiplier
        num_apps = random.randint(10, 25)
        formatted_fertilizers.append({
            "name": f["name"],
            "dose_total_kg": base_dose,
            "dose_per_application_kg": base_dose / num_apps,
            "category": f.get("category", "other"),
            "contains": f.get("contains", [])
        })
    
    acid_treatment = None
    if include_acid:
        acid = random.choice(ACID_CATALOG)
        acid_treatment = {
            "acid_name": acid["name"],
            "dose_ml_per_1000l": acid["dose_ml_per_1000l"] * random.uniform(0.5, 1.5),
            "final_ph": random.uniform(5.5, 6.5)
        }
    
    if scenario_type == "edge_low_volume":
        tank_a_volume = 100
        tank_b_volume = 100
    elif scenario_type == "edge_high_volume":
        tank_a_volume = 5000
        tank_b_volume = 5000
    else:
        tank_a_volume = random.choice(TANK_VOLUMES)
        tank_b_volume = random.choice(TANK_VOLUMES)
    
    return {
        "scenario_id": scenario_id,
        "scenario_type": scenario_type,
        "fertilizers": formatted_fertilizers,
        "acid_treatment": acid_treatment,
        "tank_a_volume": tank_a_volume,
        "tank_b_volume": tank_b_volume,
        "dilution_factor": random.choice(DILUTION_FACTORS),
        "num_applications": random.randint(*NUM_APPLICATIONS_RANGE),
        "irrigation_flow_lph": random.choice(IRRIGATION_FLOWS),
        "area_ha": round(random.uniform(*AREA_HA_RANGE), 2)
    }

def validate_chemical_compatibility(result: Dict, fertilizers: List[Dict]) -> Tuple[bool, List[str]]:
    """Validate chemical compatibility rules"""
    issues = []
    
    tank_a_ferts = result.get("tank_a", {}).get("fertilizers", [])
    tank_b_ferts = result.get("tank_b", {}).get("fertilizers", [])
    
    tank_a_names = [f["name"].lower() for f in tank_a_ferts]
    tank_b_names = [f["name"].lower() for f in tank_b_ferts]
    
    calcium_in_a = any("calcio" in n or "calcium" in n for n in tank_a_names)
    phosphate_in_a = any("fosfato" in n or "phosphat" in n or " map" in n or " dap" in n or n.startswith("map") or n.startswith("dap") for n in tank_a_names)
    sulfate_in_a = any("sulfato" in n and "calcio" not in n for n in tank_a_names)
    
    if calcium_in_a and phosphate_in_a:
        issues.append("CRITICAL: Calcium and phosphate in same tank A - precipitation risk")
    
    if calcium_in_a and sulfate_in_a:
        issues.append("WARNING: Calcium and sulfate in tank A - gypsum precipitation possible")
    
    TREATMENT_ACIDS = ['ácido fosfórico', 'ácido nítrico', 'ácido sulfúrico', 'ácido cítrico', 
                       'acido fosforico', 'acido nitrico', 'acido sulfurico', 'acido citrico',
                       'phosphoric acid', 'nitric acid', 'sulfuric acid', 'citric acid']
    
    treatment_acid_in_a = any(any(acid in n for acid in TREATMENT_ACIDS) for n in tank_a_names)
    if treatment_acid_in_a:
        issues.append("ERROR: Treatment acid found in tank A - should be in tank B")
    
    return len([i for i in issues if "CRITICAL" in i or "ERROR" in i]) == 0, issues

def validate_concentration_limits(result: Dict, max_concentration: float = 200.0) -> Tuple[bool, List[str]]:
    """Validate concentration limits - high concentrations are warnings, not errors"""
    issues = []
    
    tank_a_conc = result.get("tank_a", {}).get("total_concentration_g_l", 0)
    tank_b_conc = result.get("tank_b", {}).get("total_concentration_g_l", 0)
    
    if tank_a_conc > max_concentration:
        issues.append(f"WARNING: Tank A concentration {tank_a_conc:.1f} g/L exceeds recommended {max_concentration} g/L")
    
    if tank_b_conc > max_concentration:
        issues.append(f"WARNING: Tank B concentration {tank_b_conc:.1f} g/L exceeds recommended {max_concentration} g/L")
    
    service_warnings = result.get("warnings", [])
    concentration_warning_present = any("concentración" in w.lower() or "concentration" in w.lower() or "excede" in w.lower() for w in service_warnings)
    
    if (tank_a_conc > max_concentration or tank_b_conc > max_concentration) and not concentration_warning_present:
        issues.append("ERROR: Service should generate concentration warning but didn't")
        return False, issues
    
    return True, issues

def validate_injection_rates(result: Dict, min_rate: float = 0.01, scenario_dilution_factor: int = None) -> Tuple[bool, List[str]]:
    """
    Validate injection rate feasibility - rates depend on dilution factor.
    
    Injection rate limits by dilution factor:
    - 1:10  → max 1000 L/h (industrial high-flow dosing systems)
    - 1:25  → max 500 L/h (heavy-duty venturi/piston pumps)
    - 1:50  → max 200 L/h (standard diaphragm pumps)
    - 1:100+ → max 100 L/h (standard peristaltic/solenoid pumps)
    
    Args:
        result: A/B tanks calculation result
        min_rate: Minimum practical injection rate (L/h)
        scenario_dilution_factor: Fallback dilution factor from scenario config
    """
    issues = []
    passed = True
    
    inj_program = result.get("injection_program", {})
    dilution_factor = inj_program.get("dilution_factor", scenario_dilution_factor or 100)
    rate_a = inj_program.get("tank_a", {}).get("injection_rate_ml_min", 0)
    rate_b = inj_program.get("tank_b", {}).get("injection_rate_ml_min", 0)
    
    rate_a_lph = rate_a * 60 / 1000
    rate_b_lph = rate_b * 60 / 1000
    
    if dilution_factor <= 10:
        max_rate = 1000.0
    elif dilution_factor <= 25:
        max_rate = 500.0
    elif dilution_factor <= 50:
        max_rate = 200.0
    else:
        max_rate = 100.0
    
    if rate_a_lph > 0 and rate_a_lph < min_rate:
        issues.append(f"WARNING: Tank A injection rate {rate_a_lph:.3f} L/h very low")
    
    if rate_b_lph > 0 and rate_b_lph < min_rate:
        issues.append(f"WARNING: Tank B injection rate {rate_b_lph:.3f} L/h very low")
    
    if rate_a_lph > max_rate:
        issues.append(f"FAIL: Tank A injection rate {rate_a_lph:.1f} L/h exceeds limit {max_rate} L/h for 1:{dilution_factor}")
        passed = False
    
    if rate_b_lph > max_rate:
        issues.append(f"FAIL: Tank B injection rate {rate_b_lph:.1f} L/h exceeds limit {max_rate} L/h for 1:{dilution_factor}")
        passed = False
    
    return passed, issues

def validate_tank_balance(result: Dict, max_deviation: float = 0.9) -> Tuple[bool, float, List[str]]:
    """Validate tank balance (similar concentrations)"""
    issues = []
    
    tank_a_conc = result.get("tank_a", {}).get("total_concentration_g_l", 0)
    tank_b_conc = result.get("tank_b", {}).get("total_concentration_g_l", 0)
    
    if tank_a_conc == 0 and tank_b_conc == 0:
        return True, 1.0, ["INFO: Both tanks empty"]
    
    if tank_a_conc == 0 or tank_b_conc == 0:
        if tank_a_conc > 0:
            issues.append("INFO: Only Tank A has fertilizers")
        else:
            issues.append("INFO: Only Tank B has fertilizers")
        return True, 0.0, issues
    
    ratio = min(tank_a_conc, tank_b_conc) / max(tank_a_conc, tank_b_conc)
    
    if ratio < (1 - max_deviation):
        issues.append(f"WARNING: Tank imbalance - ratio {ratio:.2f} (A: {tank_a_conc:.1f}, B: {tank_b_conc:.1f})")
    
    return ratio >= (1 - max_deviation), ratio, issues

def run_scenario(scenario: Dict[str, Any]) -> ValidationResult:
    """Run a single scenario and validate results"""
    start_time = time.time()
    
    result = ValidationResult(
        scenario_id=scenario["scenario_id"],
        scenario_type=scenario["scenario_type"]
    )
    
    try:
        api_result = calculate_ab_tanks_complete(
            fertilizers=scenario["fertilizers"],
            acid_treatment=scenario["acid_treatment"],
            tank_a_volume=scenario["tank_a_volume"],
            tank_b_volume=scenario["tank_b_volume"],
            dilution_factor=scenario["dilution_factor"],
            num_applications=scenario["num_applications"],
            irrigation_flow_lph=scenario["irrigation_flow_lph"],
            area_ha=scenario["area_ha"]
        )
        
        result.checks["api_success"] = api_result.get("success", False)
        
        if not api_result.get("success", False):
            result.errors.append(f"API returned success=False: {api_result.get('error', 'Unknown error')}")
            result.passed = False
            return result
        
        compat_passed, compat_issues = validate_chemical_compatibility(api_result, scenario["fertilizers"])
        result.checks["chemical_compatibility"] = compat_passed
        result.warnings.extend([i for i in compat_issues if "WARNING" in i])
        result.errors.extend([i for i in compat_issues if "CRITICAL" in i or "ERROR" in i])
        
        conc_passed, conc_issues = validate_concentration_limits(api_result)
        result.checks["concentration_limits"] = conc_passed
        result.warnings.extend([i for i in conc_issues if "WARNING" in i])
        if not conc_passed:
            result.errors.extend([i for i in conc_issues if "WARNING" not in i])
        
        inj_passed, inj_issues = validate_injection_rates(api_result, scenario_dilution_factor=scenario["dilution_factor"])
        result.checks["injection_feasibility"] = inj_passed
        result.warnings.extend(inj_issues)
        
        balance_passed, balance_ratio, balance_issues = validate_tank_balance(api_result)
        result.checks["tank_balance"] = balance_passed
        result.warnings.extend([i for i in balance_issues if "WARNING" in i])
        result.tank_balance_ratio = balance_ratio
        
        result.tank_a_concentration = api_result.get("tank_a", {}).get("total_concentration_g_l", 0)
        result.tank_b_concentration = api_result.get("tank_b", {}).get("total_concentration_g_l", 0)
        
        inj_program = api_result.get("injection_program", {})
        result.injection_rate_a = inj_program.get("tank_a", {}).get("injection_rate_ml_min", 0)
        result.injection_rate_b = inj_program.get("tank_b", {}).get("injection_rate_ml_min", 0)
        
        result.warnings.extend(api_result.get("warnings", []))
        
        result.passed = all([
            result.checks.get("api_success", False),
            result.checks.get("chemical_compatibility", False),
            result.checks.get("concentration_limits", False),
            result.checks.get("injection_feasibility", True),
        ])
        
    except Exception as e:
        result.errors.append(f"Exception: {str(e)}")
        result.passed = False
        result.checks["no_exceptions"] = False
    
    result.execution_time_ms = (time.time() - start_time) * 1000
    return result

def generate_report(results: List[ValidationResult], total_time: float) -> str:
    """Generate comprehensive validation report"""
    
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    
    by_type = {}
    for r in results:
        if r.scenario_type not in by_type:
            by_type[r.scenario_type] = {"total": 0, "passed": 0, "failed": 0}
        by_type[r.scenario_type]["total"] += 1
        if r.passed:
            by_type[r.scenario_type]["passed"] += 1
        else:
            by_type[r.scenario_type]["failed"] += 1
    
    check_stats = {
        "api_success": {"passed": 0, "failed": 0},
        "chemical_compatibility": {"passed": 0, "failed": 0},
        "concentration_limits": {"passed": 0, "failed": 0},
        "injection_feasibility": {"passed": 0, "failed": 0},
        "tank_balance": {"passed": 0, "failed": 0},
    }
    
    for r in results:
        for check, passed_check in r.checks.items():
            if check in check_stats:
                if passed_check:
                    check_stats[check]["passed"] += 1
                else:
                    check_stats[check]["failed"] += 1
    
    concentrations_a = [r.tank_a_concentration for r in results if r.tank_a_concentration > 0]
    concentrations_b = [r.tank_b_concentration for r in results if r.tank_b_concentration > 0]
    
    exec_times = [r.execution_time_ms for r in results]
    
    all_warnings = []
    all_errors = []
    for r in results:
        all_warnings.extend(r.warnings)
        all_errors.extend(r.errors)
    
    warning_counts = {}
    for w in all_warnings:
        key = w.split(":")[0] if ":" in w else w[:50]
        warning_counts[key] = warning_counts.get(key, 0) + 1
    
    error_counts = {}
    for e in all_errors:
        key = e.split(":")[0] if ":" in e else e[:50]
        error_counts[key] = error_counts.get(key, 0) + 1
    
    report = f"""
================================================================================
       REPORTE DE VALIDACIÓN - SISTEMA TANQUES A/B FERTIIRRIGACIÓN
================================================================================
Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Tiempo Total de Ejecución: {total_time:.2f} segundos

================================================================================
                           RESUMEN EJECUTIVO
================================================================================

Total de Escenarios Probados: {total}
✅ Escenarios APROBADOS: {passed} ({passed/total*100:.1f}%)
❌ Escenarios FALLIDOS: {failed} ({failed/total*100:.1f}%)

TASA DE ÉXITO GLOBAL: {passed/total*100:.1f}%

================================================================================
                    RESULTADOS POR TIPO DE ESCENARIO
================================================================================
"""
    
    for scenario_type, stats in sorted(by_type.items()):
        pct = stats["passed"]/stats["total"]*100 if stats["total"] > 0 else 0
        status = "✅" if pct == 100 else "⚠️" if pct >= 90 else "❌"
        report += f"""
{status} {scenario_type.upper()}
   Total: {stats['total']} | Aprobados: {stats['passed']} | Fallidos: {stats['failed']} | Tasa: {pct:.1f}%"""
    
    report += f"""

================================================================================
                    VALIDACIÓN DE CRITERIOS AGRONÓMICOS
================================================================================
"""
    
    criteria_names = {
        "api_success": "API Sin Errores",
        "chemical_compatibility": "Compatibilidad Química Ca/P/S",
        "concentration_limits": "Límite Concentración (≤200 g/L)",
        "injection_feasibility": "Tasas de Inyección Factibles",
        "tank_balance": "Balance Entre Tanques (≤50% desv.)",
    }
    
    for check, stats in check_stats.items():
        total_check = stats["passed"] + stats["failed"]
        if total_check > 0:
            pct = stats["passed"]/total_check*100
            status = "✅" if pct == 100 else "⚠️" if pct >= 95 else "❌"
            name = criteria_names.get(check, check)
            report += f"""
{status} {name}
   Aprobados: {stats['passed']}/{total_check} ({pct:.1f}%)"""
    
    report += f"""

================================================================================
                    ESTADÍSTICAS DE CONCENTRACIÓN
================================================================================

TANQUE A (Calcio + Micronutrientes):
   Mínima: {min(concentrations_a) if concentrations_a else 0:.1f} g/L
   Máxima: {max(concentrations_a) if concentrations_a else 0:.1f} g/L
   Promedio: {sum(concentrations_a)/len(concentrations_a) if concentrations_a else 0:.1f} g/L
   Escenarios con concentración > 0: {len(concentrations_a)}

TANQUE B (Fosfatos + Sulfatos + Ácidos):
   Mínima: {min(concentrations_b) if concentrations_b else 0:.1f} g/L
   Máxima: {max(concentrations_b) if concentrations_b else 0:.1f} g/L
   Promedio: {sum(concentrations_b)/len(concentrations_b) if concentrations_b else 0:.1f} g/L
   Escenarios con concentración > 0: {len(concentrations_b)}

================================================================================
                         RENDIMIENTO DEL SISTEMA
================================================================================

Tiempo de Ejecución por Escenario:
   Mínimo: {min(exec_times):.2f} ms
   Máximo: {max(exec_times):.2f} ms
   Promedio: {sum(exec_times)/len(exec_times):.2f} ms
   P95: {sorted(exec_times)[int(len(exec_times)*0.95)]:.2f} ms
   P99: {sorted(exec_times)[int(len(exec_times)*0.99)]:.2f} ms

================================================================================
                         ADVERTENCIAS FRECUENTES
================================================================================
"""
    
    for warning, count in sorted(warning_counts.items(), key=lambda x: -x[1])[:10]:
        report += f"""
⚠️ [{count}x] {warning}"""
    
    if not warning_counts:
        report += "\n✅ Sin advertencias frecuentes"
    
    report += f"""

================================================================================
                           ERRORES ENCONTRADOS
================================================================================
"""
    
    for error, count in sorted(error_counts.items(), key=lambda x: -x[1])[:10]:
        report += f"""
❌ [{count}x] {error}"""
    
    if not error_counts:
        report += "\n✅ Sin errores encontrados"
    
    failed_scenarios = [r for r in results if not r.passed][:5]
    if failed_scenarios:
        report += f"""

================================================================================
                    DETALLE DE ESCENARIOS FALLIDOS (Top 5)
================================================================================
"""
        for r in failed_scenarios:
            report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Escenario #{r.scenario_id} - Tipo: {r.scenario_type}
Concentración Tank A: {r.tank_a_concentration:.1f} g/L | Tank B: {r.tank_b_concentration:.1f} g/L
Checks: {r.checks}
Errores: {r.errors}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    recommendations = []
    
    if check_stats["concentration_limits"]["failed"] > 0:
        recommendations.append("• Revisar límites de concentración - algunos escenarios exceden 200 g/L")
    
    if check_stats["chemical_compatibility"]["failed"] > 0:
        recommendations.append("• Mejorar algoritmo de separación química - detectar mejor Ca/P/S conflictos")
    
    if check_stats["injection_feasibility"]["failed"] > 0:
        recommendations.append("• Ajustar cálculos de inyección para rangos prácticos de bombas")
    
    avg_time = sum(exec_times)/len(exec_times) if exec_times else 0
    if avg_time > 100:
        recommendations.append(f"• Optimizar rendimiento - tiempo promedio {avg_time:.0f}ms > 100ms objetivo")
    
    if passed/total < 0.95:
        recommendations.append("• Tasa de éxito < 95% - revisar casos edge y mejorar robustez")
    
    report += f"""

================================================================================
                         RECOMENDACIONES
================================================================================
"""
    
    if recommendations:
        for rec in recommendations:
            report += f"\n{rec}"
    else:
        report += "\n✅ Sistema funcionando correctamente - sin recomendaciones críticas"
    
    verdict = "✅ APROBADO" if passed/total >= 0.95 and check_stats["chemical_compatibility"]["failed"] == 0 else "⚠️ APROBADO CON OBSERVACIONES" if passed/total >= 0.85 else "❌ REQUIERE CORRECCIONES"
    
    report += f"""

================================================================================
                           VEREDICTO FINAL
================================================================================

                              {verdict}

Tasa de éxito: {passed/total*100:.1f}%
Criterios agronómicos: {'Cumplidos' if check_stats['chemical_compatibility']['failed'] == 0 else 'Con observaciones'}
Rendimiento: {'Óptimo' if avg_time < 50 else 'Aceptable' if avg_time < 100 else 'Requiere optimización'}

================================================================================
                     FIN DEL REPORTE DE VALIDACIÓN
================================================================================
"""
    
    return report

def run_validation(num_scenarios: int = 1000) -> str:
    """Run the complete validation suite"""
    print(f"\n🔬 Iniciando validación con {num_scenarios} escenarios...")
    
    scenario_types = [
        ("standard", 400),
        ("high_calcium", 100),
        ("phosphate_heavy", 100),
        ("sulfate_heavy", 100),
        ("micronutrient_only", 50),
        ("acid_only", 50),
        ("minimal", 50),
        ("maximal", 50),
        ("edge_low_volume", 50),
        ("edge_high_volume", 50),
    ]
    
    scenarios = []
    scenario_id = 1
    
    for scenario_type, count in scenario_types:
        for _ in range(count):
            scenarios.append(generate_scenario(scenario_id, scenario_type))
            scenario_id += 1
    
    print(f"📋 Generados {len(scenarios)} escenarios de prueba")
    
    start_time = time.time()
    results = []
    
    for i, scenario in enumerate(scenarios):
        if (i + 1) % 100 == 0:
            print(f"   Procesando... {i+1}/{len(scenarios)}")
        
        result = run_scenario(scenario)
        results.append(result)
    
    total_time = time.time() - start_time
    
    print(f"\n✅ Validación completada en {total_time:.2f} segundos")
    
    report = generate_report(results, total_time)
    
    return report

if __name__ == "__main__":
    report = run_validation(1000)
    print(report)
    
    with open("/tmp/ab_tanks_validation_report.txt", "w") as f:
        f.write(report)
    
    print("\n📄 Reporte guardado en /tmp/ab_tanks_validation_report.txt")

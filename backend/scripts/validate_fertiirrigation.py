#!/usr/bin/env python3
"""
FertiIrrigation Calculator Validation Script
Runs 100 randomized scenarios to validate calculation accuracy.
"""
import sys
import os
import random
import json
from dataclasses import asdict
from typing import List, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.fertiirrigation_calculator import (
    fertiirrigation_calculator,
    SoilData,
    WaterData,
    CropData,
    IrrigationData,
)

SOIL_ANALYSES = [
    {"name": "Tomate Invernadero", "texture": "franco", "ph": 6.8, "ec": 1.2, "om": 3.5, "n_no3": 25, "n_nh4": 8, "p": 28, "k": 180, "ca": 2200, "mg": 320, "s": 15, "cic": 22, "depth": 30, "bd": 1.3},
    {"name": "Pimiento Morrón", "texture": "franco-arcilloso", "ph": 7.2, "ec": 0.8, "om": 2.8, "n_no3": 18, "n_nh4": 5, "p": 22, "k": 210, "ca": 2800, "mg": 380, "s": 12, "cic": 28, "depth": 30, "bd": 1.25},
    {"name": "Pepino Invernadero", "texture": "franco-arenoso", "ph": 6.5, "ec": 0.6, "om": 2.2, "n_no3": 32, "n_nh4": 12, "p": 35, "k": 145, "ca": 1600, "mg": 240, "s": 18, "cic": 15, "depth": 30, "bd": 1.4},
    {"name": "Aguacate Sector 2", "texture": "arcilloso", "ph": 5.8, "ec": 0.5, "om": 4.5, "n_no3": 15, "n_nh4": 6, "p": 12, "k": 165, "ca": 1200, "mg": 180, "s": 8, "cic": 35, "depth": 40, "bd": 1.2},
    {"name": "Maíz Temporal", "texture": "franco", "ph": 7.0, "ec": 0.7, "om": 2.5, "n_no3": 12, "n_nh4": 4, "p": 18, "k": 155, "ca": 2400, "mg": 290, "s": 10, "cic": 20, "depth": 30, "bd": 1.35},
    {"name": "Fresa Hidropónica", "texture": "franco-arenoso", "ph": 6.2, "ec": 0.9, "om": 1.8, "n_no3": 28, "n_nh4": 10, "p": 42, "k": 195, "ca": 1800, "mg": 260, "s": 22, "cic": 12, "depth": 25, "bd": 1.45},
    {"name": "Cebolla Bajío", "texture": "franco", "ph": 7.4, "ec": 1.0, "om": 2.0, "n_no3": 10, "n_nh4": 3, "p": 15, "k": 140, "ca": 3200, "mg": 420, "s": 14, "cic": 25, "depth": 30, "bd": 1.3},
    {"name": "Papa Altiplano", "texture": "franco-limoso", "ph": 5.5, "ec": 0.4, "om": 5.0, "n_no3": 20, "n_nh4": 8, "p": 25, "k": 120, "ca": 1000, "mg": 150, "s": 6, "cic": 18, "depth": 35, "bd": 1.25},
    {"name": "Sandía Campo Abierto", "texture": "arenoso", "ph": 6.8, "ec": 0.3, "om": 1.2, "n_no3": 8, "n_nh4": 2, "p": 10, "k": 80, "ca": 800, "mg": 100, "s": 5, "cic": 8, "depth": 30, "bd": 1.5},
    {"name": "Melón Invernadero", "texture": "franco", "ph": 6.6, "ec": 0.8, "om": 3.0, "n_no3": 22, "n_nh4": 7, "p": 30, "k": 170, "ca": 2000, "mg": 280, "s": 16, "cic": 20, "depth": 30, "bd": 1.32},
    {"name": "Suelo Ácido Pobre", "texture": "arenoso", "ph": 5.2, "ec": 0.2, "om": 0.8, "n_no3": 5, "n_nh4": 2, "p": 5, "k": 45, "ca": 300, "mg": 50, "s": 3, "cic": 5, "depth": 30, "bd": 1.55},
    {"name": "Suelo Degradado", "texture": "franco-arenoso", "ph": 6.0, "ec": 0.3, "om": 1.0, "n_no3": 6, "n_nh4": 2, "p": 8, "k": 60, "ca": 450, "mg": 70, "s": 4, "cic": 7, "depth": 25, "bd": 1.48},
    {"name": "Arena Costera", "texture": "arena", "ph": 7.8, "ec": 0.5, "om": 0.5, "n_no3": 3, "n_nh4": 1, "p": 4, "k": 35, "ca": 250, "mg": 40, "s": 2, "cic": 4, "depth": 30, "bd": 1.6},
    {"name": "Sustrato Nuevo", "texture": "franco", "ph": 6.5, "ec": 0.1, "om": 2.0, "n_no3": 8, "n_nh4": 3, "p": 12, "k": 75, "ca": 550, "mg": 85, "s": 6, "cic": 12, "depth": 30, "bd": 1.35},
    {"name": "Suelo Lavado", "texture": "franco-arenoso", "ph": 5.8, "ec": 0.15, "om": 1.5, "n_no3": 4, "n_nh4": 2, "p": 6, "k": 50, "ca": 380, "mg": 55, "s": 3, "cic": 6, "depth": 30, "bd": 1.5},
]

WATER_ANALYSES = [
    {"name": "Pozo Profundo", "ec": 0.85, "ph": 7.4, "no3": 0.2, "h2po4": 0.01, "so4": 0.8, "hco3": 4.2, "k": 0.15, "ca": 2.8, "mg": 1.2, "na": 1.5, "units": "meq"},
    {"name": "Agua Municipal", "ec": 0.65, "ph": 7.1, "no3": 0.1, "h2po4": 0.0, "so4": 0.3, "hco3": 2.8, "k": 0.08, "ca": 1.5, "mg": 0.8, "na": 0.8, "units": "meq"},
    {"name": "Pozo Agrícola", "ec": 1.1, "ph": 7.6, "no3": 0.35, "h2po4": 0.02, "so4": 1.2, "hco3": 5.5, "k": 0.22, "ca": 3.5, "mg": 1.8, "na": 2.0, "units": "meq"},
    {"name": "Agua de Lluvia", "ec": 0.08, "ph": 6.2, "no3": 0.05, "h2po4": 0.0, "so4": 0.1, "hco3": 0.2, "k": 0.02, "ca": 0.1, "mg": 0.05, "na": 0.05, "units": "meq"},
    {"name": "Río Temporal", "ec": 0.72, "ph": 7.8, "no3": 0.15, "h2po4": 0.03, "so4": 0.5, "hco3": 3.2, "k": 0.12, "ca": 2.2, "mg": 1.0, "na": 1.2, "units": "meq"},
    {"name": "Pozo Somero", "ec": 1.25, "ph": 7.2, "no3": 0.5, "h2po4": 0.05, "so4": 1.5, "hco3": 4.0, "k": 0.3, "ca": 4.0, "mg": 2.0, "na": 2.5, "units": "meq"},
    {"name": "Agua Tratada", "ec": 0.55, "ph": 7.0, "no3": 0.08, "h2po4": 0.01, "so4": 0.25, "hco3": 2.0, "k": 0.05, "ca": 1.2, "mg": 0.6, "na": 0.6, "units": "meq"},
    {"name": "Manantial", "ec": 0.35, "ph": 6.8, "no3": 0.02, "h2po4": 0.0, "so4": 0.15, "hco3": 1.5, "k": 0.03, "ca": 0.8, "mg": 0.4, "na": 0.3, "units": "meq"},
    {"name": "Pozo Salino", "ec": 2.2, "ph": 7.5, "no3": 0.4, "h2po4": 0.02, "so4": 2.5, "hco3": 5.0, "k": 0.4, "ca": 5.0, "mg": 3.0, "na": 6.0, "units": "meq"},
    {"name": "Agua Blanda", "ec": 0.25, "ph": 6.5, "no3": 0.03, "h2po4": 0.0, "so4": 0.1, "hco3": 0.8, "k": 0.02, "ca": 0.5, "mg": 0.2, "na": 0.15, "units": "meq"},
]

CROPS = [
    {"id": "tomato", "name": "Tomate", "stages": ["seedling", "vegetative", "flowering", "fruit_set", "fruit_development", "maturation"], "yield": 80, "reqs": {"N": 200, "P2O5": 80, "K2O": 300, "Ca": 160, "Mg": 40, "S": 35}},
    {"id": "pepper", "name": "Pimiento", "stages": ["seedling", "vegetative", "flowering", "fruit_set", "fruit_development", "maturation"], "yield": 50, "reqs": {"N": 180, "P2O5": 70, "K2O": 250, "Ca": 140, "Mg": 35, "S": 30}},
    {"id": "maize", "name": "Maíz", "stages": ["emergence", "rapid_growth", "pre_flowering", "flowering", "grain_fill", "maturity"], "yield": 12, "reqs": {"N": 220, "P2O5": 90, "K2O": 180, "Ca": 50, "Mg": 45, "S": 30}},
    {"id": "bean", "name": "Frijol", "stages": ["emergence", "vegetative", "flowering", "pod_fill", "maturity"], "yield": 2.5, "reqs": {"N": 80, "P2O5": 60, "K2O": 80, "Ca": 60, "Mg": 20, "S": 15}},
    {"id": "cucumber", "name": "Pepino", "stages": ["seedling", "vegetative", "flowering", "fruit_production", "final_harvest"], "yield": 100, "reqs": {"N": 180, "P2O5": 60, "K2O": 240, "Ca": 100, "Mg": 30, "S": 25}},
    {"id": "squash", "name": "Calabaza", "stages": ["seedling", "vegetative", "flowering", "fruit_development", "maturation"], "yield": 40, "reqs": {"N": 150, "P2O5": 50, "K2O": 200, "Ca": 80, "Mg": 25, "S": 20}},
    {"id": "onion", "name": "Cebolla", "stages": ["establishment", "leaf_growth", "bulb_formation", "maturation"], "yield": 50, "reqs": {"N": 140, "P2O5": 60, "K2O": 160, "Ca": 70, "Mg": 20, "S": 40}},
    {"id": "potato", "name": "Papa", "stages": ["emergence", "vegetative", "tuber_initiation", "tuber_bulking", "maturation"], "yield": 40, "reqs": {"N": 180, "P2O5": 80, "K2O": 280, "Ca": 60, "Mg": 30, "S": 25}},
    {"id": "watermelon", "name": "Sandía", "stages": ["seedling", "vine_growth", "flowering", "fruit_development", "maturation"], "yield": 60, "reqs": {"N": 160, "P2O5": 80, "K2O": 220, "Ca": 80, "Mg": 30, "S": 20}},
    {"id": "melon", "name": "Melón", "stages": ["seedling", "vegetative", "flowering", "fruit_development", "maturation"], "yield": 45, "reqs": {"N": 150, "P2O5": 70, "K2O": 200, "Ca": 90, "Mg": 25, "S": 18}},
]

IRRIGATION_SYSTEMS = ["goteo", "aspersion", "microaspersion", "gravedad"]
TEXTURES = ["arenoso", "franco-arenoso", "franco", "franco-arcilloso", "franco-limoso", "arcilloso"]

AGRONOMIC_RANGES = {
    "N": {"min": 0, "max": 350, "typical_min": 80, "typical_max": 280},
    "P2O5": {"min": 0, "max": 150, "typical_min": 30, "typical_max": 100},
    "K2O": {"min": 0, "max": 400, "typical_min": 80, "typical_max": 320},
    "Ca": {"min": 0, "max": 200, "typical_min": 20, "typical_max": 160},
    "Mg": {"min": 0, "max": 80, "typical_min": 10, "typical_max": 50},
    "S": {"min": 0, "max": 60, "typical_min": 10, "typical_max": 45},
}

def create_soil_data(soil: Dict) -> SoilData:
    return SoilData(
        texture=soil["texture"],
        bulk_density=soil["bd"],
        depth_cm=soil["depth"],
        ph=soil["ph"],
        ec_ds_m=soil["ec"],
        organic_matter_pct=soil["om"],
        n_no3_ppm=soil["n_no3"],
        n_nh4_ppm=soil["n_nh4"],
        p_ppm=soil["p"],
        k_ppm=soil["k"],
        ca_ppm=soil["ca"],
        mg_ppm=soil["mg"],
        s_ppm=soil["s"],
        cic_cmol_kg=soil["cic"],
    )

def create_water_data(water: Dict) -> WaterData:
    return WaterData(
        ec=water["ec"],
        ph=water["ph"],
        no3_meq=water["no3"],
        h2po4_meq=water["h2po4"],
        so4_meq=water["so4"],
        hco3_meq=water["hco3"],
        k_meq=water["k"],
        ca_meq=water["ca"],
        mg_meq=water["mg"],
        na_meq=water["na"],
    )

def run_validation(num_tests: int = 100, seed: int = 42) -> Dict[str, Any]:
    random.seed(seed)
    
    results = []
    anomalies = []
    stats = {
        "total_tests": num_tests,
        "successful": 0,
        "failed": 0,
        "anomalies": 0,
        "deficits_found": {"N": 0, "P2O5": 0, "K2O": 0, "Ca": 0, "Mg": 0, "S": 0},
        "zero_deficits": {"N": 0, "P2O5": 0, "K2O": 0, "Ca": 0, "Mg": 0, "S": 0},
        "out_of_range": {"N": 0, "P2O5": 0, "K2O": 0, "Ca": 0, "Mg": 0, "S": 0},
        "avg_deficits": {"N": 0, "P2O5": 0, "K2O": 0, "Ca": 0, "Mg": 0, "S": 0},
        "concentration_issues": 0,
    }
    
    deficit_sums = {"N": 0, "P2O5": 0, "K2O": 0, "Ca": 0, "Mg": 0, "S": 0}
    
    for i in range(num_tests):
        try:
            soil_data = random.choice(SOIL_ANALYSES)
            water_data = random.choice(WATER_ANALYSES)
            crop = random.choice(CROPS)
            stage = random.choice(crop["stages"])
            
            yield_factor = random.uniform(0.6, 1.2)
            yield_target = crop["yield"] * yield_factor
            
            irrigation_volume = random.choice([30, 40, 50, 60, 80, 100])
            num_applications = random.choice([6, 8, 10, 12, 15, 20])
            irrigation_system = random.choice(IRRIGATION_SYSTEMS)
            irrigation_freq = random.choice([3, 5, 7, 10, 14])
            
            stage_percent = random.uniform(0.4, 1.0)
            
            soil = create_soil_data(soil_data)
            water = create_water_data(water_data)
            
            crop_reqs = crop["reqs"].copy()
            for nutrient in crop_reqs:
                crop_reqs[nutrient] = crop_reqs[nutrient] * (yield_target / crop["yield"]) * stage_percent
            
            crop_obj = CropData(
                name=crop["name"],
                variety="",
                growth_stage=stage,
                yield_target=yield_target,
                n_kg_ha=crop_reqs["N"],
                p2o5_kg_ha=crop_reqs["P2O5"],
                k2o_kg_ha=crop_reqs["K2O"],
                ca_kg_ha=crop_reqs["Ca"],
                mg_kg_ha=crop_reqs["Mg"],
                s_kg_ha=crop_reqs["S"],
            )
            
            irrigation = IrrigationData(
                system=irrigation_system,
                frequency_days=irrigation_freq,
                volume_m3_ha=irrigation_volume,
                area_ha=1.0,
                num_applications=num_applications,
            )
            
            result = fertiirrigation_calculator.calculate(soil, water, crop_obj, irrigation)
            
            test_result = {
                "test_id": i + 1,
                "soil": soil_data["name"],
                "water": water_data["name"],
                "crop": crop["name"],
                "stage": stage,
                "yield_target": round(yield_target, 1),
                "irrigation_volume": irrigation_volume,
                "num_applications": num_applications,
                "status": result.get("status", "unknown"),
            }
            
            balance = result.get("nutrient_balance", [])
            for nb in balance:
                nutrient = nb["nutrient"]
                deficit = nb.get("fertilizer_needed_kg_ha", 0)
                
                test_result[f"{nutrient}_deficit"] = round(deficit, 1)
                test_result[f"{nutrient}_soil_avail"] = round(nb.get("soil_available_kg_ha", 0), 1)
                test_result[f"{nutrient}_water_contrib"] = round(nb.get("water_contribution_kg_ha", 0), 1)
                test_result[f"{nutrient}_requirement"] = round(nb.get("requirement_kg_ha", 0), 1)
                
                if deficit > 0:
                    stats["deficits_found"][nutrient] += 1
                    deficit_sums[nutrient] += deficit
                else:
                    stats["zero_deficits"][nutrient] += 1
                
                ranges = AGRONOMIC_RANGES.get(nutrient, {})
                if deficit > ranges.get("max", 500):
                    stats["out_of_range"][nutrient] += 1
                    anomalies.append({
                        "test_id": i + 1,
                        "issue": f"{nutrient} deficit too high",
                        "value": deficit,
                        "max_expected": ranges.get("max", 500),
                        "soil": soil_data["name"],
                        "crop": crop["name"],
                    })
            
            program = result.get("fertilizer_program", [])
            for fert in program:
                conc = fert.get("concentration_g_l", 0)
                if conc > 5.0:
                    stats["concentration_issues"] += 1
                    anomalies.append({
                        "test_id": i + 1,
                        "issue": "Concentration too high",
                        "fertilizer": fert.get("fertilizer_name", "Unknown"),
                        "concentration_g_l": conc,
                        "max_recommended": 3.0,
                    })
                    break
            
            test_result["warnings_count"] = len(result.get("warnings", []))
            test_result["recommendations_count"] = len(result.get("recommendations", []))
            
            results.append(test_result)
            stats["successful"] += 1
            
        except Exception as e:
            stats["failed"] += 1
            anomalies.append({
                "test_id": i + 1,
                "issue": "Calculation error",
                "error": str(e),
            })
    
    for nutrient in deficit_sums:
        count = stats["deficits_found"][nutrient]
        if count > 0:
            stats["avg_deficits"][nutrient] = round(deficit_sums[nutrient] / count, 1)
    
    stats["anomalies"] = len(anomalies)
    
    return {
        "stats": stats,
        "results": results,
        "anomalies": anomalies,
    }

def generate_report(validation: Dict) -> str:
    stats = validation["stats"]
    results = validation["results"]
    anomalies = validation["anomalies"]
    
    report = []
    report.append("=" * 80)
    report.append("REPORTE DE VALIDACIÓN - CALCULADORA FERTIRRIEGO")
    report.append("=" * 80)
    report.append("")
    
    report.append("## RESUMEN EJECUTIVO")
    report.append("-" * 40)
    report.append(f"Total de pruebas: {stats['total_tests']}")
    report.append(f"Exitosas: {stats['successful']}")
    report.append(f"Fallidas: {stats['failed']}")
    report.append(f"Anomalías detectadas: {stats['anomalies']}")
    report.append(f"Problemas de concentración: {stats['concentration_issues']}")
    report.append("")
    
    report.append("## ANÁLISIS DE DÉFICITS POR NUTRIENTE")
    report.append("-" * 40)
    report.append(f"{'Nutriente':<10} {'Con Déficit':<12} {'Sin Déficit':<12} {'Fuera Rango':<12} {'Promedio':<10}")
    report.append("-" * 56)
    for nutrient in ["N", "P2O5", "K2O", "Ca", "Mg", "S"]:
        with_def = stats["deficits_found"][nutrient]
        zero_def = stats["zero_deficits"][nutrient]
        out_range = stats["out_of_range"][nutrient]
        avg = stats["avg_deficits"][nutrient]
        pct_with = (with_def / stats["total_tests"]) * 100
        report.append(f"{nutrient:<10} {with_def:>4} ({pct_with:>4.0f}%) {zero_def:>7}       {out_range:>7}       {avg:>8.1f}")
    report.append("")
    
    report.append("## EVALUACIÓN DE RANGOS AGRONÓMICOS")
    report.append("-" * 40)
    for nutrient, ranges in AGRONOMIC_RANGES.items():
        avg = stats["avg_deficits"][nutrient]
        typical_min = ranges["typical_min"]
        typical_max = ranges["typical_max"]
        
        if avg == 0:
            status = "⚠️ SIN DÉFICITS"
        elif typical_min <= avg <= typical_max:
            status = "✓ DENTRO DE RANGO"
        elif avg < typical_min:
            status = "⚠️ BAJO"
        else:
            status = "⚠️ ALTO"
        
        report.append(f"{nutrient}: Promedio={avg:.1f} kg/ha, Rango típico={typical_min}-{typical_max} kg/ha → {status}")
    report.append("")
    
    report.append("## DISTRIBUCIÓN DE RESULTADOS")
    report.append("-" * 40)
    
    n_deficits = [r.get("N_deficit", 0) for r in results if "N_deficit" in r]
    if n_deficits:
        report.append(f"N déficit: min={min(n_deficits):.0f}, max={max(n_deficits):.0f}, mediana={sorted(n_deficits)[len(n_deficits)//2]:.0f}")
    
    p_deficits = [r.get("P2O5_deficit", 0) for r in results if "P2O5_deficit" in r]
    if p_deficits:
        report.append(f"P2O5 déficit: min={min(p_deficits):.0f}, max={max(p_deficits):.0f}, mediana={sorted(p_deficits)[len(p_deficits)//2]:.0f}")
    
    k_deficits = [r.get("K2O_deficit", 0) for r in results if "K2O_deficit" in r]
    if k_deficits:
        report.append(f"K2O déficit: min={min(k_deficits):.0f}, max={max(k_deficits):.0f}, mediana={sorted(k_deficits)[len(k_deficits)//2]:.0f}")
    report.append("")
    
    if anomalies:
        report.append("## ANOMALÍAS DETECTADAS")
        report.append("-" * 40)
        for i, anom in enumerate(anomalies[:15]):
            report.append(f"{i+1}. Test #{anom.get('test_id', '?')}: {anom.get('issue', 'Unknown')}")
            for k, v in anom.items():
                if k not in ["test_id", "issue"]:
                    report.append(f"   - {k}: {v}")
        if len(anomalies) > 15:
            report.append(f"   ... y {len(anomalies) - 15} anomalías más")
        report.append("")
    
    report.append("## MUESTRA DE RESULTADOS (10 escenarios)")
    report.append("-" * 40)
    sample = random.sample(results, min(10, len(results)))
    for r in sample:
        report.append(f"\nTest #{r['test_id']}: {r['crop']} - {r['stage']}")
        report.append(f"  Suelo: {r['soil']}, Agua: {r['water']}")
        report.append(f"  Rendimiento: {r['yield_target']} ton/ha, Aplicaciones: {r['num_applications']}")
        report.append(f"  Déficits: N={r.get('N_deficit', 0):.0f}, P2O5={r.get('P2O5_deficit', 0):.0f}, K2O={r.get('K2O_deficit', 0):.0f}")
        report.append(f"  Suelo disponible: N={r.get('N_soil_avail', 0):.0f}, P2O5={r.get('P2O5_soil_avail', 0):.0f}, K2O={r.get('K2O_soil_avail', 0):.0f}")
    report.append("")
    
    report.append("## CONCLUSIONES")
    report.append("-" * 40)
    
    n_pct = (stats["deficits_found"]["N"] / stats["total_tests"]) * 100
    p_pct = (stats["deficits_found"]["P2O5"] / stats["total_tests"]) * 100
    k_pct = (stats["deficits_found"]["K2O"] / stats["total_tests"]) * 100
    
    if n_pct >= 50 and p_pct >= 40 and k_pct >= 50:
        report.append("✓ La calculadora genera déficits de manera apropiada para la mayoría de escenarios.")
    else:
        report.append(f"⚠️ Déficits generados: N={n_pct:.0f}%, P2O5={p_pct:.0f}%, K2O={k_pct:.0f}%")
    
    if stats["concentration_issues"] == 0:
        report.append("✓ Todas las concentraciones de aplicación están dentro de rangos manejables.")
    else:
        report.append(f"⚠️ {stats['concentration_issues']} casos con concentraciones superiores a 5 g/L.")
    
    if stats["failed"] == 0:
        report.append("✓ Todos los cálculos se completaron sin errores.")
    else:
        report.append(f"⚠️ {stats['failed']} cálculos fallaron con errores.")
    
    out_of_range_total = sum(stats["out_of_range"].values())
    if out_of_range_total == 0:
        report.append("✓ Todos los déficits están dentro de rangos agronómicos aceptables.")
    else:
        report.append(f"⚠️ {out_of_range_total} casos con déficits fuera de rango esperado.")
    
    report.append("")
    report.append("=" * 80)
    report.append("FIN DEL REPORTE")
    report.append("=" * 80)
    
    return "\n".join(report)

if __name__ == "__main__":
    print("Ejecutando validación de FertiRiego (100 escenarios)...")
    print("")
    
    validation = run_validation(num_tests=100, seed=42)
    
    report = generate_report(validation)
    print(report)
    
    with open("fertiirrigation_validation_report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    
    with open("fertiirrigation_validation_data.json", "w", encoding="utf-8") as f:
        json.dump(validation, f, indent=2, ensure_ascii=False)
    
    print("\nArchivos generados:")
    print("- fertiirrigation_validation_report.txt")
    print("- fertiirrigation_validation_data.json")

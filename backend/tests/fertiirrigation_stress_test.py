#!/usr/bin/env python3
"""
FertiIrrigation Stress Test - Bad Water Quality Scenarios
Tests the fertigation calculator with various problematic water profiles.
"""

import random
import time
import json
import sys
import os
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.fertiirrigation_calculator import (
    fertiirrigation_calculator,
    SoilData,
    WaterData,
    CropData,
    IrrigationData,
    AcidData,
)

random.seed(42)

@dataclass
class WaterProfile:
    name: str
    category: str
    severity: str
    ec: float
    ph: float
    no3_meq: float
    h2po4_meq: float
    so4_meq: float
    hco3_meq: float
    k_meq: float
    ca_meq: float
    mg_meq: float
    na_meq: float
    cl_meq: float = 0.0

@dataclass
class SoilProfile:
    name: str
    texture: str
    ph: float
    ec_ds_m: float
    organic_matter_pct: float
    n_no3_ppm: float
    p_ppm: float
    k_ppm: float
    ca_ppm: float
    mg_ppm: float

@dataclass
class CropProfile:
    name: str
    n_total: float
    p2o5: float
    k2o: float
    cao: float
    mgo: float
    s: float
    fe: float
    mn: float
    zn: float
    cu: float
    b: float

@dataclass
class TestResult:
    test_id: int
    water_name: str
    water_category: str
    severity: str
    soil_name: str
    crop_name: str
    success: bool
    has_recommendations: bool
    total_fertilizers: int
    execution_time_ms: float
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

SOIL_PROFILES = [
    SoilProfile("Suelo Franco", "franco", 7.0, 0.8, 2.5, 15, 20, 180, 2000, 300),
    SoilProfile("Suelo Arcilloso", "arcilloso", 7.5, 1.2, 3.0, 10, 15, 150, 2500, 400),
    SoilProfile("Suelo Arenoso", "arenoso", 6.5, 0.5, 1.5, 8, 10, 100, 1200, 200),
    SoilProfile("Suelo Calcareo", "franco_arcilloso", 8.0, 1.5, 2.0, 12, 8, 200, 4000, 350),
    SoilProfile("Suelo Acido", "franco_arenoso", 5.5, 0.4, 4.0, 20, 5, 80, 800, 150),
]

CROP_PROFILES = [
    CropProfile("Tomate", 250, 80, 350, 180, 50, 40, 3, 1.5, 0.5, 0.3, 0.5),
    CropProfile("Pimiento", 220, 70, 300, 160, 45, 35, 2.5, 1.2, 0.4, 0.25, 0.4),
    CropProfile("Chile", 200, 65, 280, 150, 40, 30, 2.5, 1.0, 0.4, 0.2, 0.4),
    CropProfile("Pepino", 180, 60, 250, 140, 35, 25, 2.0, 0.8, 0.3, 0.2, 0.3),
    CropProfile("Melon", 160, 55, 220, 120, 30, 22, 2.0, 0.7, 0.3, 0.15, 0.3),
    CropProfile("Fresa", 140, 50, 200, 100, 25, 20, 1.5, 0.6, 0.25, 0.15, 0.25),
]

def generate_bad_water_profiles(per_category: int = 6) -> List[WaterProfile]:
    """Generate water profiles with problematic characteristics."""
    profiles = []
    
    for i in range(per_category):
        severity = ["moderate", "severe", "extreme"][i % 3]
        s = [0, 0.5, 1.0][i % 3]
        base_hco3 = 5 + s * 6 + random.uniform(-0.3, 0.3)
        profiles.append(WaterProfile(
            name=f"HCO3-{i+1}", category="HCO3_dominant", severity=severity,
            ec=1.0 + s * 0.5, ph=7.5 + s * 0.5,
            no3_meq=0.2, h2po4_meq=0.05, so4_meq=random.uniform(1, 3),
            hco3_meq=base_hco3, k_meq=0.2, ca_meq=random.uniform(2, 5),
            mg_meq=random.uniform(1, 3), na_meq=random.uniform(0.5, 2),
            cl_meq=random.uniform(0.5, 2)
        ))
    
    for i in range(per_category):
        severity = ["moderate", "severe", "extreme"][i % 3]
        s = [0, 0.5, 1.0][i % 3]
        base_na = 4 + s * 8 + random.uniform(-0.5, 0.5)
        profiles.append(WaterProfile(
            name=f"Na-{i+1}", category="Na_dominant", severity=severity,
            ec=1.5 + s * 1.0, ph=7.8 + s * 0.3,
            no3_meq=0.1, h2po4_meq=0.02, so4_meq=random.uniform(1, 3),
            hco3_meq=random.uniform(3, 5), k_meq=0.3, ca_meq=random.uniform(2, 4),
            mg_meq=random.uniform(1, 2.5), na_meq=base_na,
            cl_meq=random.uniform(2, 5)
        ))
    
    for i in range(per_category):
        severity = ["moderate", "severe", "extreme"][i % 3]
        s = [0, 0.5, 1.0][i % 3]
        base_cl = 5 + s * 10 + random.uniform(-0.5, 0.5)
        profiles.append(WaterProfile(
            name=f"Cl-{i+1}", category="Cl_dominant", severity=severity,
            ec=1.5 + s * 1.0, ph=7.2 + s * 0.2,
            no3_meq=0.15, h2po4_meq=0.03, so4_meq=random.uniform(1, 3),
            hco3_meq=random.uniform(2, 4), k_meq=0.25, ca_meq=random.uniform(3, 6),
            mg_meq=random.uniform(1.5, 3), na_meq=random.uniform(2, 5),
            cl_meq=base_cl
        ))
    
    for i in range(per_category):
        severity = ["moderate", "severe", "extreme"][i % 3]
        s = [0, 0.5, 1.0][i % 3]
        base_ec = 2.0 + s * 2.5
        profiles.append(WaterProfile(
            name=f"EC-{i+1}", category="EC_salinity", severity=severity,
            ec=base_ec, ph=7.5 + s * 0.3,
            no3_meq=0.3, h2po4_meq=0.05, so4_meq=3 + s * 4,
            hco3_meq=random.uniform(3, 5), k_meq=0.4, ca_meq=5 + s * 5,
            mg_meq=2 + s * 2.5, na_meq=random.uniform(3, 6),
            cl_meq=random.uniform(3, 6)
        ))
    
    for i in range(per_category):
        severity = ["moderate", "severe", "extreme"][i % 3]
        mult = [1.0, 1.5, 2.0][i % 3]
        profiles.append(WaterProfile(
            name=f"MULTI-{i+1}", category="multi_contaminant", severity=severity,
            ec=2.0 * mult, ph=7.8,
            no3_meq=0.2, h2po4_meq=0.04, so4_meq=random.uniform(4, 7) * mult,
            hco3_meq=random.uniform(5, 8) * mult, k_meq=0.3,
            ca_meq=random.uniform(4, 7) * mult, mg_meq=random.uniform(2, 4) * mult,
            na_meq=random.uniform(4, 8) * mult, cl_meq=random.uniform(4, 8) * mult
        ))
    
    return profiles

def create_soil_data(profile: SoilProfile) -> SoilData:
    return SoilData(
        texture=profile.texture,
        bulk_density=1.3,
        depth_cm=30,
        ph=profile.ph,
        ec_ds_m=profile.ec_ds_m,
        organic_matter_pct=profile.organic_matter_pct,
        n_no3_ppm=profile.n_no3_ppm,
        n_nh4_ppm=2.0,
        p_ppm=profile.p_ppm,
        k_ppm=profile.k_ppm,
        ca_ppm=profile.ca_ppm,
        mg_ppm=profile.mg_ppm,
        s_ppm=15.0,
        cic_cmol_kg=20.0,
    )

def create_water_data(profile: WaterProfile) -> WaterData:
    return WaterData(
        ec=profile.ec,
        ph=profile.ph,
        no3_meq=profile.no3_meq,
        h2po4_meq=profile.h2po4_meq,
        so4_meq=profile.so4_meq,
        hco3_meq=profile.hco3_meq,
        k_meq=profile.k_meq,
        ca_meq=profile.ca_meq,
        mg_meq=profile.mg_meq,
        na_meq=profile.na_meq,
        fe_ppm=0.1,
        mn_ppm=0.05,
        zn_ppm=0.02,
        cu_ppm=0.01,
        b_ppm=0.05,
    )

def create_crop_data(profile: CropProfile) -> CropData:
    return CropData(
        name=profile.name,
        variety=None,
        growth_stage="desarrollo",
        yield_target=50.0,
        n_kg_ha=profile.n_total,
        p2o5_kg_ha=profile.p2o5,
        k2o_kg_ha=profile.k2o,
        ca_kg_ha=profile.cao,
        mg_kg_ha=profile.mgo,
        s_kg_ha=profile.s,
    )

def create_irrigation_data() -> IrrigationData:
    return IrrigationData(
        system="goteo",
        frequency_days=7.0,
        volume_m3_ha=50.0,
        area_ha=1.0,
    )

def run_test(test_id: int, water: WaterProfile, soil: SoilProfile, crop: CropProfile) -> TestResult:
    """Run a single fertigation calculation test."""
    start = time.time()
    
    try:
        soil_data = create_soil_data(soil)
        water_data = create_water_data(water)
        crop_data = create_crop_data(crop)
        irrigation_data = create_irrigation_data()
        
        result = fertiirrigation_calculator.calculate(
            soil=soil_data,
            water=water_data,
            crop=crop_data,
            irrigation=irrigation_data,
            acid=None,
            currency="MXN",
            user_prices=None,
        )
        
        has_recommendations = len(result.get("fertilizer_program", [])) > 0
        total_ferts = len(result.get("fertilizer_program", []))
        warnings = result.get("warnings", [])
        
        return TestResult(
            test_id=test_id,
            water_name=water.name,
            water_category=water.category,
            severity=water.severity,
            soil_name=soil.name,
            crop_name=crop.name,
            success=True,
            has_recommendations=has_recommendations,
            total_fertilizers=total_ferts,
            execution_time_ms=(time.time() - start) * 1000,
            warnings=warnings if isinstance(warnings, list) else []
        )
        
    except Exception as e:
        return TestResult(
            test_id=test_id,
            water_name=water.name,
            water_category=water.category,
            severity=water.severity,
            soil_name=soil.name,
            crop_name=crop.name,
            success=False,
            has_recommendations=False,
            total_fertilizers=0,
            execution_time_ms=(time.time() - start) * 1000,
            error=str(e)[:100]
        )

def main():
    print("=" * 70)
    print("FERTIIRRIGATION STRESS TEST - Bad Water Quality Scenarios")
    print("=" * 70)
    
    water_profiles = generate_bad_water_profiles(per_category=6)
    total_tests = len(water_profiles) * len(CROP_PROFILES)
    
    print(f"\nGenerated {len(water_profiles)} water profiles")
    print(f"Testing with {len(SOIL_PROFILES)} soil types and {len(CROP_PROFILES)} crops")
    print(f"Total scenarios: {total_tests}\n")
    
    results = []
    test_id = 0
    
    for water in water_profiles:
        soil = random.choice(SOIL_PROFILES)
        crop = random.choice(CROP_PROFILES)
        test_id += 1
        
        result = run_test(test_id, water, soil, crop)
        results.append(result)
        
        status = "OK" if result.success else "FAIL"
        rec = "+" if result.has_recommendations else "-"
        print(f"[{test_id:2d}/{len(water_profiles)}] {status} {rec} {water.name:8s} ({water.severity:8s}) {crop.name:10s} Ferts:{result.total_fertilizers:2d} {result.execution_time_ms:.0f}ms")
    
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    
    ok = [r for r in results if r.success]
    fail = [r for r in results if not r.success]
    with_recs = [r for r in ok if r.has_recommendations]
    
    print(f"\nTotal: {len(ok)}/{len(results)} successful ({100*len(ok)//len(results)}%)")
    print(f"With recommendations: {len(with_recs)}/{len(ok)} ({100*len(with_recs)//max(len(ok),1)}%)")
    
    if fail:
        print(f"\nFailed: {len(fail)}")
        for r in fail[:5]:
            print(f"  - {r.water_name} + {r.soil_name}: {r.error}")
    
    if ok:
        times = [r.execution_time_ms for r in ok]
        fert_counts = [r.total_fertilizers for r in ok]
        
        print(f"\nExecution Time:")
        print(f"  Average: {sum(times)/len(times):.1f} ms")
        print(f"  Max: {max(times):.1f} ms")
        
        print(f"\nFertilizer Count:")
        print(f"  Average: {sum(fert_counts)/len(fert_counts):.1f}")
        print(f"  Max: {max(fert_counts)}")
        
        print(f"\nBy Water Category:")
        for cat in ["HCO3_dominant", "Na_dominant", "Cl_dominant", "EC_salinity", "multi_contaminant"]:
            cat_r = [r for r in ok if r.water_category == cat]
            if cat_r:
                with_rec = len([r for r in cat_r if r.has_recommendations])
                print(f"  {cat:20s}: {len(cat_r)}/{len(cat_r)} OK, {with_rec} with recs")
        
        print(f"\nBy Severity:")
        for sev in ["moderate", "severe", "extreme"]:
            sev_r = [r for r in ok if r.severity == sev]
            if sev_r:
                with_rec = len([r for r in sev_r if r.has_recommendations])
                print(f"  {sev:10s}: {len(sev_r)} OK, {with_rec} with recommendations")
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": len(results),
        "successful": len(ok),
        "failed": len(fail),
        "with_recommendations": len(with_recs),
        "results": [asdict(r) for r in results]
    }
    
    results_path = os.path.join(os.path.dirname(__file__), "fertiirrigation_stress_results.json")
    with open(results_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nResults saved to fertiirrigation_stress_results.json")
    
    print("\n" + "=" * 70)
    if len(ok) == len(results) and len(with_recs) > len(results) * 0.8:
        print("VEREDICTO: APROBADO - Calculator handles bad water scenarios well")
    elif len(ok) >= len(results) * 0.9:
        print("VEREDICTO: APROBADO CON OBSERVACIONES")
    else:
        print("VEREDICTO: REQUIERE REVISION")
    print("=" * 70)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
IA GROWER V Test Suite - 100 Diverse Scenarios
Tests 4 calculator modes:
- Hydroponics Direct Solution (25 tests)
- Hydroponics A/B Tanks (25 tests) 
- FertiIrrigation Direct Solution (25 tests)
- FertiIrrigation A/B Tanks (25 tests)

Evaluates: Nutrients, Acids, Micronutrients with IA GROWER V integration
"""

import asyncio
import httpx
import json
import time
import random
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import create_access_token

BASE_URL = "http://localhost:8000"
TEST_USER_ID = 2

CROPS_FERTIRRIEGO = [
    {"crop": "Maíz", "stage": "V6-V10", "n_req": 180, "p_req": 60, "k_req": 120},
    {"crop": "Trigo", "stage": "Encañado", "n_req": 150, "p_req": 50, "k_req": 80},
    {"crop": "Tomate Campo", "stage": "Floración", "n_req": 200, "p_req": 80, "k_req": 300},
    {"crop": "Chile", "stage": "Fructificación", "n_req": 180, "p_req": 70, "k_req": 250},
    {"crop": "Cebolla", "stage": "Bulbificación", "n_req": 120, "p_req": 60, "k_req": 180},
    {"crop": "Papa", "stage": "Tuberización", "n_req": 160, "p_req": 80, "k_req": 200},
    {"crop": "Aguacate", "stage": "Desarrollo fruto", "n_req": 140, "p_req": 50, "k_req": 200},
    {"crop": "Mango", "stage": "Floración", "n_req": 100, "p_req": 40, "k_req": 150},
    {"crop": "Caña de Azúcar", "stage": "Gran crecimiento", "n_req": 200, "p_req": 60, "k_req": 180},
    {"crop": "Alfalfa", "stage": "Rebrote", "n_req": 40, "p_req": 80, "k_req": 200},
]

WATER_QUALITIES = [
    {"name": "Agua Pura", "ca": 0.5, "mg": 0.2, "na": 0.1, "hco3": 1.0, "so4": 0.2, "cl": 0.1},
    {"name": "Pozo Limpio", "ca": 2.0, "mg": 1.0, "na": 0.5, "hco3": 3.0, "so4": 1.0, "cl": 0.5},
    {"name": "Pozo con Fe", "ca": 1.5, "mg": 0.8, "na": 0.3, "hco3": 2.5, "so4": 0.8, "cl": 0.3},
    {"name": "Agua Tratada", "ca": 1.0, "mg": 0.5, "na": 2.0, "hco3": 2.0, "so4": 1.5, "cl": 1.0},
    {"name": "Agua con B Alto", "ca": 1.2, "mg": 0.6, "na": 0.4, "hco3": 2.0, "so4": 0.5, "cl": 0.2},
    {"name": "Agua Salobre", "ca": 3.0, "mg": 2.0, "na": 5.0, "hco3": 4.0, "so4": 2.0, "cl": 4.0},
]

DILUTION_FACTORS = [10, 25, 50, 100, 150, 200]

SOIL_TYPES = [
    {"name": "Arenoso", "n_avail": 10, "p_avail": 8, "k_avail": 50, "ca_avail": 200, "mg_avail": 30},
    {"name": "Franco", "n_avail": 25, "p_avail": 15, "k_avail": 150, "ca_avail": 800, "mg_avail": 100},
    {"name": "Arcilloso", "n_avail": 40, "p_avail": 25, "k_avail": 300, "ca_avail": 1500, "mg_avail": 200},
    {"name": "Calcáreo", "n_avail": 20, "p_avail": 10, "k_avail": 100, "ca_avail": 3000, "mg_avail": 150},
    {"name": "Volcánico", "n_avail": 35, "p_avail": 5, "k_avail": 200, "ca_avail": 600, "mg_avail": 80},
]

HYDRO_RECIPES = ["steiner", "hoagland", "lechuga", "pimiento", "pepino", "melon", "berenjena"]


@dataclass
class TestResult:
    test_id: int
    mode: str
    scenario: str
    success: bool
    response_time_ms: float
    ia_validation_present: bool = False
    ia_is_valid: bool = True
    ia_risk_level: str = "low"
    adjustments_count: int = 0
    recommendations: List[str] = field(default_factory=list)
    fertilizers_count: int = 0
    micronutrients_count: int = 0
    acid_used: bool = False
    total_cost: float = 0.0
    error_message: str = ""
    raw_response: Dict = field(default_factory=dict)


class IAGrowerVTestSuite:
    def __init__(self):
        self.results: List[TestResult] = []
        self.token: Optional[str] = None
        
    async def authenticate(self) -> bool:
        """Generate test token directly using create_access_token."""
        try:
            self.token = create_access_token(data={"sub": str(TEST_USER_ID)})
            print(f"Generated test token for user ID {TEST_USER_ID}")
            return True
        except Exception as e:
            print(f"Auth error: {e}")
            return False
    
    def get_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}
    
    async def run_hydroponics_direct_test(self, test_id: int) -> TestResult:
        """Test hydroponics direct solution mode."""
        recipe = random.choice(HYDRO_RECIPES)
        water = random.choice(WATER_QUALITIES)
        volume = random.choice([500, 1000, 2000, 5000])
        
        scenario = f"{recipe} + {water['name']} + {volume}L"
        
        try:
            start = time.time()
            
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
                session_resp = await client.post(
                    "/api/hydro_ions/sessions",
                    headers=self.get_headers(),
                    json={
                        "recipe_id": recipe,
                        "reservoir_volume_liters": volume,
                        "preparation_mode": "direct"
                    }
                )
                
                if session_resp.status_code != 201:
                    return TestResult(
                        test_id=test_id,
                        mode="hydro_direct",
                        scenario=scenario,
                        success=False,
                        response_time_ms=(time.time() - start) * 1000,
                        error_message=f"Session creation failed: {session_resp.status_code} - {session_resp.text[:100]}"
                    )
                
                session_id = session_resp.json().get("id")
                
                deficit_resp = await client.post(
                    "/api/hydro_ions/calculate/deficits",
                    headers=self.get_headers(),
                    json={
                        "session_id": session_id,
                        "water_analysis": {
                            "ca_meq": water["ca"],
                            "mg_meq": water["mg"],
                            "na_meq": water["na"],
                            "hco3_meq": water["hco3"],
                            "so4_meq": water["so4"],
                            "cl_meq": water["cl"],
                            "no3_meq": 0.1,
                            "nh4_meq": 0.0,
                            "k_meq": 0.1,
                            "h2po4_meq": 0.0,
                            "ec_ds_m": 0.5,
                            "ph": 7.2
                        }
                    }
                )
                
                if deficit_resp.status_code != 200:
                    return TestResult(
                        test_id=test_id,
                        mode="hydro_direct",
                        scenario=scenario,
                        success=False,
                        response_time_ms=(time.time() - start) * 1000,
                        error_message=f"Deficit calculation failed: {deficit_resp.status_code} - {deficit_resp.text[:100]}"
                    )
                
                deficit_data = deficit_resp.json()
                deficits = deficit_data.get("deficits", {})
                micronutrient_deficits = deficit_data.get("micronutrient_deficits", {})
                
                # Step 3: Get AI fertilizer suggestions
                suggest_resp = await client.post(
                    "/api/hydro_ions/suggest-fertilizers",
                    headers=self.get_headers(),
                    json={
                        "session_id": session_id,
                        "deficits": deficits,
                        "micronutrient_deficits": micronutrient_deficits,
                        "crop_name": recipe,
                        "water_analysis": {
                            "ca_meq": water["ca"],
                            "mg_meq": water["mg"],
                            "na_meq": water["na"],
                            "hco3_meq": water["hco3"],
                            "so4_meq": water["so4"],
                            "cl_meq": water["cl"]
                        },
                        "preparation_mode": "direct"
                    }
                )
                
                if suggest_resp.status_code != 200:
                    return TestResult(
                        test_id=test_id,
                        mode="hydro_direct",
                        scenario=scenario,
                        success=False,
                        response_time_ms=(time.time() - start) * 1000,
                        error_message=f"Fertilizer suggestion failed: {suggest_resp.status_code} - {suggest_resp.text[:100]}"
                    )
                
                suggest_data = suggest_resp.json()
                recommended_ferts = suggest_data.get("recommended_fertilizers", [])
                
                # Extract fertilizer IDs from recommendations
                selected_fertilizers = []
                for f in recommended_ferts:
                    if isinstance(f, dict):
                        selected_fertilizers.append(f.get("id") or f.get("fertilizer_id") or f.get("slug", ""))
                    elif isinstance(f, str):
                        selected_fertilizers.append(f)
                
                # Step 4: Calculate doses with selected fertilizers
                dose_resp = await client.post(
                    "/api/hydro_ions/calculate/doses",
                    headers=self.get_headers(),
                    json={
                        "session_id": session_id,
                        "selected_fertilizers": selected_fertilizers,
                        "profile": random.choice(["balanced", "economic", "complete"])
                    }
                )
                
                if dose_resp.status_code != 200:
                    return TestResult(
                        test_id=test_id,
                        mode="hydro_direct",
                        scenario=scenario,
                        success=False,
                        response_time_ms=(time.time() - start) * 1000,
                        error_message=f"Dose calculation failed: {dose_resp.status_code} - {dose_resp.text[:100]}"
                    )
                
                dose_data = dose_resp.json()
                
                micro_resp = await client.get(
                    f"/api/hydro_ions/sessions/{session_id}/micronutrient-proposal",
                    headers=self.get_headers()
                )
                
                micro_data = {}
                if micro_resp.status_code == 200:
                    micro_data = micro_resp.json()
                
                elapsed = (time.time() - start) * 1000
                
                ia_validation = dose_data.get("ia_validation", {})
                
                return TestResult(
                    test_id=test_id,
                    mode="hydro_direct",
                    scenario=scenario,
                    success=True,
                    response_time_ms=elapsed,
                    ia_validation_present=bool(ia_validation),
                    ia_is_valid=ia_validation.get("is_valid", True) if ia_validation else True,
                    ia_risk_level=ia_validation.get("risk_level", "low") if ia_validation else "low",
                    adjustments_count=len(ia_validation.get("adjusted_doses", {}) or {}) if ia_validation else 0,
                    recommendations=ia_validation.get("recommendations", [])[:3] if ia_validation else [],
                    fertilizers_count=len(dose_data.get("doses", [])),
                    micronutrients_count=len(micro_data.get("doses", [])) if micro_data else 0,
                    acid_used=bool(dose_data.get("acid_treatment")),
                    total_cost=dose_data.get("total_cost", 0) + (micro_data.get("total_cost", 0) if micro_data else 0),
                    raw_response={"doses": dose_data, "micro": micro_data}
                )
                
        except Exception as e:
            return TestResult(
                test_id=test_id,
                mode="hydro_direct",
                scenario=scenario,
                success=False,
                response_time_ms=0,
                error_message=str(e)
            )
    
    async def run_hydroponics_ab_test(self, test_id: int) -> TestResult:
        """Test hydroponics A/B tanks mode."""
        recipe = random.choice(HYDRO_RECIPES)
        water = random.choice(WATER_QUALITIES)
        dilution = random.choice(DILUTION_FACTORS)
        volume = random.choice([500, 1000, 2000])
        
        scenario = f"{recipe} + {water['name']} + 1:{dilution}"
        
        try:
            start = time.time()
            
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
                session_resp = await client.post(
                    "/api/hydro_ions/sessions",
                    headers=self.get_headers(),
                    json={
                        "recipe_id": recipe,
                        "reservoir_volume_liters": volume,
                        "preparation_mode": "stock_ab",
                        "stock_concentration_ratio": dilution
                    }
                )
                
                if session_resp.status_code != 201:
                    return TestResult(
                        test_id=test_id,
                        mode="hydro_ab",
                        scenario=scenario,
                        success=False,
                        response_time_ms=(time.time() - start) * 1000,
                        error_message=f"Session creation failed: {session_resp.status_code} - {session_resp.text[:100]}"
                    )
                
                session_id = session_resp.json().get("id")
                
                deficit_resp = await client.post(
                    "/api/hydro_ions/calculate/deficits",
                    headers=self.get_headers(),
                    json={
                        "session_id": session_id,
                        "water_analysis": {
                            "ca_meq": water["ca"],
                            "mg_meq": water["mg"],
                            "na_meq": water["na"],
                            "hco3_meq": water["hco3"],
                            "so4_meq": water["so4"],
                            "cl_meq": water["cl"],
                            "no3_meq": 0.1,
                            "nh4_meq": 0.0,
                            "k_meq": 0.1,
                            "h2po4_meq": 0.0,
                            "ec_ds_m": 0.5,
                            "ph": 7.2
                        }
                    }
                )
                
                if deficit_resp.status_code != 200:
                    return TestResult(
                        test_id=test_id,
                        mode="hydro_ab",
                        scenario=scenario,
                        success=False,
                        response_time_ms=(time.time() - start) * 1000,
                        error_message=f"Deficit calculation failed: {deficit_resp.status_code} - {deficit_resp.text[:100]}"
                    )
                
                deficit_data = deficit_resp.json()
                deficits = deficit_data.get("deficits", {})
                micronutrient_deficits = deficit_data.get("micronutrient_deficits", {})
                
                # Step 3: Get AI fertilizer suggestions
                suggest_resp = await client.post(
                    "/api/hydro_ions/suggest-fertilizers",
                    headers=self.get_headers(),
                    json={
                        "session_id": session_id,
                        "deficits": deficits,
                        "micronutrient_deficits": micronutrient_deficits,
                        "crop_name": recipe,
                        "water_analysis": {
                            "ca_meq": water["ca"],
                            "mg_meq": water["mg"],
                            "na_meq": water["na"],
                            "hco3_meq": water["hco3"],
                            "so4_meq": water["so4"],
                            "cl_meq": water["cl"]
                        },
                        "preparation_mode": "stock_ab"
                    }
                )
                
                if suggest_resp.status_code != 200:
                    return TestResult(
                        test_id=test_id,
                        mode="hydro_ab",
                        scenario=scenario,
                        success=False,
                        response_time_ms=(time.time() - start) * 1000,
                        error_message=f"Fertilizer suggestion failed: {suggest_resp.status_code} - {suggest_resp.text[:100]}"
                    )
                
                suggest_data = suggest_resp.json()
                recommended_ferts = suggest_data.get("recommended_fertilizers", [])
                
                # Extract fertilizer IDs
                selected_fertilizers = []
                for f in recommended_ferts:
                    if isinstance(f, dict):
                        selected_fertilizers.append(f.get("id") or f.get("fertilizer_id") or f.get("slug", ""))
                    elif isinstance(f, str):
                        selected_fertilizers.append(f)
                
                # Step 4: Calculate doses with selected fertilizers
                dose_resp = await client.post(
                    "/api/hydro_ions/calculate/doses",
                    headers=self.get_headers(),
                    json={
                        "session_id": session_id,
                        "selected_fertilizers": selected_fertilizers,
                        "profile": random.choice(["balanced", "economic", "complete"])
                    }
                )
                
                if dose_resp.status_code != 200:
                    return TestResult(
                        test_id=test_id,
                        mode="hydro_ab",
                        scenario=scenario,
                        success=False,
                        response_time_ms=(time.time() - start) * 1000,
                        error_message=f"Dose calculation failed: {dose_resp.status_code} - {dose_resp.text[:100]}"
                    )
                
                dose_data = dose_resp.json()
                
                elapsed = (time.time() - start) * 1000
                
                ia_validation = dose_data.get("ia_validation", {})
                tank_a = dose_data.get("tank_a_doses", [])
                tank_b = dose_data.get("tank_b_doses", [])
                
                return TestResult(
                    test_id=test_id,
                    mode="hydro_ab",
                    scenario=scenario,
                    success=True,
                    response_time_ms=elapsed,
                    ia_validation_present=bool(ia_validation),
                    ia_is_valid=ia_validation.get("is_valid", True) if ia_validation else True,
                    ia_risk_level=ia_validation.get("risk_level", "low") if ia_validation else "low",
                    adjustments_count=len(ia_validation.get("adjusted_doses", {}) or {}) if ia_validation else 0,
                    recommendations=ia_validation.get("recommendations", [])[:3] if ia_validation else [],
                    fertilizers_count=len(tank_a) + len(tank_b) if tank_a or tank_b else len(dose_data.get("doses", [])),
                    micronutrients_count=0,
                    acid_used=bool(dose_data.get("acid_treatment")),
                    total_cost=dose_data.get("total_cost", 0),
                    raw_response=dose_data
                )
                
        except Exception as e:
            return TestResult(
                test_id=test_id,
                mode="hydro_ab",
                scenario=scenario,
                success=False,
                response_time_ms=0,
                error_message=str(e)
            )
    
    async def run_fertiirrigation_direct_test(self, test_id: int) -> TestResult:
        """Test fertiirrigation direct solution mode."""
        crop = random.choice(CROPS_FERTIRRIEGO)
        soil = random.choice(SOIL_TYPES)
        water = random.choice(WATER_QUALITIES)
        
        scenario = f"{crop['crop']} + {soil['name']} + {water['name']}"
        
        n_deficit = max(0, crop["n_req"] - soil["n_avail"])
        p_deficit = max(0, crop["p_req"] - soil["p_avail"])
        k_deficit = max(0, crop["k_req"] - soil["k_avail"])
        
        try:
            start = time.time()
            
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=90.0) as client:
                optimize_resp = await client.post(
                    "/api/fertiirrigation/optimize",
                    headers=self.get_headers(),
                    json={
                        "deficit": {
                            "n_kg_ha": n_deficit,
                            "p2o5_kg_ha": p_deficit,
                            "k2o_kg_ha": k_deficit,
                            "ca_kg_ha": max(0, 50 - soil["ca_avail"] * 0.01),
                            "mg_kg_ha": max(0, 30 - soil["mg_avail"] * 0.01),
                            "s_kg_ha": 15
                        },
                        "area_ha": random.choice([1, 5, 10, 25, 50]),
                        "num_applications": random.choice([5, 10, 15, 20]),
                        "currency": random.choice(["MXN", "USD"]),
                        "irrigation_volume_m3_ha": random.choice([30, 50, 80, 100]),
                        "micro_deficit": {
                            "fe_g_ha": random.uniform(100, 400),
                            "mn_g_ha": random.uniform(30, 100),
                            "zn_g_ha": random.uniform(10, 50),
                            "cu_g_ha": random.uniform(5, 15),
                            "b_g_ha": random.uniform(20, 60),
                            "mo_g_ha": random.uniform(2, 8)
                        },
                        "crop_name": crop["crop"],
                        "growth_stage": crop["stage"],
                        "soil_info": {"type": soil["name"]},
                        "water_info": {"quality": water["name"]}
                    }
                )
                
                elapsed = (time.time() - start) * 1000
                
                if optimize_resp.status_code != 200:
                    return TestResult(
                        test_id=test_id,
                        mode="fertirriego_direct",
                        scenario=scenario,
                        success=False,
                        response_time_ms=elapsed,
                        error_message=f"Optimize failed: {optimize_resp.status_code} - {optimize_resp.text[:200]}"
                    )
                
                data = optimize_resp.json()
                
                profiles = data.get("profiles", [])
                best_profile = profiles[0] if profiles else {}
                
                ia_validation = best_profile.get("ia_validation", {})
                
                return TestResult(
                    test_id=test_id,
                    mode="fertirriego_direct",
                    scenario=scenario,
                    success=True,
                    response_time_ms=elapsed,
                    ia_validation_present=bool(ia_validation),
                    ia_is_valid=ia_validation.get("is_valid", True) if ia_validation else True,
                    ia_risk_level=ia_validation.get("risk_level", "low") if ia_validation else "low",
                    adjustments_count=len(ia_validation.get("adjusted_doses", {}) or {}) if ia_validation else 0,
                    recommendations=ia_validation.get("recommendations", [])[:3] if ia_validation else [],
                    fertilizers_count=len(best_profile.get("fertilizers", [])),
                    micronutrients_count=len(best_profile.get("micronutrients", [])),
                    acid_used=bool(data.get("acid_treatment")),
                    total_cost=best_profile.get("total_cost_total", 0),
                    raw_response=data
                )
                
        except Exception as e:
            return TestResult(
                test_id=test_id,
                mode="fertirriego_direct",
                scenario=scenario,
                success=False,
                response_time_ms=0,
                error_message=str(e)
            )
    
    async def run_fertiirrigation_ab_test(self, test_id: int) -> TestResult:
        """Test fertiirrigation A/B tanks mode."""
        crop = random.choice(CROPS_FERTIRRIEGO)
        soil = random.choice(SOIL_TYPES)
        dilution = random.choice(DILUTION_FACTORS)
        
        scenario = f"{crop['crop']} + {soil['name']} + 1:{dilution}"
        
        n_deficit = max(0, crop["n_req"] - soil["n_avail"])
        p_deficit = max(0, crop["p_req"] - soil["p_avail"])
        k_deficit = max(0, crop["k_req"] - soil["k_avail"])
        
        try:
            start = time.time()
            
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=90.0) as client:
                optimize_resp = await client.post(
                    "/api/fertiirrigation/optimize",
                    headers=self.get_headers(),
                    json={
                        "deficit": {
                            "n_kg_ha": n_deficit,
                            "p2o5_kg_ha": p_deficit,
                            "k2o_kg_ha": k_deficit,
                            "ca_kg_ha": max(0, 50 - soil["ca_avail"] * 0.01),
                            "mg_kg_ha": max(0, 30 - soil["mg_avail"] * 0.01),
                            "s_kg_ha": 15
                        },
                        "area_ha": random.choice([5, 10, 25]),
                        "num_applications": random.choice([10, 15, 20]),
                        "currency": "MXN",
                        "irrigation_volume_m3_ha": 50,
                        "crop_name": crop["crop"],
                        "growth_stage": crop["stage"],
                        "soil_info": {"type": soil["name"]}
                    }
                )
                
                if optimize_resp.status_code != 200:
                    return TestResult(
                        test_id=test_id,
                        mode="fertirriego_ab",
                        scenario=scenario,
                        success=False,
                        response_time_ms=(time.time() - start) * 1000,
                        error_message=f"Optimize failed: {optimize_resp.status_code}"
                    )
                
                optimize_data = optimize_resp.json()
                profiles = optimize_data.get("profiles", [])
                best_profile = profiles[0] if profiles else {}
                fertilizers = best_profile.get("fertilizers", [])
                
                ferts_for_ab = [
                    {
                        "fertilizer_name": f.get("fertilizer_name"),
                        "fertilizer_slug": f.get("fertilizer_slug"),
                        "dose_kg_ha": f.get("dose_kg_ha", 0),
                        "dose_kg_total": f.get("dose_kg_total", 0),
                        "n_contribution": f.get("n_contribution", 0),
                        "p2o5_contribution": f.get("p2o5_contribution", 0),
                        "k2o_contribution": f.get("k2o_contribution", 0),
                        "ca_contribution": f.get("ca_contribution", 0),
                        "mg_contribution": f.get("mg_contribution", 0),
                        "s_contribution": f.get("s_contribution", 0)
                    }
                    for f in fertilizers
                ]
                
                ab_resp = await client.post(
                    "/api/fertiirrigation/calculate-ab-tanks",
                    headers=self.get_headers(),
                    json={
                        "fertilizers": ferts_for_ab,
                        "acid_treatment": optimize_data.get("acid_treatment"),
                        "tank_a_volume": 1000,
                        "tank_b_volume": 1000,
                        "dilution_factor": dilution,
                        "num_applications": 10,
                        "irrigation_flow_lph": 1000,
                        "area_ha": 10
                    }
                )
                
                elapsed = (time.time() - start) * 1000
                
                if ab_resp.status_code != 200:
                    return TestResult(
                        test_id=test_id,
                        mode="fertirriego_ab",
                        scenario=scenario,
                        success=False,
                        response_time_ms=elapsed,
                        error_message=f"A/B calculation failed: {ab_resp.status_code}"
                    )
                
                ab_data = ab_resp.json()
                
                ia_validation = best_profile.get("ia_validation", {})
                
                return TestResult(
                    test_id=test_id,
                    mode="fertirriego_ab",
                    scenario=scenario,
                    success=True,
                    response_time_ms=elapsed,
                    ia_validation_present=bool(ia_validation),
                    ia_is_valid=ia_validation.get("is_valid", True) if ia_validation else True,
                    ia_risk_level=ia_validation.get("risk_level", "low") if ia_validation else "low",
                    adjustments_count=len(ia_validation.get("adjusted_doses", {}) or {}) if ia_validation else 0,
                    recommendations=ia_validation.get("recommendations", [])[:3] if ia_validation else [],
                    fertilizers_count=len(ab_data.get("tank_a", {}).get("fertilizers", [])) + 
                                     len(ab_data.get("tank_b", {}).get("fertilizers", [])),
                    micronutrients_count=0,
                    acid_used=bool(ab_data.get("acid_treatment")),
                    total_cost=ab_data.get("total_fertilizer_cost", 0),
                    raw_response=ab_data
                )
                
        except Exception as e:
            return TestResult(
                test_id=test_id,
                mode="fertirriego_ab",
                scenario=scenario,
                success=False,
                response_time_ms=0,
                error_message=str(e)
            )
    
    async def run_all_tests(self):
        """Run all 100 tests."""
        print("="*80)
        print("IA GROWER V TEST SUITE - 100 Diverse Scenarios")
        print("="*80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        if not await self.authenticate():
            print("FAILED: Could not authenticate")
            return
        
        print("[1/4] Running 25 Hydroponics Direct Solution tests...")
        for i in range(1, 26):
            result = await self.run_hydroponics_direct_test(i)
            self.results.append(result)
            status = "OK" if result.success else "FAIL"
            print(f"  Test {i:02d}: {status} - {result.scenario} ({result.response_time_ms:.0f}ms)")
        
        print()
        print("[2/4] Running 25 Hydroponics A/B Tanks tests...")
        for i in range(26, 51):
            result = await self.run_hydroponics_ab_test(i)
            self.results.append(result)
            status = "OK" if result.success else "FAIL"
            print(f"  Test {i:02d}: {status} - {result.scenario} ({result.response_time_ms:.0f}ms)")
        
        print()
        print("[3/4] Running 25 FertiIrrigation Direct Solution tests...")
        for i in range(51, 76):
            result = await self.run_fertiirrigation_direct_test(i)
            self.results.append(result)
            status = "OK" if result.success else "FAIL"
            print(f"  Test {i:02d}: {status} - {result.scenario} ({result.response_time_ms:.0f}ms)")
        
        print()
        print("[4/4] Running 25 FertiIrrigation A/B Tanks tests...")
        for i in range(76, 101):
            result = await self.run_fertiirrigation_ab_test(i)
            self.results.append(result)
            status = "OK" if result.success else "FAIL"
            print(f"  Test {i:02d}: {status} - {result.scenario} ({result.response_time_ms:.0f}ms)")
        
        print()
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report."""
        print("="*80)
        print("REPORTE DE EVALUACION - IA GROWER V")
        print("="*80)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        modes = {
            "hydro_direct": "Hidroponia Solucion Directa",
            "hydro_ab": "Hidroponia Tanques A/B",
            "fertirriego_direct": "Fertirriego Solucion Directa",
            "fertirriego_ab": "Fertirriego Tanques A/B"
        }
        
        print("="*80)
        print("RESUMEN GENERAL")
        print("="*80)
        
        total = len(self.results)
        success = sum(1 for r in self.results if r.success)
        ia_present = sum(1 for r in self.results if r.ia_validation_present)
        ia_valid = sum(1 for r in self.results if r.ia_is_valid)
        with_adjustments = sum(1 for r in self.results if r.adjustments_count > 0)
        total_adjustments = sum(r.adjustments_count for r in self.results)
        avg_time = sum(r.response_time_ms for r in self.results) / total if total else 0
        
        print(f"Total de pruebas: {total}")
        print(f"Pruebas exitosas: {success} ({success/total*100:.1f}%)")
        print(f"Pruebas fallidas: {total - success} ({(total-success)/total*100:.1f}%)")
        print(f"IA GROWER V presente: {ia_present} ({ia_present/total*100:.1f}%)")
        print(f"IA valida recetas: {ia_valid} ({ia_valid/total*100:.1f}%)")
        print(f"Pruebas con ajustes: {with_adjustments} ({with_adjustments/total*100:.1f}%)")
        print(f"Total de ajustes aplicados: {total_adjustments}")
        print(f"Tiempo promedio: {avg_time:.0f}ms")
        print()
        
        for mode_key, mode_name in modes.items():
            mode_results = [r for r in self.results if r.mode == mode_key]
            if not mode_results:
                continue
            
            print("="*80)
            print(f"{mode_name.upper()}")
            print("="*80)
            
            m_total = len(mode_results)
            m_success = sum(1 for r in mode_results if r.success)
            m_ia_present = sum(1 for r in mode_results if r.ia_validation_present)
            m_adjustments = sum(1 for r in mode_results if r.adjustments_count > 0)
            m_total_adj = sum(r.adjustments_count for r in mode_results)
            m_avg_time = sum(r.response_time_ms for r in mode_results) / m_total if m_total else 0
            m_avg_ferts = sum(r.fertilizers_count for r in mode_results if r.success) / m_success if m_success else 0
            m_avg_micros = sum(r.micronutrients_count for r in mode_results if r.success) / m_success if m_success else 0
            m_with_acid = sum(1 for r in mode_results if r.acid_used)
            m_avg_cost = sum(r.total_cost for r in mode_results if r.success) / m_success if m_success else 0
            
            risk_counts = {}
            for r in mode_results:
                risk_counts[r.ia_risk_level] = risk_counts.get(r.ia_risk_level, 0) + 1
            
            print(f"Pruebas: {m_total}")
            print(f"Exitosas: {m_success} ({m_success/m_total*100:.1f}%)")
            print(f"IA presente: {m_ia_present} ({m_ia_present/m_total*100:.1f}%)")
            print(f"Con ajustes IA: {m_adjustments} ({m_adjustments/m_total*100:.1f}%)")
            print(f"Total ajustes: {m_total_adj}")
            print(f"Tiempo promedio: {m_avg_time:.0f}ms")
            print(f"Fertilizantes promedio: {m_avg_ferts:.1f}")
            print(f"Micronutrientes promedio: {m_avg_micros:.1f}")
            print(f"Con acido: {m_with_acid} ({m_with_acid/m_total*100:.1f}%)")
            print(f"Costo promedio: ${m_avg_cost:,.2f}")
            print(f"Niveles de riesgo: {risk_counts}")
            print()
            
            if m_total - m_success > 0:
                print("Errores encontrados:")
                for r in mode_results:
                    if not r.success:
                        print(f"  - Test {r.test_id}: {r.error_message[:100]}")
                print()
            
            if m_adjustments > 0:
                print("Ejemplos de ajustes IA:")
                count = 0
                for r in mode_results:
                    if r.adjustments_count > 0 and r.recommendations:
                        print(f"  - Test {r.test_id} ({r.scenario}):")
                        for rec in r.recommendations[:2]:
                            print(f"      {rec[:80]}...")
                        count += 1
                        if count >= 3:
                            break
                print()
        
        print("="*80)
        print("ANALISIS DE CALIDAD DE IA GROWER V")
        print("="*80)
        
        all_recommendations = []
        for r in self.results:
            all_recommendations.extend(r.recommendations)
        
        print(f"Total de recomendaciones generadas: {len(all_recommendations)}")
        
        recommendation_types = {
            "dosis": 0,
            "equilibrio": 0,
            "micronutriente": 0,
            "acido": 0,
            "compatibilidad": 0,
            "costo": 0,
            "otro": 0
        }
        
        for rec in all_recommendations:
            rec_lower = rec.lower()
            if "dosis" in rec_lower or "cantidad" in rec_lower or "gramo" in rec_lower:
                recommendation_types["dosis"] += 1
            elif "equilibrio" in rec_lower or "balance" in rec_lower or "relacion" in rec_lower:
                recommendation_types["equilibrio"] += 1
            elif "micro" in rec_lower or "hierro" in rec_lower or "zinc" in rec_lower or "boro" in rec_lower:
                recommendation_types["micronutriente"] += 1
            elif "acido" in rec_lower or "ph" in rec_lower:
                recommendation_types["acido"] += 1
            elif "compatib" in rec_lower or "precipit" in rec_lower:
                recommendation_types["compatibilidad"] += 1
            elif "costo" in rec_lower or "precio" in rec_lower or "econom" in rec_lower:
                recommendation_types["costo"] += 1
            else:
                recommendation_types["otro"] += 1
        
        print("\nCategorias de recomendaciones:")
        for cat, count in sorted(recommendation_types.items(), key=lambda x: -x[1]):
            if count > 0:
                print(f"  - {cat.capitalize()}: {count}")
        
        print()
        print("="*80)
        print("CONCLUSION")
        print("="*80)
        
        success_rate = success / total * 100 if total else 0
        ia_rate = ia_present / total * 100 if total else 0
        adjustment_rate = with_adjustments / total * 100 if total else 0
        
        if success_rate >= 95:
            print("EXCELENTE: Tasa de exito del sistema >= 95%")
        elif success_rate >= 80:
            print("BUENO: Tasa de exito del sistema >= 80%")
        else:
            print("MEJORAR: Tasa de exito del sistema < 80%")
        
        if ia_rate >= 90:
            print("EXCELENTE: IA GROWER V presente en >= 90% de pruebas")
        elif ia_rate >= 70:
            print("BUENO: IA GROWER V presente en >= 70% de pruebas")
        else:
            print("MEJORAR: IA GROWER V presente en < 70% de pruebas")
        
        if adjustment_rate >= 10:
            print(f"IA activa: {adjustment_rate:.1f}% de pruebas recibieron ajustes")
        else:
            print(f"IA conservadora: Solo {adjustment_rate:.1f}% de pruebas recibieron ajustes")
        
        print()
        print("="*80)
        print("FIN DEL REPORTE")
        print("="*80)


async def main():
    suite = IAGrowerVTestSuite()
    await suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

"""
Test suite for FertiIrrigation Manual Mode - 1000 Scenarios
Tests the optimization endpoint when users select their own fertilizers via HTTP API.
"""

import random
import json
import sys
import os
import httpx
from datetime import datetime
from typing import List, Dict, Any, Optional

BASE_URL = "http://localhost:8000"

FERTILIZER_SLUGS = [
    "urea_46_0_0",
    "sulfato_amonio_21_0_0_24s",
    "nitrato_amonio_34_0_0",
    "nitrato_calcio_granular",
    "can_27_0_0_ca",
    "uan_32_n_liquido",
    "dap_18_46_0",
    "map_cristalino",
    "map_11_52_0",
    "acido_fosforico_0_52_0",
    "fosfato_urea_17_44_0",
    "npk_17_17_17",
    "npk_15_15_15",
    "npk_13_13_21",
    "npk_8_24_24",
    "npk_20_10_10",
    "npk_12_24_12",
    "npk_10_30_10",
    "npk_20_20_20_foliar",
    "npk_12_12_36_foliar",
    "npk_15_05_35_foliar",
    "npk_10_52_10_foliar",
    "fe_edta_13",
    "fe_eddha_6",
    "zn_edta_14",
    "mn_edta_13",
    "cu_edta_14",
    "sulfato_zinc_23",
    "sulfato_manganeso_32",
    "sulfato_cobre_25",
    "acido_borico_17_b",
    "molibdato_sodio_39_mo",
    "quelato_hierro_eddha_6",
    "tradecorp_az",
    "multimicro_haifa",
    "ultrasol_micro_sqm",
    "acido_nitrico_60",
    "acido_sulfurico_98",
    "ats_12_0_0_26s",
    "kts_0_0_25_17s",
    "cats_6ca_10s",
]

CROPS = [
    "Tomate", "Chile", "Pepino", "Calabaza", "Melón", "Sandía", "Fresa", "Papa",
    "Maíz", "Trigo", "Sorgo", "Arroz", "Soya", "Frijol", "Alfalfa", "Avena",
    "Aguacate", "Mango", "Limón", "Naranja", "Uva", "Manzana", "Durazno",
    "Rosa", "Crisantemo", "Nochebuena", "Gerbera", "Orquídea"
]

GROWTH_STAGES = [
    "Germinación", "Plántula", "Vegetativo temprano", "Vegetativo",
    "Floración inicial", "Floración plena", "Fructificación",
    "Llenado de fruto", "Maduración", "Cosecha"
]

SOIL_TYPES = ["Arenoso", "Franco", "Arcilloso", "Franco-arcilloso", "Franco-arenoso", "Volcánico", "Orgánico", "Calcáreo"]

CURRENCIES = ["MXN", "USD", "EUR", "BRL", "PEN", "ARS", "CLP", "COP"]

def generate_random_deficit():
    """Generate random nutrient deficits based on realistic agronomic scenarios."""
    scenario_type = random.choice(["low", "medium", "high", "very_high", "micro_only", "macro_balanced"])
    
    if scenario_type == "low":
        return {
            "n_kg_ha": random.uniform(10, 50),
            "p2o5_kg_ha": random.uniform(5, 30),
            "k2o_kg_ha": random.uniform(10, 40),
            "ca_kg_ha": random.uniform(5, 20),
            "mg_kg_ha": random.uniform(2, 15),
            "s_kg_ha": random.uniform(2, 10),
        }
    elif scenario_type == "medium":
        return {
            "n_kg_ha": random.uniform(50, 150),
            "p2o5_kg_ha": random.uniform(30, 80),
            "k2o_kg_ha": random.uniform(40, 120),
            "ca_kg_ha": random.uniform(20, 60),
            "mg_kg_ha": random.uniform(10, 30),
            "s_kg_ha": random.uniform(10, 25),
        }
    elif scenario_type == "high":
        return {
            "n_kg_ha": random.uniform(150, 300),
            "p2o5_kg_ha": random.uniform(80, 150),
            "k2o_kg_ha": random.uniform(120, 250),
            "ca_kg_ha": random.uniform(60, 120),
            "mg_kg_ha": random.uniform(30, 60),
            "s_kg_ha": random.uniform(25, 50),
        }
    elif scenario_type == "very_high":
        return {
            "n_kg_ha": random.uniform(250, 400),
            "p2o5_kg_ha": random.uniform(100, 200),
            "k2o_kg_ha": random.uniform(200, 400),
            "ca_kg_ha": random.uniform(80, 150),
            "mg_kg_ha": random.uniform(40, 80),
            "s_kg_ha": random.uniform(40, 80),
        }
    elif scenario_type == "micro_only":
        return {
            "n_kg_ha": random.uniform(0, 20),
            "p2o5_kg_ha": random.uniform(0, 10),
            "k2o_kg_ha": random.uniform(0, 20),
            "ca_kg_ha": random.uniform(0, 10),
            "mg_kg_ha": random.uniform(0, 5),
            "s_kg_ha": random.uniform(0, 5),
        }
    else:
        base = random.uniform(80, 180)
        return {
            "n_kg_ha": base,
            "p2o5_kg_ha": base * 0.5,
            "k2o_kg_ha": base * 1.2,
            "ca_kg_ha": base * 0.4,
            "mg_kg_ha": base * 0.15,
            "s_kg_ha": base * 0.12,
        }

def generate_random_micro_deficit():
    """Generate random micronutrient deficits."""
    return {
        "fe_g_ha": random.uniform(0, 1500),
        "mn_g_ha": random.uniform(0, 800),
        "zn_g_ha": random.uniform(0, 600),
        "cu_g_ha": random.uniform(0, 200),
        "b_g_ha": random.uniform(0, 400),
        "mo_g_ha": random.uniform(0, 50),
    }

def select_random_fertilizers(min_count=3, max_count=12):
    """Select random fertilizers from the catalog."""
    count = random.randint(min_count, max_count)
    selected = random.sample(FERTILIZER_SLUGS, min(count, len(FERTILIZER_SLUGS)))
    return selected

def run_manual_optimization_test(scenario_id: int, client: httpx.Client, auth_headers: Dict[str, str]) -> Dict[str, Any]:
    """Run a single optimization test with random parameters."""
    deficit = generate_random_deficit()
    micro_deficit = generate_random_micro_deficit() if random.random() > 0.3 else None
    selected_slugs = select_random_fertilizers()
    area_ha = random.choice([0.5, 1, 2, 5, 10, 20, 50, 100])
    num_applications = random.choice([5, 8, 10, 12, 15, 20])
    currency = random.choice(CURRENCIES)
    irrigation_volume = random.choice([30, 50, 75, 100, 150, 200])
    
    crop = random.choice(CROPS)
    stage = random.choice(GROWTH_STAGES)
    soil_type = random.choice(SOIL_TYPES)
    
    acid_treatment = None
    if random.random() > 0.6:
        acid_treatment = {
            "acid_type": random.choice(["phosphoric", "sulfuric", "nitric", "citric"]),
            "ml_per_1000L": random.uniform(50, 500),
            "cost_mxn_per_1000L": random.uniform(20, 200),
            "n_g_per_1000L": random.uniform(0, 50) if random.random() > 0.5 else 0,
            "p_g_per_1000L": random.uniform(0, 100) if random.random() > 0.5 else 0,
            "s_g_per_1000L": random.uniform(0, 80) if random.random() > 0.5 else 0,
        }
    
    payload = {
        "deficit": deficit,
        "area_ha": area_ha,
        "num_applications": num_applications,
        "selected_fertilizer_slugs": selected_slugs,
        "currency": currency,
        "irrigation_volume_m3_ha": irrigation_volume,
    }
    
    if micro_deficit:
        payload["micro_deficit"] = micro_deficit
    if acid_treatment:
        payload["acid_treatment"] = acid_treatment
    
    errors = []
    warnings = []
    result = None
    status_code = None
    response_time_ms = 0
    
    try:
        import time
        start = time.time()
        response = client.post(
            f"{BASE_URL}/api/fertiirrigation/optimize",
            json=payload,
            headers=auth_headers,
            timeout=30.0
        )
        response_time_ms = (time.time() - start) * 1000
        status_code = response.status_code
        
        if response.status_code != 200:
            errors.append(f"HTTP {response.status_code}: {response.text[:200]}")
        else:
            result = response.json()
            
            profiles = result.get("profiles", [])
            if not profiles:
                errors.append("No profiles returned")
            else:
                for profile in profiles:
                    profile_type = profile.get("profile_type", "unknown")
                    fertilizers = profile.get("fertilizers", [])
                    coverage = profile.get("coverage", {})
                    total_cost = profile.get("total_cost_ha", 0)
                    
                    if not fertilizers and sum(deficit.values()) > 20:
                        warnings.append(f"{profile_type}: No fertilizers despite significant deficit")
                    
                    for nutrient, pct in coverage.items():
                        if pct < 0:
                            errors.append(f"{profile_type}: Negative coverage for {nutrient}: {pct}%")
                        if pct > 200:
                            warnings.append(f"{profile_type}: Very high coverage for {nutrient}: {pct}%")
                    
                    if total_cost < 0:
                        errors.append(f"{profile_type}: Negative cost: {total_cost}")
                    
                    for fert in fertilizers:
                        dose = fert.get("dose_kg_ha", 0)
                        if dose < 0:
                            errors.append(f"{profile_type}: Negative dose for {fert.get('fertilizer_name')}: {dose}")
                        if dose > 5000:
                            warnings.append(f"{profile_type}: Very high dose for {fert.get('fertilizer_name')}: {dose} kg/ha")
                        
                        cost_ha = fert.get("cost_ha", 0)
                        if cost_ha < 0:
                            errors.append(f"{profile_type}: Negative cost for {fert.get('fertilizer_name')}: {cost_ha}")
                            
    except httpx.TimeoutException:
        errors.append("Request timeout (>30s)")
    except Exception as e:
        errors.append(f"Exception: {str(e)}")
    
    return {
        "scenario_id": scenario_id,
        "crop": crop,
        "stage": stage,
        "soil_type": soil_type,
        "currency": currency,
        "num_fertilizers_selected": len(selected_slugs),
        "area_ha": area_ha,
        "num_applications": num_applications,
        "has_acid": acid_treatment is not None,
        "has_micro_deficit": micro_deficit is not None,
        "deficit_total": sum(deficit.values()),
        "errors": errors,
        "warnings": warnings,
        "success": len(errors) == 0,
        "status_code": status_code,
        "response_time_ms": response_time_ms,
        "profiles_count": len(result.get("profiles", [])) if result else 0
    }

def login_test_user(client: httpx.Client) -> Optional[Dict[str, str]]:
    """Login and get auth headers. Returns None if login fails."""
    try:
        login_data = {
            "email": "test@agridoser.com",
            "password": "testpassword123"
        }
        response = client.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if response.status_code == 200:
            token = response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        else:
            print(f"Login failed, trying to register: {response.status_code}")
            response_try_register = client.post(
                f"{BASE_URL}/api/auth/register",
                json={
                    "email": "test@agridoser.com",
                    "password": "testpassword123",
                    "full_name": "Test User"
                }
            )
            if response_try_register.status_code in [200, 201]:
                response = client.post(f"{BASE_URL}/api/auth/login", json=login_data)
                if response.status_code == 200:
                    token = response.json().get("access_token")
                    return {"Authorization": f"Bearer {token}"}
                else:
                    print(f"Login after register failed: {response.status_code} - {response.text[:200]}")
            else:
                print(f"Register failed: {response_try_register.status_code} - {response_try_register.text[:200]}")
    except Exception as e:
        print(f"Login error: {e}")
    return None

def run_all_tests(num_tests=1000):
    """Run all tests and collect results."""
    print(f"\n{'='*70}")
    print(f"FertiIrrigation Manual Mode - {num_tests} Scenario Test Suite")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")
    
    with httpx.Client(timeout=30.0) as client:
        print("Logging in...")
        auth_headers = login_test_user(client)
        if not auth_headers:
            print("ERROR: Could not authenticate. Creating test user...")
            register_data = {
                "email": "fertiirrigation_test@agridoser.com",
                "password": "TestPassword123!",
                "nombres": "Test",
                "apellido_paterno": "User",
                "apellido_materno": "Fertirriego",
                "phone": "+525551234567",
                "has_whatsapp": False
            }
            reg_response = client.post(f"{BASE_URL}/api/auth/register", json=register_data)
            print(f"Registration response: {reg_response.status_code}")
            
            login_data = {"email": register_data["email"], "password": register_data["password"]}
            login_response = client.post(f"{BASE_URL}/api/auth/login", json=login_data)
            if login_response.status_code == 200:
                token = login_response.json().get("access_token")
                auth_headers = {"Authorization": f"Bearer {token}"}
            else:
                print(f"Still cannot login: {login_response.status_code}")
                return {"total": 0, "passed": 0, "failed": 0, "with_warnings": 0, "pass_rate": 0, "results": []}
        
        print("Authentication successful. Starting tests...\n")
        
        results = []
        passed = 0
        failed = 0
        with_warnings = 0
        total_response_time = 0
        
        for i in range(num_tests):
            result = run_manual_optimization_test(i + 1, client, auth_headers)
            results.append(result)
            total_response_time += result.get("response_time_ms", 0)
            
            if result["success"]:
                passed += 1
                if result["warnings"]:
                    with_warnings += 1
            else:
                failed += 1
            
            if (i + 1) % 100 == 0:
                avg_time = total_response_time / (i + 1)
                print(f"Progress: {i + 1}/{num_tests} tests ({passed} passed, {failed} failed, avg {avg_time:.0f}ms)")
            
            import time
            time.sleep(0.35)
    
    avg_response_time = total_response_time / num_tests if num_tests > 0 else 0
    
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}")
    print(f"Total Tests: {num_tests}")
    print(f"Passed: {passed} ({100*passed/num_tests:.1f}%)")
    print(f"Failed: {failed} ({100*failed/num_tests:.1f}%)")
    print(f"With Warnings: {with_warnings} ({100*with_warnings/num_tests:.1f}%)")
    print(f"Avg Response Time: {avg_response_time:.1f}ms")
    
    if failed > 0:
        print(f"\n{'='*70}")
        print("ERROR ANALYSIS")
        print(f"{'='*70}")
        
        error_types = {}
        for r in results:
            for err in r["errors"]:
                err_key = err.split(":")[0] if ":" in err else err[:50]
                error_types[err_key] = error_types.get(err_key, 0) + 1
        
        for err_type, count in sorted(error_types.items(), key=lambda x: -x[1])[:10]:
            print(f"  {count}x: {err_type}")
    
    if with_warnings > 0:
        print(f"\n{'='*70}")
        print("WARNING ANALYSIS")
        print(f"{'='*70}")
        
        warning_types = {}
        for r in results:
            for warn in r["warnings"]:
                warn_key = warn.split(":")[0] if ":" in warn else warn[:50]
                warning_types[warn_key] = warning_types.get(warn_key, 0) + 1
        
        for warn_type, count in sorted(warning_types.items(), key=lambda x: -x[1])[:10]:
            print(f"  {count}x: {warn_type}")
    
    print(f"\n{'='*70}")
    print("STATISTICS BY CATEGORY")
    print(f"{'='*70}")
    
    currency_stats = {}
    for r in results:
        c = r["currency"]
        if c not in currency_stats:
            currency_stats[c] = {"total": 0, "passed": 0}
        currency_stats[c]["total"] += 1
        if r["success"]:
            currency_stats[c]["passed"] += 1
    
    print("\nBy Currency:")
    for c, stats in sorted(currency_stats.items()):
        pct = 100 * stats["passed"] / stats["total"]
        print(f"  {c}: {stats['passed']}/{stats['total']} ({pct:.1f}%)")
    
    fert_count_stats = {}
    for r in results:
        fc = r["num_fertilizers_selected"]
        if fc not in fert_count_stats:
            fert_count_stats[fc] = {"total": 0, "passed": 0}
        fert_count_stats[fc]["total"] += 1
        if r["success"]:
            fert_count_stats[fc]["passed"] += 1
    
    print("\nBy Fertilizer Count:")
    for fc in sorted(fert_count_stats.keys()):
        stats = fert_count_stats[fc]
        pct = 100 * stats["passed"] / stats["total"]
        print(f"  {fc} fertilizers: {stats['passed']}/{stats['total']} ({pct:.1f}%)")
    
    if failed > 0:
        print(f"\n{'='*70}")
        print("SAMPLE FAILURES (first 5)")
        print(f"{'='*70}")
        
        failure_count = 0
        for r in results:
            if not r["success"] and failure_count < 5:
                print(f"\nScenario {r['scenario_id']}:")
                print(f"  Crop: {r['crop']}, Stage: {r['stage']}")
                print(f"  Currency: {r['currency']}, Fertilizers: {r['num_fertilizers_selected']}")
                print(f"  Status: {r['status_code']}, Time: {r['response_time_ms']:.0f}ms")
                print(f"  Errors: {r['errors'][:3]}")
                failure_count += 1
    
    print(f"\n{'='*70}")
    print(f"Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")
    
    return {
        "total": num_tests,
        "passed": passed,
        "failed": failed,
        "with_warnings": with_warnings,
        "pass_rate": 100 * passed / num_tests if num_tests > 0 else 0,
        "avg_response_time_ms": avg_response_time,
        "results": results
    }

if __name__ == "__main__":
    num_tests = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    summary = run_all_tests(num_tests)
    
    with open("/tmp/fertiirrigation_manual_test_results.json", "w") as f:
        json.dump({
            "summary": {
                "total": summary["total"],
                "passed": summary["passed"],
                "failed": summary["failed"],
                "with_warnings": summary["with_warnings"],
                "pass_rate": summary["pass_rate"],
                "avg_response_time_ms": summary.get("avg_response_time_ms", 0)
            },
            "failures": [r for r in summary["results"] if not r["success"]],
            "warnings": [r for r in summary["results"] if r["warnings"]]
        }, f, indent=2)
    
    print(f"Detailed results saved to /tmp/fertiirrigation_manual_test_results.json")
    
    sys.exit(0 if summary["failed"] == 0 else 1)

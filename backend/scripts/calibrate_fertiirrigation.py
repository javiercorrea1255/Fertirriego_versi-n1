#!/usr/bin/env python3
"""
FertiIrrigation Optimizer Calibration Script V2
Runs 1000 scenarios with balancer metrics to transform optimizer from "input adder" to "nutrient balancer".

Metrics tracked:
- Coverage deviation per nutrient (target: 100±5% for Balanced/Complete)
- Overshoot occurrences (>110% coverage)
- Fertilizer diversity index
- Warning severity counts
- Micronutrient coverage completeness
- Cost hierarchy compliance
"""

import sys
import os
import random
import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.fertiirrigation_optimizer import (
    FertiIrrigationOptimizer,
    NutrientDeficit,
    MicronutrientDeficit,
)

DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

CONFIG_PATH = Path(__file__).parent.parent / "app" / "data" / "calibration_config.json"
CHECKPOINT_DIR = Path(__file__).parent / "calibration_checkpoints"
CHECKPOINT_DIR.mkdir(exist_ok=True)


def load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    return {}


@dataclass
class BalancerMetrics:
    coverage_deviation_avg: float = 0.0
    coverage_deviation_max: float = 0.0
    overshoot_count: int = 0
    overshoot_nutrients: List[str] = field(default_factory=list)
    undershoot_count: int = 0
    undershoot_nutrients: List[str] = field(default_factory=list)
    diversity_index: float = 0.0
    warning_count: int = 0
    critical_warning_count: int = 0
    micronutrient_coverage_pct: float = 0.0
    is_balanced: bool = False


@dataclass
class CalibrationResult:
    scenario_id: int
    profile_type: str
    num_fertilizers: int
    total_cost_ha: float
    grand_total_ha: float
    coverage: Dict[str, float]
    micronutrients_count: int
    micronutrient_cost: float
    warnings: List[str]
    passed: bool
    failure_reason: str = ""
    balancer_metrics: BalancerMetrics = field(default_factory=BalancerMetrics)


@dataclass
class ProfileStats:
    passed: int = 0
    failed: int = 0
    costs: List[float] = field(default_factory=list)
    grand_totals: List[float] = field(default_factory=list)
    fert_counts: List[int] = field(default_factory=list)
    micro_counts: List[int] = field(default_factory=list)
    coverage_deviations: List[float] = field(default_factory=list)
    overshoot_occurrences: int = 0
    undershoot_occurrences: int = 0
    warning_counts: List[int] = field(default_factory=list)
    diversity_indices: List[float] = field(default_factory=list)
    balanced_count: int = 0
    failure_reasons: Dict[str, int] = field(default_factory=dict)


def calculate_balancer_metrics(
    result, 
    config: Dict[str, Any],
    micro_deficit: Optional[MicronutrientDeficit] = None
) -> BalancerMetrics:
    metrics = BalancerMetrics()
    profile_config = config.get("profile_targets", {}).get(result.profile_type, {})
    thresholds = config.get("balancer_thresholds", {})
    
    target_coverage = profile_config.get("target_coverage_pct", 100)
    tolerance = profile_config.get("coverage_tolerance_pct", 5)
    max_overshoot = thresholds.get("max_overshoot_ratio", 1.2) * 100
    
    coverages = list(result.coverage.values())
    if coverages:
        deviations = [abs(c - target_coverage) for c in coverages]
        metrics.coverage_deviation_avg = sum(deviations) / len(deviations)
        metrics.coverage_deviation_max = max(deviations)
        
        for nutrient, cov in result.coverage.items():
            if cov > 110:
                metrics.overshoot_count += 1
                metrics.overshoot_nutrients.append(f"{nutrient}:{cov:.1f}%")
            elif cov < profile_config.get("min_coverage_pct", 75):
                metrics.undershoot_count += 1
                metrics.undershoot_nutrients.append(f"{nutrient}:{cov:.1f}%")
    
    if result.fertilizers:
        nutrient_sources = {}
        for fert in result.fertilizers:
            nutrient_map = {
                "N": getattr(fert, 'n_contribution', 0),
                "P2O5": getattr(fert, 'p2o5_contribution', 0),
                "K2O": getattr(fert, 'k2o_contribution', 0),
                "Ca": getattr(fert, 'ca_contribution', 0),
                "Mg": getattr(fert, 'mg_contribution', 0),
                "S": getattr(fert, 's_contribution', 0),
            }
            for nutrient, contribution in nutrient_map.items():
                if contribution and contribution > 0:
                    if nutrient not in nutrient_sources:
                        nutrient_sources[nutrient] = 0
                    nutrient_sources[nutrient] += 1
        
        total_sources = sum(nutrient_sources.values())
        num_nutrients = len(nutrient_sources)
        if num_nutrients > 0 and total_sources > 0:
            avg_sources_per_nutrient = total_sources / num_nutrients
            metrics.diversity_index = min(1.0, avg_sources_per_nutrient / 3)
    
    if result.warnings:
        for warning in result.warnings:
            if any(kw in warning.lower() for kw in ["crítico", "prohibid", "incompatib"]):
                metrics.critical_warning_count += 1
            else:
                metrics.warning_count += 1
    
    if micro_deficit and hasattr(result, 'micronutrients') and result.micronutrients:
        total_micro_needed = sum([
            micro_deficit.fe_g_ha, micro_deficit.mn_g_ha, micro_deficit.zn_g_ha,
            micro_deficit.cu_g_ha, micro_deficit.b_g_ha, micro_deficit.mo_g_ha
        ])
        if total_micro_needed > 0:
            covered_count = len(result.micronutrients)
            total_possible = sum(1 for v in [
                micro_deficit.fe_g_ha, micro_deficit.mn_g_ha, micro_deficit.zn_g_ha,
                micro_deficit.cu_g_ha, micro_deficit.b_g_ha, micro_deficit.mo_g_ha
            ] if v > 0)
            metrics.micronutrient_coverage_pct = (covered_count / total_possible * 100) if total_possible > 0 else 100
        else:
            metrics.micronutrient_coverage_pct = 100
    else:
        metrics.micronutrient_coverage_pct = 100
    
    ideal_deviation = thresholds.get("ideal_coverage_deviation_pct", 5.0)
    max_warnings = thresholds.get("max_warnings_per_profile", 3)
    
    metrics.is_balanced = (
        metrics.coverage_deviation_avg <= ideal_deviation and
        metrics.overshoot_count == 0 and
        metrics.undershoot_count == 0 and
        metrics.critical_warning_count == 0 and
        metrics.warning_count <= max_warnings
    )
    
    return metrics


def validate_result(
    result, 
    profile_type: str, 
    scenario_id: int,
    config: Dict[str, Any],
    micro_deficit: Optional[MicronutrientDeficit] = None
) -> CalibrationResult:
    profile_config = config.get("profile_targets", {}).get(profile_type, {})
    
    limits = {
        "min_fert": profile_config.get("min_fertilizers", 3),
        "max_fert": profile_config.get("max_fertilizers", 12),
        "min_cov": profile_config.get("min_coverage_pct", 75),
        "max_cov": profile_config.get("max_coverage_pct", 120),
    }
    
    num_ferts = len(result.fertilizers)
    all_coverages = list(result.coverage.values())
    min_cov = min(all_coverages) if all_coverages else 0
    max_cov = max(all_coverages) if all_coverages else 0
    
    passed = True
    failure_reason = ""
    
    if num_ferts < limits["min_fert"]:
        passed = False
        failure_reason = f"Too few fertilizers: {num_ferts} < {limits['min_fert']}"
    elif num_ferts > limits["max_fert"]:
        passed = False
        failure_reason = f"Too many fertilizers: {num_ferts} > {limits['max_fert']}"
    
    if min_cov < limits["min_cov"]:
        passed = False
        failure_reason = f"Coverage too low: {min_cov:.1f}% < {limits['min_cov']}%"
    
    if max_cov > limits["max_cov"]:
        passed = False
        failure_reason = f"Coverage too high: {max_cov:.1f}% > {limits['max_cov']}%"
    
    micro_count = len(result.micronutrients) if hasattr(result, 'micronutrients') else 0
    micro_cost = result.micronutrient_cost_ha if hasattr(result, 'micronutrient_cost_ha') else 0
    
    grand_total = result.grand_total_ha if hasattr(result, 'grand_total_ha') else result.total_cost_ha
    
    balancer_metrics = calculate_balancer_metrics(result, config, micro_deficit)
    
    return CalibrationResult(
        scenario_id=scenario_id,
        profile_type=profile_type,
        num_fertilizers=num_ferts,
        total_cost_ha=result.total_cost_ha,
        grand_total_ha=grand_total,
        coverage=result.coverage,
        micronutrients_count=micro_count,
        micronutrient_cost=micro_cost,
        warnings=result.warnings,
        passed=passed,
        failure_reason=failure_reason,
        balancer_metrics=balancer_metrics,
    )


def generate_random_deficit(config: Dict[str, Any]) -> NutrientDeficit:
    ranges = config.get("scenario_distribution", {}).get("deficit_ranges", {})
    
    return NutrientDeficit(
        n_kg_ha=random.uniform(*ranges.get("n_kg_ha", [50, 280])),
        p2o5_kg_ha=random.uniform(*ranges.get("p2o5_kg_ha", [20, 150])),
        k2o_kg_ha=random.uniform(*ranges.get("k2o_kg_ha", [40, 250])),
        ca_kg_ha=random.uniform(*ranges.get("ca_kg_ha", [10, 100])),
        mg_kg_ha=random.uniform(*ranges.get("mg_kg_ha", [5, 50])),
        s_kg_ha=random.uniform(*ranges.get("s_kg_ha", [5, 60])),
    )


def generate_random_micro_deficit() -> MicronutrientDeficit:
    return MicronutrientDeficit(
        fe_g_ha=random.uniform(0, 1500),
        mn_g_ha=random.uniform(0, 800),
        zn_g_ha=random.uniform(0, 600),
        cu_g_ha=random.uniform(0, 150),
        b_g_ha=random.uniform(0, 300),
        mo_g_ha=random.uniform(0, 30),
    )


def save_checkpoint(
    batch_num: int,
    profile_stats: Dict[str, ProfileStats],
    results: List[CalibrationResult],
    errors: List[Dict],
    config: Dict[str, Any]
):
    checkpoint = {
        "batch": batch_num,
        "timestamp": datetime.now().isoformat(),
        "scenarios_completed": batch_num * 200,
        "profile_stats": {},
        "errors_count": len(errors),
        "config_hash": hash(json.dumps(config, sort_keys=True)),
    }
    
    for profile, stats in profile_stats.items():
        total = stats.passed + stats.failed
        checkpoint["profile_stats"][profile] = {
            "passed": stats.passed,
            "failed": stats.failed,
            "pass_rate": (stats.passed / total * 100) if total > 0 else 0,
            "avg_cost": sum(stats.costs) / len(stats.costs) if stats.costs else 0,
            "avg_deviation": sum(stats.coverage_deviations) / len(stats.coverage_deviations) if stats.coverage_deviations else 0,
            "overshoot_rate": (stats.overshoot_occurrences / total * 100) if total > 0 else 0,
            "balanced_rate": (stats.balanced_count / total * 100) if total > 0 else 0,
            "top_failures": dict(sorted(stats.failure_reasons.items(), key=lambda x: -x[1])[:5]),
        }
    
    checkpoint_file = CHECKPOINT_DIR / f"checkpoint_batch_{batch_num}.json"
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    
    print(f"  [Checkpoint saved: {checkpoint_file.name}]")


def run_calibration(num_scenarios: int = 1000, batch_size: int = 200, seed: int = 42):
    random.seed(seed)
    config = load_config()
    
    print(f"\n{'='*70}")
    print(f"FertiIrrigation Optimizer Calibration V2 - BALANCER MODE")
    print(f"Scenarios: {num_scenarios} | Batch Size: {batch_size} | Seed: {seed}")
    print(f"{'='*70}\n")
    
    db = SessionLocal()
    optimizer = FertiIrrigationOptimizer(db=db, user_id=None, currency="MXN")
    
    results: List[CalibrationResult] = []
    profile_stats = {p: ProfileStats() for p in ["economic", "balanced", "complete"]}
    errors = []
    cost_hierarchy_violations = 0
    
    start_time = time.time()
    
    for i in range(num_scenarios):
        batch_num = (i // batch_size) + 1
        
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            remaining = (num_scenarios - i - 1) / rate if rate > 0 else 0
            print(f"Progress: {i + 1}/{num_scenarios} ({(i+1)/num_scenarios*100:.1f}%) "
                  f"| Elapsed: {elapsed:.0f}s | ETA: {remaining:.0f}s")
        
        if (i + 1) % batch_size == 0 and i > 0:
            save_checkpoint(batch_num, profile_stats, results, errors, config)
        
        try:
            deficit = generate_random_deficit(config)
            micro_deficit = generate_random_micro_deficit()
            area_ha = random.uniform(
                *config.get("scenario_distribution", {}).get("area_range_ha", [0.5, 15])
            )
            num_apps = random.randint(
                *config.get("scenario_distribution", {}).get("applications_range", [5, 25])
            )
            
            optimization_results = optimizer.optimize(
                deficit=deficit,
                area_ha=area_ha,
                num_applications=num_apps,
                micro_deficit=micro_deficit,
            )
            
            scenario_costs = {}
            
            for result in optimization_results:
                cal_result = validate_result(
                    result, result.profile_type, i + 1, config, micro_deficit
                )
                results.append(cal_result)
                
                scenario_costs[result.profile_type] = cal_result.grand_total_ha
                
                stats = profile_stats[result.profile_type]
                if cal_result.passed:
                    stats.passed += 1
                else:
                    stats.failed += 1
                    reason_key = cal_result.failure_reason.split(":")[0] if cal_result.failure_reason else "Unknown"
                    stats.failure_reasons[reason_key] = stats.failure_reasons.get(reason_key, 0) + 1
                
                stats.costs.append(result.total_cost_ha)
                stats.grand_totals.append(cal_result.grand_total_ha)
                stats.fert_counts.append(len(result.fertilizers))
                stats.micro_counts.append(cal_result.micronutrients_count)
                
                bm = cal_result.balancer_metrics
                stats.coverage_deviations.append(bm.coverage_deviation_avg)
                stats.warning_counts.append(bm.warning_count + bm.critical_warning_count)
                stats.diversity_indices.append(bm.diversity_index)
                
                if bm.overshoot_count > 0:
                    stats.overshoot_occurrences += 1
                if bm.undershoot_count > 0:
                    stats.undershoot_occurrences += 1
                if bm.is_balanced:
                    stats.balanced_count += 1
            
            eco = scenario_costs.get("economic", 0)
            bal = scenario_costs.get("balanced", 0)
            com = scenario_costs.get("complete", 0)
            if not (eco <= bal <= com):
                cost_hierarchy_violations += 1
                
        except Exception as e:
            errors.append({"scenario": i + 1, "error": str(e)})
    
    db.close()
    
    elapsed_total = time.time() - start_time
    
    print(f"\n{'='*70}")
    print("CALIBRATION RESULTS - BALANCER METRICS")
    print(f"{'='*70}\n")
    
    for profile, stats in profile_stats.items():
        total = stats.passed + stats.failed
        pass_rate = (stats.passed / total * 100) if total > 0 else 0
        avg_cost = sum(stats.costs) / len(stats.costs) if stats.costs else 0
        avg_grand = sum(stats.grand_totals) / len(stats.grand_totals) if stats.grand_totals else 0
        avg_ferts = sum(stats.fert_counts) / len(stats.fert_counts) if stats.fert_counts else 0
        avg_deviation = sum(stats.coverage_deviations) / len(stats.coverage_deviations) if stats.coverage_deviations else 0
        overshoot_rate = (stats.overshoot_occurrences / total * 100) if total > 0 else 0
        balanced_rate = (stats.balanced_count / total * 100) if total > 0 else 0
        avg_warnings = sum(stats.warning_counts) / len(stats.warning_counts) if stats.warning_counts else 0
        avg_diversity = sum(stats.diversity_indices) / len(stats.diversity_indices) if stats.diversity_indices else 0
        
        success_criteria = config.get("success_criteria", {}).get(profile, {})
        min_pass = success_criteria.get("min_pass_rate_pct", 85)
        max_overshoot = success_criteria.get("max_overshoot_occurrences_pct", 10)
        
        status = "✓" if pass_rate >= min_pass and overshoot_rate <= max_overshoot else "✗"
        
        print(f"\n{profile.upper()} Profile {status}:")
        print(f"  Pass Rate: {pass_rate:.1f}% ({stats.passed}/{total}) [target: ≥{min_pass}%]")
        print(f"  Avg Fertilizers: {avg_ferts:.1f}")
        print(f"  Avg Cost/ha: ${avg_cost:.2f} | Grand Total: ${avg_grand:.2f}")
        print(f"  --- BALANCER METRICS ---")
        print(f"  Avg Coverage Deviation: {avg_deviation:.2f}% [ideal: <5%]")
        print(f"  Overshoot Rate: {overshoot_rate:.1f}% [target: <{max_overshoot}%]")
        print(f"  Balanced Scenarios: {balanced_rate:.1f}%")
        print(f"  Avg Warnings: {avg_warnings:.2f}")
        print(f"  Diversity Index: {avg_diversity:.2f}")
        
        if stats.failure_reasons:
            print(f"  Top Failures: {dict(sorted(stats.failure_reasons.items(), key=lambda x: -x[1])[:3])}")
    
    if errors:
        print(f"\n\nERRORS ({len(errors)}):")
        for err in errors[:5]:
            print(f"  Scenario {err['scenario']}: {err['error'][:80]}")
    
    total_passed = sum(s.passed for s in profile_stats.values())
    total_tests = sum(s.passed + s.failed for s in profile_stats.values())
    overall_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    total_balanced = sum(s.balanced_count for s in profile_stats.values())
    balanced_rate = (total_balanced / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Overall Pass Rate: {overall_rate:.1f}% ({total_passed}/{total_tests})")
    print(f"Balanced Scenarios: {balanced_rate:.1f}% ({total_balanced}/{total_tests})")
    print(f"Cost Hierarchy Violations: {cost_hierarchy_violations}/{num_scenarios} ({cost_hierarchy_violations/num_scenarios*100:.1f}%)")
    print(f"Errors: {len(errors)}")
    print(f"Total Time: {elapsed_total:.1f}s ({elapsed_total/num_scenarios*1000:.1f}ms per scenario)")
    
    print("\nCOST HIERARCHY CHECK:")
    eco_avg = sum(profile_stats["economic"].grand_totals) / len(profile_stats["economic"].grand_totals) if profile_stats["economic"].grand_totals else 0
    bal_avg = sum(profile_stats["balanced"].grand_totals) / len(profile_stats["balanced"].grand_totals) if profile_stats["balanced"].grand_totals else 0
    com_avg = sum(profile_stats["complete"].grand_totals) / len(profile_stats["complete"].grand_totals) if profile_stats["complete"].grand_totals else 0
    
    print(f"  Economic avg: ${eco_avg:.2f}")
    print(f"  Balanced avg: ${bal_avg:.2f}")
    print(f"  Complete avg: ${com_avg:.2f}")
    
    if eco_avg <= bal_avg <= com_avg:
        print("  ✓ Cost hierarchy correct: Economic ≤ Balanced ≤ Complete")
    else:
        print("  ✗ Cost hierarchy VIOLATED!")
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "seed": seed,
        "num_scenarios": num_scenarios,
        "elapsed_seconds": elapsed_total,
        "overall_pass_rate": overall_rate,
        "balanced_rate": balanced_rate,
        "cost_hierarchy_violations": cost_hierarchy_violations,
        "errors": len(errors),
        "profile_results": {},
    }
    
    for profile, stats in profile_stats.items():
        total = stats.passed + stats.failed
        report["profile_results"][profile] = {
            "passed": stats.passed,
            "failed": stats.failed,
            "pass_rate": (stats.passed / total * 100) if total > 0 else 0,
            "avg_cost_ha": sum(stats.costs) / len(stats.costs) if stats.costs else 0,
            "avg_grand_total_ha": sum(stats.grand_totals) / len(stats.grand_totals) if stats.grand_totals else 0,
            "avg_fertilizers": sum(stats.fert_counts) / len(stats.fert_counts) if stats.fert_counts else 0,
            "avg_coverage_deviation": sum(stats.coverage_deviations) / len(stats.coverage_deviations) if stats.coverage_deviations else 0,
            "overshoot_rate": (stats.overshoot_occurrences / total * 100) if total > 0 else 0,
            "balanced_rate": (stats.balanced_count / total * 100) if total > 0 else 0,
            "avg_warnings": sum(stats.warning_counts) / len(stats.warning_counts) if stats.warning_counts else 0,
            "diversity_index": sum(stats.diversity_indices) / len(stats.diversity_indices) if stats.diversity_indices else 0,
            "top_failures": dict(sorted(stats.failure_reasons.items(), key=lambda x: -x[1])[:5]),
        }
    
    report_file = CHECKPOINT_DIR / "calibration_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n[Report saved: {report_file}]")
    print(f"{'='*70}\n")
    
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FertiIrrigation Calibration V2")
    parser.add_argument("--scenarios", type=int, default=1000, help="Number of scenarios")
    parser.add_argument("--batch", type=int, default=200, help="Batch size for checkpoints")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()
    
    run_calibration(num_scenarios=args.scenarios, batch_size=args.batch, seed=args.seed)

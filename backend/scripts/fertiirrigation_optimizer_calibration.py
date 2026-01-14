#!/usr/bin/env python3
"""
FertiIrrigation Optimizer Calibration Suite
============================================
Simulates multiple agronomic scenarios to find the optimal algorithm configuration.

Based on agronomic best practices:
- Liebig's Law of the Minimum: Crop yield is limited by the scarcest nutrient
- 4R Nutrient Stewardship: Right source, rate, time, place
- Balanced fertilization: All nutrients should reach acceptable levels before maximizing any

Metrics evaluated:
1. Min Coverage: The lowest nutrient coverage (Liebig constraint)
2. Liebig Balance: Standard deviation across nutrients (lower = better balance)
3. Cost Efficiency: Cost per average coverage point
4. Profile Differentiation: Complete > Balanced > Economic coverage
"""

import json
import random
import statistics
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

NUTRIENT_PRIORITY = ['N', 'K2O', 'P2O5', 'Ca', 'Mg', 'S']

# ============================================================================
# TEST SCENARIO GENERATOR
# ============================================================================

@dataclass
class TestScenario:
    """Represents a single test case for the optimizer."""
    name: str
    crop: str
    deficits: Dict[str, float]
    water_hco3_meq: float
    water_cl_meq: float
    budget_level: str  # 'low', 'medium', 'high'
    area_ha: float
    num_applications: int
    expected_challenge: str  # Description of what makes this scenario challenging
    
    def to_dict(self):
        return asdict(self)


def generate_test_scenarios() -> List[TestScenario]:
    """Generate diverse test scenarios covering edge cases and common situations."""
    scenarios = []
    
    # === SCENARIO 1: Standard Maize - Balanced deficits ===
    scenarios.append(TestScenario(
        name="maize_standard",
        crop="Maíz",
        deficits={'N': 180, 'P2O5': 80, 'K2O': 150, 'Ca': 40, 'Mg': 30, 'S': 25},
        water_hco3_meq=4.8,
        water_cl_meq=0.5,
        budget_level='medium',
        area_ha=50,
        num_applications=10,
        expected_challenge="Balanced deficits - algorithm should cover all nutrients evenly"
    ))
    
    # === SCENARIO 2: High Mg Deficit ===
    scenarios.append(TestScenario(
        name="maize_high_mg_deficit",
        crop="Maíz",
        deficits={'N': 120, 'P2O5': 60, 'K2O': 100, 'Ca': 30, 'Mg': 80, 'S': 20},
        water_hco3_meq=3.0,
        water_cl_meq=0.3,
        budget_level='medium',
        area_ha=30,
        num_applications=8,
        expected_challenge="High Mg deficit - tests if algorithm prioritizes scarce nutrients"
    ))
    
    # === SCENARIO 3: High Ca Deficit ===
    scenarios.append(TestScenario(
        name="tomato_high_ca",
        crop="Tomate",
        deficits={'N': 200, 'P2O5': 100, 'K2O': 250, 'Ca': 120, 'Mg': 40, 'S': 30},
        water_hco3_meq=6.0,
        water_cl_meq=0.8,
        budget_level='high',
        area_ha=10,
        num_applications=15,
        expected_challenge="High Ca deficit - critical for tomato (blossom end rot prevention)"
    ))
    
    # === SCENARIO 4: Very High Bicarbonates ===
    scenarios.append(TestScenario(
        name="strawberry_high_hco3",
        crop="Fresa",
        deficits={'N': 150, 'P2O5': 70, 'K2O': 180, 'Ca': 50, 'Mg': 35, 'S': 25},
        water_hco3_meq=8.5,
        water_cl_meq=0.4,
        budget_level='high',
        area_ha=5,
        num_applications=20,
        expected_challenge="Very high bicarbonates - acid contribution affects nutrient balance"
    ))
    
    # === SCENARIO 5: Low Budget Constraint ===
    scenarios.append(TestScenario(
        name="maize_low_budget",
        crop="Maíz",
        deficits={'N': 200, 'P2O5': 90, 'K2O': 180, 'Ca': 50, 'Mg': 40, 'S': 30},
        water_hco3_meq=2.0,
        water_cl_meq=0.2,
        budget_level='low',
        area_ha=100,
        num_applications=6,
        expected_challenge="Low budget - economic profile must still reach minimum coverage"
    ))
    
    # === SCENARIO 6: High Chloride Water ===
    scenarios.append(TestScenario(
        name="pepper_high_cl",
        crop="Chile",
        deficits={'N': 180, 'P2O5': 85, 'K2O': 200, 'Ca': 60, 'Mg': 45, 'S': 35},
        water_hco3_meq=4.0,
        water_cl_meq=3.5,
        budget_level='medium',
        area_ha=20,
        num_applications=12,
        expected_challenge="High chloride water - must avoid chloride fertilizers"
    ))
    
    # === SCENARIO 7: Only Secondary Nutrients Deficient ===
    scenarios.append(TestScenario(
        name="lettuce_secondary_only",
        crop="Lechuga",
        deficits={'N': 50, 'P2O5': 30, 'K2O': 60, 'Ca': 80, 'Mg': 60, 'S': 45},
        water_hco3_meq=3.5,
        water_cl_meq=0.3,
        budget_level='medium',
        area_ha=8,
        num_applications=10,
        expected_challenge="Secondary nutrients are primary deficits - tests priority inversion"
    ))
    
    # === SCENARIO 8: Extreme N Deficit ===
    scenarios.append(TestScenario(
        name="maize_extreme_n",
        crop="Maíz",
        deficits={'N': 350, 'P2O5': 60, 'K2O': 120, 'Ca': 30, 'Mg': 25, 'S': 20},
        water_hco3_meq=5.0,
        water_cl_meq=0.5,
        budget_level='medium',
        area_ha=80,
        num_applications=8,
        expected_challenge="Extreme N deficit - must not neglect other nutrients"
    ))
    
    # === SCENARIO 9: Balanced Small Farm ===
    scenarios.append(TestScenario(
        name="vegetables_small_farm",
        crop="Hortalizas",
        deficits={'N': 100, 'P2O5': 50, 'K2O': 80, 'Ca': 40, 'Mg': 30, 'S': 20},
        water_hco3_meq=2.5,
        water_cl_meq=0.2,
        budget_level='low',
        area_ha=2,
        num_applications=15,
        expected_challenge="Small scale with many applications - cost efficiency critical"
    ))
    
    # === SCENARIO 10: Premium Greenhouse ===
    scenarios.append(TestScenario(
        name="tomato_greenhouse_premium",
        crop="Tomate Invernadero",
        deficits={'N': 250, 'P2O5': 120, 'K2O': 350, 'Ca': 150, 'Mg': 60, 'S': 50},
        water_hco3_meq=4.5,
        water_cl_meq=0.3,
        budget_level='high',
        area_ha=1,
        num_applications=25,
        expected_challenge="Premium greenhouse - complete profile must achieve near-perfect coverage"
    ))
    
    # === GENERATE RANDOM VARIATIONS ===
    base_crops = ["Maíz", "Tomate", "Fresa", "Chile", "Pepino", "Lechuga", "Sandía", "Melón"]
    budget_levels = ['low', 'medium', 'high']
    
    for i in range(40):
        crop = random.choice(base_crops)
        budget = random.choice(budget_levels)
        
        # Generate realistic deficits based on crop type
        if crop in ["Tomate", "Chile", "Pepino"]:
            base_n, base_k = 180, 220
        elif crop in ["Maíz"]:
            base_n, base_k = 200, 150
        else:
            base_n, base_k = 120, 100
        
        deficits = {
            'N': base_n * random.uniform(0.6, 1.4),
            'P2O5': random.uniform(40, 120),
            'K2O': base_k * random.uniform(0.7, 1.3),
            'Ca': random.uniform(20, 120),
            'Mg': random.uniform(15, 80),
            'S': random.uniform(15, 50)
        }
        
        # Round deficits
        deficits = {k: round(v, 1) for k, v in deficits.items()}
        
        scenarios.append(TestScenario(
            name=f"random_{crop.lower()}_{i+1}",
            crop=crop,
            deficits=deficits,
            water_hco3_meq=round(random.uniform(1.0, 8.0), 1),
            water_cl_meq=round(random.uniform(0.1, 2.0), 1),
            budget_level=budget,
            area_ha=round(random.uniform(1, 100), 1),
            num_applications=random.randint(5, 20),
            expected_challenge=f"Random variation #{i+1} - general robustness test"
        ))
    
    return scenarios


# ============================================================================
# EVALUATION METRICS
# ============================================================================

@dataclass
class OptimizationResult:
    """Result from running the optimizer on a scenario."""
    scenario_name: str
    profile_type: str
    coverage: Dict[str, float]
    total_cost_ha: float
    num_fertilizers: int
    fertilizers: List[str]
    acid_cost_ha: float
    warnings: List[str] = field(default_factory=list)


@dataclass 
class EvaluationMetrics:
    """Metrics for evaluating optimization quality."""
    min_coverage: float  # Liebig constraint - lowest nutrient
    avg_coverage: float
    liebig_balance: float  # Std dev of coverage (lower = better balance)
    cost_per_coverage_point: float
    nutrients_below_80: int
    nutrients_below_95: int
    all_above_80: bool
    profile_order_correct: bool  # Complete > Balanced > Economic
    
    def to_dict(self):
        return asdict(self)
    
    def score(self) -> float:
        """Calculate overall score (higher = better)."""
        score = 0
        
        # Liebig: Minimum coverage is critical (0-40 points)
        score += min(40, self.min_coverage * 0.5)
        
        # Balance: Lower std dev is better (0-20 points)
        balance_score = max(0, 20 - self.liebig_balance)
        score += balance_score
        
        # All nutrients above 80%: Big bonus (0-20 points)
        if self.all_above_80:
            score += 20
        else:
            score -= self.nutrients_below_80 * 5
        
        # Average coverage bonus (0-15 points)
        score += min(15, (self.avg_coverage - 80) * 0.3)
        
        # Cost efficiency (0-5 points) - lower cost per point is better
        if self.cost_per_coverage_point > 0:
            efficiency = min(5, 500 / self.cost_per_coverage_point)
            score += efficiency
        
        return round(score, 2)


def evaluate_result(result: OptimizationResult) -> EvaluationMetrics:
    """Calculate evaluation metrics for an optimization result."""
    coverages = list(result.coverage.values())
    
    if not coverages:
        return EvaluationMetrics(
            min_coverage=0, avg_coverage=0, liebig_balance=100,
            cost_per_coverage_point=float('inf'), nutrients_below_80=6,
            nutrients_below_95=6, all_above_80=False, profile_order_correct=False
        )
    
    min_cov = min(coverages)
    avg_cov = statistics.mean(coverages)
    std_dev = statistics.stdev(coverages) if len(coverages) > 1 else 0
    
    below_80 = sum(1 for c in coverages if c < 80)
    below_95 = sum(1 for c in coverages if c < 95)
    
    cost_per_point = result.total_cost_ha / avg_cov if avg_cov > 0 else float('inf')
    
    return EvaluationMetrics(
        min_coverage=round(min_cov, 1),
        avg_coverage=round(avg_cov, 1),
        liebig_balance=round(std_dev, 2),
        cost_per_coverage_point=round(cost_per_point, 2),
        nutrients_below_80=below_80,
        nutrients_below_95=below_95,
        all_above_80=(below_80 == 0),
        profile_order_correct=True  # Will be set when comparing profiles
    )


# ============================================================================
# FERTILIZER CATALOG (Simplified for simulation)
# ============================================================================

FERTILIZER_CATALOG = [
    # High N fertilizers
    {'id': 'urea', 'name': 'Urea', 'n_pct': 46, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0, 'price_per_kg': 18},
    {'id': 'ammonium_nitrate', 'name': 'Nitrato de Amonio', 'n_pct': 33.5, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0, 'price_per_kg': 22},
    {'id': 'calcium_nitrate', 'name': 'Nitrato de Calcio', 'n_pct': 15.5, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 19, 'mg_pct': 0, 's_pct': 0, 'price_per_kg': 28},
    
    # High P fertilizers  
    {'id': 'map', 'name': 'MAP', 'n_pct': 12, 'p2o5_pct': 61, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0, 'price_per_kg': 32},
    {'id': 'dap', 'name': 'DAP', 'n_pct': 18, 'p2o5_pct': 46, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0, 'price_per_kg': 30},
    {'id': 'triple_superphosphate', 'name': 'Triple Superfosfato', 'n_pct': 0, 'p2o5_pct': 46, 'k2o_pct': 0, 'ca_pct': 14, 'mg_pct': 0, 's_pct': 0, 'price_per_kg': 25},
    
    # High K fertilizers
    {'id': 'potassium_sulfate', 'name': 'Sulfato de Potasio', 'n_pct': 0, 'p2o5_pct': 0, 'k2o_pct': 50, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 18, 'price_per_kg': 35},
    {'id': 'potassium_chloride', 'name': 'Cloruro de Potasio', 'n_pct': 0, 'p2o5_pct': 0, 'k2o_pct': 60, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0, 'price_per_kg': 22, 'has_chloride': True},
    {'id': 'potassium_nitrate', 'name': 'Nitrato de Potasio', 'n_pct': 13, 'p2o5_pct': 0, 'k2o_pct': 44, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0, 'price_per_kg': 45},
    
    # Ca fertilizers
    {'id': 'calcium_chloride', 'name': 'Cloruro de Calcio', 'n_pct': 0, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 36, 'mg_pct': 0, 's_pct': 0, 'price_per_kg': 20, 'has_chloride': True},
    {'id': 'gypsum', 'name': 'Yeso Agrícola', 'n_pct': 0, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 23, 'mg_pct': 0, 's_pct': 18, 'price_per_kg': 8},
    
    # Mg fertilizers
    {'id': 'magnesium_sulfate', 'name': 'Sulfato de Magnesio', 'n_pct': 0, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 10, 's_pct': 13, 'price_per_kg': 18},
    {'id': 'kieserite', 'name': 'Kieserita', 'n_pct': 0, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 16, 's_pct': 22, 'price_per_kg': 22},
    {'id': 'magnesium_nitrate', 'name': 'Nitrato de Magnesio', 'n_pct': 11, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 9.5, 's_pct': 0, 'price_per_kg': 38},
    
    # Multi-nutrient
    {'id': 'fosfonitrato', 'name': 'Fosfonitrato', 'n_pct': 33, 'p2o5_pct': 3, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0, 'price_per_kg': 24},
    {'id': 'npk_17_17_17', 'name': 'NPK 17-17-17', 'n_pct': 17, 'p2o5_pct': 17, 'k2o_pct': 17, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0, 'price_per_kg': 28},
    {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'n_pct': 21, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 24, 'price_per_kg': 16},
]


# ============================================================================
# ALGORITHM VARIANTS
# ============================================================================

def get_nutrient_content(fert: Dict, nutrient: str) -> float:
    """Get nutrient content percentage from fertilizer."""
    mapping = {'N': 'n_pct', 'P2O5': 'p2o5_pct', 'K2O': 'k2o_pct', 
               'Ca': 'ca_pct', 'Mg': 'mg_pct', 'S': 's_pct'}
    return fert.get(mapping.get(nutrient, ''), 0) or 0


def calculate_dose_for_nutrient(fert: Dict, nutrient: str, deficit_kg: float, max_coverage: float = 1.15) -> float:
    """Calculate dose needed to cover a nutrient deficit."""
    content = get_nutrient_content(fert, nutrient)
    if content <= 0:
        return 0
    max_kg = deficit_kg * max_coverage
    dose = (max_kg / content) * 100
    return dose


def apply_dose(fert: Dict, dose_kg: float, contributions: Dict[str, float]) -> Dict[str, float]:
    """Apply a fertilizer dose and return updated contributions."""
    new_contrib = contributions.copy()
    for nutrient in NUTRIENT_PRIORITY:
        content = get_nutrient_content(fert, nutrient)
        if content > 0:
            added = (dose_kg * content) / 100
            new_contrib[nutrient] = new_contrib.get(nutrient, 0) + added
    return new_contrib


def calculate_coverage(contributions: Dict[str, float], deficits: Dict[str, float]) -> Dict[str, float]:
    """Calculate coverage percentage for each nutrient."""
    coverage = {}
    for nutrient in NUTRIENT_PRIORITY:
        deficit = deficits.get(nutrient, 0)
        contrib = contributions.get(nutrient, 0)
        if deficit > 0:
            coverage[nutrient] = round((contrib / deficit) * 100, 1)
        else:
            coverage[nutrient] = 100.0
    return coverage


# === VARIANT A: Fixed Priority (Current Algorithm) ===
def optimize_variant_a(scenario: TestScenario, profile_type: str, max_ferts: int) -> OptimizationResult:
    """Fixed priority order: N > K2O > P2O5 > Ca > Mg > S"""
    contributions = {n: 0 for n in NUTRIENT_PRIORITY}
    selected = []
    total_cost = 0
    deficits = scenario.deficits.copy()
    
    priority = ['N', 'K2O', 'P2O5', 'Ca', 'Mg', 'S']
    
    for _ in range(max_ferts):
        best_fert = None
        best_score = float('inf')
        best_dose = 0
        
        for fert in FERTILIZER_CATALOG:
            if fert['id'] in [s['id'] for s in selected]:
                continue
            if scenario.water_cl_meq > 2 and fert.get('has_chloride'):
                continue
            
            # Find target nutrient with highest remaining deficit
            target = None
            for n in priority:
                current_cov = (contributions[n] / deficits[n] * 100) if deficits[n] > 0 else 100
                if current_cov < 115 and get_nutrient_content(fert, n) > 0:
                    target = n
                    break
            
            if not target:
                continue
            
            # Calculate constrained dose
            remaining = deficits[target] - contributions[target]
            max_allowed = deficits[target] * 1.15 - contributions[target]
            dose = calculate_dose_for_nutrient(fert, target, max_allowed)
            
            # Check other nutrients don't exceed 115%
            test_contrib = apply_dose(fert, dose, contributions)
            for n in NUTRIENT_PRIORITY:
                if deficits[n] > 0 and test_contrib[n] > deficits[n] * 1.15:
                    denominator = test_contrib[n] - contributions[n]
                    if denominator > 0:
                        dose = dose * (deficits[n] * 1.15 - contributions[n]) / denominator
            
            if dose < 1:
                continue
            
            # Score: cost per coverage point
            price = fert.get('price_per_kg', 25)
            cost = dose * price
            test_contrib = apply_dose(fert, dose, contributions)
            test_cov = calculate_coverage(test_contrib, deficits)
            delta = sum(test_cov[n] - calculate_coverage(contributions, deficits)[n] for n in NUTRIENT_PRIORITY)
            
            if delta > 0:
                score = cost / delta
                if score < best_score:
                    best_score = score
                    best_fert = fert
                    best_dose = dose
        
        if best_fert:
            selected.append({'id': best_fert['id'], 'name': best_fert['name'], 'dose': best_dose})
            contributions = apply_dose(best_fert, best_dose, contributions)
            total_cost += best_dose * best_fert.get('price_per_kg', 25)
        else:
            break
    
    coverage = calculate_coverage(contributions, deficits)
    
    return OptimizationResult(
        scenario_name=scenario.name,
        profile_type=profile_type,
        coverage=coverage,
        total_cost_ha=round(total_cost, 2),
        num_fertilizers=len(selected),
        fertilizers=[f['name'] for f in selected],
        acid_cost_ha=0
    )


# === VARIANT B: Dynamic Priority by Current Coverage ===
def optimize_variant_b(scenario: TestScenario, profile_type: str, max_ferts: int) -> OptimizationResult:
    """Dynamic priority: Always target the nutrient with LOWEST current coverage."""
    contributions = {n: 0 for n in NUTRIENT_PRIORITY}
    selected = []
    total_cost = 0
    deficits = scenario.deficits.copy()
    
    for _ in range(max_ferts):
        # Dynamic priority: sort by current coverage (ascending)
        current_cov = calculate_coverage(contributions, deficits)
        priority = sorted(NUTRIENT_PRIORITY, key=lambda n: current_cov.get(n, 100))
        
        best_fert = None
        best_score = float('inf')
        best_dose = 0
        
        for fert in FERTILIZER_CATALOG:
            if fert['id'] in [s['id'] for s in selected]:
                continue
            if scenario.water_cl_meq > 2 and fert.get('has_chloride'):
                continue
            
            # Target the lowest coverage nutrient this fertilizer can help
            target = None
            for n in priority:
                if current_cov[n] < 115 and get_nutrient_content(fert, n) > 0:
                    target = n
                    break
            
            if not target:
                continue
            
            # Calculate constrained dose
            max_allowed = deficits[target] * 1.15 - contributions[target]
            dose = calculate_dose_for_nutrient(fert, target, max_allowed)
            
            # Check other nutrients don't exceed 115%
            for n in NUTRIENT_PRIORITY:
                content = get_nutrient_content(fert, n)
                if content > 0 and deficits[n] > 0:
                    headroom = deficits[n] * 1.15 - contributions[n]
                    max_dose_for_n = (headroom / content) * 100
                    dose = min(dose, max_dose_for_n)
            
            if dose < 1:
                continue
            
            # Score with urgency bonus for low-coverage nutrients
            price = fert.get('price_per_kg', 25)
            cost = dose * price
            test_contrib = apply_dose(fert, dose, contributions)
            test_cov = calculate_coverage(test_contrib, deficits)
            
            # Weight deltas by how far below 95% each nutrient is
            weighted_delta = 0
            for n in NUTRIENT_PRIORITY:
                delta = test_cov[n] - current_cov[n]
                if delta > 0:
                    gap = max(0, 95 - current_cov[n])
                    urgency = 1 + (gap / 30)
                    weighted_delta += delta * urgency
            
            if weighted_delta > 0:
                score = cost / weighted_delta
                if score < best_score:
                    best_score = score
                    best_fert = fert
                    best_dose = dose
        
        if best_fert:
            selected.append({'id': best_fert['id'], 'name': best_fert['name'], 'dose': best_dose})
            contributions = apply_dose(best_fert, best_dose, contributions)
            total_cost += best_dose * best_fert.get('price_per_kg', 25)
        else:
            break
    
    coverage = calculate_coverage(contributions, deficits)
    
    return OptimizationResult(
        scenario_name=scenario.name,
        profile_type=profile_type,
        coverage=coverage,
        total_cost_ha=round(total_cost, 2),
        num_fertilizers=len(selected),
        fertilizers=[f['name'] for f in selected],
        acid_cost_ha=0
    )


# === VARIANT C: Rescue Phase for Low Nutrients ===
def optimize_variant_c(scenario: TestScenario, profile_type: str, max_ferts: int) -> OptimizationResult:
    """Dynamic priority + rescue phase for nutrients below 80%."""
    # First run variant B
    result = optimize_variant_b(scenario, profile_type, max_ferts - 2)  # Reserve 2 slots
    
    contributions = {n: 0 for n in NUTRIENT_PRIORITY}
    # Recalculate contributions from result
    deficits = scenario.deficits.copy()
    selected = []
    total_cost = 0
    
    # Rebuild from variant B result
    for fert_name in result.fertilizers:
        fert = next((f for f in FERTILIZER_CATALOG if f['name'] == fert_name), None)
        if fert:
            # Recalculate dose
            current_cov = calculate_coverage(contributions, deficits)
            priority = sorted(NUTRIENT_PRIORITY, key=lambda n: current_cov.get(n, 100))
            target = None
            for n in priority:
                if current_cov[n] < 115 and get_nutrient_content(fert, n) > 0:
                    target = n
                    break
            if target:
                max_allowed = deficits[target] * 1.15 - contributions[target]
                dose = calculate_dose_for_nutrient(fert, target, max_allowed)
                for n in NUTRIENT_PRIORITY:
                    content = get_nutrient_content(fert, n)
                    if content > 0 and deficits[n] > 0:
                        headroom = deficits[n] * 1.15 - contributions[n]
                        max_dose_for_n = (headroom / content) * 100
                        dose = min(dose, max_dose_for_n)
                if dose >= 1:
                    selected.append({'id': fert['id'], 'name': fert['name'], 'dose': dose})
                    contributions = apply_dose(fert, dose, contributions)
                    total_cost += dose * fert.get('price_per_kg', 25)
    
    # RESCUE PHASE: Check for nutrients below 80%
    current_cov = calculate_coverage(contributions, deficits)
    rescue_nutrients = [n for n in NUTRIENT_PRIORITY if current_cov[n] < 80]
    
    for rescue_n in rescue_nutrients:
        if len(selected) >= max_ferts:
            break
        
        # Find best fertilizer for this specific nutrient
        best_fert = None
        best_efficiency = float('inf')
        
        for fert in FERTILIZER_CATALOG:
            if fert['id'] in [s['id'] for s in selected]:
                continue
            if scenario.water_cl_meq > 2 and fert.get('has_chloride'):
                continue
            
            content = get_nutrient_content(fert, rescue_n)
            if content <= 0:
                continue
            
            # Calculate max dose respecting all caps
            max_allowed = deficits[rescue_n] * 1.15 - contributions[rescue_n]
            dose = calculate_dose_for_nutrient(fert, rescue_n, max_allowed)
            
            for n in NUTRIENT_PRIORITY:
                n_content = get_nutrient_content(fert, n)
                if n_content > 0 and deficits[n] > 0:
                    headroom = deficits[n] * 1.15 - contributions[n]
                    if headroom > 0:
                        max_dose_for_n = (headroom / n_content) * 100
                        dose = min(dose, max_dose_for_n)
            
            if dose < 1:
                continue
            
            # Efficiency: cost per point of rescue nutrient coverage
            price = fert.get('price_per_kg', 25)
            coverage_gain = (dose * content / 100) / deficits[rescue_n] * 100
            efficiency = (price * dose) / coverage_gain if coverage_gain > 0 else float('inf')
            
            if efficiency < best_efficiency:
                best_efficiency = efficiency
                best_fert = (fert, dose)
        
        if best_fert:
            fert, dose = best_fert
            selected.append({'id': fert['id'], 'name': fert['name'], 'dose': dose})
            contributions = apply_dose(fert, dose, contributions)
            total_cost += dose * fert.get('price_per_kg', 25)
    
    coverage = calculate_coverage(contributions, deficits)
    
    return OptimizationResult(
        scenario_name=scenario.name,
        profile_type=profile_type,
        coverage=coverage,
        total_cost_ha=round(total_cost, 2),
        num_fertilizers=len(selected),
        fertilizers=[f['name'] for f in selected],
        acid_cost_ha=0
    )


# === VARIANT D: Reserved Slots for Secondary Nutrients ===
def optimize_variant_d(scenario: TestScenario, profile_type: str, max_ferts: int) -> OptimizationResult:
    """Reserve slots for Ca/Mg before filling with N/P/K."""
    contributions = {n: 0 for n in NUTRIENT_PRIORITY}
    selected = []
    total_cost = 0
    deficits = scenario.deficits.copy()
    
    # Phase 1: Reserve 1-2 slots for secondary nutrients (Ca, Mg)
    secondary = ['Ca', 'Mg']
    reserved_slots = min(2, max_ferts // 3)
    
    for sec_n in secondary[:reserved_slots]:
        if deficits.get(sec_n, 0) <= 0:
            continue
        
        # Find best fertilizer for this secondary nutrient
        best_fert = None
        best_efficiency = float('inf')
        
        for fert in FERTILIZER_CATALOG:
            if fert['id'] in [s['id'] for s in selected]:
                continue
            if scenario.water_cl_meq > 2 and fert.get('has_chloride'):
                continue
            
            content = get_nutrient_content(fert, sec_n)
            if content <= 0:
                continue
            
            price = fert.get('price_per_kg', 25)
            efficiency = price / content  # Cost per % content
            
            if efficiency < best_efficiency:
                best_efficiency = efficiency
                best_fert = fert
        
        if best_fert:
            # Calculate dose
            max_allowed = deficits[sec_n] * 1.15
            dose = calculate_dose_for_nutrient(best_fert, sec_n, max_allowed)
            
            # Cap by other nutrients
            for n in NUTRIENT_PRIORITY:
                n_content = get_nutrient_content(best_fert, n)
                if n_content > 0 and deficits.get(n, 0) > 0:
                    headroom = deficits[n] * 1.15 - contributions[n]
                    if headroom > 0:
                        max_dose_for_n = (headroom / n_content) * 100
                        dose = min(dose, max_dose_for_n)
            
            if dose >= 1:
                selected.append({'id': best_fert['id'], 'name': best_fert['name'], 'dose': dose})
                contributions = apply_dose(best_fert, dose, contributions)
                total_cost += dose * best_fert.get('price_per_kg', 25)
    
    # Phase 2: Fill remaining slots with dynamic priority
    remaining_slots = max_ferts - len(selected)
    
    for _ in range(remaining_slots):
        current_cov = calculate_coverage(contributions, deficits)
        priority = sorted(NUTRIENT_PRIORITY, key=lambda n: current_cov.get(n, 100))
        
        best_fert = None
        best_score = float('inf')
        best_dose = 0
        
        for fert in FERTILIZER_CATALOG:
            if fert['id'] in [s['id'] for s in selected]:
                continue
            if scenario.water_cl_meq > 2 and fert.get('has_chloride'):
                continue
            
            target = None
            for n in priority:
                if current_cov[n] < 115 and get_nutrient_content(fert, n) > 0:
                    target = n
                    break
            
            if not target:
                continue
            
            max_allowed = deficits[target] * 1.15 - contributions[target]
            dose = calculate_dose_for_nutrient(fert, target, max_allowed)
            
            for n in NUTRIENT_PRIORITY:
                content = get_nutrient_content(fert, n)
                if content > 0 and deficits.get(n, 0) > 0:
                    headroom = deficits[n] * 1.15 - contributions[n]
                    if headroom > 0:
                        max_dose_for_n = (headroom / content) * 100
                        dose = min(dose, max_dose_for_n)
            
            if dose < 1:
                continue
            
            price = fert.get('price_per_kg', 25)
            cost = dose * price
            test_contrib = apply_dose(fert, dose, contributions)
            test_cov = calculate_coverage(test_contrib, deficits)
            
            weighted_delta = 0
            for n in NUTRIENT_PRIORITY:
                delta = test_cov[n] - current_cov[n]
                if delta > 0:
                    gap = max(0, 95 - current_cov[n])
                    urgency = 1 + (gap / 30)
                    weighted_delta += delta * urgency
            
            if weighted_delta > 0:
                score = cost / weighted_delta
                if score < best_score:
                    best_score = score
                    best_fert = fert
                    best_dose = dose
        
        if best_fert:
            selected.append({'id': best_fert['id'], 'name': best_fert['name'], 'dose': best_dose})
            contributions = apply_dose(best_fert, best_dose, contributions)
            total_cost += best_dose * best_fert.get('price_per_kg', 25)
        else:
            break
    
    coverage = calculate_coverage(contributions, deficits)
    
    return OptimizationResult(
        scenario_name=scenario.name,
        profile_type=profile_type,
        coverage=coverage,
        total_cost_ha=round(total_cost, 2),
        num_fertilizers=len(selected),
        fertilizers=[f['name'] for f in selected],
        acid_cost_ha=0
    )


# === VARIANT E: Combined (Dynamic + Reserved + Rescue) ===
def optimize_variant_e(scenario: TestScenario, profile_type: str, max_ferts: int) -> OptimizationResult:
    """Combined approach: Reserved slots + Dynamic priority + Rescue phase."""
    contributions = {n: 0 for n in NUTRIENT_PRIORITY}
    selected = []
    total_cost = 0
    deficits = scenario.deficits.copy()
    
    # Phase 1: Reserve slots for secondary nutrients with highest relative deficit
    current_cov = calculate_coverage(contributions, deficits)
    secondary = sorted(['Ca', 'Mg', 'S'], key=lambda n: current_cov.get(n, 100))
    reserved_slots = min(2, max(1, max_ferts // 4))
    rescue_slots = 1
    main_slots = max_ferts - reserved_slots - rescue_slots
    
    # Add secondary nutrients first
    for sec_n in secondary[:reserved_slots]:
        if deficits.get(sec_n, 0) <= 0:
            continue
        
        best_fert = None
        best_score = float('inf')
        
        for fert in FERTILIZER_CATALOG:
            if fert['id'] in [s['id'] for s in selected]:
                continue
            if scenario.water_cl_meq > 2 and fert.get('has_chloride'):
                continue
            
            content = get_nutrient_content(fert, sec_n)
            if content < 5:  # Must have significant content
                continue
            
            price = fert.get('price_per_kg', 25)
            # Prefer fertilizers with high content of target + low content of already-covered
            score = price / content
            
            if score < best_score:
                best_score = score
                best_fert = fert
        
        if best_fert:
            max_allowed = deficits[sec_n] * 1.15
            dose = calculate_dose_for_nutrient(best_fert, sec_n, max_allowed)
            
            for n in NUTRIENT_PRIORITY:
                n_content = get_nutrient_content(best_fert, n)
                if n_content > 0 and deficits.get(n, 0) > 0:
                    headroom = deficits[n] * 1.15 - contributions[n]
                    if headroom > 0:
                        max_dose_for_n = (headroom / n_content) * 100
                        dose = min(dose, max_dose_for_n)
            
            if dose >= 1:
                selected.append({'id': best_fert['id'], 'name': best_fert['name'], 'dose': dose})
                contributions = apply_dose(best_fert, dose, contributions)
                total_cost += dose * best_fert.get('price_per_kg', 25)
    
    # Phase 2: Fill main slots with dynamic priority
    for _ in range(main_slots):
        current_cov = calculate_coverage(contributions, deficits)
        priority = sorted(NUTRIENT_PRIORITY, key=lambda n: current_cov.get(n, 100))
        
        best_fert = None
        best_score = float('inf')
        best_dose = 0
        
        for fert in FERTILIZER_CATALOG:
            if fert['id'] in [s['id'] for s in selected]:
                continue
            if scenario.water_cl_meq > 2 and fert.get('has_chloride'):
                continue
            
            target = None
            for n in priority:
                if current_cov[n] < 115 and get_nutrient_content(fert, n) > 0:
                    target = n
                    break
            
            if not target:
                continue
            
            max_allowed = deficits[target] * 1.15 - contributions[target]
            dose = calculate_dose_for_nutrient(fert, target, max_allowed)
            
            for n in NUTRIENT_PRIORITY:
                content = get_nutrient_content(fert, n)
                if content > 0 and deficits.get(n, 0) > 0:
                    headroom = deficits[n] * 1.15 - contributions[n]
                    if headroom > 0:
                        max_dose_for_n = (headroom / content) * 100
                        dose = min(dose, max_dose_for_n)
            
            if dose < 1:
                continue
            
            price = fert.get('price_per_kg', 25)
            cost = dose * price
            test_contrib = apply_dose(fert, dose, contributions)
            test_cov = calculate_coverage(test_contrib, deficits)
            
            weighted_delta = 0
            for n in NUTRIENT_PRIORITY:
                delta = test_cov[n] - current_cov[n]
                if delta > 0:
                    gap = max(0, 95 - current_cov[n])
                    urgency = 1 + (gap / 25)
                    weighted_delta += delta * urgency
            
            if weighted_delta > 0:
                score = cost / weighted_delta
                if score < best_score:
                    best_score = score
                    best_fert = fert
                    best_dose = dose
        
        if best_fert:
            selected.append({'id': best_fert['id'], 'name': best_fert['name'], 'dose': best_dose})
            contributions = apply_dose(best_fert, best_dose, contributions)
            total_cost += best_dose * best_fert.get('price_per_kg', 25)
        else:
            break
    
    # Phase 3: Rescue phase for any nutrient below 80%
    current_cov = calculate_coverage(contributions, deficits)
    rescue_nutrients = sorted(
        [n for n in NUTRIENT_PRIORITY if current_cov[n] < 80],
        key=lambda n: current_cov[n]
    )
    
    for rescue_n in rescue_nutrients[:rescue_slots]:
        if len(selected) >= max_ferts:
            break
        
        best_fert = None
        best_efficiency = float('inf')
        
        for fert in FERTILIZER_CATALOG:
            if fert['id'] in [s['id'] for s in selected]:
                continue
            if scenario.water_cl_meq > 2 and fert.get('has_chloride'):
                continue
            
            content = get_nutrient_content(fert, rescue_n)
            if content <= 0:
                continue
            
            max_allowed = deficits[rescue_n] * 1.15 - contributions[rescue_n]
            dose = calculate_dose_for_nutrient(fert, rescue_n, max_allowed)
            
            for n in NUTRIENT_PRIORITY:
                n_content = get_nutrient_content(fert, n)
                if n_content > 0 and deficits.get(n, 0) > 0:
                    headroom = deficits[n] * 1.15 - contributions[n]
                    if headroom > 0:
                        max_dose_for_n = (headroom / n_content) * 100
                        dose = min(dose, max_dose_for_n)
            
            if dose < 1:
                continue
            
            price = fert.get('price_per_kg', 25)
            coverage_gain = (dose * content / 100) / deficits[rescue_n] * 100
            efficiency = (price * dose) / coverage_gain if coverage_gain > 0 else float('inf')
            
            if efficiency < best_efficiency:
                best_efficiency = efficiency
                best_fert = (fert, dose)
        
        if best_fert:
            fert, dose = best_fert
            selected.append({'id': fert['id'], 'name': fert['name'], 'dose': dose})
            contributions = apply_dose(fert, dose, contributions)
            total_cost += dose * fert.get('price_per_kg', 25)
    
    coverage = calculate_coverage(contributions, deficits)
    
    return OptimizationResult(
        scenario_name=scenario.name,
        profile_type=profile_type,
        coverage=coverage,
        total_cost_ha=round(total_cost, 2),
        num_fertilizers=len(selected),
        fertilizers=[f['name'] for f in selected],
        acid_cost_ha=0
    )


# ============================================================================
# SIMULATION RUNNER
# ============================================================================

ALGORITHM_VARIANTS = {
    'A_fixed_priority': optimize_variant_a,
    'B_dynamic_priority': optimize_variant_b,
    'C_rescue_phase': optimize_variant_c,
    'D_reserved_slots': optimize_variant_d,
    'E_combined': optimize_variant_e
}

PROFILE_CONFIGS = {
    'economic': {'max_ferts': 4},
    'balanced': {'max_ferts': 6},
    'complete': {'max_ferts': 10}
}


def run_simulation():
    """Run all scenarios with all algorithm variants and generate report."""
    print("=" * 80)
    print("FertiIrrigation Optimizer Calibration Suite")
    print("=" * 80)
    print()
    
    scenarios = generate_test_scenarios()
    print(f"Generated {len(scenarios)} test scenarios")
    print()
    
    results = {}
    
    for variant_name, variant_fn in ALGORITHM_VARIANTS.items():
        print(f"Running variant {variant_name}...")
        results[variant_name] = {
            'by_scenario': {},
            'aggregate': {
                'economic': [],
                'balanced': [],
                'complete': []
            }
        }
        
        for scenario in scenarios:
            scenario_results = {}
            
            for profile, config in PROFILE_CONFIGS.items():
                result = variant_fn(scenario, profile, config['max_ferts'])
                metrics = evaluate_result(result)
                scenario_results[profile] = {
                    'result': result,
                    'metrics': metrics
                }
                results[variant_name]['aggregate'][profile].append(metrics)
            
            # Check profile differentiation
            eco_avg = scenario_results['economic']['metrics'].avg_coverage
            bal_avg = scenario_results['balanced']['metrics'].avg_coverage
            com_avg = scenario_results['complete']['metrics'].avg_coverage
            
            profile_order_ok = com_avg >= bal_avg >= eco_avg
            for profile in PROFILE_CONFIGS:
                scenario_results[profile]['metrics'].profile_order_correct = profile_order_ok
            
            results[variant_name]['by_scenario'][scenario.name] = scenario_results
    
    # Calculate aggregate metrics
    print()
    print("=" * 80)
    print("AGGREGATE RESULTS")
    print("=" * 80)
    
    summary = {}
    
    for variant_name in ALGORITHM_VARIANTS:
        summary[variant_name] = {}
        
        for profile in PROFILE_CONFIGS:
            metrics_list = results[variant_name]['aggregate'][profile]
            
            avg_min_cov = statistics.mean(m.min_coverage for m in metrics_list)
            avg_avg_cov = statistics.mean(m.avg_coverage for m in metrics_list)
            avg_balance = statistics.mean(m.liebig_balance for m in metrics_list)
            pct_all_above_80 = sum(1 for m in metrics_list if m.all_above_80) / len(metrics_list) * 100
            avg_score = statistics.mean(m.score() for m in metrics_list)
            
            summary[variant_name][profile] = {
                'avg_min_coverage': round(avg_min_cov, 1),
                'avg_avg_coverage': round(avg_avg_cov, 1),
                'avg_liebig_balance': round(avg_balance, 2),
                'pct_all_above_80': round(pct_all_above_80, 1),
                'avg_score': round(avg_score, 2)
            }
    
    # Print summary table
    print()
    print(f"{'Variant':<25} | {'Profile':<10} | {'Min Cov':<8} | {'Avg Cov':<8} | {'Balance':<8} | {'>80%':<6} | {'Score':<8}")
    print("-" * 90)
    
    for variant_name in ALGORITHM_VARIANTS:
        for profile in PROFILE_CONFIGS:
            s = summary[variant_name][profile]
            print(f"{variant_name:<25} | {profile:<10} | {s['avg_min_coverage']:>6.1f}% | {s['avg_avg_coverage']:>6.1f}% | {s['avg_liebig_balance']:>6.2f} | {s['pct_all_above_80']:>5.1f}% | {s['avg_score']:>6.2f}")
        print("-" * 90)
    
    # Find best variant
    print()
    print("=" * 80)
    print("WINNER ANALYSIS")
    print("=" * 80)
    
    # Score by total average score across all profiles
    variant_scores = {}
    for variant_name in ALGORITHM_VARIANTS:
        total_score = sum(
            summary[variant_name][profile]['avg_score'] 
            for profile in PROFILE_CONFIGS
        )
        variant_scores[variant_name] = total_score
    
    winner = max(variant_scores, key=variant_scores.get)
    print(f"\nBest overall variant: {winner}")
    print(f"Total score: {variant_scores[winner]:.2f}")
    print()
    
    # Detailed comparison
    print("Variant rankings:")
    for i, (variant, score) in enumerate(sorted(variant_scores.items(), key=lambda x: -x[1]), 1):
        print(f"  {i}. {variant}: {score:.2f}")
    
    # Save detailed report
    report = {
        'timestamp': datetime.now().isoformat(),
        'num_scenarios': len(scenarios),
        'variants_tested': list(ALGORITHM_VARIANTS.keys()),
        'summary': summary,
        'variant_scores': variant_scores,
        'winner': winner,
        'recommendations': generate_recommendations(summary, winner)
    }
    
    report_path = 'backend/calibration_reports/fertiirrigation_calibration_report.json'
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_path}")
    
    return report


def generate_recommendations(summary: Dict, winner: str) -> List[str]:
    """Generate implementation recommendations based on results."""
    recommendations = []
    
    recommendations.append(f"WINNING ALGORITHM: {winner}")
    
    if winner == 'E_combined':
        recommendations.append(
            "Implement 3-phase optimization: "
            "(1) Reserve 1-2 slots for secondary nutrients (Ca/Mg), "
            "(2) Fill remaining slots with dynamic priority by current coverage, "
            "(3) Rescue phase for any nutrient below 80%"
        )
    elif winner == 'B_dynamic_priority':
        recommendations.append(
            "Replace fixed priority order with dynamic sorting by current coverage. "
            "Always target the nutrient with LOWEST coverage first."
        )
    elif winner == 'C_rescue_phase':
        recommendations.append(
            "Add rescue phase after main optimization. "
            "Reserve 1-2 fertilizer slots to boost any nutrient that remains below 80%."
        )
    elif winner == 'D_reserved_slots':
        recommendations.append(
            "Reserve fertilizer slots for secondary nutrients (Ca, Mg) before filling with N/P/K. "
            "This prevents the 'blocked by carrier' problem."
        )
    
    # Check for specific issues
    for variant in summary:
        for profile in summary[variant]:
            if summary[variant][profile]['pct_all_above_80'] < 90:
                recommendations.append(
                    f"WARNING: {variant}/{profile} has only {summary[variant][profile]['pct_all_above_80']}% "
                    f"of scenarios with all nutrients above 80%. Consider increasing max_fertilizers."
                )
    
    return recommendations


if __name__ == '__main__':
    run_simulation()

"""
Smoke test for FertiIrrigation AI Optimizer pipeline.

This test runs the post-processing pipeline WITHOUT GPT calls:
  enforce_hard_constraints -> cap_by_S -> normalize_coverage

Tests must complete in < 0.2s to ensure no loops/hangs.
"""
import pytest
import time
import json
import os
from app.services.fertiirrigation_ai_optimizer import (
    enforce_hard_constraints,
    cap_fertilizers_by_nutrient,
    normalize_coverage,
    SulfurCapError,
    SULFATE_FERTILIZERS
)


# =============================================================================
# Test Fixtures - Simulated real data
# =============================================================================

@pytest.fixture
def real_catalog():
    """Load real fertilizer catalog or use mock equivalent."""
    catalog_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'data', 'hydro_fertilizers.json')
    
    if os.path.exists(catalog_path):
        with open(catalog_path, 'r') as f:
            data = json.load(f)
        # Convert to format expected by optimizer
        fertilizers = []
        for fert in data.get('fertilizers', []):
            # Map hydro format to fertiirrigation format
            fertilizers.append({
                'id': fert.get('id', ''),
                'name': fert.get('name', ''),
                'n_pct': fert.get('composition', {}).get('n_total_pct', 0) or fert.get('ion_contributions', {}).get('NO3', 0) * 14 / 62 * 100 if fert.get('ion_contributions') else 0,
                'p2o5_pct': fert.get('composition', {}).get('p2o5_pct', 0) or 0,
                'k2o_pct': fert.get('composition', {}).get('k2o_pct', 0) or 0,
                'ca_pct': fert.get('composition', {}).get('cao_pct', 0) * 0.714 if fert.get('composition', {}).get('cao_pct') else 0,
                'mg_pct': fert.get('composition', {}).get('mgo_pct', 0) * 0.603 if fert.get('composition', {}).get('mgo_pct') else 0,
                's_pct': fert.get('composition', {}).get('s_pct', 0) or 0,
            })
        return fertilizers
    
    # Fallback mock catalog
    return [
        {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'n_pct': 21, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 24},
        {'id': 'magnesium_sulfate', 'name': 'Sulfato de Magnesio', 'n_pct': 0, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 9.8, 's_pct': 13},
        {'id': 'map', 'name': 'Fosfato Monoamónico (MAP)', 'n_pct': 12, 'p2o5_pct': 61, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0},
        {'id': 'calcium_nitrate', 'name': 'Nitrato de Calcio', 'n_pct': 15.5, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 19, 'mg_pct': 0, 's_pct': 0},
        {'id': 'urea', 'name': 'Urea', 'n_pct': 46, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0},
        {'id': 'potassium_nitrate', 'name': 'Nitrato de Potasio', 'n_pct': 13, 'p2o5_pct': 0, 'k2o_pct': 46, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0},
        {'id': 'potassium_sulfate', 'name': 'Sulfato de Potasio', 'n_pct': 0, 'p2o5_pct': 0, 'k2o_pct': 50, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 17},
    ]


@pytest.fixture
def mock_catalog():
    """Simplified mock catalog for deterministic tests."""
    return [
        {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'n_pct': 21, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 24},
        {'id': 'magnesium_sulfate', 'name': 'Sulfato de Magnesio', 'n_pct': 0, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 9.8, 's_pct': 13},
        {'id': 'map', 'name': 'Fosfato Monoamónico (MAP)', 'n_pct': 12, 'p2o5_pct': 61, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0},
        {'id': 'calcium_nitrate', 'name': 'Nitrato de Calcio', 'n_pct': 15.5, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 19, 'mg_pct': 0, 's_pct': 0},
        {'id': 'urea', 'name': 'Urea', 'n_pct': 46, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0},
    ]


@pytest.fixture
def sulfate_only_catalog():
    """Catalog with ONLY sulfate N sources - will trigger error."""
    return [
        {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'n_pct': 21, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 24},
        {'id': 'tsp', 'name': 'Triple Superfosfato', 'n_pct': 0, 'p2o5_pct': 46, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0},
    ]


@pytest.fixture
def profile_with_sulfates():
    """Profile containing sulfato de amonio + MgSO4 + MAP + nitrato de calcio."""
    return {
        'fertilizers': [
            {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'dose_kg_ha': 15, 'dose_per_application': 1.5},
            {'id': 'magnesium_sulfate', 'name': 'Sulfato de Magnesio', 'dose_kg_ha': 10, 'dose_per_application': 1.0},
            {'id': 'map', 'name': 'Fosfato Monoamónico (MAP)', 'dose_kg_ha': 24, 'dose_per_application': 2.4},
            {'id': 'calcium_nitrate', 'name': 'Nitrato de Calcio', 'dose_kg_ha': 20, 'dose_per_application': 2.0},
        ],
        'notes': ''
    }


@pytest.fixture
def deficits_low_s():
    """Deficits with low S (1.5 kg/ha) - triggers aggressive capping."""
    return {
        'N': 10.0,
        'P2O5': 14.6,
        'K2O': 5.0,
        'Ca': 10.0,
        'Mg': 2.0,
        'S': 1.5  # Low S deficit - cap to 1.65 kg max (110%)
    }


@pytest.fixture
def deficits_zero_s():
    """Deficits with S = 0 - no sulfur allowed."""
    return {
        'N': 8.0,
        'P2O5': 10.0,
        'K2O': 5.0,
        'Ca': 10.0,
        'Mg': 2.0,
        'S': 0  # Zero S deficit - all sulfates must be removed
    }


# =============================================================================
# Smoke Tests - Must complete in < 0.2s
# =============================================================================

def run_pipeline(profile, deficits, catalog, water_analysis=None):
    """
    Run the full post-processing pipeline:
    1. enforce_hard_constraints
    2. cap_fertilizers_by_nutrient (S cap)
    3. normalize_coverage
    
    Returns (profile, elapsed_time)
    """
    water = water_analysis or {'cl_meq_l': 0.5}
    agronomic_context = {'water': water}
    
    start = time.perf_counter()
    
    # Phase 1: Hard constraints
    # Signature: profile, deficits, agronomic_context, available_fertilizers, growth_stage
    profile = enforce_hard_constraints(profile, deficits, agronomic_context, catalog)
    
    # Phase 2: S Cap (only if S deficit > 0 and < 5 kg/ha)
    s_deficit = deficits.get('S', 0)
    if s_deficit > 0 and s_deficit < 5.0:
        profile = cap_fertilizers_by_nutrient(
            profile, deficits, catalog,
            max_coverage_pct=110,
            nutrient='S',
            num_applications=10
        )
    elif s_deficit <= 0:
        # Zero deficit - force zero sulfates
        profile = cap_fertilizers_by_nutrient(
            profile, deficits, catalog,
            max_coverage_pct=110,
            nutrient='S',
            num_applications=10
        )
    
    # Phase 3: Normalize coverage
    profile = normalize_coverage(
        profile, deficits, catalog,
        max_coverage_pct=110,
        num_applications=10
    )
    
    elapsed = time.perf_counter() - start
    return profile, elapsed


def test_smoke_pipeline_low_s_deficit(profile_with_sulfates, deficits_low_s, mock_catalog):
    """
    SMOKE TEST: Pipeline with S=1.5 kg/ha must complete in < 0.2s
    and produce valid output with S ≤ 110%.
    """
    profile, elapsed = run_pipeline(profile_with_sulfates, deficits_low_s, mock_catalog)
    
    # Must complete quickly
    assert elapsed < 0.2, f"Pipeline took {elapsed:.3f}s - exceeds 0.2s limit (possible loop)"
    
    # Must return valid profile
    assert profile is not None
    assert 'fertilizers' in profile
    
    # Calculate S coverage
    total_s = 0
    for fert in profile['fertilizers']:
        fert_id = fert.get('id', '')
        dose = fert.get('dose_kg_ha', 0)
        if fert_id == 'ammonium_sulfate':
            total_s += dose * 0.24
        elif fert_id == 'magnesium_sulfate':
            total_s += dose * 0.13
    
    max_s_allowed = deficits_low_s['S'] * 1.10  # 1.65 kg
    assert total_s <= max_s_allowed + 0.01, f"S must be ≤{max_s_allowed:.2f} kg, got {total_s:.2f} kg"
    
    print(f"\n[SMOKE] Pipeline completed in {elapsed*1000:.1f}ms")
    print(f"[SMOKE] S coverage: {total_s:.2f} kg / {max_s_allowed:.2f} kg max ({total_s/deficits_low_s['S']*100:.0f}%)")


def test_smoke_pipeline_zero_s_deficit(profile_with_sulfates, deficits_zero_s, mock_catalog):
    """
    SMOKE TEST: Pipeline with S=0 must complete in < 0.2s
    and remove all sulfate contributions.
    """
    profile, elapsed = run_pipeline(profile_with_sulfates, deficits_zero_s, mock_catalog)
    
    # Must complete quickly
    assert elapsed < 0.2, f"Pipeline took {elapsed:.3f}s - exceeds 0.2s limit (possible loop)"
    
    # Must return valid profile
    assert profile is not None
    assert 'fertilizers' in profile
    
    # S must be 0 (all sulfates removed or zeroed)
    total_s = 0
    for fert in profile['fertilizers']:
        fert_id = fert.get('id', '')
        dose = fert.get('dose_kg_ha', 0)
        if fert_id == 'ammonium_sulfate':
            total_s += dose * 0.24
        elif fert_id == 'magnesium_sulfate':
            total_s += dose * 0.13
    
    assert total_s <= 0.01, f"S must be ~0 when deficit=0, got {total_s:.2f} kg"
    
    print(f"\n[SMOKE] Pipeline completed in {elapsed*1000:.1f}ms")
    print(f"[SMOKE] S contribution: {total_s:.4f} kg (should be ~0)")


def test_smoke_catalog_incompatible(deficits_low_s, sulfate_only_catalog):
    """
    SMOKE TEST: When catalog has no S-free N sources, must raise
    SulfurCapError cleanly without hanging.
    """
    profile = {
        'fertilizers': [
            {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'dose_kg_ha': 20},
        ]
    }
    
    start = time.perf_counter()
    
    try:
        result = cap_fertilizers_by_nutrient(
            profile, deficits_low_s, sulfate_only_catalog,
            max_coverage_pct=110,
            nutrient='S',
            num_applications=10
        )
        elapsed = time.perf_counter() - start
        
        # Should have raised error, but if not, check for cap_error or optimization_failed
        assert elapsed < 0.2, f"Took {elapsed:.3f}s - exceeds limit"
        assert 'cap_error' in result or 'optimization_failed' in result, \
            "Should indicate failure when no S-free alternatives exist"
        
    except SulfurCapError as e:
        elapsed = time.perf_counter() - start
        assert elapsed < 0.2, f"Exception path took {elapsed:.3f}s - exceeds limit"
        assert "S-free" in str(e) or "alternatives" in str(e) or "exceeds" in str(e), \
            "Error message should mention S-free alternatives"
        print(f"\n[SMOKE] Correctly raised SulfurCapError in {elapsed*1000:.1f}ms")
        print(f"[SMOKE] Error: {e}")


def test_smoke_multiple_sulfates(mock_catalog):
    """
    SMOKE TEST: Profile with multiple sulfate fertilizers
    must be capped correctly without loops.
    """
    profile = {
        'fertilizers': [
            {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'dose_kg_ha': 10},
            {'id': 'magnesium_sulfate', 'name': 'Sulfato de Magnesio', 'dose_kg_ha': 10},
        ]
    }
    deficits = {
        'N': 5.0,
        'P2O5': 0,
        'K2O': 0,
        'Ca': 0,
        'Mg': 1.0,
        'S': 1.0  # Low S deficit
    }
    
    profile, elapsed = run_pipeline(profile, deficits, mock_catalog)
    
    assert elapsed < 0.2, f"Pipeline took {elapsed:.3f}s - exceeds limit"
    
    # Calculate S
    total_s = 0
    for fert in profile['fertilizers']:
        fert_id = fert.get('id', '')
        dose = fert.get('dose_kg_ha', 0)
        if fert_id == 'ammonium_sulfate':
            total_s += dose * 0.24
        elif fert_id == 'magnesium_sulfate':
            total_s += dose * 0.13
    
    max_s = deficits['S'] * 1.10
    assert total_s <= max_s + 0.01, f"S must be ≤{max_s:.2f} kg, got {total_s:.2f} kg"
    
    print(f"\n[SMOKE] Multi-sulfate completed in {elapsed*1000:.1f}ms, S={total_s:.2f} kg")


def test_smoke_no_capping_needed(mock_catalog):
    """
    SMOKE TEST: When S is already within limits, pipeline should
    pass through quickly without modifications.
    """
    profile = {
        'fertilizers': [
            {'id': 'calcium_nitrate', 'name': 'Nitrato de Calcio', 'dose_kg_ha': 50},
            {'id': 'map', 'name': 'MAP', 'dose_kg_ha': 20},
        ]
    }
    deficits = {
        'N': 10.0,
        'P2O5': 12.0,
        'K2O': 0,
        'Ca': 10.0,
        'Mg': 0,
        'S': 5.0  # Sufficient S deficit - no aggressive cap needed
    }
    
    profile, elapsed = run_pipeline(profile, deficits, mock_catalog)
    
    assert elapsed < 0.1, f"No-cap pipeline took {elapsed:.3f}s - should be instant"
    assert 'fertilizers' in profile
    
    print(f"\n[SMOKE] Pass-through completed in {elapsed*1000:.1f}ms")


def test_smoke_many_small_sulfates(mock_catalog):
    """
    REGRESSION TEST: Many small sulfate doses where individual S contributions
    are under max but TOTAL exceeds cap. PRE-CAP must calculate N loss using
    total excess, not per-fertilizer excess.
    """
    profile = {
        'fertilizers': [
            {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'dose_kg_ha': 5},
            {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio 2', 'dose_kg_ha': 5},
            {'id': 'magnesium_sulfate', 'name': 'Sulfato de Magnesio', 'dose_kg_ha': 5},
            {'id': 'magnesium_sulfate', 'name': 'Sulfato de Magnesio 2', 'dose_kg_ha': 5},
        ]
    }
    deficits = {
        'N': 5.0,
        'P2O5': 0,
        'K2O': 0,
        'Ca': 0,
        'Mg': 1.0,
        'S': 1.0  # Low S deficit, total S from 4 sulfates ~3 kg
    }
    
    profile, elapsed = run_pipeline(profile, deficits, mock_catalog)
    
    assert elapsed < 0.2, f"Pipeline took {elapsed:.3f}s - exceeds limit"
    
    # Calculate S
    total_s = 0
    for fert in profile['fertilizers']:
        fert_id = fert.get('id', '')
        dose = fert.get('dose_kg_ha', 0)
        if fert_id == 'ammonium_sulfate':
            total_s += dose * 0.24
        elif fert_id == 'magnesium_sulfate':
            total_s += dose * 0.13
    
    max_s = deficits['S'] * 1.10
    assert total_s <= max_s + 0.01, f"S must be ≤{max_s:.2f} kg, got {total_s:.2f} kg"
    
    print(f"\n[SMOKE] Many-small-sulfates completed in {elapsed*1000:.1f}ms, S={total_s:.2f} kg")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])

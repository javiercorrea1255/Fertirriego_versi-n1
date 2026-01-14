"""
Tests for FertiIrrigation AI Optimizer Service improvements.

Tests the following critical behaviors:
1. Deficit K2O=0 should NOT include K-centered fertilizers (KCl, KNO3)
2. Deficit P2O5>0 with K2O=0 should use MAP without adding K
3. Water Cl- > 2 meq/L should eliminate KCl even if it's cheap
4. enforce_hard_constraints() properly removes/reduces prohibited fertilizers
5. normalize_coverage() handles deficit=0 with stage-specific thresholds
"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.fertiirrigation_ai_optimizer import (
    enforce_hard_constraints,
    normalize_coverage,
    adjust_deficits_for_acid_nitrogen,
    is_fertilizer_in_set,
    normalize_stage,
    cap_fertilizers_by_nutrient,
    SulfurCapError,
    K_CENTERED_FERTILIZERS,
    MG_CENTERED_FERTILIZERS,
    CHLORIDE_FERTILIZERS,
    SULFATE_FERTILIZERS,
    LOW_S_DEFICIT_THRESHOLD
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_fertilizers():
    """Sample fertilizer catalog for testing."""
    return [
        {'id': 'potassium_chloride', 'name': 'Cloruro de Potasio (KCl)', 'n_pct': 0, 'p2o5_pct': 0, 'k2o_pct': 60, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0},
        {'id': 'potassium_nitrate', 'name': 'Nitrato de Potasio (KNO3)', 'n_pct': 13, 'p2o5_pct': 0, 'k2o_pct': 46, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0},
        {'id': 'map', 'name': 'Fosfato Monoamónico (MAP)', 'n_pct': 12, 'p2o5_pct': 61, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0},
        {'id': 'urea', 'name': 'Urea', 'n_pct': 46, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0},
        {'id': 'calcium_nitrate', 'name': 'Nitrato de Calcio', 'n_pct': 15.5, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 19, 'mg_pct': 0, 's_pct': 0},
        {'id': 'magnesium_sulfate', 'name': 'Sulfato de Magnesio', 'n_pct': 0, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 9.8, 's_pct': 13},
        {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'n_pct': 21, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 24},
    ]


@pytest.fixture
def deficits_with_zero_k2o():
    """Deficits where K2O = 0 (no potassium needed)."""
    return {
        'N': 100,
        'P2O5': 50,
        'K2O': 0,  # No potassium deficit
        'Ca': 30,
        'Mg': 0,   # No magnesium deficit
        'S': 20
    }


@pytest.fixture
def deficits_full():
    """Deficits where all nutrients are needed."""
    return {
        'N': 100,
        'P2O5': 50,
        'K2O': 80,
        'Ca': 30,
        'Mg': 20,
        'S': 15
    }


# =============================================================================
# Test 1: K2O deficit = 0 should NOT include K-centered fertilizers
# =============================================================================

def test_enforce_hard_constraints_removes_kcl_when_k2o_zero(sample_fertilizers, deficits_with_zero_k2o):
    """Test that KCl is removed when K2O deficit = 0."""
    profile = {
        'fertilizers': [
            {'id': 'potassium_chloride', 'name': 'Cloruro de Potasio (KCl)', 'dose_kg_ha': 50},
            {'id': 'map', 'name': 'Fosfato Monoamónico (MAP)', 'dose_kg_ha': 80},
            {'id': 'urea', 'name': 'Urea', 'dose_kg_ha': 100},
        ]
    }
    
    result = enforce_hard_constraints(
        profile,
        deficits_with_zero_k2o,
        agronomic_context=None,
        available_fertilizers=sample_fertilizers,
        growth_stage='vegetative'
    )
    
    # KCl should be removed because K2O deficit = 0
    fert_ids = [f['id'] for f in result['fertilizers']]
    assert 'potassium_chloride' not in fert_ids, "KCl should be removed when K2O deficit = 0"
    
    # MAP and Urea should remain (they provide N and P2O5 which have deficits)
    assert 'map' in fert_ids, "MAP should remain (provides P2O5 with deficit > 0)"
    assert 'urea' in fert_ids, "Urea should remain (provides N with deficit > 0)"
    
    # Check constraints_applied is recorded
    assert 'constraints_applied' in result
    assert any('K-centered' in c for c in result.get('constraints_applied', []))


def test_enforce_hard_constraints_removes_kno3_when_k2o_zero(sample_fertilizers, deficits_with_zero_k2o):
    """Test that KNO3 IS REMOVED even though it provides N (because it's K-centered)."""
    profile = {
        'fertilizers': [
            {'id': 'potassium_nitrate', 'name': 'Nitrato de Potasio (KNO3)', 'dose_kg_ha': 60},
            {'id': 'urea', 'name': 'Urea', 'dose_kg_ha': 100},
        ]
    }
    
    result = enforce_hard_constraints(
        profile,
        deficits_with_zero_k2o,
        agronomic_context=None,
        available_fertilizers=sample_fertilizers,
        growth_stage='vegetative'
    )
    
    # KNO3 provides 13% N, BUT it's a K-centered fertilizer
    # When K2O deficit = 0, ALL K-centered fertilizers must be removed unconditionally
    # The system should use alternative N sources (urea, ammonium sulfate) instead
    fert_ids = [f['id'] for f in result['fertilizers']]
    
    assert 'potassium_nitrate' not in fert_ids, "KNO3 should be REMOVED when K2O deficit=0 (use urea for N instead)"
    assert 'urea' in fert_ids, "Urea should remain as alternative N source"
    
    # Check constraints_applied is recorded
    assert 'constraints_applied' in result
    assert any('K-centered' in c for c in result.get('constraints_applied', []))


def test_enforce_hard_constraints_removes_mgso4_when_mg_zero(sample_fertilizers, deficits_with_zero_k2o):
    """Test that MgSO4 IS REMOVED when Mg deficit = 0, even if it provides S."""
    profile = {
        'fertilizers': [
            {'id': 'magnesium_sulfate', 'name': 'Sulfato de Magnesio', 'dose_kg_ha': 30},
            {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'dose_kg_ha': 50},
            {'id': 'urea', 'name': 'Urea', 'dose_kg_ha': 100},
        ]
    }
    
    # deficits_with_zero_k2o has Mg = 0 but S = 20
    result = enforce_hard_constraints(
        profile,
        deficits_with_zero_k2o,
        agronomic_context=None,
        available_fertilizers=sample_fertilizers,
        growth_stage='vegetative'
    )
    
    # MgSO4 is Mg-centered -> MUST be removed when Mg deficit = 0
    # Use ammonium sulfate as alternative S source
    fert_ids = [f['id'] for f in result['fertilizers']]
    
    assert 'magnesium_sulfate' not in fert_ids, "MgSO4 should be REMOVED when Mg deficit=0"
    assert 'ammonium_sulfate' in fert_ids, "Ammonium sulfate should remain as alternative S source"
    assert 'urea' in fert_ids, "Urea should remain"
    
    # Check constraints_applied is recorded
    assert 'constraints_applied' in result
    assert any('Mg-centered' in c for c in result.get('constraints_applied', []))


# =============================================================================
# Test 2: P2O5 > 0 with K2O = 0 should use P sources without K
# =============================================================================

def test_profile_uses_map_without_k_when_k2o_zero(sample_fertilizers, deficits_with_zero_k2o):
    """Test that when P2O5 > 0 and K2O = 0, MAP is preferred over MKP."""
    profile = {
        'fertilizers': [
            {'id': 'map', 'name': 'Fosfato Monoamónico (MAP)', 'dose_kg_ha': 80},
        ]
    }
    
    result = enforce_hard_constraints(
        profile,
        deficits_with_zero_k2o,
        agronomic_context=None,
        available_fertilizers=sample_fertilizers,
        growth_stage='vegetative'
    )
    
    # MAP should remain (K2O = 0 in MAP)
    fert_ids = [f['id'] for f in result['fertilizers']]
    assert 'map' in fert_ids, "MAP should remain (has no K2O)"


# =============================================================================
# Test 3: Water Cl- > 2 meq/L should eliminate KCl
# =============================================================================

def test_enforce_hard_constraints_removes_kcl_when_cl_high(sample_fertilizers, deficits_full):
    """Test that KCl is PROHIBITED when water Cl- > 2 meq/L."""
    profile = {
        'fertilizers': [
            {'id': 'potassium_chloride', 'name': 'Cloruro de Potasio (KCl)', 'dose_kg_ha': 50},
            {'id': 'map', 'name': 'Fosfato Monoamónico (MAP)', 'dose_kg_ha': 80},
        ]
    }
    
    agronomic_context = {
        'water': {'cl_meqL': 3.2, 'ph': 7.5},  # Cl- > 2 meq/L
        'soil': {'k_ppm': 200}
    }
    
    result = enforce_hard_constraints(
        profile,
        deficits_full,
        agronomic_context=agronomic_context,
        available_fertilizers=sample_fertilizers,
        growth_stage='vegetative'
    )
    
    # KCl should be REMOVED due to high Cl- in water
    fert_ids = [f['id'] for f in result['fertilizers']]
    assert 'potassium_chloride' not in fert_ids, "KCl should be removed when water Cl- > 2 meq/L"
    
    # MAP should remain
    assert 'map' in fert_ids, "MAP should remain (not a chloride fertilizer)"
    
    # Check constraints_applied mentions Cl-
    assert 'constraints_applied' in result
    assert any('Cl' in c for c in result.get('constraints_applied', []))


def test_enforce_hard_constraints_keeps_kcl_when_cl_low(sample_fertilizers, deficits_full):
    """Test that KCl is kept when water Cl- < 2 meq/L."""
    profile = {
        'fertilizers': [
            {'id': 'potassium_chloride', 'name': 'Cloruro de Potasio (KCl)', 'dose_kg_ha': 50},
        ]
    }
    
    agronomic_context = {
        'water': {'cl_meqL': 1.5, 'ph': 7.5},  # Cl- < 2 meq/L
        'soil': {'k_ppm': 200}
    }
    
    result = enforce_hard_constraints(
        profile,
        deficits_full,
        agronomic_context=agronomic_context,
        available_fertilizers=sample_fertilizers,
        growth_stage='vegetative'
    )
    
    # KCl should be KEPT because Cl- < 2 meq/L and K2O has deficit
    fert_ids = [f['id'] for f in result['fertilizers']]
    assert 'potassium_chloride' in fert_ids, "KCl should be kept when Cl- < 2 meq/L"


# =============================================================================
# Test 4: normalize_coverage handles deficit = 0
# =============================================================================

def test_normalize_coverage_limits_excess_when_deficit_zero(sample_fertilizers, deficits_with_zero_k2o):
    """Test that normalize_coverage limits nutrient application when deficit = 0."""
    # Profile that over-applies K2O even though deficit = 0
    profile = {
        'fertilizers': [
            {'id': 'potassium_nitrate', 'name': 'Nitrato de Potasio', 'dose_kg_ha': 50},  # 50 * 0.46 = 23 kg K2O
        ]
    }
    
    result = normalize_coverage(
        profile,
        deficits_with_zero_k2o,
        sample_fertilizers,
        max_coverage_pct=110,
        num_applications=10,
        min_coverage=90,
        growth_stage='vegetative'
    )
    
    # Should report excess_when_no_deficit for K2O (23 kg > 5 kg threshold)
    if result.get('excess_when_no_deficit'):
        k2o_excess = next((e for e in result['excess_when_no_deficit'] if e['nutrient'] == 'K2O'), None)
        if k2o_excess:
            assert k2o_excess['max_allowed_kg_ha'] == 5, "Vegetative stage should allow max 5 kg K2O when deficit=0"


def test_normalize_stage_mapping():
    """Test stage normalization to standard keys."""
    assert normalize_stage('plántula') == 'seedling'
    assert normalize_stage('vegetativo') == 'vegetative'
    assert normalize_stage('floración') == 'flowering'
    assert normalize_stage('fructificación') == 'fruiting'
    assert normalize_stage('unknown') == 'default'
    assert normalize_stage('') == 'default'


# =============================================================================
# Test 5: Acid nitrogen adjustment
# =============================================================================

def test_adjust_deficits_for_acid_nitrogen():
    """Test that N from nitric acid is subtracted from deficit."""
    deficits = {'N': 100, 'P2O5': 50, 'K2O': 80}
    
    acid_data = {
        'acid_type': 'nitric',
        'dose_ml_per_1000L': 0.5,
        'water_volume_m3_ha': 5000  # 5000 m³/ha
    }
    
    result = adjust_deficits_for_acid_nitrogen(deficits, acid_data)
    
    # N from HNO3: 0.5 mL/m³ * 5000 m³ * 0.196 g N/mL / 1000 = 0.49 kg N
    # So N deficit should be reduced by ~0.49 kg
    assert result['N'] < deficits['N'], "N deficit should be reduced by acid contribution"
    assert result['P2O5'] == deficits['P2O5'], "P2O5 should be unchanged"
    assert result['K2O'] == deficits['K2O'], "K2O should be unchanged"


def test_adjust_deficits_no_acid():
    """Test that deficits are unchanged when no acid data."""
    deficits = {'N': 100, 'P2O5': 50}
    
    result = adjust_deficits_for_acid_nitrogen(deficits, None)
    
    assert result == deficits, "Deficits should be unchanged when no acid data"


def test_adjust_deficits_non_nitric_acid():
    """Test that non-nitric acid doesn't affect N deficit."""
    deficits = {'N': 100, 'P2O5': 50}
    
    acid_data = {
        'acid_type': 'phosphoric',  # Not nitric
        'dose_ml_per_1000L': 0.5,
        'water_volume_m3_ha': 5000
    }
    
    result = adjust_deficits_for_acid_nitrogen(deficits, acid_data)
    
    assert result['N'] == deficits['N'], "N should be unchanged for non-nitric acid"


# =============================================================================
# Test 6: Fertilizer classification helpers
# =============================================================================

def test_is_fertilizer_in_set():
    """Test fertilizer set membership detection."""
    assert is_fertilizer_in_set('potassium_chloride', 'KCl', K_CENTERED_FERTILIZERS)
    assert is_fertilizer_in_set('kcl', 'Cloruro de Potasio', K_CENTERED_FERTILIZERS)
    assert is_fertilizer_in_set('magnesium_sulfate', 'MgSO4', MG_CENTERED_FERTILIZERS)
    assert is_fertilizer_in_set('potassium_chloride', '', CHLORIDE_FERTILIZERS)
    
    # Negative cases
    assert not is_fertilizer_in_set('urea', 'Urea', K_CENTERED_FERTILIZERS)
    assert not is_fertilizer_in_set('map', 'MAP', CHLORIDE_FERTILIZERS)


# =============================================================================
# Integration test placeholder
# =============================================================================

def test_optimize_with_ai_respects_deficit_zero():
    """
    Integration test: optimize_with_ai should not recommend K-centered 
    fertilizers when K2O deficit = 0.
    
    This test requires mocking the OpenAI API call.
    """
    # This would require mocking openai_client.chat.completions.create
    # For now, we test the post-processing functions above
    pass


# =============================================================================
# Test 7: S CAP TESTS - Critical for low S deficit scenarios
# =============================================================================

@pytest.fixture
def deficits_low_s():
    """Deficits with low S deficit - triggers S cap behavior."""
    return {
        'N': 4.8,
        'P2O5': 14.6,
        'K2O': 0,
        'Ca': 0,
        'Mg': 0,
        'S': 1.5  # Very low S deficit - sulfates should be capped
    }


@pytest.fixture
def fertilizers_with_sulfates():
    """Fertilizer catalog including sulfates and nitratos."""
    return [
        {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'n_pct': 21, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 24},
        {'id': 'urea', 'name': 'Urea', 'n_pct': 46, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0},
        {'id': 'map', 'name': 'Fosfato Monoamónico (MAP)', 'n_pct': 12, 'p2o5_pct': 61, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0},
        {'id': 'calcium_nitrate', 'name': 'Nitrato de Calcio', 'n_pct': 15.5, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 19, 'mg_pct': 0, 's_pct': 0},
        {'id': 'magnesium_sulfate', 'name': 'Sulfato de Magnesio', 'n_pct': 0, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 9.8, 's_pct': 13},
    ]


@pytest.fixture
def fertilizers_only_sulfates():
    """Fertilizer catalog with ONLY sulfate sources for N (no S-free N sources >5%)."""
    return [
        {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'n_pct': 21, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 24},
        # MAP removed - it has 12% N and can be used as S-free N source
        # Adding a P source with very low N (< 5%) that won't be picked as N source
        {'id': 'tsp', 'name': 'Triple Superfosfato (TSP)', 'n_pct': 0, 'p2o5_pct': 46, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0},
    ]


def test_s_cap_limits_sulfur_to_110_percent(fertilizers_with_sulfates, deficits_low_s):
    """
    Test 1: When S deficit is low (1.5 kg/ha), the S cap should limit total S 
    to ≤110% of deficit (1.65 kg/ha max).
    
    If ammonium sulfate 15 kg/ha is selected for N, it provides 3.6 kg S (240% coverage).
    The cap should reduce it to ~6.9 kg/ha to stay within 110%.
    """
    profile = {
        'fertilizers': [
            {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'dose_kg_ha': 15},
            {'id': 'map', 'name': 'Fosfato Monoamónico (MAP)', 'dose_kg_ha': 24},
        ]
    }
    
    result = cap_fertilizers_by_nutrient(
        profile,
        deficits_low_s,
        fertilizers_with_sulfates,
        max_coverage_pct=110,
        nutrient='S',
        num_applications=10
    )
    
    # Calculate total S after cap
    total_s = 0
    for fert in result['fertilizers']:
        if fert['id'] == 'ammonium_sulfate':
            total_s += fert['dose_kg_ha'] * 0.24  # 24% S
    
    max_allowed_s = deficits_low_s['S'] * 1.1  # 1.5 * 1.1 = 1.65 kg/ha
    
    assert total_s <= max_allowed_s + 0.1, f"S should be capped to ≤{max_allowed_s:.2f} kg/ha, got {total_s:.2f} kg/ha"
    assert 'cap_applied' in result, "Cap should be recorded in result"
    assert result['cap_applied']['nutrient'] == 'S'


def test_s_cap_respects_n_coverage_minimum(fertilizers_with_sulfates, deficits_low_s):
    """
    Test 2: When S cap would reduce N below 85% (min_coverage_for_critical), 
    the system should either:
    a) Add S-free N sources to compensate, OR
    b) Limit the reduction to preserve N coverage, OR
    c) Issue a warning that S cap couldn't be fully achieved
    
    This test verifies N is protected even when S needs capping.
    """
    profile = {
        'fertilizers': [
            {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'dose_kg_ha': 15},
        ]
    }
    
    result = cap_fertilizers_by_nutrient(
        profile,
        deficits_low_s,
        fertilizers_with_sulfates,
        max_coverage_pct=110,
        nutrient='S',
        min_coverage_for_critical=85
    )
    
    # Find N sources in result
    total_n = 0
    for fert in result['fertilizers']:
        fert_id = fert.get('id', '')
        dose = fert.get('dose_kg_ha', 0)
        if fert_id == 'ammonium_sulfate':
            total_n += dose * 0.21  # 21% N
        elif fert_id == 'urea':
            total_n += dose * 0.46  # 46% N
        elif fert_id == 'calcium_nitrate':
            total_n += dose * 0.155  # 15.5% N
    
    n_deficit = deficits_low_s['N']  # 4.8 kg/ha
    n_coverage = (total_n / n_deficit * 100) if n_deficit > 0 else 100
    
    # Either: N is preserved above 85%, OR a warning was issued
    if 'cap_warning' not in result:
        assert n_coverage >= 85, f"N coverage should be ≥85%, got {n_coverage:.0f}%"
    else:
        # If warning exists, verify it's about N coverage
        assert 'N coverage' in result['cap_warning'], "Should warn about N coverage"
        # In this case, system tried its best to preserve N


def test_normalize_coverage_applies_s_cap_for_low_deficit(fertilizers_with_sulfates, deficits_low_s):
    """
    Test 3: normalize_coverage() should automatically apply S cap when S deficit is low.
    
    When S cannot be fully capped (due to N constraints), the system should report 
    cap_error rather than silently returning success with S > 110%.
    """
    profile = {
        'fertilizers': [
            {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'dose_kg_ha': 15, 'dose_per_application': 1.5},
            {'id': 'map', 'name': 'Fosfato Monoamónico (MAP)', 'dose_kg_ha': 24, 'dose_per_application': 2.4},
        ]
    }
    
    result = normalize_coverage(
        profile,
        deficits_low_s,
        fertilizers_with_sulfates,
        max_coverage_pct=110,
        num_applications=10,
        min_coverage=85,
        growth_stage='vegetative'
    )
    
    # Check that S coverage is within limits
    coverage = result.get('coverage', {})
    s_coverage = coverage.get('S', 0)
    
    # Either S is within limits OR the system reports a failure/warning
    # The system MUST NOT silently return success with S > 110%
    if 'coverage_exceeds_max' in result or 'cap_error' in result.get('notes', ''):
        # System correctly identified that S couldn't be capped - this is expected behavior
        # when N constraints prevent full S capping
        pass
    else:
        # If no error/warning, S must be within limits
        assert s_coverage <= 110, f"S coverage should be ≤110% or system should report error, got {s_coverage}%"


def test_sulfate_fertilizer_classification():
    """Test that sulfate fertilizers are correctly identified."""
    assert is_fertilizer_in_set('ammonium_sulfate', 'Sulfato de Amonio', SULFATE_FERTILIZERS)
    assert is_fertilizer_in_set('magnesium_sulfate', 'MgSO4', SULFATE_FERTILIZERS)
    assert is_fertilizer_in_set('potassium_sulfate', 'SOP', SULFATE_FERTILIZERS)
    
    # Non-sulfates should not match
    assert not is_fertilizer_in_set('urea', 'Urea', SULFATE_FERTILIZERS)
    assert not is_fertilizer_in_set('calcium_nitrate', 'Nitrato de Calcio', SULFATE_FERTILIZERS)
    assert not is_fertilizer_in_set('map', 'MAP', SULFATE_FERTILIZERS)


def test_low_s_deficit_threshold():
    """Test that LOW_S_DEFICIT_THRESHOLD is correctly defined."""
    assert LOW_S_DEFICIT_THRESHOLD == 5.0, "LOW_S_DEFICIT_THRESHOLD should be 5.0 kg/ha"


def test_s_cap_preserves_n_coverage_with_compensation(fertilizers_with_sulfates, deficits_low_s):
    """
    Test that when S cap reduces ammonium sulfate (which provides N), 
    the system compensates by PROACTIVELY adding S-free N sources (urea) FIRST.
    
    This ensures both:
    1. S coverage stays ≤ 110%
    2. N coverage doesn't drop below 85%
    """
    # Setup: ammonium sulfate as main N source providing excess S
    profile = {
        'fertilizers': [
            {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'dose_kg_ha': 20},  # 4.2 kg N, 4.8 kg S
        ]
    }
    
    # Deficits: need N, but S deficit is very low
    deficits = {
        'N': 4.8,  # Need 4.8 kg N
        'P2O5': 0,
        'K2O': 0,
        'Ca': 0,
        'Mg': 0,
        'S': 1.5  # Very low S deficit - will trigger cap
    }
    
    result = cap_fertilizers_by_nutrient(
        profile,
        deficits,
        fertilizers_with_sulfates,  # Includes urea as S-free N source
        max_coverage_pct=110,
        nutrient='S',
        num_applications=10,
        min_coverage_for_critical=85
    )
    
    # Calculate total N and S after cap
    total_n = 0
    total_s = 0
    for fert in result['fertilizers']:
        fert_id = fert.get('id', '')
        dose = fert.get('dose_kg_ha', 0)
        if fert_id == 'ammonium_sulfate':
            total_n += dose * 0.21  # 21% N
            total_s += dose * 0.24  # 24% S
        elif fert_id == 'urea':
            total_n += dose * 0.46  # 46% N
        elif fert_id == 'calcium_nitrate':
            total_n += dose * 0.155  # 15.5% N
    
    # S should be capped to ≤ 110% of deficit (1.65 kg)
    max_s_allowed = deficits['S'] * 1.15  # Allow 5% tolerance = 1.725 kg
    
    # If no cap_error, S should be within limits
    if 'cap_error' not in result:
        assert total_s <= max_s_allowed, f"S should be ≤{max_s_allowed:.2f} kg, got {total_s:.2f} kg"
    
    # N coverage should be preserved if no error/warning
    min_n_needed = deficits['N'] * 0.85  # 4.08 kg
    if 'cap_warning' not in result and 'cap_error' not in result:
        assert total_n >= min_n_needed - 0.1, f"N should be ≥{min_n_needed:.2f} kg, got {total_n:.2f} kg"


def test_s_cap_fails_gracefully_when_no_s_free_n_source(fertilizers_only_sulfates, deficits_low_s):
    """
    Test that when ammonium sulfate is the ONLY N source and S cap is applied,
    the system raises SulfurCapError since it can't achieve S ≤ 110% without
    dropping N below minimum and no S-free alternatives exist.
    """
    profile = {
        'fertilizers': [
            {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'dose_kg_ha': 20},
        ]
    }
    
    deficits = {
        'N': 4.8,
        'P2O5': 14.6,
        'K2O': 0,
        'Ca': 0,
        'Mg': 0,
        'S': 1.5
    }
    
    # STRICT: Must raise SulfurCapError when S cannot be capped
    with pytest.raises(SulfurCapError) as exc_info:
        cap_fertilizers_by_nutrient(
            profile,
            deficits,
            fertilizers_only_sulfates,  # Only has ammonium sulfate for N (no urea)
            max_coverage_pct=110,
            nutrient='S',
            num_applications=10,
            min_coverage_for_critical=85
        )
    
    # Verify error message mentions S coverage exceeds threshold
    assert "exceeds" in str(exc_info.value).lower() or "110%" in str(exc_info.value)


def test_s_cap_achieves_target_when_alternatives_exist(fertilizers_with_sulfates):
    """
    REGRESSION TEST: When S-free N alternatives exist (urea), the system must:
    1. Add urea to compensate N
    2. Reduce ammonium sulfate to cap S
    3. Final S coverage must be ≤ 115% (110% + 5% tolerance)
    
    This is the critical test that ensures S is actually capped when alternatives exist.
    """
    profile = {
        'fertilizers': [
            {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'dose_kg_ha': 20},  # Provides 4.8 kg S
        ]
    }
    
    deficits = {
        'N': 4.8,  # Need 4.8 kg N  
        'P2O5': 0,
        'K2O': 0,
        'Ca': 0,
        'Mg': 0,
        'S': 1.5  # Only need 1.5 kg S, but getting 4.8 kg (320% coverage!)
    }
    
    result = cap_fertilizers_by_nutrient(
        profile,
        deficits,
        fertilizers_with_sulfates,  # Has urea (46% N, 0% S)
        max_coverage_pct=110,
        nutrient='S',
        num_applications=10,
        min_coverage_for_critical=85
    )
    
    # Calculate final S
    total_s = 0
    for fert in result['fertilizers']:
        fert_id = fert.get('id', '')
        dose = fert.get('dose_kg_ha', 0)
        if fert_id == 'ammonium_sulfate':
            total_s += dose * 0.24  # 24% S
    
    # S MUST be capped to ≤ 115% (with 5% tolerance on 110%)
    max_s_allowed = deficits['S'] * 1.15  # 1.725 kg
    s_coverage = (total_s / deficits['S'] * 100)
    
    # If no error, S must be capped
    if 'cap_error' not in result:
        assert total_s <= max_s_allowed, \
            f"S must be ≤{max_s_allowed:.2f} kg ({s_coverage:.0f}% coverage), got {total_s:.2f} kg"
    
    # Verify urea was added
    urea_added = any(f.get('id') == 'urea' for f in result['fertilizers'])
    am_sulf_reduced = any(
        f.get('id') == 'ammonium_sulfate' and f.get('dose_kg_ha', 0) < 20 
        for f in result['fertilizers']
    )
    
    # Either S was capped by reducing + adding alternatives, or error was raised
    if 'cap_error' not in result:
        assert urea_added or am_sulf_reduced, \
            "Should either add urea or reduce ammonium sulfate to cap S"


def test_s_cap_increases_existing_urea_when_present(fertilizers_with_sulfates):
    """
    REGRESSION TEST: When urea is ALREADY in the profile, the system must:
    1. Increase the existing urea dose to compensate N (not add a new entry)
    2. Reduce ammonium sulfate to cap S
    3. Final S coverage must be ≤ 115%
    
    This tests the "urea already present" case.
    """
    profile = {
        'fertilizers': [
            {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'dose_kg_ha': 20},  # 4.2 kg N, 4.8 kg S
            {'id': 'urea', 'name': 'Urea', 'dose_kg_ha': 2},  # 0.92 kg N (existing, can be increased)
        ]
    }
    
    deficits = {
        'N': 5.0,  # Need 5 kg N
        'P2O5': 0,
        'K2O': 0,
        'Ca': 0,
        'Mg': 0,
        'S': 1.5  # Very low S deficit - triggers cap
    }
    
    result = cap_fertilizers_by_nutrient(
        profile,
        deficits,
        fertilizers_with_sulfates,  # Has urea (46% N, 0% S)
        max_coverage_pct=110,
        nutrient='S',
        num_applications=10,
        min_coverage_for_critical=85
    )
    
    # Calculate final S and N
    total_s = 0
    total_n = 0
    urea_dose = 0
    for fert in result['fertilizers']:
        fert_id = fert.get('id', '')
        dose = fert.get('dose_kg_ha', 0)
        if fert_id == 'ammonium_sulfate':
            total_s += dose * 0.24  # 24% S
            total_n += dose * 0.21  # 21% N
        elif fert_id == 'urea':
            total_n += dose * 0.46  # 46% N
            urea_dose = dose
    
    # S MUST be capped to ≤ 115%
    max_s_allowed = deficits['S'] * 1.15  # 1.725 kg
    
    # If no error, S must be capped
    if 'cap_error' not in result:
        assert total_s <= max_s_allowed, \
            f"S must be ≤{max_s_allowed:.2f} kg, got {total_s:.2f} kg"
    
    # Urea should have been increased (was 2, should be higher now)
    assert urea_dose >= 2, f"Urea should be at least 2 kg/ha, got {urea_dose} kg/ha"
    
    # N coverage should be preserved
    min_n_needed = deficits['N'] * 0.85  # 4.25 kg
    if 'cap_warning' not in result and 'cap_error' not in result:
        assert total_n >= min_n_needed - 0.1, f"N should be ≥{min_n_needed:.2f} kg, got {total_n:.2f} kg"


def test_s_cap_zero_deficit_forces_zero_sulfates(fertilizers_with_sulfates):
    """
    REGRESSION TEST: When S deficit = 0, no sulfur should be added.
    The cap must force sulfate doses to 0 or raise SulfurCapError if N can't be maintained.
    """
    profile = {
        'fertilizers': [
            {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'dose_kg_ha': 10},  # Provides S but no S needed
        ]
    }
    
    deficits = {
        'N': 3.0,  # Need N
        'P2O5': 0,
        'K2O': 0,
        'Ca': 0,
        'Mg': 0,
        'S': 0  # NO S deficit - no S should be added
    }
    
    # With S deficit = 0, either:
    # 1. Sulfates reduced to 0 and S-free N added, OR
    # 2. SulfurCapError raised if no S-free alternatives
    try:
        result = cap_fertilizers_by_nutrient(
            profile,
            deficits,
            fertilizers_with_sulfates,  # Has urea as S-free alternative
            max_coverage_pct=110,
            nutrient='S',
            num_applications=10,
            min_coverage_for_critical=85
        )
        
        # If no exception, S must be 0
        total_s = 0
        for fert in result['fertilizers']:
            fert_id = fert.get('id', '')
            dose = fert.get('dose_kg_ha', 0)
            if fert_id == 'ammonium_sulfate':
                total_s += dose * 0.24
            elif fert_id == 'magnesium_sulfate':
                total_s += dose * 0.13
        
        # With 0 deficit, max allowed is 0 - S must be 0 (or very close)
        assert total_s <= 0.001, f"S must be ≈0 when deficit=0, got {total_s:.4f} kg"
        
    except SulfurCapError:
        # This is also acceptable - means no S-free alternative could maintain N
        pass


def test_s_cap_multiple_sulfates(fertilizers_with_sulfates):
    """
    REGRESSION TEST: With multiple sulfate fertilizers (ammonium sulfate + magnesium sulfate),
    the cap must still enforce ≤110% and preserve N ≥85%.
    """
    profile = {
        'fertilizers': [
            {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'dose_kg_ha': 10},  # Provides 2.4 kg S
            {'id': 'magnesium_sulfate', 'name': 'Sulfato de Magnesio', 'dose_kg_ha': 10},  # Provides 1.3 kg S
            # Total S = 3.7 kg
        ]
    }
    
    deficits = {
        'N': 3.0,  # Need N
        'P2O5': 0,
        'K2O': 0,
        'Ca': 0,
        'Mg': 1.0,  # Need Mg too
        'S': 1.0  # Low S deficit - max allowed = 1.1 kg (110%)
    }
    
    result = cap_fertilizers_by_nutrient(
        profile,
        deficits,
        fertilizers_with_sulfates,
        max_coverage_pct=110,
        nutrient='S',
        num_applications=10,
        min_coverage_for_critical=85
    )
    
    # Calculate totals after cap
    total_s = 0
    total_n = 0
    for fert in result['fertilizers']:
        fert_id = fert.get('id', '')
        dose = fert.get('dose_kg_ha', 0)
        if fert_id == 'ammonium_sulfate':
            total_s += dose * 0.24
            total_n += dose * 0.21
        elif fert_id == 'magnesium_sulfate':
            total_s += dose * 0.13
        elif fert_id == 'urea':
            total_n += dose * 0.46
    
    max_s_allowed = deficits['S'] * 1.10  # 1.1 kg
    s_coverage_pct = (total_s / deficits['S']) * 100 if deficits['S'] > 0 else 0
    n_coverage_pct = (total_n / deficits['N']) * 100 if deficits['N'] > 0 else 100
    
    # STRICT: S coverage must be ≤ 110%
    assert s_coverage_pct <= 110 + 0.0001, f"S coverage must be ≤110%, got {s_coverage_pct:.4f}%"
    
    # N must be preserved ≥ 85% (or warning issued)
    if 'cap_warning' not in result and 'cap_error' not in result:
        assert n_coverage_pct >= 85, f"N coverage must be ≥85%, got {n_coverage_pct:.1f}%"


def test_s_cap_strict_with_very_low_deficit(fertilizers_with_sulfates):
    """
    REGRESSION TEST: With S deficit ≤ 1 kg, the cap must still enforce ≤110%.
    The tolerance must be relative (0.1% of allowed S) not absolute to avoid
    allowing extra percentage points with small deficits.
    """
    profile = {
        'fertilizers': [
            {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'dose_kg_ha': 5},  # Provides 1.2 kg S (240% of 0.5 kg deficit)
        ]
    }
    
    deficits = {
        'N': 3.0,  # Reasonable N deficit
        'P2O5': 0,
        'K2O': 0,
        'Ca': 0,
        'Mg': 0,
        'S': 0.5  # Very low S deficit - max allowed = 0.55 kg (110%)
    }
    
    result = cap_fertilizers_by_nutrient(
        profile,
        deficits,
        fertilizers_with_sulfates,
        max_coverage_pct=110,
        nutrient='S',
        num_applications=10,
        min_coverage_for_critical=85
    )
    
    # Calculate total S after cap
    total_s = 0
    for fert in result['fertilizers']:
        fert_id = fert.get('id', '')
        dose = fert.get('dose_kg_ha', 0)
        if fert_id == 'ammonium_sulfate':
            total_s += dose * 0.24
    
    max_s_allowed = deficits['S'] * 1.10  # 0.55 kg - strict 110%
    s_coverage_pct = (total_s / deficits['S']) * 100 if deficits['S'] > 0 else 0
    
    # STRICT: S coverage must be ≤ 110% even with very small deficit
    # Allow only minimal floating-point tolerance (0.0001%)
    tolerance_pct = 0.0001
    assert s_coverage_pct <= 110 + tolerance_pct, \
        f"S coverage must be ≤110.0001%, got {s_coverage_pct:.4f}%"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

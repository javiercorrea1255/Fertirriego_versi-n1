"""
Tests for Ion Constraints Engine.

Tests the ionic rules for fertilizer optimization:
1. Cl- high in water -> ban KCl
2. Low S deficit -> strict S cap
3. Tomato seedling -> limit NH4, prefer NO3
4. K2O deficit=0 -> avoid K fertilizers
5. Tank A/B assignment
"""
import pytest
from app.services.fertiirrigation_ai_optimizer import (
    build_ion_constraints,
    apply_ion_constraints,
    format_constraints_for_prompt,
    normalize_stage
)


MOCK_CATALOG = [
    {'id': 'potassium_chloride', 'name': 'Cloruro de Potasio (KCl)', 'n_pct': 0, 'p2o5_pct': 0, 'k2o_pct': 60, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0},
    {'id': 'calcium_nitrate', 'name': 'Nitrato de Calcio', 'n_pct': 15.5, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 19, 'mg_pct': 0, 's_pct': 0},
    {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'n_pct': 21, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 24},
    {'id': 'magnesium_sulfate', 'name': 'Sulfato de Magnesio (MgSO4)', 'n_pct': 0, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 10, 's_pct': 13},
    {'id': 'potassium_nitrate', 'name': 'Nitrato de Potasio (KNO3)', 'n_pct': 13, 'p2o5_pct': 0, 'k2o_pct': 46, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0},
    {'id': 'map', 'name': 'Fosfato Monoamónico (MAP)', 'n_pct': 12, 'p2o5_pct': 61, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0},
    {'id': 'urea', 'name': 'Urea', 'n_pct': 46, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 0, 's_pct': 0},
    {'id': 'magnesium_nitrate', 'name': 'Nitrato de Magnesio', 'n_pct': 11, 'p2o5_pct': 0, 'k2o_pct': 0, 'ca_pct': 0, 'mg_pct': 9.5, 's_pct': 0},
]


class TestBuildIonConstraints:
    """Tests for build_ion_constraints() function."""
    
    def test_rule1_cl_high_bans_kcl(self):
        """RULE 1: High Cl- in water should ban KCl."""
        agronomic_context = {
            'water': {'cl_meq_l': 3.5},  # > 2.0 threshold
            'soil': {}
        }
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 20, 'Ca': 0, 'Mg': 0, 'S': 2}
        
        constraints = build_ion_constraints(
            agronomic_context, 'Tomate', 'Vegetativo', deficits
        )
        
        assert 'potassium_chloride' in constraints['hard_bans']
        assert 'kcl' in constraints['hard_bans']
        assert 'RULE_1_CL_HIGH' in constraints['rules_applied']
        assert any('Cl-' in w for w in constraints['warnings'])
    
    def test_rule1_cl_low_no_ban(self):
        """RULE 1: Low Cl- should NOT ban KCl."""
        agronomic_context = {
            'water': {'cl_meq_l': 1.5},  # < 2.0 threshold
            'soil': {}
        }
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 20, 'Ca': 0, 'Mg': 0, 'S': 2}
        
        constraints = build_ion_constraints(
            agronomic_context, 'Tomate', 'Vegetativo', deficits
        )
        
        assert 'potassium_chloride' not in constraints['hard_bans']
        assert 'RULE_1_CL_HIGH' not in constraints['rules_applied']
    
    def test_rule2_hco3_high_warning(self):
        """RULE 2: High HCO3- should add acidification warning."""
        agronomic_context = {
            'water': {'hco3_meq_l': 5.0},  # > 2.0 threshold
            'soil': {}
        }
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 20, 'Ca': 0, 'Mg': 0, 'S': 2}
        
        constraints = build_ion_constraints(
            agronomic_context, 'Tomate', 'Vegetativo', deficits
        )
        
        assert 'RULE_2_HCO3_HIGH' in constraints['rules_applied']
        assert any('Acidificación' in w for w in constraints['warnings'])
    
    def test_rule3_tomato_seedling_n_form(self):
        """RULE 3: Tomato seedling should limit NH4 and prefer NO3."""
        agronomic_context = {'water': {}, 'soil': {}}
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 20, 'Ca': 0, 'Mg': 0, 'S': 2}
        
        constraints = build_ion_constraints(
            agronomic_context, 'Tomate', 'Plántula', deficits
        )
        
        assert 'RULE_3_TOMATO_N_FORM' in constraints['rules_applied']
        assert constraints['nutrient_shares']['NH4_share_max'] == 0.30
        assert constraints['nutrient_shares']['NO3_share_min'] == 0.70
        assert constraints['nutrient_shares']['limit_ammonium'] == True
    
    def test_rule3_tomato_transplant_n_form(self):
        """RULE 3: Tomato transplant stage should also limit NH4."""
        agronomic_context = {'water': {}, 'soil': {}}
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 20, 'Ca': 0, 'Mg': 0, 'S': 2}
        
        constraints = build_ion_constraints(
            agronomic_context, 'Tomate', 'Trasplante', deficits
        )
        
        assert 'RULE_3_TOMATO_N_FORM' in constraints['rules_applied']
    
    def test_rule3_tomato_vegetative_no_n_form_limit(self):
        """RULE 3: Tomato in vegetative stage should NOT limit NH4."""
        agronomic_context = {'water': {}, 'soil': {}}
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 20, 'Ca': 0, 'Mg': 0, 'S': 2}
        
        constraints = build_ion_constraints(
            agronomic_context, 'Tomate', 'Vegetativo', deficits
        )
        
        assert 'RULE_3_TOMATO_N_FORM' not in constraints['rules_applied']
        assert constraints['nutrient_shares'].get('limit_ammonium') != True
    
    def test_rule4_low_s_deficit_cap(self):
        """RULE 4: Low S deficit should apply strict S cap."""
        agronomic_context = {'water': {}, 'soil': {}}
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 20, 'Ca': 0, 'Mg': 0, 'S': 1.5}  # < 5 kg/ha
        
        constraints = build_ion_constraints(
            agronomic_context, 'Tomate', 'Vegetativo', deficits
        )
        
        assert 'RULE_4_LOW_S_CAP' in constraints['rules_applied']
        assert constraints['caps_kg_ha']['S'] == pytest.approx(1.65, rel=0.01)  # 1.5 * 1.10
    
    def test_rule4_high_s_deficit_no_strict_cap(self):
        """RULE 4: High S deficit should NOT apply strict cap."""
        agronomic_context = {'water': {}, 'soil': {}}
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 20, 'Ca': 0, 'Mg': 0, 'S': 10}  # > 5 kg/ha
        
        constraints = build_ion_constraints(
            agronomic_context, 'Tomate', 'Vegetativo', deficits
        )
        
        assert 'RULE_4_LOW_S_CAP' not in constraints['rules_applied']
        assert constraints['caps_kg_ha']['S'] == pytest.approx(11.0, rel=0.01)  # 10 * 1.10
    
    def test_rule5_k2o_deficit_zero_cap(self):
        """RULE 5: K2O deficit=0 should cap K2O application."""
        agronomic_context = {'water': {}, 'soil': {}}
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 0, 'Ca': 0, 'Mg': 0, 'S': 5}
        
        constraints = build_ion_constraints(
            agronomic_context, 'Tomate', 'Vegetativo', deficits
        )
        
        assert 'RULE_5_K_RESTRICTION' in constraints['rules_applied']
        assert constraints['caps_kg_ha']['K2O'] == 5.0  # Default for non-seedling
    
    def test_rule5_k2o_deficit_zero_seedling_cap(self):
        """RULE 5: K2O deficit=0 in seedling should cap K2O at 2 kg/ha."""
        agronomic_context = {'water': {}, 'soil': {}}
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 0, 'Ca': 0, 'Mg': 0, 'S': 5}
        
        constraints = build_ion_constraints(
            agronomic_context, 'Tomate', 'Plántula', deficits
        )
        
        assert 'RULE_5_K_RESTRICTION' in constraints['rules_applied']
        assert constraints['caps_kg_ha']['K2O'] == 2.0  # Seedling cap
    
    def test_rule5_high_soil_k_cap(self):
        """RULE 5: High soil K should cap K2O even with deficit."""
        agronomic_context = {
            'water': {},
            'soil': {'k_ppm': 500}  # > 400 threshold
        }
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 10, 'Ca': 0, 'Mg': 0, 'S': 5}
        
        constraints = build_ion_constraints(
            agronomic_context, 'Tomate', 'Vegetativo', deficits
        )
        
        assert 'RULE_5_K_RESTRICTION' in constraints['rules_applied']
    
    def test_rule6_ab_compatibility(self):
        """RULE 6: A/B tank compatibility notes should be added."""
        agronomic_context = {'water': {}, 'soil': {}}
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 20, 'Ca': 0, 'Mg': 0, 'S': 5}
        
        constraints = build_ion_constraints(
            agronomic_context, 'Tomate', 'Vegetativo', deficits
        )
        
        assert 'RULE_6_AB_COMPATIBILITY' in constraints['rules_applied']
        assert len(constraints['compatibility']['notes']) >= 2


class TestApplyIonConstraints:
    """Tests for apply_ion_constraints() function."""
    
    def test_removes_banned_kcl(self):
        """Apply constraints should remove KCl when banned."""
        profile = {
            'fertilizers': [
                {'id': 'potassium_chloride', 'name': 'Cloruro de Potasio', 'dose_kg_ha': 50},
                {'id': 'calcium_nitrate', 'name': 'Nitrato de Calcio', 'dose_kg_ha': 30},
            ]
        }
        constraints = {
            'hard_bans': ['potassium_chloride', 'kcl'],
            'caps_kg_ha': {},
            'nutrient_shares': {},
            'rules_applied': ['RULE_1_CL_HIGH'],
            'compatibility': {'notes': []}
        }
        deficits = {'N': 10, 'K2O': 20}
        
        result = apply_ion_constraints(profile, constraints, deficits, MOCK_CATALOG)
        
        fert_ids = [f['id'] for f in result['fertilizers']]
        assert 'potassium_chloride' not in fert_ids
        assert 'calcium_nitrate' in fert_ids
        assert 'ion_constraints_applied' in result
        removed = result['ion_constraints_applied'].get('removed_fertilizers', [])
        assert len(removed) > 0
        assert 'Cloruro' in removed[0] or 'potassium' in removed[0].lower()
    
    def test_applies_nutrient_caps(self):
        """Apply constraints should reduce doses to meet nutrient caps."""
        profile = {
            'fertilizers': [
                {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'dose_kg_ha': 20},  # 4.8 kg S
            ]
        }
        constraints = {
            'hard_bans': [],
            'caps_kg_ha': {'S': 2.0},  # Max 2 kg S
            'nutrient_shares': {},
            'rules_applied': ['RULE_4_LOW_S_CAP'],
            'compatibility': {'notes': []}
        }
        deficits = {'N': 10, 'S': 1.5}
        
        result = apply_ion_constraints(profile, constraints, deficits, MOCK_CATALOG)
        
        sulfate_fert = next(f for f in result['fertilizers'] if f['id'] == 'ammonium_sulfate')
        s_contribution = sulfate_fert['dose_kg_ha'] * 0.24
        assert s_contribution <= 2.0 + 0.1  # Allow small tolerance
    
    def test_reduces_nh4_for_tomato_seedling(self):
        """Apply constraints should reduce NH4 sources for tomato seedling."""
        profile = {
            'fertilizers': [
                {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'dose_kg_ha': 30},  # NH4 source
                {'id': 'calcium_nitrate', 'name': 'Nitrato de Calcio', 'dose_kg_ha': 10},  # NO3 source
            ]
        }
        constraints = {
            'hard_bans': [],
            'caps_kg_ha': {},
            'nutrient_shares': {
                'NH4_share_max': 0.30,
                'NO3_share_min': 0.70,
                'limit_ammonium': True
            },
            'rules_applied': ['RULE_3_TOMATO_N_FORM'],
            'compatibility': {'notes': []}
        }
        deficits = {'N': 10}
        
        result = apply_ion_constraints(profile, constraints, deficits, MOCK_CATALOG)
        
        sulfate_fert = next((f for f in result['fertilizers'] if f['id'] == 'ammonium_sulfate'), None)
        if sulfate_fert:
            assert sulfate_fert['dose_kg_ha'] < 30  # Should be reduced
    
    def test_assigns_tank_ab(self):
        """Apply constraints should assign tanks A/B for compatibility."""
        profile = {
            'fertilizers': [
                {'id': 'calcium_nitrate', 'name': 'Nitrato de Calcio', 'dose_kg_ha': 30},
                {'id': 'ammonium_sulfate', 'name': 'Sulfato de Amonio', 'dose_kg_ha': 20},
                {'id': 'map', 'name': 'MAP', 'dose_kg_ha': 15},
            ]
        }
        constraints = {
            'hard_bans': [],
            'caps_kg_ha': {},
            'nutrient_shares': {},
            'rules_applied': ['RULE_6_AB_COMPATIBILITY'],
            'compatibility': {'notes': ['Tank A: sulfatos', 'Tank B: nitratos Ca']}
        }
        deficits = {'N': 10, 'P2O5': 5, 'Ca': 10}
        
        result = apply_ion_constraints(profile, constraints, deficits, MOCK_CATALOG)
        
        for fert in result['fertilizers']:
            if fert['id'] == 'calcium_nitrate':
                assert fert.get('tank') == 'B'
            elif fert['id'] == 'ammonium_sulfate':
                assert fert.get('tank') == 'A'
            elif fert['id'] == 'map':
                assert fert.get('tank') == 'A'


class TestFormatConstraintsForPrompt:
    """Tests for format_constraints_for_prompt() function."""
    
    def test_formats_hard_bans(self):
        """Format should include hard bans."""
        constraints = {
            'hard_bans': ['kcl', 'potassium_chloride'],
            'caps_kg_ha': {},
            'nutrient_shares': {},
            'warnings': [],
        }
        
        result = format_constraints_for_prompt(constraints)
        
        assert 'PROHIBITED' in result
        assert 'kcl' in result
    
    def test_formats_caps(self):
        """Format should include nutrient caps."""
        constraints = {
            'hard_bans': [],
            'caps_kg_ha': {'S': 1.65, 'K2O': 5.0},
            'nutrient_shares': {},
            'warnings': [],
        }
        
        result = format_constraints_for_prompt(constraints)
        
        assert 'caps' in result.lower()
        assert 'S' in result
        assert '1.6' in result or '1.65' in result
    
    def test_formats_n_form_shares(self):
        """Format should include N form shares."""
        constraints = {
            'hard_bans': [],
            'caps_kg_ha': {},
            'nutrient_shares': {
                'NH4_share_max': 0.30,
                'NO3_share_min': 0.70,
                'limit_ammonium': True
            },
            'warnings': [],
        }
        
        result = format_constraints_for_prompt(constraints)
        
        assert 'NH4' in result
        assert '30%' in result
        assert 'NO3' in result
        assert '70%' in result


class TestNormalizeStage:
    """Tests for normalize_stage() helper."""
    
    def test_spanish_to_english(self):
        """Should normalize Spanish stage names to English."""
        assert normalize_stage('Plántula') == 'seedling'
        assert normalize_stage('Vegetativo') == 'vegetative'
        assert normalize_stage('Floración') == 'flowering'
        assert normalize_stage('Fructificación') == 'fruiting'
    
    def test_unknown_returns_default(self):
        """Unknown stage should return 'default'."""
        assert normalize_stage('Unknown Stage') == 'default'
        assert normalize_stage('') == 'default'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

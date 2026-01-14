"""
Tests for Explainability Engine.

Tests that the system properly explains when low coverage is intentional:
1. Tomato + Seedling + High soil NO3-N -> N min reduced, no error
2. High Cl in water -> KCl banned
3. High soil K + K2O deficit=0 -> K sources avoided
4. Low S deficit -> S cap respected
"""
import pytest
from app.services.fertiirrigation_ai_optimizer import (
    build_explainability_notes,
    get_profile_targets,
    build_coverage_explained,
    normalize_stage,
    LOW_S_DEFICIT_THRESHOLD
)


class TestBuildExplainabilityNotes:
    """Tests for build_explainability_notes() function."""
    
    def test_high_soil_no3n_early_stage_note(self):
        """High soil NO3-N + early stage should add N reduction note."""
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 0, 'Ca': 0, 'Mg': 0, 'S': 2}
        agronomic_context = {
            'water': {},
            'soil': {'no3n_ppm': 54.4}  # High NO3-N
        }
        profile = {'coverage': {'N': 25}}
        
        notes = build_explainability_notes(
            deficits, agronomic_context, 'Tomate', 'Plántula', profile
        )
        
        assert 'Cobertura de N reducida intencionalmente' in notes
        assert 'NO3-N alto en suelo' in notes
        assert '54.4 ppm' in notes
        assert 'prioriza NO3-' in notes
    
    def test_high_soil_no3n_vegetative_no_note(self):
        """High soil NO3-N in vegetative stage should NOT add N reduction note."""
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 0, 'Ca': 0, 'Mg': 0, 'S': 2}
        agronomic_context = {
            'water': {},
            'soil': {'no3n_ppm': 54.4}
        }
        profile = {'coverage': {'N': 25}}
        
        notes = build_explainability_notes(
            deficits, agronomic_context, 'Tomate', 'Vegetativo', profile
        )
        
        assert 'Cobertura de N reducida intencionalmente' not in notes
    
    def test_k_deficit_zero_note(self):
        """K2O deficit=0 should add K sources avoided note."""
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 0, 'Ca': 0, 'Mg': 0, 'S': 2}
        agronomic_context = {'water': {}, 'soil': {}}
        profile = {}
        
        notes = build_explainability_notes(
            deficits, agronomic_context, 'Tomate', 'Vegetativo', profile
        )
        
        assert 'Fuentes de K evitadas' in notes
        assert 'déficit K2O = 0' in notes
    
    def test_high_soil_k_note(self):
        """High soil K should add K sources avoided note."""
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 10, 'Ca': 0, 'Mg': 0, 'S': 2}
        agronomic_context = {
            'water': {},
            'soil': {'k_ppm': 950}  # High K
        }
        profile = {}
        
        notes = build_explainability_notes(
            deficits, agronomic_context, 'Tomate', 'Vegetativo', profile
        )
        
        assert 'Fuentes de K evitadas' in notes
        assert 'K alto en suelo' in notes
        assert '950 ppm' in notes
    
    def test_high_cl_water_note(self):
        """High Cl- in water should add KCl banned note."""
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 20, 'Ca': 0, 'Mg': 0, 'S': 2}
        agronomic_context = {
            'water': {'cl_meq_l': 3.2},  # High Cl-
            'soil': {}
        }
        profile = {}
        
        notes = build_explainability_notes(
            deficits, agronomic_context, 'Tomate', 'Vegetativo', profile
        )
        
        assert 'KCl prohibido' in notes
        assert 'Cl- alto en agua' in notes
        assert '3.2' in notes
    
    def test_low_s_deficit_note(self):
        """Low S deficit should add S cap note."""
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 20, 'Ca': 0, 'Mg': 0, 'S': 1.5}  # < 5 kg/ha
        agronomic_context = {'water': {}, 'soil': {}}
        profile = {}
        
        notes = build_explainability_notes(
            deficits, agronomic_context, 'Tomate', 'Vegetativo', profile
        )
        
        assert 'S limitado por cap de seguridad' in notes
        assert '110%' in notes
    
    def test_acid_n_contribution_note(self):
        """Acid N contribution should be noted."""
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 20, 'Ca': 0, 'Mg': 0, 'S': 5}
        agronomic_context = {'water': {}, 'soil': {}}
        profile = {'acid_n_contribution_kg_ha': 2.5}
        
        notes = build_explainability_notes(
            deficits, agronomic_context, 'Tomate', 'Vegetativo', profile
        )
        
        assert 'Ácido nítrico aporta' in notes
        assert '2.5' in notes or '2.50' in notes
    
    def test_acid_n_contribution_no_missing_volume_note(self):
        """When acid N is calculated, should NOT show 'missing volume' note."""
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 20, 'Ca': 0, 'Mg': 0, 'S': 5}
        agronomic_context = {'water': {}, 'soil': {}}
        profile = {
            'acid_n_contribution_kg_ha': 2.5,
            'acid_recommended': False  # Calculated successfully
        }
        
        notes = build_explainability_notes(
            deficits, agronomic_context, 'Tomate', 'Vegetativo', profile
        )
        
        assert 'falta de volumen' not in notes
        assert 'TODO' not in notes
    
    def test_acid_recommended_no_volume_shows_todo(self):
        """When acid recommended but volume missing, should show TODO note."""
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 20, 'Ca': 0, 'Mg': 0, 'S': 5}
        agronomic_context = {'water': {}, 'soil': {}}
        profile = {
            'acid_n_contribution_kg_ha': 0,
            'acid_recommended': True  # Volume missing
        }
        
        notes = build_explainability_notes(
            deficits, agronomic_context, 'Tomate', 'Vegetativo', profile
        )
        
        assert 'falta de volumen' in notes or 'no contabilizado' in notes


class TestGetProfileTargets:
    """Tests for get_profile_targets() function."""
    
    def test_tomato_seedling_high_no3n_reduces_n_min(self):
        """Tomato + Seedling + high NO3-N should reduce N min to <=30%."""
        agronomic_context = {
            'water': {},
            'soil': {'no3n_ppm': 54.4}
        }
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 0, 'Ca': 0, 'Mg': 0, 'S': 2}
        
        targets = get_profile_targets(
            'Tomate', 'Plántula', agronomic_context, deficits, 'balanced'
        )
        
        assert targets['min_coverage']['N'] <= 30
        assert 'N' in targets['coverage_explained']
        assert 'soil_sufficient' in targets['coverage_explained']['N']
    
    def test_k2o_deficit_zero_min_is_zero(self):
        """K2O deficit=0 should set K2O min to 0."""
        agronomic_context = {'water': {}, 'soil': {}}
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 0, 'Ca': 0, 'Mg': 0, 'S': 2}
        
        targets = get_profile_targets(
            'Tomate', 'Vegetativo', agronomic_context, deficits, 'balanced'
        )
        
        assert targets['min_coverage']['K2O'] == 0
        assert targets['coverage_explained']['K2O'] == 'no_deficit'
    
    def test_high_soil_k_min_is_zero(self):
        """High soil K should set K2O min to 0."""
        agronomic_context = {
            'water': {},
            'soil': {'k_ppm': 950}
        }
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 10, 'Ca': 0, 'Mg': 0, 'S': 2}
        
        targets = get_profile_targets(
            'Tomate', 'Vegetativo', agronomic_context, deficits, 'balanced'
        )
        
        assert targets['min_coverage']['K2O'] == 0
        assert 'soil_sufficient' in targets['coverage_explained']['K2O']
    
    def test_ca_mg_deficit_zero_min_is_zero(self):
        """Ca/Mg deficit=0 should set min to 0."""
        agronomic_context = {'water': {}, 'soil': {}}
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 10, 'Ca': 0, 'Mg': 0, 'S': 5}
        
        targets = get_profile_targets(
            'Tomate', 'Vegetativo', agronomic_context, deficits, 'balanced'
        )
        
        assert targets['min_coverage']['Ca'] == 0
        assert targets['min_coverage']['Mg'] == 0
        assert targets['coverage_explained']['Ca'] == 'no_deficit'
        assert targets['coverage_explained']['Mg'] == 'no_deficit'
    
    def test_low_s_deficit_lower_min(self):
        """Low S deficit should have lower min coverage."""
        agronomic_context = {'water': {}, 'soil': {}}
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 10, 'Ca': 5, 'Mg': 5, 'S': 1.5}
        
        targets = get_profile_targets(
            'Tomate', 'Vegetativo', agronomic_context, deficits, 'balanced'
        )
        
        assert targets['min_coverage']['S'] <= 50
        assert 'low_deficit_capped' in targets['coverage_explained']['S']
    
    def test_economic_profile_lower_mins(self):
        """Economic profile should have lower minimum requirements."""
        agronomic_context = {'water': {}, 'soil': {}}
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 10, 'Ca': 5, 'Mg': 5, 'S': 5}
        
        targets_economic = get_profile_targets(
            'Tomate', 'Vegetativo', agronomic_context, deficits, 'economic'
        )
        targets_complete = get_profile_targets(
            'Tomate', 'Vegetativo', agronomic_context, deficits, 'complete'
        )
        
        assert targets_economic['min_coverage']['N'] < targets_complete['min_coverage']['N']


class TestBuildCoverageExplained:
    """Tests for build_coverage_explained() function."""
    
    def test_no_deficit_shows_not_required(self):
        """Nutrient with deficit=0 should show 'no_required'."""
        profile = {'coverage': {'N': 50, 'K2O': 0}}
        deficits = {'N': 10, 'K2O': 0}
        agronomic_context = {'water': {}, 'soil': {}}
        
        explained = build_coverage_explained(
            profile, deficits, agronomic_context, 'Vegetativo'
        )
        
        assert 'no_required' in explained['K2O']
        assert 'déficit=0' in explained['K2O']
    
    def test_high_soil_no3n_shows_reduced(self):
        """High soil NO3-N should show 'reducido'."""
        profile = {'coverage': {'N': 25}}
        deficits = {'N': 10, 'K2O': 0}
        agronomic_context = {
            'water': {},
            'soil': {'no3n_ppm': 54.4}
        }
        
        explained = build_coverage_explained(
            profile, deficits, agronomic_context, 'Plántula'
        )
        
        assert 'reducido' in explained['N']
        assert 'NO3-N suelo' in explained['N']
    
    def test_high_soil_k_shows_evitado(self):
        """High soil K should show 'evitado'."""
        profile = {'coverage': {'K2O': 5}}
        deficits = {'K2O': 10}
        agronomic_context = {
            'water': {},
            'soil': {'k_ppm': 950}
        }
        
        explained = build_coverage_explained(
            profile, deficits, agronomic_context, 'Vegetativo'
        )
        
        assert 'evitado' in explained['K2O']
        assert '950 ppm' in explained['K2O']
    
    def test_low_s_deficit_shows_limitado(self):
        """Low S deficit should show 'limitado'."""
        profile = {'coverage': {'S': 100}}
        deficits = {'S': 1.5}
        agronomic_context = {'water': {}, 'soil': {}}
        
        explained = build_coverage_explained(
            profile, deficits, agronomic_context, 'Vegetativo'
        )
        
        assert 'limitado' in explained['S']
        assert 'cap' in explained['S']
    
    def test_good_coverage_shows_cubierto(self):
        """Good coverage (>=85%) should show 'cubierto'."""
        profile = {'coverage': {'N': 95, 'P2O5': 100}}
        deficits = {'N': 10, 'P2O5': 5}
        agronomic_context = {'water': {}, 'soil': {}}
        
        explained = build_coverage_explained(
            profile, deficits, agronomic_context, 'Vegetativo'
        )
        
        assert explained['N'] == 'cubierto'
        assert explained['P2O5'] == 'cubierto'


class TestIntegrationScenarios:
    """Integration tests matching user's real scenarios."""
    
    def test_scenario_tomato_seedling_high_no3n_54ppm(self):
        """
        REAL SCENARIO: Tomate + Plántula + NO3N suelo 54.4 ppm
        N min requerido debe ser <=30% y no disparar error por N bajo.
        """
        agronomic_context = {
            'water': {'cl_meqL': 3.2, 'hco3_meqL': 8.2},
            'soil': {'no3n_ppm': 54.4, 'k_ppm': 950}
        }
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 0, 'Ca': 0, 'Mg': 0, 'S': 2}
        
        # Get targets
        targets = get_profile_targets(
            'Tomate', 'Plántula', agronomic_context, deficits, 'balanced'
        )
        
        # N min should be <=30%
        assert targets['min_coverage']['N'] <= 30
        
        # Should have explanation
        assert 'soil_sufficient' in targets['coverage_explained']['N']
        
        # Notes should explain
        profile = {'coverage': {'N': 25}}
        notes = build_explainability_notes(
            deficits, agronomic_context, 'Tomate', 'Plántula', profile
        )
        assert 'Cobertura de N reducida intencionalmente' in notes
    
    def test_scenario_cl_water_3_2_bans_kcl(self):
        """
        REAL SCENARIO: Cl agua 3.2 => KCl prohibido
        """
        agronomic_context = {
            'water': {'cl_meq_l': 3.2},
            'soil': {}
        }
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 20, 'Ca': 0, 'Mg': 0, 'S': 2}
        profile = {}
        
        notes = build_explainability_notes(
            deficits, agronomic_context, 'Tomate', 'Vegetativo', profile
        )
        
        assert 'KCl prohibido' in notes
        assert '3.2' in notes
    
    def test_scenario_k_soil_950_deficit_zero_avoids_k(self):
        """
        REAL SCENARIO: K suelo 950 + deficit K2O=0 => evitar fuentes K
        """
        agronomic_context = {
            'water': {},
            'soil': {'k_ppm': 950}
        }
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 0, 'Ca': 0, 'Mg': 0, 'S': 2}
        
        # Targets
        targets = get_profile_targets(
            'Tomate', 'Vegetativo', agronomic_context, deficits, 'balanced'
        )
        assert targets['min_coverage']['K2O'] == 0
        
        # Notes
        profile = {}
        notes = build_explainability_notes(
            deficits, agronomic_context, 'Tomate', 'Vegetativo', profile
        )
        assert 'Fuentes de K evitadas' in notes
    
    def test_scenario_s_deficit_small_cap_respected(self):
        """
        REAL SCENARIO: S deficit pequeño => cap S se respeta
        """
        agronomic_context = {'water': {}, 'soil': {}}
        deficits = {'N': 10, 'P2O5': 5, 'K2O': 20, 'Ca': 5, 'Mg': 5, 'S': 1.5}
        
        # Targets
        targets = get_profile_targets(
            'Tomate', 'Vegetativo', agronomic_context, deficits, 'balanced'
        )
        assert 'low_deficit_capped' in targets['coverage_explained']['S']
        
        # Notes
        profile = {}
        notes = build_explainability_notes(
            deficits, agronomic_context, 'Tomate', 'Vegetativo', profile
        )
        assert 'S limitado por cap de seguridad' in notes


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

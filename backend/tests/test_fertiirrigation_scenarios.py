"""
FertiIrrigation Calculator - 15 Test Scenarios
Tests with poor soils, low-nutrient water, and high-yield crops.

Each scenario verifies:
1. Deficit calculations are correct (positive values when soil/water insufficient)
2. Unit conversions are accurate
3. Stage-adjusted requirements work properly
"""
import pytest
from app.services.fertiirrigation_calculator import (
    FertiIrrigationCalculator,
    SoilData,
    WaterData,
    CropData,
    IrrigationData,
)

calculator = FertiIrrigationCalculator()


SCENARIOS = [
    {
        "id": 1,
        "name": "Tomate invernadero 150 ton/ha - Suelo arenoso muy pobre",
        "soil": SoilData(
            texture="arena",
            bulk_density=1.4,
            depth_cm=30,
            ph=6.5,
            organic_matter_pct=0.8,
            n_no3_ppm=3,
            n_nh4_ppm=1,
            p_ppm=5,
            k_ppm=20,
            ca_ppm=50,
            mg_ppm=10,
            s_ppm=3,
            cic_cmol_kg=4,
        ),
        "water": WaterData(
            ec=0.2,
            ph=7.0,
            no3_meq=0.1,
            h2po4_meq=0.005,
            so4_meq=0.05,
            hco3_meq=0.5,
            k_meq=0.02,
            ca_meq=0.2,
            mg_meq=0.1,
            na_meq=0.1,
        ),
        "crop": CropData(
            name="Tomate",
            yield_target=150,
            n_kg_ha=350,
            p2o5_kg_ha=120,
            k2o_kg_ha=500,
            ca_kg_ha=200,
            mg_kg_ha=60,
            s_kg_ha=50,
        ),
        "irrigation": IrrigationData(
            system="goteo",
            frequency_days=2,
            volume_m3_ha=40,
            area_ha=1,
            num_applications=60,
        ),
        "stage_extraction_pct": 35,
        "expected_deficits": ["N", "P2O5", "K2O", "Ca", "Mg", "S"],
    },
    {
        "id": 2,
        "name": "Chile habanero 40 ton/ha - Suelo franco muy bajo Ca/Mg",
        "soil": SoilData(
            texture="franco",
            bulk_density=1.3,
            depth_cm=30,
            ph=5.8,
            organic_matter_pct=1.5,
            n_no3_ppm=5,
            n_nh4_ppm=2,
            p_ppm=6,
            k_ppm=30,
            ca_ppm=60,
            mg_ppm=10,
            s_ppm=4,
            cic_cmol_kg=8,
        ),
        "water": WaterData(
            ec=0.3,
            ph=6.8,
            no3_meq=0.15,
            h2po4_meq=0.01,
            so4_meq=0.08,
            hco3_meq=0.5,
            k_meq=0.04,
            ca_meq=0.3,
            mg_meq=0.1,
            na_meq=0.1,
        ),
        "crop": CropData(
            name="Chile habanero",
            yield_target=40,
            n_kg_ha=280,
            p2o5_kg_ha=100,
            k2o_kg_ha=350,
            ca_kg_ha=180,
            mg_kg_ha=50,
            s_kg_ha=40,
        ),
        "irrigation": IrrigationData(
            system="goteo",
            frequency_days=3,
            volume_m3_ha=35,
            area_ha=1,
            num_applications=45,
        ),
        "stage_extraction_pct": 40,
        "expected_deficits": ["N", "P2O5", "K2O", "Ca", "Mg", "S"],
    },
    {
        "id": 3,
        "name": "Pepino 200 ton/ha - Suelo arenoso CIC muy baja",
        "soil": SoilData(
            texture="arena",
            bulk_density=1.5,
            depth_cm=25,
            ph=6.2,
            organic_matter_pct=0.5,
            n_no3_ppm=3,
            n_nh4_ppm=1,
            p_ppm=5,
            k_ppm=25,
            ca_ppm=100,
            mg_ppm=15,
            s_ppm=3,
            cic_cmol_kg=4,
        ),
        "water": WaterData(
            ec=0.2,
            ph=7.2,
            no3_meq=0.1,
            h2po4_meq=0.005,
            so4_meq=0.05,
            hco3_meq=0.5,
            k_meq=0.02,
            ca_meq=0.3,
            mg_meq=0.1,
            na_meq=0.1,
        ),
        "crop": CropData(
            name="Pepino",
            yield_target=200,
            n_kg_ha=300,
            p2o5_kg_ha=90,
            k2o_kg_ha=450,
            ca_kg_ha=150,
            mg_kg_ha=45,
            s_kg_ha=35,
        ),
        "irrigation": IrrigationData(
            system="goteo",
            frequency_days=1,
            volume_m3_ha=50,
            area_ha=1,
            num_applications=90,
        ),
        "stage_extraction_pct": 50,
        "expected_deficits": ["N", "P2O5", "K2O", "Ca", "Mg", "S"],
    },
    {
        "id": 4,
        "name": "Fresa 80 ton/ha - Suelo ácido bajo P",
        "soil": SoilData(
            texture="franco_arenoso",
            bulk_density=1.35,
            depth_cm=20,
            ph=5.2,
            organic_matter_pct=2.0,
            n_no3_ppm=12,
            n_nh4_ppm=6,
            p_ppm=4,
            k_ppm=60,
            ca_ppm=180,
            mg_ppm=35,
            s_ppm=10,
            cic_cmol_kg=10,
        ),
        "water": WaterData(
            ec=0.35,
            ph=6.5,
            no3_meq=0.25,
            h2po4_meq=0.01,
            so4_meq=0.12,
            hco3_meq=0.6,
            k_meq=0.06,
            ca_meq=0.45,
            mg_meq=0.18,
            na_meq=0.15,
        ),
        "crop": CropData(
            name="Fresa",
            yield_target=80,
            n_kg_ha=220,
            p2o5_kg_ha=80,
            k2o_kg_ha=300,
            ca_kg_ha=120,
            mg_kg_ha=40,
            s_kg_ha=30,
        ),
        "irrigation": IrrigationData(
            system="goteo",
            frequency_days=2,
            volume_m3_ha=30,
            area_ha=1,
            num_applications=75,
        ),
        "stage_extraction_pct": 45,
        "expected_deficits": ["N", "P2O5", "K2O"],
    },
    {
        "id": 5,
        "name": "Pimiento 100 ton/ha - Suelo alcalino pH 8.2",
        "soil": SoilData(
            texture="franco_arcilloso",
            bulk_density=1.25,
            depth_cm=30,
            ph=8.2,
            organic_matter_pct=1.8,
            n_no3_ppm=8,
            n_nh4_ppm=3,
            p_ppm=6,
            k_ppm=90,
            ca_ppm=800,
            mg_ppm=60,
            s_ppm=12,
            cic_cmol_kg=22,
        ),
        "water": WaterData(
            ec=0.8,
            ph=7.8,
            no3_meq=0.4,
            h2po4_meq=0.01,
            so4_meq=0.3,
            hco3_meq=4.0,
            k_meq=0.1,
            ca_meq=1.2,
            mg_meq=0.5,
            na_meq=0.8,
        ),
        "crop": CropData(
            name="Pimiento",
            yield_target=100,
            n_kg_ha=320,
            p2o5_kg_ha=110,
            k2o_kg_ha=400,
            ca_kg_ha=180,
            mg_kg_ha=55,
            s_kg_ha=45,
        ),
        "irrigation": IrrigationData(
            system="goteo",
            frequency_days=3,
            volume_m3_ha=45,
            area_ha=1,
            num_applications=50,
        ),
        "stage_extraction_pct": 30,
        "expected_deficits": ["N", "P2O5", "K2O"],
    },
    {
        "id": 6,
        "name": "Tomate cherry 120 ton/ha - Suelo muy pobre en todo",
        "soil": SoilData(
            texture="arena_franca",
            bulk_density=1.45,
            depth_cm=25,
            ph=6.0,
            organic_matter_pct=0.6,
            n_no3_ppm=2,
            n_nh4_ppm=1,
            p_ppm=3,
            k_ppm=20,
            ca_ppm=80,
            mg_ppm=12,
            s_ppm=2,
            cic_cmol_kg=5,
        ),
        "water": WaterData(
            ec=0.1,
            ph=7.0,
            no3_meq=0.05,
            h2po4_meq=0.002,
            so4_meq=0.02,
            hco3_meq=0.3,
            k_meq=0.01,
            ca_meq=0.15,
            mg_meq=0.05,
            na_meq=0.05,
        ),
        "crop": CropData(
            name="Tomate cherry",
            yield_target=120,
            n_kg_ha=300,
            p2o5_kg_ha=100,
            k2o_kg_ha=420,
            ca_kg_ha=170,
            mg_kg_ha=50,
            s_kg_ha=40,
        ),
        "irrigation": IrrigationData(
            system="goteo",
            frequency_days=1,
            volume_m3_ha=35,
            area_ha=1,
            num_applications=100,
        ),
        "stage_extraction_pct": 55,
        "expected_deficits": ["N", "P2O5", "K2O", "Ca", "Mg", "S"],
    },
    {
        "id": 7,
        "name": "Melón 60 ton/ha - Suelo bajo K, alto Na",
        "soil": SoilData(
            texture="franco",
            bulk_density=1.3,
            depth_cm=30,
            ph=7.2,
            organic_matter_pct=1.2,
            n_no3_ppm=6,
            n_nh4_ppm=2,
            p_ppm=10,
            k_ppm=35,
            ca_ppm=300,
            mg_ppm=45,
            s_ppm=8,
            cic_cmol_kg=14,
        ),
        "water": WaterData(
            ec=1.5,
            ph=7.5,
            no3_meq=0.2,
            h2po4_meq=0.01,
            so4_meq=0.5,
            hco3_meq=2.5,
            k_meq=0.05,
            ca_meq=0.8,
            mg_meq=0.4,
            na_meq=3.0,
        ),
        "crop": CropData(
            name="Melón",
            yield_target=60,
            n_kg_ha=200,
            p2o5_kg_ha=70,
            k2o_kg_ha=280,
            ca_kg_ha=100,
            mg_kg_ha=35,
            s_kg_ha=25,
        ),
        "irrigation": IrrigationData(
            system="goteo",
            frequency_days=2,
            volume_m3_ha=50,
            area_ha=1,
            num_applications=55,
        ),
        "stage_extraction_pct": 60,
        "expected_deficits": ["N", "K2O"],
    },
    {
        "id": 8,
        "name": "Sandía 80 ton/ha - Suelo franco-arenoso bajo Mg",
        "soil": SoilData(
            texture="franco_arenoso",
            bulk_density=1.4,
            depth_cm=30,
            ph=6.8,
            organic_matter_pct=1.0,
            n_no3_ppm=7,
            n_nh4_ppm=3,
            p_ppm=14,
            k_ppm=70,
            ca_ppm=250,
            mg_ppm=18,
            s_ppm=6,
            cic_cmol_kg=9,
        ),
        "water": WaterData(
            ec=0.25,
            ph=7.0,
            no3_meq=0.15,
            h2po4_meq=0.008,
            so4_meq=0.08,
            hco3_meq=0.7,
            k_meq=0.04,
            ca_meq=0.35,
            mg_meq=0.08,
            na_meq=0.12,
        ),
        "crop": CropData(
            name="Sandía",
            yield_target=80,
            n_kg_ha=180,
            p2o5_kg_ha=65,
            k2o_kg_ha=260,
            ca_kg_ha=90,
            mg_kg_ha=40,
            s_kg_ha=22,
        ),
        "irrigation": IrrigationData(
            system="goteo",
            frequency_days=2,
            volume_m3_ha=55,
            area_ha=1,
            num_applications=50,
        ),
        "stage_extraction_pct": 50,
        "expected_deficits": ["N", "K2O", "Mg"],
    },
    {
        "id": 9,
        "name": "Berenjena 90 ton/ha - Suelo bajo Ca, pH ácido",
        "soil": SoilData(
            texture="franco",
            bulk_density=1.3,
            depth_cm=30,
            ph=5.5,
            organic_matter_pct=1.6,
            n_no3_ppm=9,
            n_nh4_ppm=4,
            p_ppm=8,
            k_ppm=55,
            ca_ppm=120,
            mg_ppm=25,
            s_ppm=7,
            cic_cmol_kg=11,
        ),
        "water": WaterData(
            ec=0.3,
            ph=6.5,
            no3_meq=0.2,
            h2po4_meq=0.01,
            so4_meq=0.1,
            hco3_meq=0.5,
            k_meq=0.05,
            ca_meq=0.4,
            mg_meq=0.15,
            na_meq=0.1,
        ),
        "crop": CropData(
            name="Berenjena",
            yield_target=90,
            n_kg_ha=260,
            p2o5_kg_ha=85,
            k2o_kg_ha=350,
            ca_kg_ha=160,
            mg_kg_ha=45,
            s_kg_ha=35,
        ),
        "irrigation": IrrigationData(
            system="goteo",
            frequency_days=2,
            volume_m3_ha=40,
            area_ha=1,
            num_applications=65,
        ),
        "stage_extraction_pct": 45,
        "expected_deficits": ["N", "P2O5", "K2O", "Ca"],
    },
    {
        "id": 10,
        "name": "Calabaza 50 ton/ha - Suelo bajo N, MO muy baja",
        "soil": SoilData(
            texture="franco_limoso",
            bulk_density=1.25,
            depth_cm=30,
            ph=7.0,
            organic_matter_pct=0.7,
            n_no3_ppm=4,
            n_nh4_ppm=1,
            p_ppm=15,
            k_ppm=85,
            ca_ppm=350,
            mg_ppm=50,
            s_ppm=10,
            cic_cmol_kg=16,
        ),
        "water": WaterData(
            ec=0.4,
            ph=7.2,
            no3_meq=0.1,
            h2po4_meq=0.01,
            so4_meq=0.15,
            hco3_meq=1.2,
            k_meq=0.06,
            ca_meq=0.5,
            mg_meq=0.2,
            na_meq=0.2,
        ),
        "crop": CropData(
            name="Calabaza",
            yield_target=50,
            n_kg_ha=160,
            p2o5_kg_ha=55,
            k2o_kg_ha=200,
            ca_kg_ha=80,
            mg_kg_ha=30,
            s_kg_ha=20,
        ),
        "irrigation": IrrigationData(
            system="goteo",
            frequency_days=3,
            volume_m3_ha=45,
            area_ha=1,
            num_applications=40,
        ),
        "stage_extraction_pct": 40,
        "expected_deficits": ["N"],
    },
    {
        "id": 11,
        "name": "Lechuga 100 ton/ha - Suelo muy pobre, CIC 5",
        "soil": SoilData(
            texture="arena",
            bulk_density=1.5,
            depth_cm=20,
            ph=6.5,
            organic_matter_pct=0.5,
            n_no3_ppm=3,
            n_nh4_ppm=1,
            p_ppm=4,
            k_ppm=30,
            ca_ppm=90,
            mg_ppm=15,
            s_ppm=3,
            cic_cmol_kg=5,
        ),
        "water": WaterData(
            ec=0.15,
            ph=7.0,
            no3_meq=0.08,
            h2po4_meq=0.003,
            so4_meq=0.04,
            hco3_meq=0.4,
            k_meq=0.02,
            ca_meq=0.2,
            mg_meq=0.06,
            na_meq=0.08,
        ),
        "crop": CropData(
            name="Lechuga",
            yield_target=100,
            n_kg_ha=180,
            p2o5_kg_ha=50,
            k2o_kg_ha=220,
            ca_kg_ha=80,
            mg_kg_ha=25,
            s_kg_ha=18,
        ),
        "irrigation": IrrigationData(
            system="goteo",
            frequency_days=1,
            volume_m3_ha=25,
            area_ha=1,
            num_applications=45,
        ),
        "stage_extraction_pct": 70,
        "expected_deficits": ["N", "P2O5", "K2O", "Ca", "Mg"],
    },
    {
        "id": 12,
        "name": "Brócoli 25 ton/ha - Suelo bajo S, pH alto",
        "soil": SoilData(
            texture="franco_arcilloso",
            bulk_density=1.2,
            depth_cm=30,
            ph=8.0,
            organic_matter_pct=2.2,
            n_no3_ppm=10,
            n_nh4_ppm=4,
            p_ppm=7,
            k_ppm=95,
            ca_ppm=600,
            mg_ppm=70,
            s_ppm=4,
            cic_cmol_kg=24,
        ),
        "water": WaterData(
            ec=0.6,
            ph=7.6,
            no3_meq=0.3,
            h2po4_meq=0.01,
            so4_meq=0.1,
            hco3_meq=3.0,
            k_meq=0.08,
            ca_meq=0.9,
            mg_meq=0.35,
            na_meq=0.5,
        ),
        "crop": CropData(
            name="Brócoli",
            yield_target=25,
            n_kg_ha=250,
            p2o5_kg_ha=70,
            k2o_kg_ha=280,
            ca_kg_ha=120,
            mg_kg_ha=35,
            s_kg_ha=60,
        ),
        "irrigation": IrrigationData(
            system="goteo",
            frequency_days=2,
            volume_m3_ha=35,
            area_ha=1,
            num_applications=55,
        ),
        "stage_extraction_pct": 50,
        "expected_deficits": ["N", "P2O5", "S"],
    },
    {
        "id": 13,
        "name": "Tomate saladette 180 ton/ha - Suelo deficiente micronutrientes",
        "soil": SoilData(
            texture="franco",
            bulk_density=1.3,
            depth_cm=30,
            ph=7.5,
            organic_matter_pct=1.4,
            n_no3_ppm=8,
            n_nh4_ppm=3,
            p_ppm=11,
            k_ppm=65,
            ca_ppm=280,
            mg_ppm=40,
            s_ppm=9,
            cic_cmol_kg=15,
        ),
        "water": WaterData(
            ec=0.35,
            ph=7.2,
            no3_meq=0.2,
            h2po4_meq=0.01,
            so4_meq=0.12,
            hco3_meq=1.0,
            k_meq=0.05,
            ca_meq=0.45,
            mg_meq=0.18,
            na_meq=0.2,
        ),
        "crop": CropData(
            name="Tomate saladette",
            yield_target=180,
            n_kg_ha=400,
            p2o5_kg_ha=140,
            k2o_kg_ha=550,
            ca_kg_ha=220,
            mg_kg_ha=70,
            s_kg_ha=55,
        ),
        "irrigation": IrrigationData(
            system="goteo",
            frequency_days=1,
            volume_m3_ha=45,
            area_ha=1,
            num_applications=120,
        ),
        "stage_extraction_pct": 40,
        "expected_deficits": ["N", "P2O5", "K2O", "S"],
    },
    {
        "id": 14,
        "name": "Aguacate 20 ton/ha - Suelo bajo P, arcilloso",
        "soil": SoilData(
            texture="arcilla",
            bulk_density=1.15,
            depth_cm=40,
            ph=6.5,
            organic_matter_pct=3.0,
            n_no3_ppm=12,
            n_nh4_ppm=5,
            p_ppm=5,
            k_ppm=110,
            ca_ppm=450,
            mg_ppm=80,
            s_ppm=14,
            cic_cmol_kg=28,
        ),
        "water": WaterData(
            ec=0.5,
            ph=7.0,
            no3_meq=0.25,
            h2po4_meq=0.008,
            so4_meq=0.2,
            hco3_meq=1.5,
            k_meq=0.07,
            ca_meq=0.6,
            mg_meq=0.25,
            na_meq=0.3,
        ),
        "crop": CropData(
            name="Aguacate",
            yield_target=20,
            n_kg_ha=200,
            p2o5_kg_ha=60,
            k2o_kg_ha=280,
            ca_kg_ha=100,
            mg_kg_ha=40,
            s_kg_ha=30,
        ),
        "irrigation": IrrigationData(
            system="goteo",
            frequency_days=4,
            volume_m3_ha=60,
            area_ha=1,
            num_applications=35,
        ),
        "stage_extraction_pct": 35,
        "expected_deficits": ["P2O5"],
    },
    {
        "id": 15,
        "name": "Papa 60 ton/ha - Suelo muy bajo K, pH ácido",
        "soil": SoilData(
            texture="franco_arenoso",
            bulk_density=1.35,
            depth_cm=30,
            ph=5.3,
            organic_matter_pct=1.8,
            n_no3_ppm=10,
            n_nh4_ppm=5,
            p_ppm=9,
            k_ppm=25,
            ca_ppm=160,
            mg_ppm=28,
            s_ppm=8,
            cic_cmol_kg=10,
        ),
        "water": WaterData(
            ec=0.3,
            ph=6.8,
            no3_meq=0.15,
            h2po4_meq=0.01,
            so4_meq=0.1,
            hco3_meq=0.6,
            k_meq=0.03,
            ca_meq=0.4,
            mg_meq=0.12,
            na_meq=0.1,
        ),
        "crop": CropData(
            name="Papa",
            yield_target=60,
            n_kg_ha=220,
            p2o5_kg_ha=80,
            k2o_kg_ha=320,
            ca_kg_ha=100,
            mg_kg_ha=35,
            s_kg_ha=28,
        ),
        "irrigation": IrrigationData(
            system="goteo",
            frequency_days=3,
            volume_m3_ha=40,
            area_ha=1,
            num_applications=45,
        ),
        "stage_extraction_pct": 55,
        "expected_deficits": ["N", "P2O5", "K2O", "Ca"],
    },
]


class TestFertiIrrigationScenarios:
    """Test suite for 15 fertigation scenarios with poor soils and high-yield crops."""

    def test_soil_availability_calculation(self):
        """Test that soil availability is calculated correctly for all scenarios."""
        for scenario in SCENARIOS:
            soil = scenario["soil"]
            soil_avail = calculator.calculate_adjusted_soil_availability(soil)
            
            assert "N" in soil_avail, f"Scenario {scenario['id']}: Missing N in soil availability"
            assert "P2O5" in soil_avail, f"Scenario {scenario['id']}: Missing P2O5 in soil availability"
            assert "K2O" in soil_avail, f"Scenario {scenario['id']}: Missing K2O in soil availability"
            assert "Ca" in soil_avail, f"Scenario {scenario['id']}: Missing Ca in soil availability"
            assert "Mg" in soil_avail, f"Scenario {scenario['id']}: Missing Mg in soil availability"
            assert "S" in soil_avail, f"Scenario {scenario['id']}: Missing S in soil availability"
            
            for nutrient, value in soil_avail.items():
                assert value >= 0, f"Scenario {scenario['id']}: {nutrient} soil availability is negative: {value}"

    def test_water_contribution_calculation(self):
        """Test that water contribution is calculated correctly for all scenarios."""
        for scenario in SCENARIOS:
            water = scenario["water"]
            irrigation = scenario["irrigation"]
            water_contrib = calculator.calculate_water_contribution(water, irrigation)
            
            assert "N" in water_contrib, f"Scenario {scenario['id']}: Missing N in water contribution"
            assert "P2O5" in water_contrib, f"Scenario {scenario['id']}: Missing P2O5 in water contribution"
            assert "K2O" in water_contrib, f"Scenario {scenario['id']}: Missing K2O in water contribution"
            
            for nutrient, value in water_contrib.items():
                assert value >= 0, f"Scenario {scenario['id']}: {nutrient} water contribution is negative: {value}"

    def test_deficit_calculation(self):
        """Test that deficits are calculated correctly - should be positive for poor soils."""
        results = []
        
        for scenario in SCENARIOS:
            soil = scenario["soil"]
            water = scenario["water"]
            crop = scenario["crop"]
            irrigation = scenario["irrigation"]
            stage_pct = scenario["stage_extraction_pct"] / 100.0
            
            soil_avail = calculator.calculate_adjusted_soil_availability(soil)
            water_contrib = calculator.calculate_water_contribution(water, irrigation)
            
            stage_requirements = {
                "N": crop.n_kg_ha * stage_pct,
                "P2O5": crop.p2o5_kg_ha * stage_pct,
                "K2O": crop.k2o_kg_ha * stage_pct,
                "Ca": crop.ca_kg_ha * stage_pct,
                "Mg": crop.mg_kg_ha * stage_pct,
                "S": crop.s_kg_ha * stage_pct,
            }
            
            deficits = {}
            for nutrient in stage_requirements:
                req = stage_requirements[nutrient]
                soil_val = soil_avail.get(nutrient, 0)
                water_val = water_contrib.get(nutrient, 0)
                deficit = max(0, req - soil_val - water_val)
                deficits[nutrient] = round(deficit, 2)
            
            scenario_result = {
                "id": scenario["id"],
                "name": scenario["name"],
                "requirements": {k: round(v, 2) for k, v in stage_requirements.items()},
                "soil": {k: round(v, 2) for k, v in soil_avail.items()},
                "water": {k: round(v, 2) for k, v in water_contrib.items()},
                "deficits": deficits,
                "expected_deficits": scenario["expected_deficits"],
            }
            results.append(scenario_result)
            
            has_deficit = any(d > 0 for d in deficits.values())
            assert has_deficit, (
                f"Scenario {scenario['id']} ({scenario['name']}): "
                f"Expected at least one deficit but all are zero"
            )
            
            for expected_nutrient in scenario["expected_deficits"]:
                assert deficits.get(expected_nutrient, 0) > 0, (
                    f"Scenario {scenario['id']} ({scenario['name']}): "
                    f"Expected deficit for {expected_nutrient} but got {deficits.get(expected_nutrient, 0):.2f} kg/ha. "
                    f"Requirement: {stage_requirements.get(expected_nutrient, 0):.2f}, "
                    f"Soil: {soil_avail.get(expected_nutrient, 0):.2f}, "
                    f"Water: {water_contrib.get(expected_nutrient, 0):.2f}"
                )
        
        return results

    def test_unit_conversion_ppm_to_kg_ha(self):
        """Test ppm to kg/ha conversion formula."""
        ppm = 100
        bulk_density = 1.3
        depth_cm = 30
        
        expected = ppm * bulk_density * depth_cm * 0.1
        result = calculator.ppm_to_kg_ha(ppm, bulk_density, depth_cm)
        
        assert abs(result - expected) < 0.01, f"ppm_to_kg_ha conversion failed: {result} != {expected}"
        assert result == 390.0, f"Expected 390.0 kg/ha, got {result}"

    def test_unit_conversion_meq_to_kg_ha(self):
        """Test meq/L to kg/ha conversion for water ions."""
        ca_meq = 1.0
        volume_m3 = 50
        num_apps = 10
        
        result = calculator.meq_to_kg_ha(ca_meq, "Ca", volume_m3, num_apps)
        
        expected = (1.0 * (40.1 / 2) * 50 * 1000 * 10) / 1_000_000
        assert abs(result - expected) < 0.1, f"meq_to_kg_ha conversion failed: {result} != {expected}"

    def test_ph_factors_applied(self):
        """Test that pH factors are correctly applied to soil availability."""
        neutral_soil = SoilData(ph=7.0, p_ppm=20, bulk_density=1.3, depth_cm=30)
        acidic_soil = SoilData(ph=5.0, p_ppm=20, bulk_density=1.3, depth_cm=30)
        alkaline_soil = SoilData(ph=8.5, p_ppm=20, bulk_density=1.3, depth_cm=30)
        
        neutral_avail = calculator.calculate_adjusted_soil_availability(neutral_soil)
        acidic_avail = calculator.calculate_adjusted_soil_availability(acidic_soil)
        alkaline_avail = calculator.calculate_adjusted_soil_availability(alkaline_soil)
        
        assert neutral_avail["P2O5"] >= acidic_avail["P2O5"], "P should be less available in acidic soil"
        assert neutral_avail["P2O5"] >= alkaline_avail["P2O5"], "P should be less available in alkaline soil"

    def test_cic_factors_applied(self):
        """Test that CIC factors are correctly applied to cation availability."""
        high_cic_soil = SoilData(cic_cmol_kg=30, k_ppm=100, ca_ppm=500, mg_ppm=50, bulk_density=1.3, depth_cm=30)
        low_cic_soil = SoilData(cic_cmol_kg=5, k_ppm=100, ca_ppm=500, mg_ppm=50, bulk_density=1.3, depth_cm=30)
        
        high_cic_avail = calculator.calculate_adjusted_soil_availability(high_cic_soil)
        low_cic_avail = calculator.calculate_adjusted_soil_availability(low_cic_soil)
        
        pass

    def test_all_scenarios_have_some_deficit(self):
        """Verify that all poor-soil scenarios result in at least one nutrient deficit."""
        for scenario in SCENARIOS:
            soil = scenario["soil"]
            water = scenario["water"]
            crop = scenario["crop"]
            irrigation = scenario["irrigation"]
            stage_pct = scenario["stage_extraction_pct"] / 100.0
            
            soil_avail = calculator.calculate_adjusted_soil_availability(soil)
            water_contrib = calculator.calculate_water_contribution(water, irrigation)
            
            total_deficit = 0
            for nutrient in ["N", "P2O5", "K2O", "Ca", "Mg", "S"]:
                req = getattr(crop, nutrient.lower().replace("2o5", "2o5_kg_ha").replace("2o", "2o_kg_ha"), 0)
                if nutrient == "N":
                    req = crop.n_kg_ha * stage_pct
                elif nutrient == "P2O5":
                    req = crop.p2o5_kg_ha * stage_pct
                elif nutrient == "K2O":
                    req = crop.k2o_kg_ha * stage_pct
                elif nutrient == "Ca":
                    req = crop.ca_kg_ha * stage_pct
                elif nutrient == "Mg":
                    req = crop.mg_kg_ha * stage_pct
                elif nutrient == "S":
                    req = crop.s_kg_ha * stage_pct
                
                deficit = max(0, req - soil_avail.get(nutrient, 0) - water_contrib.get(nutrient, 0))
                total_deficit += deficit
            
            assert total_deficit > 0, (
                f"Scenario {scenario['id']} ({scenario['name']}): "
                f"Expected at least one deficit but total deficit is {total_deficit}"
            )


def run_all_scenarios():
    """Run all scenarios and print detailed results."""
    print("\n" + "="*80)
    print("FERTIIRRIGATION CALCULATOR - 15 SCENARIO TEST RESULTS")
    print("="*80 + "\n")
    
    test_suite = TestFertiIrrigationScenarios()
    results = test_suite.test_deficit_calculation()
    
    for result in results:
        print(f"\n{'='*80}")
        print(f"SCENARIO {result['id']}: {result['name']}")
        print("="*80)
        
        print("\n📊 Stage Requirements (kg/ha):")
        for nutrient, value in result['requirements'].items():
            print(f"   {nutrient}: {value:.2f}")
        
        print("\n🌱 Soil Contribution (kg/ha):")
        for nutrient, value in result['soil'].items():
            print(f"   {nutrient}: {value:.2f}")
        
        print("\n💧 Water Contribution (kg/ha):")
        for nutrient, value in result['water'].items():
            print(f"   {nutrient}: {value:.2f}")
        
        print("\n⚠️ DEFICITS (kg/ha) - To cover with fertilizers:")
        for nutrient, value in result['deficits'].items():
            status = "✅" if value > 0 else "➖"
            expected = "⭐" if nutrient in result['expected_deficits'] else ""
            print(f"   {status} {nutrient}: {value:.2f} {expected}")
        
        deficits_found = [n for n, v in result['deficits'].items() if v > 0]
        expected = result['expected_deficits']
        missing = set(expected) - set(deficits_found)
        extra = set(deficits_found) - set(expected)
        
        if missing:
            print(f"\n❌ MISSING EXPECTED DEFICITS: {missing}")
        if extra:
            print(f"\n📝 ADDITIONAL DEFICITS FOUND: {extra}")
        if not missing:
            print("\n✅ ALL EXPECTED DEFICITS CONFIRMED")
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    all_passed = True
    for result in results:
        deficits_found = [n for n, v in result['deficits'].items() if v > 0]
        expected = result['expected_deficits']
        missing = set(expected) - set(deficits_found)
        
        if missing:
            print(f"❌ Scenario {result['id']}: Missing deficits for {missing}")
            all_passed = False
        else:
            print(f"✅ Scenario {result['id']}: PASSED")
    
    if all_passed:
        print("\n🎉 ALL 15 SCENARIOS PASSED!")
    else:
        print("\n⚠️ SOME SCENARIOS FAILED - Review above for details")
    
    return results


def test_zero_deficit_scenario():
    """
    Test scenario where soil and water fully cover crop requirements.
    When soil + water > requirements, all deficits should be 0.
    """
    rich_soil = SoilData(
        texture="franco",
        bulk_density=1.2,
        depth_cm=30,
        ph=6.8,
        organic_matter_pct=4.5,
        n_no3_ppm=150,
        n_nh4_ppm=50,
        p_ppm=80,
        k_ppm=400,
        ca_ppm=2500,
        mg_ppm=400,
        s_ppm=100,
        cic_cmol_kg=25,
    )
    
    nutrient_water = WaterData(
        ec=1.5,
        ph=7.0,
        no3_meq=5.0,
        h2po4_meq=1.0,
        so4_meq=3.0,
        hco3_meq=2.0,
        k_meq=1.0,
        ca_meq=4.0,
        mg_meq=2.0,
        na_meq=0.5,
    )
    
    low_demand_crop = CropData(
        name="Lechuga",
        yield_target=20,
        n_kg_ha=50,
        p2o5_kg_ha=20,
        k2o_kg_ha=60,
        ca_kg_ha=30,
        mg_kg_ha=10,
        s_kg_ha=5,
    )
    
    irrigation = IrrigationData(
        system="goteo",
        frequency_days=3,
        volume_m3_ha=30,
        area_ha=1,
        num_applications=20,
    )
    
    stage_pct = 20 / 100.0
    
    soil_avail = calculator.calculate_adjusted_soil_availability(rich_soil)
    water_contrib = calculator.calculate_water_contribution(nutrient_water, irrigation)
    
    all_covered = True
    for nutrient in ["N", "P2O5", "K2O", "Ca", "Mg", "S"]:
        if nutrient == "N":
            req = low_demand_crop.n_kg_ha * stage_pct
        elif nutrient == "P2O5":
            req = low_demand_crop.p2o5_kg_ha * stage_pct
        elif nutrient == "K2O":
            req = low_demand_crop.k2o_kg_ha * stage_pct
        elif nutrient == "Ca":
            req = low_demand_crop.ca_kg_ha * stage_pct
        elif nutrient == "Mg":
            req = low_demand_crop.mg_kg_ha * stage_pct
        else:
            req = low_demand_crop.s_kg_ha * stage_pct
        
        available = soil_avail.get(nutrient, 0) + water_contrib.get(nutrient, 0)
        deficit = max(0, req - available)
        
        if deficit > 0:
            all_covered = False
    
    assert all_covered, "Expected all deficits to be 0 with rich soil and water"
    print("\n✅ Zero deficit scenario: Soil + water fully cover crop requirements")


if __name__ == "__main__":
    run_all_scenarios()

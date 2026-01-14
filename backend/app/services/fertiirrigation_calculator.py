"""
FertiIrrigation Calculator Service (Independent Module).

Calculates fertigation requirements based on:
- Soil analysis (nutrient availability)
- Water analysis (nutrient contribution)
- Crop requirements
- Irrigation parameters
- Crop extraction curves (nutrient uptake by growth stage)
- Soil availability factors (pH, OM, CIC, carbonates)
- Agronomic minimums by crop (structural nutrients never zero)

All calculations are independent from the hydroponics module.
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import math
import json
import os
import logging

from app.routers.fertilizer_prices import DEFAULT_PRICES_BY_CURRENCY

logger = logging.getLogger(__name__)

AGRONOMIC_MINIMUMS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "agronomic_minimums.json"
)

SOIL_AVAILABILITY_FACTORS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "soil_availability_factors.json"
)

_agronomic_minimums_cache = None
_soil_availability_factors_cache = None

def clear_agronomic_minimums_cache():
    """Clear the cache to reload agronomic minimums on next call."""
    global _agronomic_minimums_cache
    _agronomic_minimums_cache = None

def clear_soil_availability_factors_cache():
    """Clear the cache to reload soil availability factors on next call."""
    global _soil_availability_factors_cache
    _soil_availability_factors_cache = None

def load_soil_availability_factors() -> Dict:
    """Load soil availability factors from JSON file."""
    global _soil_availability_factors_cache
    if _soil_availability_factors_cache is not None:
        return _soil_availability_factors_cache
    
    try:
        with open(SOIL_AVAILABILITY_FACTORS_PATH, "r", encoding="utf-8") as f:
            _soil_availability_factors_cache = json.load(f)
            return _soil_availability_factors_cache
    except Exception as e:
        logger.error(f"Error loading soil availability factors: {e}")
        return {
            "base_factors": {
                "N": {"factor": 0.65},
                "P2O5": {"factor": 0.20},
                "K2O": {"factor": 0.50},
                "Ca": {"factor": 0.12},
                "Mg": {"factor": 0.18},
                "S": {"factor": 0.45}
            },
            "crop_overrides": {}
        }

def get_soil_availability_factor(nutrient: str, crop_name: Optional[str] = None) -> float:
    """
    Get the soil availability factor for a specific nutrient and optional crop.
    
    Args:
        nutrient: Nutrient key (N, P2O5, K2O, Ca, Mg, S)
        crop_name: Optional crop name for crop-specific overrides
        
    Returns:
        Availability factor (0-1) representing fraction of soil nutrient
        that the plant can extract during one growing cycle.
    """
    config = load_soil_availability_factors()
    base_factors = config.get("base_factors", {})
    crop_overrides = config.get("crop_overrides", {})
    
    base_factor = base_factors.get(nutrient, {}).get("factor", 0.5)
    
    if crop_name:
        crop_key = crop_name.lower().strip()
        for key, prefix in [
            ("tomate", "tomate"), ("chile", "chile"), ("pimiento", "chile"),
            ("pepino", "pepino"), ("fresa", "fresa"), ("lechuga", "lechuga"),
            ("maiz", "maiz"), ("maíz", "maiz"), ("papa", "papa"),
            ("cebolla", "cebolla"), ("ajo", "ajo"), ("aguacate", "aguacate"),
            ("mango", "mango"), ("citricos", "citricos"), ("limón", "citricos"),
            ("naranja", "citricos"), ("vid", "vid"), ("uva", "vid"),
            ("brocoli", "brocoli"), ("brócoli", "brocoli"), ("coliflor", "coliflor")
        ]:
            if crop_key.startswith(key):
                crop_data = crop_overrides.get(prefix, {})
                if nutrient in crop_data:
                    return crop_data[nutrient]
                break
    
    return base_factor

def load_agronomic_minimums() -> Dict:
    """Load agronomic minimums configuration from JSON file."""
    global _agronomic_minimums_cache
    if _agronomic_minimums_cache is not None:
        return _agronomic_minimums_cache
    
    try:
        with open(AGRONOMIC_MINIMUMS_PATH, "r", encoding="utf-8") as f:
            _agronomic_minimums_cache = json.load(f)
            return _agronomic_minimums_cache
    except Exception as e:
        logger.error(f"Error loading agronomic minimums: {e}")
        return {"crops": {}, "default": {"minimums": {}}}

CROP_NAME_TO_ID = {
    'tomate': 'tomato',
    'chile': 'pepper',
    'pimiento': 'pepper',
    'maíz': 'maize',
    'maiz': 'maize',
    'frijol': 'bean',
    'pepino': 'cucumber',
    'calabaza': 'squash',
    'cebolla': 'onion',
    'papa': 'potato',
    'sandía': 'watermelon',
    'sandia': 'watermelon',
    'melón': 'melon',
    'melon': 'melon',
    'aguacate': 'avocado',
    'fresa': 'strawberry',
    'lechuga': 'lettuce',
    'albahaca': 'basil',
    'tomato': 'tomato',
    'pepper': 'pepper',
    'corn': 'maize',
    'bean': 'bean',
    'cucumber': 'cucumber',
    'squash': 'squash',
    'onion': 'onion',
    'potato': 'potato',
    'watermelon': 'watermelon',
    'avocado': 'avocado',
    'strawberry': 'strawberry',
    'lettuce': 'lettuce',
    'basil': 'basil',
}

def infer_crop_id_from_name(crop_name: Optional[str]) -> Optional[str]:
    """
    Infer the crop ID from the crop name (Spanish/English to crop ID).
    
    Used as fallback when frontend doesn't send extraction_crop_id.
    Handles varietal suffixes like "Tomate Saladette" -> "tomato"
    
    Args:
        crop_name: Crop name in Spanish or English (e.g., 'Tomate', 'Tomate Saladette', 'tomato')
        
    Returns:
        Crop ID (e.g., 'tomato', 'pepper') or None if not found
    """
    if not crop_name:
        return None
    
    normalized = crop_name.lower().strip()
    
    if normalized in CROP_NAME_TO_ID:
        return CROP_NAME_TO_ID[normalized]
    
    for key, crop_id in CROP_NAME_TO_ID.items():
        if normalized.startswith(key + ' ') or normalized.startswith(key + '_'):
            return crop_id
    
    return None

def get_crop_minimums(crop_id: Optional[str], stage: Optional[str] = None) -> Dict[str, float]:
    """
    Get agronomic safety percentages for a specific crop and phenological stage.
    
    Version 2.1: Uses universal_defaults for completely custom crops/stages.
    
    Priority:
    1. Specific crop + stage from crops config
    2. Crop alias resolution
    3. stage_defaults for known stage names
    4. universal_defaults for custom/unknown stages
    
    Args:
        crop_id: Crop identifier (e.g., 'tomato', 'corn', 'pepper')
        stage: Phenological stage (e.g., 'seedling', 'vegetative', 'flowering', etc.)
        
    Returns:
        Dict with safety percentages for N, P2O5, K2O, Ca, Mg, S (always returns values)
    """
    config = load_agronomic_minimums()
    stage_defaults = config.get("stage_defaults", {})
    universal_defaults = config.get("universal_defaults", {
        "N": 0.15, "P2O5": 0.15, "K2O": 0.20, "Ca": 0.25, "Mg": 0.20, "S": 0.15
    })
    universal_defaults = {k: v for k, v in universal_defaults.items() if k != "description"}
    
    if not crop_id:
        if stage and stage in stage_defaults:
            return stage_defaults[stage]
        logger.debug(f"No crop_id, stage '{stage}' not in stage_defaults, using universal_defaults")
        return universal_defaults
    
    crop_key = crop_id.lower().replace(" ", "_").replace("-", "_")
    crops_config = config.get("crops", {})
    
    if crop_key in crops_config:
        crop_data = crops_config[crop_key]
        
        if "alias_of" in crop_data:
            alias_key = crop_data["alias_of"]
            if alias_key in crops_config:
                crop_data = crops_config[alias_key]
        
        if "stages" in crop_data:
            if stage and stage in crop_data["stages"]:
                stage_data = crop_data["stages"][stage]
                return {k: v for k, v in stage_data.items() if k != "notes"}
            
            if stage and stage in stage_defaults:
                return stage_defaults[stage]
            
            if "vegetative" in crop_data["stages"]:
                stage_data = crop_data["stages"]["vegetative"]
                return {k: v for k, v in stage_data.items() if k != "notes"}
        
        if "minimums" in crop_data:
            return crop_data["minimums"]
    
    if stage and stage in stage_defaults:
        return stage_defaults[stage]
    
    logger.debug(f"Crop '{crop_id}' or stage '{stage}' not found, using universal_defaults")
    return universal_defaults


@dataclass
class AcidData:
    """Acid treatment data for calculations."""
    acid_type: str = ""  # phosphoric_acid, nitric_acid, sulfuric_acid
    ml_per_1000L: float = 0.0
    cost_mxn_per_1000L: float = 0.0
    # Nutrient contribution in g/1000L
    n_g_per_1000L: float = 0.0
    p_g_per_1000L: float = 0.0
    s_g_per_1000L: float = 0.0


@dataclass
class SoilData:
    """Soil analysis data for calculations."""
    texture: str = "franco"
    bulk_density: float = 1.3  # g/cm3
    depth_cm: float = 30.0
    ph: float = 7.0
    ec_ds_m: float = 0.0  # dS/m
    organic_matter_pct: float = 2.0
    n_no3_ppm: float = 0.0
    n_nh4_ppm: float = 0.0
    p_ppm: float = 0.0
    k_ppm: float = 0.0
    ca_ppm: float = 0.0
    mg_ppm: float = 0.0
    s_ppm: float = 0.0
    na_ppm: float = 0.0
    cic_cmol_kg: float = 20.0


@dataclass
class WaterData:
    """Water analysis data for calculations."""
    ec: float = 0.5  # dS/m
    ph: float = 7.0
    # Ions in meq/L
    no3_meq: float = 0.0
    h2po4_meq: float = 0.0
    so4_meq: float = 0.0
    hco3_meq: float = 0.0
    k_meq: float = 0.0
    ca_meq: float = 0.0
    mg_meq: float = 0.0
    na_meq: float = 0.0
    # Micronutrients in ppm
    fe_ppm: float = 0.0
    mn_ppm: float = 0.0
    zn_ppm: float = 0.0
    cu_ppm: float = 0.0
    b_ppm: float = 0.0


@dataclass
class CropData:
    """Crop nutrient requirements."""
    name: str
    variety: Optional[str] = None
    growth_stage: Optional[str] = None
    yield_target: float = 10.0  # ton/ha
    # Requirements in kg/ha
    n_kg_ha: float = 150.0
    p2o5_kg_ha: float = 60.0
    k2o_kg_ha: float = 180.0
    ca_kg_ha: float = 40.0
    mg_kg_ha: float = 20.0
    s_kg_ha: float = 25.0
    # Extraction curve parameters (optional)
    extraction_crop_id: Optional[str] = None
    extraction_stage_id: Optional[str] = None
    previous_stage_id: Optional[str] = None
    custom_extraction_percent: Optional[Dict[str, float]] = None


@dataclass
class IrrigationData:
    """Irrigation parameters."""
    system: str = "goteo"
    frequency_days: float = 7.0
    volume_m3_ha: float = 50.0
    area_ha: float = 1.0
    num_applications: int = 10
    
    def __post_init__(self):
        """Validate and clamp values to prevent division by zero."""
        self.frequency_days = max(1.0, self.frequency_days)
        self.volume_m3_ha = max(1.0, self.volume_m3_ha)
        self.area_ha = max(0.01, self.area_ha)
        self.num_applications = max(1, self.num_applications)


class FertiIrrigationCalculator:
    """
    Calculator for fertigation requirements.
    
    Methodology:
    1. Calculate available nutrients in soil (ppm -> kg/ha)
    2. Calculate nutrient contribution from irrigation water
    3. Calculate deficit (requirement - soil - water)
    4. Apply efficiency factors based on texture
    5. Distribute fertilization across applications
    """
    
    # Efficiency factors by texture (fraction absorbed by plant in fertigation systems)
    # P efficiency increased for fertigation (localized application near roots)
    TEXTURE_EFFICIENCY = {
        "arena": {"N": 0.50, "P": 0.30, "K": 0.60, "default": 0.50},
        "arena_franca": {"N": 0.55, "P": 0.35, "K": 0.65, "default": 0.55},
        "franco_arenoso": {"N": 0.60, "P": 0.40, "K": 0.70, "default": 0.60},
        "franco": {"N": 0.70, "P": 0.45, "K": 0.75, "default": 0.70},
        "franco_limoso": {"N": 0.70, "P": 0.45, "K": 0.75, "default": 0.70},
        "franco_arcilloso": {"N": 0.75, "P": 0.50, "K": 0.70, "default": 0.72},
        "arcilla": {"N": 0.80, "P": 0.55, "K": 0.65, "default": 0.75},
    }
    
    # Conversion factors
    P_TO_P2O5 = 2.29  # P -> P2O5
    K_TO_K2O = 1.20   # K -> K2O
    
    # Molecular weights for water analysis conversions
    ION_WEIGHTS = {
        "NO3": 62.0,
        "H2PO4": 97.0,
        "SO4": 96.0,
        "HCO3": 61.0,
        "K": 39.1,
        "Ca": 40.1,
        "Mg": 24.3,
        "Na": 23.0,
    }
    
    ION_VALENCES = {
        "NO3": 1,
        "H2PO4": 1,
        "SO4": 2,
        "HCO3": 1,
        "K": 1,
        "Ca": 2,
        "Mg": 2,
        "Na": 1,
    }
    
    def __init__(self):
        """Initialize calculator and load extraction curves data."""
        self.extraction_curves = self._load_extraction_curves()
    
    def _load_extraction_curves(self) -> Dict:
        """Load crop extraction curves from JSON file."""
        try:
            data_path = os.path.join(
                os.path.dirname(__file__), 
                "..", "data", "fertiirrigation_extraction_curves.json"
            )
            with open(data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load extraction curves: {e}")
            return {}
    
    def get_available_crops(self) -> List[Dict]:
        """Get list of available crops with extraction curve data."""
        if not self.extraction_curves or "crops" not in self.extraction_curves:
            return []
        
        crops = []
        for crop_id, crop_data in self.extraction_curves.get("crops", {}).items():
            crops.append({
                "id": crop_id,
                "name": crop_data.get("name", crop_id),
                "scientific_name": crop_data.get("scientific_name", ""),
                "cycle_days": crop_data.get("cycle_days", {}),
                "stages": list(crop_data.get("extraction_curves", {}).keys()),
                "total_requirements": crop_data.get("total_requirements_kg_ha", {})
            })
        return crops
    
    def get_crop_stages(self, crop_id: str) -> List[Dict]:
        """Get growth stages for a specific crop."""
        if not self.extraction_curves:
            return []
        
        crop_data = self.extraction_curves.get("crops", {}).get(crop_id.lower(), {})
        if not crop_data:
            return []
        
        stages = []
        for stage_id, stage_data in crop_data.get("extraction_curves", {}).items():
            stages.append({
                "id": stage_id,
                "name": stage_data.get("name", stage_id),
                "duration_days": stage_data.get("duration_days", {}),
                "cumulative_percent": stage_data.get("cumulative_percent", {}),
                "notes": stage_data.get("notes", "")
            })
        return stages
    
    def get_extraction_curve(self, crop_id: str, current_stage: str) -> Dict[str, float]:
        """
        Get the extraction percentages for nutrients at the current growth stage.
        
        Returns dict with nutrient -> cumulative percent extracted at this stage.
        """
        if not self.extraction_curves:
            return {}
        
        crop_data = self.extraction_curves.get("crops", {}).get(crop_id.lower(), {})
        if not crop_data:
            return {}
        
        stage_data = crop_data.get("extraction_curves", {}).get(current_stage.lower(), {})
        return stage_data.get("cumulative_percent", {})
    
    def calculate_stage_requirements(
        self, 
        crop: CropData, 
        crop_id: str, 
        current_stage: str,
        previous_stage: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Calculate nutrient requirements for a specific growth stage.
        
        Uses extraction curves to determine what percentage of total
        requirements should be applied during this stage (delta between
        the current and previous cumulative percentages).
        
        Returns dict with adjusted nutrient requirements in kg/ha for this stage.
        """
        current_curve = self.get_extraction_curve(crop_id, current_stage)
        
        n_val = crop.n_kg_ha or 0.0
        p_val = crop.p2o5_kg_ha or 0.0
        k_val = crop.k2o_kg_ha or 0.0
        ca_val = crop.ca_kg_ha or 0.0
        mg_val = crop.mg_kg_ha or 0.0
        s_val = crop.s_kg_ha or 0.0
        
        if not current_curve:
            return {
                "N": n_val,
                "P2O5": p_val,
                "K2O": k_val,
                "Ca": ca_val,
                "Mg": mg_val,
                "S": s_val,
            }
        
        if previous_stage:
            prev_curve = self.get_extraction_curve(crop_id, previous_stage)
        else:
            prev_curve = {"N": 0, "P2O5": 0, "K2O": 0, "Ca": 0, "Mg": 0, "S": 0}
        
        stage_pct = {
            "N": (current_curve.get("N", 100) - prev_curve.get("N", 0)) / 100.0,
            "P2O5": (current_curve.get("P2O5", 100) - prev_curve.get("P2O5", 0)) / 100.0,
            "K2O": (current_curve.get("K2O", 100) - prev_curve.get("K2O", 0)) / 100.0,
            "Ca": (current_curve.get("Ca", 100) - prev_curve.get("Ca", 0)) / 100.0,
            "Mg": (current_curve.get("Mg", 100) - prev_curve.get("Mg", 0)) / 100.0,
            "S": (current_curve.get("S", 100) - prev_curve.get("S", 0)) / 100.0,
        }
        
        return {
            "N": n_val * stage_pct["N"],
            "P2O5": p_val * stage_pct["P2O5"],
            "K2O": k_val * stage_pct["K2O"],
            "Ca": ca_val * stage_pct["Ca"],
            "Mg": mg_val * stage_pct["Mg"],
            "S": s_val * stage_pct["S"],
        }
    
    def get_ph_availability_factors(self, ph: float) -> Dict[str, float]:
        """
        Get nutrient availability factors based on soil pH.
        
        Returns multipliers (0-1.2) for each nutrient based on pH effects.
        """
        if not self.extraction_curves:
            return {n: 1.0 for n in ["N", "P", "K", "Ca", "Mg", "S", "Fe", "Mn", "Zn", "Cu", "B"]}
        
        ph_effects = self.extraction_curves.get("soil_availability_factors", {}).get("ph_effects", {})
        ranges = ph_effects.get("ranges", {})
        
        for range_name, range_data in ranges.items():
            ph_range = range_data.get("ph_range", [0, 14])
            if ph_range[0] <= ph < ph_range[1]:
                return {
                    "N": range_data.get("N", 1.0),
                    "P": range_data.get("P", 1.0),
                    "K": range_data.get("K", 1.0),
                    "Ca": range_data.get("Ca", 1.0),
                    "Mg": range_data.get("Mg", 1.0),
                    "S": range_data.get("S", 1.0),
                    "Fe": range_data.get("Fe", 1.0),
                    "Mn": range_data.get("Mn", 1.0),
                    "Zn": range_data.get("Zn", 1.0),
                    "Cu": range_data.get("Cu", 1.0),
                    "B": range_data.get("B", 1.0),
                }
        
        return {n: 1.0 for n in ["N", "P", "K", "Ca", "Mg", "S", "Fe", "Mn", "Zn", "Cu", "B"]}
    
    def get_om_nitrogen_release(self, organic_matter_pct: float) -> float:
        """
        Calculate N release from organic matter mineralization.
        
        Returns estimated kg N/ha released during the crop cycle.
        """
        if not self.extraction_curves:
            return organic_matter_pct * 25
        
        om_effects = self.extraction_curves.get("soil_availability_factors", {}).get("organic_matter_effects", {})
        rates = om_effects.get("mineralization_rate_kg_per_percent", {})
        
        for range_name, range_data in rates.items():
            om_range = range_data.get("om_range", [0, 100])
            if om_range[0] <= organic_matter_pct < om_range[1]:
                return organic_matter_pct * range_data.get("n_release_kg_per_percent", 25)
        
        return organic_matter_pct * 25
    
    def get_cic_availability_factors(self, cic: float) -> Dict[str, float]:
        """
        Get cation availability factors based on CIC (Cation Exchange Capacity).
        
        Returns multipliers for K, Ca, Mg based on CIC effects.
        """
        if not self.extraction_curves:
            return {"K": 1.0, "Ca": 1.0, "Mg": 1.0}
        
        cic_effects = self.extraction_curves.get("soil_availability_factors", {}).get("cic_effects", {})
        ranges = cic_effects.get("ranges", {})
        
        for range_name, range_data in ranges.items():
            cic_range = range_data.get("cic_range", [0, 100])
            if cic_range[0] <= cic < cic_range[1]:
                return {
                    "K": range_data.get("K", 1.0),
                    "Ca": range_data.get("Ca", 1.0),
                    "Mg": range_data.get("Mg", 1.0),
                }
        
        return {"K": 1.0, "Ca": 1.0, "Mg": 1.0}
    
    def get_base_extraction_factors(self, crop_name: Optional[str] = None) -> Dict[str, float]:
        """
        Get base extraction factors for soil nutrients, optionally adjusted for crop type.
        
        These represent the fraction of extractable nutrients (from soil analysis)
        that is actually available to the crop in one growing cycle.
        
        Uses soil_availability_factors.json which provides:
        - Literature-backed base factors per nutrient
        - Crop-specific overrides for sensitive crops (e.g., tomato needs less Ca factor)
        
        Based on: Havlin et al., Mengel & Kirkby, NOM-021-RECNAT-2000.
        
        Args:
            crop_name: Optional crop name for crop-specific factor adjustments
        """
        return {
            "N": get_soil_availability_factor("N", crop_name),
            "P": get_soil_availability_factor("P2O5", crop_name),
            "K": get_soil_availability_factor("K2O", crop_name),
            "Ca": get_soil_availability_factor("Ca", crop_name),
            "Mg": get_soil_availability_factor("Mg", crop_name),
            "S": get_soil_availability_factor("S", crop_name),
        }
    
    def calculate_adjusted_soil_availability(
        self,
        soil: SoilData,
        stage_extraction_pct: Optional[float] = None,
        crop_name: Optional[str] = None,
        stage_extraction_pct_by_nutrient: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Calculate soil nutrient availability with base extraction, pH, OM, and CIC adjustments.
        
        This provides a more realistic estimate of what the plant can actually access
        during one growing cycle, proportioned to the current phenological stage.
        
        Formula: Available = Extractable × Base_Factor × pH_Factor × CIC_Factor × Stage_Factor + OM_Release
        
        Args:
            soil: Soil data with nutrient concentrations
            stage_extraction_pct: Percentage of total crop extraction for current stage (0-100).
                                  If provided, soil availability is proportioned to this stage.
                                  E.g., if stage uses 20% of crop's nutrients, only 20% of
                                  soil availability is credited to this stage.
            crop_name: Optional crop name for crop-specific availability factors
            stage_extraction_pct_by_nutrient: Optional per-nutrient stage extraction percentages.
        """
        base_availability = self.calculate_soil_availability(soil)
        
        base_factors = self.get_base_extraction_factors(crop_name)
        ph_factors = self.get_ph_availability_factors(soil.ph)
        cic_factors = self.get_cic_availability_factors(soil.cic_cmol_kg)
        
        om_n_release = self.get_om_nitrogen_release(soil.organic_matter_pct)
        
        stage_factor = 1.0
        if stage_extraction_pct is not None and stage_extraction_pct > 0:
            stage_factor = min(1.0, stage_extraction_pct / 100.0)

        def get_stage_factor(nutrient_key: str) -> float:
            if stage_extraction_pct_by_nutrient and nutrient_key in stage_extraction_pct_by_nutrient:
                pct = stage_extraction_pct_by_nutrient.get(nutrient_key, 0) or 0
                return min(1.0, max(0.0, pct / 100.0))
            return stage_factor
        
        adjusted = {
            "N": (base_availability["N"] * base_factors.get("N", 0.5) * ph_factors.get("N", 1.0) + om_n_release) * get_stage_factor("N"),
            "P2O5": base_availability["P2O5"] * base_factors.get("P", 0.2) * ph_factors.get("P", 1.0) * get_stage_factor("P2O5"),
            "K2O": base_availability["K2O"] * base_factors.get("K", 0.4) * ph_factors.get("K", 1.0) * cic_factors.get("K", 1.0) * get_stage_factor("K2O"),
            "Ca": base_availability["Ca"] * base_factors.get("Ca", 0.15) * ph_factors.get("Ca", 1.0) * cic_factors.get("Ca", 1.0) * get_stage_factor("Ca"),
            "Mg": base_availability["Mg"] * base_factors.get("Mg", 0.25) * ph_factors.get("Mg", 1.0) * cic_factors.get("Mg", 1.0) * get_stage_factor("Mg"),
            "S": base_availability["S"] * base_factors.get("S", 0.4) * ph_factors.get("S", 1.0) * get_stage_factor("S"),
        }
        
        return {k: max(0, v) for k, v in adjusted.items()}
    
    def ppm_to_kg_ha(self, ppm: float, bulk_density: float, depth_cm: float) -> float:
        """
        Convert soil nutrient concentration (ppm) to kg/ha.
        
        Formula: kg/ha = ppm × bulk_density × depth_cm × 0.1
        """
        return ppm * bulk_density * depth_cm * 0.1
    
    def meq_to_kg_ha(self, meq_l: float, ion: str, volume_m3_ha: float, num_applications: int) -> float:
        """
        Convert water ion concentration (meq/L) to total kg/ha contribution.
        
        Formula: kg/ha = meq/L × (MW/valence) × volume_L × applications / 1000
        """
        if ion not in self.ION_WEIGHTS:
            return 0.0
        
        mw = self.ION_WEIGHTS[ion]
        valence = self.ION_VALENCES[ion]
        volume_l = volume_m3_ha * 1000  # m3 to L
        
        # mg/L from meq/L
        mg_l = meq_l * (mw / valence)
        
        # Total kg applied
        total_kg = (mg_l * volume_l * num_applications) / 1_000_000
        
        return total_kg
    
    def get_efficiency_factor(self, texture: str, nutrient: str) -> float:
        """Get absorption efficiency factor for a nutrient based on soil texture."""
        texture_lower = texture.lower().replace(" ", "_") if texture else "franco"
        efficiency_dict = self.TEXTURE_EFFICIENCY.get(texture_lower, self.TEXTURE_EFFICIENCY["franco"])
        return efficiency_dict.get(nutrient, efficiency_dict.get("default", 0.70))
    
    def calculate_soil_availability(self, soil: SoilData) -> Dict[str, float]:
        """
        Calculate available nutrients from soil in kg/ha.
        
        Returns dict with N, P2O5, K2O, Ca, Mg, S in kg/ha.
        """
        depth = soil.depth_cm
        bd = soil.bulk_density
        
        # N from nitrates and ammonium
        n_available = self.ppm_to_kg_ha(
            (soil.n_no3_ppm or 0) + (soil.n_nh4_ppm or 0), bd, depth
        )
        
        # P (convert to P2O5)
        p_available = self.ppm_to_kg_ha(soil.p_ppm or 0, bd, depth)
        p2o5_available = p_available * self.P_TO_P2O5
        
        # K (convert to K2O)
        k_available = self.ppm_to_kg_ha(soil.k_ppm or 0, bd, depth)
        k2o_available = k_available * self.K_TO_K2O
        
        # Secondary nutrients
        ca_available = self.ppm_to_kg_ha(soil.ca_ppm or 0, bd, depth)
        mg_available = self.ppm_to_kg_ha(soil.mg_ppm or 0, bd, depth)
        s_available = self.ppm_to_kg_ha(soil.s_ppm or 0, bd, depth)
        
        return {
            "N": n_available,
            "P2O5": p2o5_available,
            "K2O": k2o_available,
            "Ca": ca_available,
            "Mg": mg_available,
            "S": s_available,
        }
    
    def calculate_water_contribution(
        self, water: WaterData, irrigation: IrrigationData
    ) -> Dict[str, float]:
        """
        Calculate nutrient contribution from irrigation water in kg/ha.
        
        Returns dict with N, P2O5, K2O, Ca, Mg, S in kg/ha.
        """
        volume = max(1.0, irrigation.volume_m3_ha)
        apps = max(1, irrigation.num_applications)
        
        # N from NO3
        n_contrib = self.meq_to_kg_ha(water.no3_meq, "NO3", volume, apps)
        # Convert NO3 to N (14/62)
        n_contrib = n_contrib * (14.0 / 62.0)
        
        # P from H2PO4 (convert to P2O5)
        p_contrib = self.meq_to_kg_ha(water.h2po4_meq, "H2PO4", volume, apps)
        p_contrib = p_contrib * (31.0 / 97.0)  # H2PO4 to P
        p2o5_contrib = p_contrib * self.P_TO_P2O5
        
        # K (convert to K2O)
        k_contrib = self.meq_to_kg_ha(water.k_meq, "K", volume, apps)
        k2o_contrib = k_contrib * self.K_TO_K2O
        
        # Secondary nutrients
        ca_contrib = self.meq_to_kg_ha(water.ca_meq, "Ca", volume, apps)
        mg_contrib = self.meq_to_kg_ha(water.mg_meq, "Mg", volume, apps)
        
        # S from SO4
        s_contrib = self.meq_to_kg_ha(water.so4_meq, "SO4", volume, apps)
        s_contrib = s_contrib * (32.0 / 96.0)  # SO4 to S
        
        return {
            "N": n_contrib,
            "P2O5": p2o5_contrib,
            "K2O": k2o_contrib,
            "Ca": ca_contrib,
            "Mg": mg_contrib,
            "S": s_contrib,
        }
    
    def calculate_acid_contribution(
        self,
        acid: Optional[AcidData],
        irrigation: IrrigationData
    ) -> Dict[str, float]:
        """
        Calculate nutrient contribution from acid treatment in kg/ha.
        
        The acid dose (g/1000L) is applied each irrigation event.
        Total contribution = (g/1000L) × (L per application) × (num applications) / 1000 = kg/ha
        
        Args:
            acid: Acid treatment data with nutrients in g/1000L
            irrigation: Irrigation parameters
        
        Returns:
            Dict with N, P2O5, K2O, Ca, Mg, S contributions in kg/ha
        """
        if not acid or not acid.acid_type:
            return {"N": 0, "P2O5": 0, "K2O": 0, "Ca": 0, "Mg": 0, "S": 0}
        
        liters_per_app = irrigation.volume_m3_ha * 1000
        apps = irrigation.num_applications
        
        factor_per_app = liters_per_app / 1000
        
        n_kg = (acid.n_g_per_1000L * factor_per_app * apps) / 1000
        p_kg = (acid.p_g_per_1000L * factor_per_app * apps) / 1000
        p2o5_kg = p_kg * self.P_TO_P2O5
        s_kg = (acid.s_g_per_1000L * factor_per_app * apps) / 1000
        
        return {
            "N": n_kg,
            "P2O5": p2o5_kg,
            "K2O": 0,
            "Ca": 0,
            "Mg": 0,
            "S": s_kg,
        }
    
    def calculate_nutrient_balance(
        self,
        soil: SoilData,
        water: WaterData,
        crop: CropData,
        irrigation: IrrigationData,
        acid: Optional[AcidData] = None,
        stage_extraction_pct: Optional[float] = None,
        previous_cumulative_pct: Optional[float] = None
    ) -> List[Dict]:
        """
        Calculate complete nutrient balance.
        
        FERTIRRIEGO MODEL (corrected Jan 2026):
        - The crop nutrient requirement represents the PHYSIOLOGICAL ABSORPTION needed.
        - SOIL availability IS NOW subtracted from deficit, proportional to the stage extraction.
        - WATER and ACID contributions are also deducted from requirements.
        - Soil data is ALSO used for alerts (antagonisms, Na excess, diagnostic).
        - Ca and Mg ALWAYS have minimum doses (never 0 kg/ha if crop requires them).
        
        PROGRESSIVE DEPLETION MODEL:
        - Each stage consumes its proportional share of soil nutrients.
        - Response includes soil_remaining metrics to show depletion across stages.
        - After all stages complete (100% cumulative), soil contribution is exhausted.
        
        Deficit formula: requirement - soil_avail_stage - water - acid
        
        Args:
            soil: Soil analysis data (nutrients deducted proportionally by stage)
            water: Water analysis data (nutrients deducted from deficit)
            crop: Crop requirements
            irrigation: Irrigation parameters
            acid: Optional acid treatment data (nutrients deducted from deficit)
            stage_extraction_pct: DELTA percentage for this stage (0-100).
            previous_cumulative_pct: Cumulative extraction % BEFORE this stage (for soil depletion tracking).
        
        Returns list of nutrient balance dictionaries with soil depletion metrics.
        """
        # Get crop name for soil availability factors
        crop_name = getattr(crop, 'name', None)
        
        # Calculate full soil availability (100% of cycle) for depletion tracking
        full_soil_avail = self.calculate_adjusted_soil_availability(
            soil,
            stage_extraction_pct=100,
            crop_name=crop_name
        )
        water_contrib = self.calculate_water_contribution(water, irrigation)
        acid_contrib = self.calculate_acid_contribution(acid, irrigation)
        
        stage_pct_by_nutrient = None
        if crop.custom_extraction_percent:
            pct = crop.custom_extraction_percent
            requirements = {
                "N": (crop.n_kg_ha or 0) * pct.get("N", 100) / 100,
                "P2O5": (crop.p2o5_kg_ha or 0) * pct.get("P2O5", 100) / 100,
                "K2O": (crop.k2o_kg_ha or 0) * pct.get("K2O", 100) / 100,
                "Ca": (crop.ca_kg_ha or 0) * pct.get("Ca", 100) / 100,
                "Mg": (crop.mg_kg_ha or 0) * pct.get("Mg", 100) / 100,
                "S": (crop.s_kg_ha or 0) * pct.get("S", 100) / 100,
            }
            stage_pct_by_nutrient = pct
        elif crop.extraction_crop_id and crop.extraction_stage_id:
            current_curve = self.get_extraction_curve(crop.extraction_crop_id, crop.extraction_stage_id)
            if crop.previous_stage_id:
                prev_curve = self.get_extraction_curve(crop.extraction_crop_id, crop.previous_stage_id)
            else:
                prev_curve = {"N": 0, "P2O5": 0, "K2O": 0, "Ca": 0, "Mg": 0, "S": 0}
            stage_pct_by_nutrient = {
                "N": current_curve.get("N", 0) - prev_curve.get("N", 0),
                "P2O5": current_curve.get("P2O5", 0) - prev_curve.get("P2O5", 0),
                "K2O": current_curve.get("K2O", 0) - prev_curve.get("K2O", 0),
                "Ca": current_curve.get("Ca", 0) - prev_curve.get("Ca", 0),
                "Mg": current_curve.get("Mg", 0) - prev_curve.get("Mg", 0),
                "S": current_curve.get("S", 0) - prev_curve.get("S", 0),
            }
            stage_requirements = self.calculate_stage_requirements(
                crop, 
                crop.extraction_crop_id, 
                crop.extraction_stage_id,
                previous_stage=crop.previous_stage_id
            )
            requirements = {
                "N": stage_requirements.get("N", crop.n_kg_ha),
                "P2O5": stage_requirements.get("P2O5", crop.p2o5_kg_ha),
                "K2O": stage_requirements.get("K2O", crop.k2o_kg_ha),
                "Ca": stage_requirements.get("Ca", crop.ca_kg_ha or 0),
                "Mg": stage_requirements.get("Mg", crop.mg_kg_ha or 0),
                "S": stage_requirements.get("S", crop.s_kg_ha or 0),
            }
        else:
            requirements = {
                "N": crop.n_kg_ha,
                "P2O5": crop.p2o5_kg_ha,
                "K2O": crop.k2o_kg_ha,
                "Ca": crop.ca_kg_ha or 0,
                "Mg": crop.mg_kg_ha or 0,
                "S": crop.s_kg_ha or 0,
            }

        # Calculate stage-proportioned soil availability
        soil_avail = self.calculate_adjusted_soil_availability(
            soil,
            stage_extraction_pct=stage_extraction_pct,
            crop_name=crop_name,
            stage_extraction_pct_by_nutrient=stage_pct_by_nutrient
        )
        balance = []
        for nutrient, requirement in requirements.items():
            soil_val = soil_avail.get(nutrient, 0)
            water_val = water_contrib.get(nutrient, 0)
            acid_val = acid_contrib.get(nutrient, 0)
            
            deficit_real = requirement - soil_val - water_val - acid_val
            deficit_real = max(0, deficit_real)
            deficit = deficit_real
            
            minimum_applied = False
            minimum_reason = None
            
            crop_id = crop.extraction_crop_id
            if not crop_id:
                crop_id = infer_crop_id_from_name(crop.name)
            stage_id = getattr(crop, 'extraction_stage_id', None)
            crop_minimums = get_crop_minimums(crop_id, stage_id)
            
            agronomic_minimum = 0.0
            if requirement > 0:
                min_pct = crop_minimums.get(nutrient)
                
                if min_pct is not None and min_pct > 0:
                    min_dose = requirement * min_pct
                    agronomic_minimum = min_dose
                    
                    if deficit < min_dose:
                        deficit = min_dose
                        minimum_applied = True
                        minimum_reason = f"Dosis mínima aplicada por seguridad ({int(min_pct*100)}% del requerimiento)"
            
            efficiency = self.get_efficiency_factor(
                soil.texture, 
                nutrient.replace("2O5", "").replace("2O", "")
            )
            
            fertilizer_needed = deficit / efficiency if efficiency > 0 else deficit
            
            # Calculate soil depletion metrics for this nutrient
            full_soil = full_soil_avail.get(nutrient, 0)
            prev_cumulative = previous_cumulative_pct or 0.0
            current_delta = stage_extraction_pct or 100.0
            current_cumulative = prev_cumulative + current_delta
            
            # Soil consumed before this stage (kg/ha)
            soil_consumed_before = full_soil * (prev_cumulative / 100.0)
            # Soil consumed in this stage (kg/ha)
            soil_consumed_this_stage = soil_val
            # Soil remaining after this stage (kg/ha)
            soil_remaining_after = full_soil - (full_soil * (min(100.0, current_cumulative) / 100.0))
            
            balance.append({
                "nutrient": nutrient,
                "requirement_kg_ha": round(requirement, 2),
                "soil_diagnostic_kg_ha": round(soil_val, 2),
                "water_contribution_kg_ha": round(water_val, 2),
                "acid_contribution_kg_ha": round(acid_val, 2),
                "deficit_real_kg_ha": round(deficit_real, 2),
                "deficit_security_kg_ha": round(agronomic_minimum, 2),
                "deficit_kg_ha": round(deficit, 2),
                "efficiency_factor": round(efficiency, 2),
                "fertilizer_needed_kg_ha": round(fertilizer_needed, 2),
                "minimum_applied": minimum_applied,
                "minimum_reason": minimum_reason,
                # Soil depletion metrics
                "soil_total_kg_ha": round(full_soil, 2),
                "soil_consumed_before_kg_ha": round(soil_consumed_before, 2),
                "soil_consumed_this_stage_kg_ha": round(soil_consumed_this_stage, 2),
                "soil_remaining_kg_ha": round(max(0, soil_remaining_after), 2),
                "cumulative_extraction_pct": round(current_cumulative, 1),
            })
        
        return balance
    
    def generate_fertilizer_program(
        self,
        balance: List[Dict],
        irrigation: IrrigationData,
        currency: str = "MXN",
        user_prices: Optional[Dict[str, float]] = None
    ) -> List[Dict]:
        """
        Generate a fertigation program based on nutrient balance.
        
        Distributes fertilization across applications with costs calculated.
        
        Args:
            balance: Nutrient balance from calculate_nutrient_balance
            irrigation: Irrigation parameters
            currency: Currency code (MXN, USD, etc.)
            user_prices: Optional dict of {fertilizer_slug: price_per_kg} from user's my-data/prices
        """
        num_apps = max(1, irrigation.num_applications)
        area = max(0.01, irrigation.area_ha)
        volume_per_app = max(1, irrigation.volume_m3_ha) * 1000  # L/ha
        
        program = []
        
        # Get total needs
        n_total = next((b["fertilizer_needed_kg_ha"] for b in balance if b["nutrient"] == "N"), 0)
        p_total = next((b["fertilizer_needed_kg_ha"] for b in balance if b["nutrient"] == "P2O5"), 0)
        k_total = next((b["fertilizer_needed_kg_ha"] for b in balance if b["nutrient"] == "K2O"), 0)
        
        # Default prices for fallback
        default_prices = {
            "urea_46_0_0": DEFAULT_PRICES_BY_CURRENCY.get("urea_46_0_0", {}).get(currency, 14.0),
            "map_11_52_0": DEFAULT_PRICES_BY_CURRENCY.get("map_11_52_0", {}).get(currency, 20.0),
            "sop_0_0_50_18s": DEFAULT_PRICES_BY_CURRENCY.get("sop_0_0_50_18s", {}).get(currency, 22.0),
        }
        
        # Use user prices if provided, otherwise fallback to defaults
        def get_price(slug: str) -> float:
            if user_prices and slug in user_prices:
                return user_prices[slug]
            return default_prices.get(slug, 0)
        
        # Price mapping for default fertilizers
        price_map = {
            "Urea (46-0-0)": get_price("urea_46_0_0"),
            "MAP (12-61-0)": get_price("map_11_52_0"),
            "Sulfato de Potasio (0-0-50)": get_price("sop_0_0_50_18s"),
        }
        
        # Simple fertilizer selection (can be expanded)
        # Using common soluble fertilizers
        fertilizers = []
        
        if n_total > 0:
            # Urea (46-0-0)
            urea_kg = n_total / 0.46
            fertilizers.append({
                "name": "Urea (46-0-0)",
                "slug": "urea_46_0_0",
                "total_kg_ha": round(urea_kg, 2),
                "nutrient": "N",
                "concentration": 0.46,
                "price_per_kg": price_map["Urea (46-0-0)"]
            })
        
        if p_total > 0:
            # MAP (12-61-0)
            map_kg = p_total / 0.61
            fertilizers.append({
                "name": "MAP (12-61-0)",
                "slug": "map_11_52_0",
                "total_kg_ha": round(map_kg, 2),
                "nutrient": "P2O5",
                "concentration": 0.61,
                "price_per_kg": price_map["MAP (12-61-0)"]
            })
        
        if k_total > 0:
            # Potassium Sulfate (0-0-50)
            ksulfate_kg = k_total / 0.50
            fertilizers.append({
                "name": "Sulfato de Potasio (0-0-50)",
                "slug": "sop_0_0_50_18s",
                "total_kg_ha": round(ksulfate_kg, 2),
                "nutrient": "K2O",
                "concentration": 0.50,
                "price_per_kg": price_map["Sulfato de Potasio (0-0-50)"]
            })
        
        # Distribute across applications
        for i in range(1, num_apps + 1):
            for fert in fertilizers:
                dose_per_app_ha = fert["total_kg_ha"] / num_apps
                dose_per_app_total = dose_per_app_ha * area
                conc_g_l = (dose_per_app_ha * 1000) / volume_per_app if volume_per_app > 0 else 0
                price_per_kg = fert.get("price_per_kg", 0)
                
                # Cost per application
                cost_per_app_ha = round(dose_per_app_ha * price_per_kg, 2)
                cost_per_app_total = round(dose_per_app_total * price_per_kg, 2)
                
                # Total cost for the whole cycle (all applications)
                total_kg_for_cycle_ha = fert["total_kg_ha"]
                total_kg_for_cycle_area = fert["total_kg_ha"] * area
                cost_cycle_ha = round(total_kg_for_cycle_ha * price_per_kg, 2)
                cost_cycle_total = round(total_kg_for_cycle_area * price_per_kg, 2)
                
                program.append({
                    "application_number": i,
                    "fertilizer_name": fert["name"],
                    "fertilizer_slug": fert.get("slug", ""),
                    "dose_kg_ha": round(dose_per_app_ha, 3),
                    "dose_kg_total": round(dose_per_app_total, 3),
                    "concentration_g_l": round(conc_g_l, 3),
                    "cost_ha": cost_per_app_ha,
                    "cost_total": cost_per_app_total,
                    "cost_cycle_ha": cost_cycle_ha,
                    "cost_cycle_total": cost_cycle_total,
                    "price_per_kg": price_per_kg
                })
        
        return program
    
    def generate_warnings(
        self,
        soil: SoilData,
        water: WaterData,
        balance: List[Dict]
    ) -> List[str]:
        """
        Generate warnings based on analysis data.
        
        FERTIRRIEGO MODEL:
        - Soil data is used for ALERTS and DIAGNOSIS only, not for deficit calculation.
        - Generates warnings for: antagonisms (Ca-Mg-K, Na), pH extremes, salinity.
        """
        warnings = []
        
        # pH warnings
        if soil.ph and soil.ph < 5.5:
            warnings.append(f"pH del suelo muy ácido ({soil.ph}). Puede afectar disponibilidad de Ca, Mg, Mo. Considere encalado.")
        elif soil.ph and soil.ph > 8.5:
            warnings.append(f"pH del suelo muy alcalino ({soil.ph}). Limita disponibilidad de Fe, Zn, Mn, B, Cu.")
        
        # EC warnings
        if soil.ec_ds_m and soil.ec_ds_m > 4.0:
            warnings.append(f"CE del suelo elevada ({soil.ec_ds_m} dS/m). Riesgo de salinidad - monitoree y aplique lavados.")
        
        # === SOIL CATION ANTAGONISM ALERTS ===
        # Ca-Mg-K ratios in soil for diagnostic purposes
        ca_meq = (soil.ca_ppm or 0) / 200.0  # Ca: 200 ppm = 1 meq
        mg_meq = (soil.mg_ppm or 0) / 121.5  # Mg: 121.5 ppm = 1 meq
        k_meq = (soil.k_ppm or 0) / 390.0    # K: 390 ppm = 1 meq
        na_meq = (soil.na_ppm or 0) / 230.0  # Na: 230 ppm = 1 meq
        
        # Ideal Ca:Mg ratio is 3-5:1
        if mg_meq > 0:
            ca_mg_ratio = ca_meq / mg_meq
            if ca_mg_ratio < 2.0:
                warnings.append(f"ANTAGONISMO Ca:Mg - Relación baja ({ca_mg_ratio:.1f}:1). Exceso de Mg puede inhibir absorción de Ca. Aumente Ca en fertirriego.")
            elif ca_mg_ratio > 8.0:
                warnings.append(f"ANTAGONISMO Ca:Mg - Relación alta ({ca_mg_ratio:.1f}:1). Exceso de Ca puede inhibir absorción de Mg. Monitoree Mg en tejido foliar.")
        
        # Ca:K ratio should be ~13-20:1 in soil
        if k_meq > 0 and ca_meq > 0:
            ca_k_ratio = ca_meq / k_meq
            if ca_k_ratio < 5.0:
                warnings.append(f"ANTAGONISMO Ca:K - Relación baja ({ca_k_ratio:.1f}:1). Exceso de K puede inhibir absorción de Ca. Riesgo de pudrición apical.")
        
        # Sodium toxicity and antagonism
        if soil.na_ppm and soil.na_ppm > 150:
            warnings.append(f"SODIO ELEVADO EN SUELO ({soil.na_ppm} ppm). Puede desplazar Ca y Mg de sitios de intercambio. Riesgo de sodificación.")
        
        # ESP (Exchangeable Sodium Percentage) if CIC available
        # ESP = (Exchangeable Na in meq/100g / CIC in cmol(+)/kg) * 100
        # CIC is already in cmol(+)/kg = meq/100g, so ESP = (Na_meq / CIC) * 100
        if soil.cic_cmol_kg and soil.cic_cmol_kg > 0 and na_meq > 0:
            esp = (na_meq / soil.cic_cmol_kg) * 100
            if esp > 15:
                warnings.append(f"ESP CRÍTICO ({esp:.1f}%). Suelo sódico - requiere enmiendas con yeso o azufre elemental.")
            elif esp > 10:
                warnings.append(f"ESP MODERADO ({esp:.1f}%). Monitoree estructura del suelo y considere enmiendas.")
        
        # === WATER QUALITY ALERTS ===
        if water.hco3_meq > 3.0:
            warnings.append(f"Bicarbonatos en agua elevados ({water.hco3_meq:.1f} meq/L). Neutralice con ácido antes de inyectar fertilizantes.")
        
        if water.na_meq > 5.0:
            warnings.append(f"Sodio en agua elevado ({water.na_meq:.1f} meq/L). Riesgo de sodificación - aplique lavados frecuentes.")
        elif water.na_meq > 3.0:
            warnings.append(f"Sodio en agua moderado ({water.na_meq:.1f} meq/L). Monitoree acumulación en suelo.")
        
        # Na+ vs Ca2+ ionic competition in water
        if water.na_meq > 0 and water.ca_meq > 0:
            na_ca_ratio = water.na_meq / water.ca_meq
            if na_ca_ratio > 1.0:
                warnings.append(f"COMPETENCIA IONICA Na+/Ca2+ en agua ({na_ca_ratio:.2f}). El sodio puede inhibir absorcion de calcio. Incremente dosis de Ca.")
        
        # Water EC
        if water.ec > 2.0:
            warnings.append(f"CE del agua muy elevada ({water.ec:.2f} dS/m). Ajuste frecuencia de riego y monitoree CE del bulbo húmedo.")
        elif water.ec > 1.5:
            warnings.append(f"CE del agua elevada ({water.ec:.2f} dS/m). Monitoree acumulación de sales.")
        
        return warnings
    
    def get_recommended_iron_chelate(self, water: WaterData) -> Dict[str, str]:
        """
        Automatic selection of iron chelate based on water quality.
        
        RULE:
        - If water pH > 7.2 OR HCO3 > 2.0 meq/L: Fe-DTPA or Fe-EDDHA (stable at high pH)
        - Otherwise: Fe-EDTA (economical, stable at pH < 7)
        
        Returns dict with recommended chelate and reason.
        """
        high_ph = water.ph and water.ph > 7.2
        high_bicarbonates = water.hco3_meq > 2.0
        
        if high_ph or high_bicarbonates:
            if water.ph and water.ph > 8.0:
                return {
                    "chelate": "Fe-EDDHA",
                    "reason": f"pH del agua muy alto ({water.ph:.1f}). Fe-EDDHA es estable hasta pH 11.",
                    "alternative": "Fe-DTPA"
                }
            else:
                return {
                    "chelate": "Fe-DTPA",
                    "reason": f"pH agua {water.ph:.1f} y/o HCO₃⁻ {water.hco3_meq:.1f} meq/L elevados. Fe-DTPA es estable hasta pH 7.5.",
                    "alternative": "Fe-EDDHA"
                }
        else:
            return {
                "chelate": "Fe-EDTA",
                "reason": f"Agua con pH {water.ph:.1f} y HCO₃⁻ {water.hco3_meq:.1f} meq/L adecuados. Fe-EDTA es económico y eficaz.",
                "alternative": None
            }

    def generate_recommendations(
        self,
        soil: SoilData,
        water: WaterData,
        balance: List[Dict]
    ) -> List[str]:
        """Generate agronomic recommendations."""
        recommendations = []
        
        # Based on organic matter
        if soil.organic_matter_pct and soil.organic_matter_pct < 2.0:
            recommendations.append("Considere incorporar materia orgánica (compostas, abonos verdes) para mejorar estructura del suelo y retención de nutrientes.")
        elif soil.organic_matter_pct and soil.organic_matter_pct > 5.0:
            recommendations.append("Materia orgánica alta. Puede reducir aplicaciones de N en las primeras etapas del cultivo.")
        
        # Based on CIC
        if soil.cic_cmol_kg and soil.cic_cmol_kg < 10:
            recommendations.append("CIC baja indica poca capacidad de retención de nutrientes. Aplique fertilizantes en dosis menores y más frecuentes.")
        elif soil.cic_cmol_kg and soil.cic_cmol_kg > 30:
            recommendations.append("CIC alta indica buena retención de cationes (Ca, Mg, K). El suelo puede mantener nutrientes entre riegos.")
        
        # Based on texture
        texture_lower = soil.texture.lower() if soil.texture else ""
        if "arena" in texture_lower:
            recommendations.append("Suelo arenoso: evite aplicar más de 30 kg N/ha por riego para prevenir lixiviación. Use fertilizantes de liberación controlada si es posible.")
        elif "arcilla" in texture_lower:
            recommendations.append("Suelo arcilloso: riegue con menos frecuencia pero mayor volumen. Evite saturación que reduce oxígeno radicular.")
        
        # N recommendations based on deficit
        n_balance = next((b for b in balance if b["nutrient"] == "N"), None)
        if n_balance:
            n_needed = n_balance.get("fertilizer_needed_kg_ha", 0)
            if n_needed > 250:
                recommendations.append(f"Requerimiento de N muy elevado ({n_needed:.0f} kg/ha). Divida en al menos 8-10 aplicaciones y monitoree nitratos en suelo.")
            elif n_needed > 150:
                recommendations.append(f"Requerimiento de N moderado-alto ({n_needed:.0f} kg/ha). Aplique 60% en desarrollo vegetativo y 40% en fructificación.")
            elif n_needed > 0:
                recommendations.append(f"Requerimiento de N adecuado ({n_needed:.0f} kg/ha). Distribuya uniformemente durante el ciclo del cultivo.")
        
        # P recommendations
        p_balance = next((b for b in balance if b["nutrient"] == "P2O5"), None)
        if p_balance:
            p_needed = p_balance.get("fertilizer_needed_kg_ha", 0)
            if p_needed > 100:
                recommendations.append(f"Requerimiento de fósforo elevado ({p_needed:.0f} kg P₂O₅/ha). Considere aplicación base con fosfato monoamónico (MAP) antes del trasplante.")
            elif p_needed > 0 and soil.ph and soil.ph > 7.5:
                recommendations.append("pH alcalino puede reducir disponibilidad de fósforo. Use ácido fosfórico para acidificar la solución nutritiva.")
        
        # K recommendations
        k_balance = next((b for b in balance if b["nutrient"] == "K2O"), None)
        if k_balance:
            k_needed = k_balance.get("fertilizer_needed_kg_ha", 0)
            if k_needed > 150:
                recommendations.append(f"Requerimiento de potasio elevado ({k_needed:.0f} kg K₂O/ha). Intensifique aplicaciones durante floración y fructificación.")
            elif k_needed > 0:
                recommendations.append("Potasio esencial para calidad de fruto. Priorice en etapas reproductivas del cultivo.")
        
        # Water quality recommendations
        if water.hco3_meq > 3.0:
            recommendations.append("Bicarbonatos altos en agua. Inyecte ácido (nítrico, fosfórico o sulfúrico) antes de la solución nutritiva.")
        
        if water.na_meq > 3.0:
            recommendations.append("Sodio moderado-alto en agua. Evite acumulación con lavados periódicos (15-20% exceso de riego).")
        
        # Salinity management
        if water.ec > 1.5:
            recommendations.append(f"CE del agua elevada ({water.ec} dS/m). Monitoree CE de la solución de suelo y ajuste frecuencia de riego.")
        
        return recommendations
    
    def calculate(
        self,
        soil: SoilData,
        water: WaterData,
        crop: CropData,
        irrigation: IrrigationData,
        acid: Optional[AcidData] = None,
        currency: str = "MXN",
        user_prices: Optional[Dict[str, float]] = None,
        stage_extraction_pct: Optional[float] = None,
        previous_cumulative_pct: Optional[float] = None
    ) -> Dict:
        """
        Perform complete fertigation calculation.
        
        Args:
            soil: Soil analysis data
            water: Water analysis data
            crop: Crop requirements
            irrigation: Irrigation parameters
            acid: Optional acid treatment data (nutrients will be deducted from deficit)
            currency: Currency code (MXN, USD, etc.)
            user_prices: Optional dict of {fertilizer_slug: price_per_kg} from user's my-data/prices
            stage_extraction_pct: DELTA percentage for this stage (0-100).
            previous_cumulative_pct: Cumulative % BEFORE this stage (for soil depletion tracking).
        
        Returns a complete result dictionary with soil depletion metrics.
        """
        balance = self.calculate_nutrient_balance(
            soil, water, crop, irrigation, acid, 
            stage_extraction_pct=stage_extraction_pct,
            previous_cumulative_pct=previous_cumulative_pct
        )
        
        total_deficit = sum(max(0, b.get("deficit_kg_ha", 0)) for b in balance)
        
        if total_deficit <= 0:
            uses_custom_prices = user_prices is not None and len(user_prices) > 0
            iron_chelate = self.get_recommended_iron_chelate(water)
            return {
                "status": "success",
                "total_n_kg_ha": 0,
                "total_p2o5_kg_ha": 0,
                "total_k2o_kg_ha": 0,
                "nutrient_balance": balance,
                "fertilizer_program": [],
                "warnings": [],
                "recommendations": ["No se requiere fertilización adicional de macronutrientes. El agua de riego cubre los requerimientos del cultivo para esta etapa."],
                "estimated_cost": 0,
                "estimated_cost_ha": 0,
                "currency": currency,
                "uses_custom_prices": uses_custom_prices,
                "no_deficit": True,
                "iron_chelate_recommendation": iron_chelate
            }
        
        # Generate fertilizer program with costs (using user prices if provided)
        program = self.generate_fertilizer_program(
            balance, irrigation, currency=currency, user_prices=user_prices
        )
        
        # Generate warnings and recommendations
        warnings = self.generate_warnings(soil, water, balance)
        recommendations = self.generate_recommendations(soil, water, balance)
        
        # Summary totals
        total_n = next((b["fertilizer_needed_kg_ha"] for b in balance if b["nutrient"] == "N"), 0)
        total_p2o5 = next((b["fertilizer_needed_kg_ha"] for b in balance if b["nutrient"] == "P2O5"), 0)
        total_k2o = next((b["fertilizer_needed_kg_ha"] for b in balance if b["nutrient"] == "K2O"), 0)
        
        # Calculate total estimated cost (sum cost_cycle_total once per unique fertilizer)
        seen_ferts = set()
        estimated_cost_total = 0.0
        estimated_cost_ha = 0.0
        for fert in program:
            fert_name = fert.get("fertilizer_name", "")
            if fert_name not in seen_ferts:
                seen_ferts.add(fert_name)
                estimated_cost_total += fert.get("cost_cycle_total", 0)
                estimated_cost_ha += fert.get("cost_cycle_ha", 0)
        
        # Indicate if custom prices were used
        uses_custom_prices = user_prices is not None and len(user_prices) > 0
        
        iron_chelate = self.get_recommended_iron_chelate(water)
        
        return {
            "status": "success",
            "total_n_kg_ha": round(total_n, 2),
            "total_p2o5_kg_ha": round(total_p2o5, 2),
            "total_k2o_kg_ha": round(total_k2o, 2),
            "nutrient_balance": balance,
            "fertilizer_program": program,
            "warnings": warnings,
            "recommendations": recommendations,
            "estimated_cost": round(estimated_cost_total, 2),
            "estimated_cost_ha": round(estimated_cost_ha, 2),
            "currency": currency,
            "uses_custom_prices": uses_custom_prices,
            "iron_chelate_recommendation": iron_chelate
        }


# Singleton instance
fertiirrigation_calculator = FertiIrrigationCalculator()


def get_user_prices_for_calculator(db, user_id: int, currency: Optional[str] = None) -> Tuple[Dict[str, float], str]:
    """
    Load user's custom fertilizer prices from the database.
    
    This function should be called by routers/endpoints that use the calculator
    to fetch user's custom prices from my-data/prices.
    
    Args:
        db: Database session
        user_id: User's ID
        currency: Currency code (MXN, USD, etc.) - if None, uses user's preferred currency
    
    Returns:
        Tuple of (Dict mapping fertilizer slugs to price_per_kg, actual currency used)
    """
    from app.models.hydro_ions_models import UserFertilizerPrice, UserPriceSettings
    
    # Get user's preferred currency if not specified
    if not currency:
        settings = db.query(UserPriceSettings).filter(
            UserPriceSettings.user_id == user_id
        ).first()
        currency = settings.preferred_currency if settings else "MXN"
    
    # Load user prices
    user_prices = {}
    prices = db.query(UserFertilizerPrice).filter(
        UserFertilizerPrice.user_id == user_id,
        UserFertilizerPrice.currency == currency
    ).all()
    
    for price in prices:
        # fertilizer_id is already the slug (e.g., "urea_46_0_0", "map_11_52_0")
        slug = price.fertilizer_id
        if price.price_per_kg is not None:
            user_prices[slug] = float(price.price_per_kg)
        elif price.price_per_liter is not None:
            user_prices[slug] = float(price.price_per_liter)
    
    return user_prices, currency

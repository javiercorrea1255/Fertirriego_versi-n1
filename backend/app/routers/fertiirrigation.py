"""
FertiIrrigation Calculator Router (Independent Module).
Provides endpoints for fertigation calculations.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
import io
import json
import logging
import math
import re

from app.database import get_db
from app.services.ia_grower_v_service import get_ia_grower_v_service, IAGrowerVValidation

logger = logging.getLogger(__name__)
from app.models.database_models import User, MySoilAnalysis, WaterAnalysis, FertiIrrigationCalculation
from app.services.usage_limit_service import UsageLimitService
from app.schemas.fertiirrigation_schemas import (
    FertiIrrigationCalculateRequest,
    FertiIrrigationCalculateResponse,
    FertiIrrigationSummary,
    FertiIrrigationListResponse,
    NutrientBalance,
    FertilizerDose,
    FertiIrrigationResult,
    AcidProgramResult,
    OptimizationProfileResult,
)
from app.services.fertiirrigation_calculator import (
    fertiirrigation_calculator,
    SoilData,
    WaterData,
    CropData,
    IrrigationData,
    AcidData,
    get_user_prices_for_calculator,
    get_crop_minimums,
    infer_crop_id_from_name,
)
from app.core.auth import get_current_active_user

router = APIRouter(prefix="/api/fertiirrigation", tags=["fertiirrigation"])

ION_CONSTANTS = {
    "no3": {"valence": 1, "atomic_weight": 62.004},
    "h2po4": {"valence": 1, "atomic_weight": 96.987},
    "so42": {"valence": 2, "atomic_weight": 96.063},
    "hco3": {"valence": 1, "atomic_weight": 61.017},
    "cl": {"valence": 1, "atomic_weight": 35.453},
    "nh4": {"valence": 1, "atomic_weight": 18.039},
    "k": {"valence": 1, "atomic_weight": 39.098},
    "ca": {"valence": 2, "atomic_weight": 40.078},
    "mg": {"valence": 2, "atomic_weight": 24.305},
    "na": {"valence": 1, "atomic_weight": 22.990},
}

MICRONUTRIENT_FERTILIZER_SLUGS = {
    'iron_chelate_eddha', 'iron_chelate_edta', 'iron_chelate_dtpa',
    'iron_sulfate', 'manganese_sulfate', 'zinc_sulfate', 'copper_sulfate',
    'boric_acid', 'sodium_molybdate', 'borax',
    'diosol', 'ultrasol_micro_sqm', 'multimicro_haifa', 
    'fetrilon_combi_basf', 'micronutrient_mix_complete',
    'quelato_hierro_eddha', 'quelato_hierro_edta', 'quelato_hierro_dtpa',
    'quelato_de_hierro_eddha', 'quelato_de_hierro_edta', 'quelato_de_hierro_dtpa',
    'sulfato_manganeso', 'sulfato_zinc', 'sulfato_cobre',
    'sulfato_de_manganeso', 'sulfato_de_zinc', 'sulfato_de_cobre',
    'acido_borico', 'molibdato_sodio', 'molibdato_de_sodio',
    'sulfato_de_hierro', 'sulfato_hierro',
}

MICRONUTRIENT_ELEMENT_MAP = {
    'iron_chelate_eddha': 'Fe', 'iron_chelate_edta': 'Fe', 'iron_chelate_dtpa': 'Fe',
    'iron_sulfate': 'Fe', 'manganese_sulfate': 'Mn', 'zinc_sulfate': 'Zn',
    'copper_sulfate': 'Cu', 'boric_acid': 'B', 'sodium_molybdate': 'Mo', 'borax': 'B',
    'quelato_hierro_eddha': 'Fe', 'quelato_hierro_edta': 'Fe', 'quelato_hierro_dtpa': 'Fe',
    'quelato_de_hierro_eddha': 'Fe', 'quelato_de_hierro_edta': 'Fe', 'quelato_de_hierro_dtpa': 'Fe',
    'sulfato_manganeso': 'Mn', 'sulfato_zinc': 'Zn', 'sulfato_cobre': 'Cu',
    'sulfato_de_manganeso': 'Mn', 'sulfato_de_zinc': 'Zn', 'sulfato_de_cobre': 'Cu',
    'acido_borico': 'B', 'molibdato_sodio': 'Mo', 'molibdato_de_sodio': 'Mo',
    'sulfato_de_hierro': 'Fe', 'sulfato_hierro': 'Fe',
}

def normalize_fertilizer_slug(slug: str) -> str:
    """Normalize fertilizer slug for micronutrient detection."""
    if not slug:
        return ''
    s = slug.lower().replace('-', '_')
    s = re.sub(r'_+', '_', s)
    s = re.sub(r'_\d+(?:pct|percent|%)?$', '', s)
    s = re.sub(r'_\d+$', '', s)
    s = s.replace('_de_', '_').replace('_del_', '_')
    s = s.strip('_')
    return s

def is_micronutrient_fertilizer(slug: str, name: str) -> bool:
    """Check if a fertilizer is a micronutrient source based on slug or name."""
    slug_lower = slug.lower().replace('-', '_') if slug else ''
    name_lower = name.lower() if name else ''
    
    if slug_lower in MICRONUTRIENT_FERTILIZER_SLUGS:
        return True
    
    slug_normalized = normalize_fertilizer_slug(slug)
    if slug_normalized in MICRONUTRIENT_FERTILIZER_SLUGS:
        return True
    
    micro_keywords = [
        'quelato', 'chelate', 'fe-', 'fe_', 'eddha', 'edta', 'dtpa',
        'sulfato de manganeso', 'sulfato_de_manganeso', 'sulfato manganeso',
        'sulfato de zinc', 'sulfato_de_zinc', 'sulfato zinc',
        'sulfato de cobre', 'sulfato_de_cobre', 'sulfato cobre',
        'sulfato de hierro', 'sulfato_de_hierro', 'sulfato hierro',
        'boro', 'borico', 'boric', 'borax', 'acido borico', 'ácido bórico',
        'molibdato', 'molybdate',
        'diosol', 'ultrasol micro', 'multimicro', 'fetrilon',
        'micronutrient', 'micronutriente', 'mezcla micro',
    ]
    
    for keyword in micro_keywords:
        if keyword in slug_lower or keyword in name_lower:
            return True
    
    micro_name_patterns = [
        'quelato de hierro', 'hierro eddha', 'hierro edta', 'hierro dtpa',
        'manganeso', 'manganese',
        'zinc', 'zn',
        'cobre', 'copper', 'cu',
    ]
    for pattern in micro_name_patterns:
        if pattern in name_lower:
            return True
    
    return False

def get_micronutrient_element(slug: str, name: str) -> str:
    """Get the primary micronutrient element for a fertilizer."""
    slug_lower = slug.lower().replace('-', '_') if slug else ''
    name_lower = name.lower() if name else ''
    
    if slug_lower in MICRONUTRIENT_ELEMENT_MAP:
        return MICRONUTRIENT_ELEMENT_MAP[slug_lower]
    
    slug_normalized = normalize_fertilizer_slug(slug)
    if slug_normalized in MICRONUTRIENT_ELEMENT_MAP:
        return MICRONUTRIENT_ELEMENT_MAP[slug_normalized]
    
    if 'hierro' in name_lower or 'iron' in name_lower or 'fe' in slug_lower:
        return 'Fe'
    if 'manganeso' in name_lower or 'manganese' in name_lower or 'mn' in slug_lower:
        return 'Mn'
    if 'zinc' in name_lower or 'zn' in slug_lower:
        return 'Zn'
    if 'cobre' in name_lower or 'copper' in name_lower or 'cu' in slug_lower:
        return 'Cu'
    if 'boro' in name_lower or 'boric' in name_lower or 'borax' in name_lower:
        return 'B'
    if 'molibdato' in name_lower or 'molybdate' in name_lower or 'mo' in slug_lower:
        return 'Mo'
    
    return 'Mezcla'


def convert_to_meq(value: float, ion_key: str, from_unit: str) -> float:
    """
    Convert ion concentration to meq/L.
    
    Args:
        value: The concentration value
        ion_key: Ion identifier (no3, ca, k, etc.)
        from_unit: Source unit (meq, ppm, mmol)
    
    Returns:
        Concentration in meq/L
    """
    if not value or from_unit == "meq":
        return value or 0.0
    
    ion = ION_CONSTANTS.get(ion_key)
    if not ion:
        return value or 0.0
    
    valence = ion["valence"]
    atomic_weight = ion["atomic_weight"]
    
    if from_unit == "ppm":
        mmol = value / atomic_weight
        return mmol * valence
    elif from_unit == "mmol":
        return value * valence
    
    return value or 0.0


def soil_model_to_data(soil: MySoilAnalysis) -> SoilData:
    """Convert database model to calculator data class.
    
    Handles fallback for N when only n_total_pct is available:
    - Converts N total % to available N ppm using mineralization factor
    - Formula: n_ppm = n_total_pct × 10000 × 0.02 (2% mineralization rate)
    """
    n_no3_ppm = soil.n_no3_ppm or 0.0
    n_nh4_ppm = soil.n_nh4_ppm or 0.0
    
    if n_no3_ppm == 0 and n_nh4_ppm == 0 and soil.n_total_pct:
        estimated_n_ppm = soil.n_total_pct * 10000 * 0.02
        n_no3_ppm = estimated_n_ppm * 0.7
        n_nh4_ppm = estimated_n_ppm * 0.3
    
    return SoilData(
        texture=soil.texture or "franco",
        bulk_density=soil.bulk_density or 1.3,
        depth_cm=soil.depth_cm or 30.0,
        ph=soil.ph or 7.0,
        ec_ds_m=soil.ec_ds_m or 0.0,
        organic_matter_pct=soil.organic_matter_pct or 2.0,
        n_no3_ppm=n_no3_ppm,
        n_nh4_ppm=n_nh4_ppm,
        p_ppm=soil.p_ppm or 0.0,
        k_ppm=soil.k_ppm or 0.0,
        ca_ppm=soil.ca_ppm or 0.0,
        mg_ppm=soil.mg_ppm or 0.0,
        s_ppm=soil.s_ppm or 0.0,
        cic_cmol_kg=soil.cic_cmol_kg or 20.0,
    )


def water_model_to_data(water: WaterAnalysis) -> WaterData:
    """
    Convert database model to calculator data class.
    
    Handles unit conversion based on saved_units field.
    All ion values are converted to meq/L for consistent calculations.
    """
    saved_unit = getattr(water, 'saved_units', 'meq') or 'meq'
    
    return WaterData(
        ec=water.ec or 0.5,
        ph=water.ph or 7.0,
        no3_meq=convert_to_meq(water.anion_no3, "no3", saved_unit),
        h2po4_meq=convert_to_meq(water.anion_h2po4, "h2po4", saved_unit),
        so4_meq=convert_to_meq(water.anion_so42, "so42", saved_unit),
        hco3_meq=convert_to_meq(water.anion_hco3, "hco3", saved_unit),
        k_meq=convert_to_meq(water.cation_k, "k", saved_unit),
        ca_meq=convert_to_meq(water.cation_ca, "ca", saved_unit),
        mg_meq=convert_to_meq(water.cation_mg, "mg", saved_unit),
        na_meq=convert_to_meq(water.cation_na, "na", saved_unit),
        fe_ppm=water.micro_fe or 0.0,
        mn_ppm=water.micro_mn or 0.0,
        zn_ppm=water.micro_zn or 0.0,
        cu_ppm=water.micro_cu or 0.0,
        b_ppm=water.micro_b or 0.0,
    )


from pydantic import BaseModel

class IrrigationSuggestionRequest(BaseModel):
    soil_texture: str
    crop_name: str
    phenological_stage: str = ""
    irrigation_system: str = "goteo"
    extraction_percent: Optional[float] = None  # Average extraction % for this stage
    stage_duration_days: Optional[int] = None  # Duration of the phenological stage in days

class IrrigationSuggestionResponse(BaseModel):
    frequency_days: int
    volume_m3_ha: float
    num_applications: int
    rationale: str

@router.post("/irrigation-suggestion", response_model=IrrigationSuggestionResponse)
async def get_irrigation_suggestion(
    request: IrrigationSuggestionRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Get deterministic irrigation parameters based on soil texture and crop stage.
    """
    texture = (request.soil_texture or "").lower()
    extraction_pct = request.extraction_percent or 0
    stage_days = request.stage_duration_days or 0

    texture_frequency = {
        "arenoso": 2,
        "franco": 4,
        "franco-arenoso": 3,
        "franco-arcilloso": 5,
        "arcilloso": 7
    }
    base_frequency = texture_frequency.get(texture, 4)
    frequency_days = max(1, min(14, base_frequency))

    volume_base = 20 + (extraction_pct / 100) * 60
    volume_texture_adjust = 5 if "arenoso" in texture else (-5 if "arcilloso" in texture else 0)
    volume_m3_ha = max(5, min(120, round(volume_base + volume_texture_adjust, 1)))

    if stage_days > 0:
        num_applications = max(4, min(30, math.ceil(stage_days / frequency_days)))
    else:
        num_applications = max(4, min(30, round(4 + (extraction_pct / 100) * 26)))

    rationale = (
        "Parámetros calculados de forma determinística según textura del suelo, "
        "porcentaje de extracción y duración de la etapa."
    )

    return IrrigationSuggestionResponse(
        frequency_days=frequency_days,
        volume_m3_ha=volume_m3_ha,
        num_applications=num_applications,
        rationale=rationale
    )


class MicroRequirements(BaseModel):
    fe_g_ha: float = 0.0
    mn_g_ha: float = 0.0
    zn_g_ha: float = 0.0
    cu_g_ha: float = 0.0
    b_g_ha: float = 0.0
    mo_g_ha: float = 0.0


class AcidContributionData(BaseModel):
    acid_type: Optional[str] = None  # phosphoric_acid, nitric_acid, sulfuric_acid
    n_g_per_1000L: float = 0.0
    p_g_per_1000L: float = 0.0
    s_g_per_1000L: float = 0.0


class NutrientContributionsRequest(BaseModel):
    soil_analysis_id: int
    water_analysis_id: Optional[int] = None
    irrigation_volume_m3_ha: float = 50.0
    irrigation_frequency_days: int = 7
    area_ha: float = 1.0
    num_applications: int = 10
    requirements: Dict[str, float] = {}
    micro_requirements: Optional[MicroRequirements] = None
    stage_extraction_pct: Optional[float] = None  # Percentage of total crop extraction for this stage (0-100)
    acid_treatment: Optional[AcidContributionData] = None  # Acid contribution data
    extraction_crop_id: Optional[str] = None  # Crop ID for agronomic minimums (e.g., 'tomato', 'maize')
    extraction_stage_id: Optional[str] = None  # Stage ID for stage-specific minimums (e.g., 'seedling', 'flowering')
    previous_stage_id: Optional[str] = None  # Previous stage ID for DELTA extraction calculation
    custom_extraction_percent: Optional[Dict[str, float]] = None  # Custom stage extraction percentages
    crop_name: Optional[str] = None  # Optional crop name for soil factors


class EfficiencyDetail(BaseModel):
    Efert: float
    Esuelo: float
    Eagua: float
    req_original: float
    req_adjusted: float
    soil_effective: float
    water_effective: float


class NutrientContributionsResponse(BaseModel):
    requirements: Dict[str, float]
    soil_contribution: Dict[str, float]
    water_contribution: Dict[str, float]
    acid_contribution: Dict[str, float]
    deficit_base: Dict[str, float]
    deficit_seguridad: Dict[str, float]
    deficit_final: Dict[str, float]
    safety_percentages: Dict[str, float]
    efficiency_details: Optional[Dict[str, EfficiencyDetail]] = None
    technical_note: Optional[str] = None
    real_deficit: Dict[str, float]
    agronomic_minimums: Dict[str, float]
    micro_requirements: Dict[str, float]
    micro_soil_contribution: Dict[str, float]
    micro_water_contribution: Dict[str, float]
    micro_real_deficit: Dict[str, float]


@router.post("/calculate-contributions", response_model=NutrientContributionsResponse)
async def calculate_nutrient_contributions(
    request: NutrientContributionsRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Calculate soil and water nutrient contributions for deficit visualization.
    
    Returns:
    - requirements: Total crop requirements in kg/ha
    - soil_contribution: Nutrients provided by soil in kg/ha
    - water_contribution: Nutrients provided by irrigation water in kg/ha
    - real_deficit: Actual deficit to cover with fertilizers (requirements - soil - water)
    - micro_*: Same for micronutrients in g/ha
    """
    # Check usage limits
    usage_service = UsageLimitService(db)
    can_use = usage_service.check_can_use(current_user, 'irrigation')
    if not can_use['can_use']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=can_use['reason']
        )
    
    soil_contribution = {"N": 0.0, "P2O5": 0.0, "K2O": 0.0, "Ca": 0.0, "Mg": 0.0, "S": 0.0}
    water_contribution = {"N": 0.0, "P2O5": 0.0, "K2O": 0.0, "Ca": 0.0, "Mg": 0.0, "S": 0.0}
    acid_contribution = {"N": 0.0, "P2O5": 0.0, "K2O": 0.0, "Ca": 0.0, "Mg": 0.0, "S": 0.0}
    micro_soil_contribution = {"Fe": 0.0, "Mn": 0.0, "Zn": 0.0, "Cu": 0.0, "B": 0.0, "Mo": 0.0}
    micro_water_contribution = {"Fe": 0.0, "Mn": 0.0, "Zn": 0.0, "Cu": 0.0, "B": 0.0, "Mo": 0.0}
    
    SOIL_MICRO_AVAILABILITY_FACTOR = 0.05
    
    soil_analysis = db.query(MySoilAnalysis).filter(
        MySoilAnalysis.id == request.soil_analysis_id,
        MySoilAnalysis.user_id == current_user.id
    ).first()
    
    water_analysis = None
    if request.water_analysis_id:
        water_analysis = db.query(WaterAnalysis).filter(
            WaterAnalysis.id == request.water_analysis_id,
            WaterAnalysis.user_id == current_user.id
        ).first()
    
    crop_name_for_factors = request.crop_name
    stage_pct_by_nutrient = None
    if request.custom_extraction_percent:
        stage_pct_by_nutrient = request.custom_extraction_percent
    elif request.extraction_crop_id and request.extraction_stage_id:
        current_curve = fertiirrigation_calculator.get_extraction_curve(
            request.extraction_crop_id,
            request.extraction_stage_id
        )
        if request.previous_stage_id:
            prev_curve = fertiirrigation_calculator.get_extraction_curve(
                request.extraction_crop_id,
                request.previous_stage_id
            )
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

    if stage_pct_by_nutrient:
        for nutrient_key, pct in stage_pct_by_nutrient.items():
            if pct < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Curva de extracción inválida: delta negativo para {nutrient_key}."
                )
            if pct > 100:
                raise HTTPException(
                    status_code=400,
                    detail=f"Curva de extracción inválida: delta > 100% para {nutrient_key}."
                )

    if soil_analysis:
        soil_data = soil_model_to_data(soil_analysis)
        soil_contribution = fertiirrigation_calculator.calculate_adjusted_soil_availability(
            soil_data,
            stage_extraction_pct=request.stage_extraction_pct,
            crop_name=crop_name_for_factors,
            stage_extraction_pct_by_nutrient=stage_pct_by_nutrient
        )
        
        bulk_density = soil_analysis.bulk_density or 1.3
        depth_cm = soil_analysis.depth_cm or 30.0
        ppm_to_g_ha = bulk_density * depth_cm * 0.1 * 1000
        
        stage_factor = 1.0
        if stage_pct_by_nutrient:
            avg_stage = sum(stage_pct_by_nutrient.values()) / len(stage_pct_by_nutrient)
            stage_factor = min(1.0, max(0.0, avg_stage / 100.0))
        elif request.stage_extraction_pct is not None and request.stage_extraction_pct > 0:
            stage_factor = min(1.0, request.stage_extraction_pct / 100.0)
        
        micro_soil_contribution = {
            "Fe": (soil_analysis.fe_ppm or 0) * ppm_to_g_ha * SOIL_MICRO_AVAILABILITY_FACTOR * stage_factor,
            "Mn": (soil_analysis.mn_ppm or 0) * ppm_to_g_ha * SOIL_MICRO_AVAILABILITY_FACTOR * stage_factor,
            "Zn": (soil_analysis.zn_ppm or 0) * ppm_to_g_ha * SOIL_MICRO_AVAILABILITY_FACTOR * stage_factor,
            "Cu": (soil_analysis.cu_ppm or 0) * ppm_to_g_ha * SOIL_MICRO_AVAILABILITY_FACTOR * stage_factor,
            "B": (soil_analysis.b_ppm or 0) * ppm_to_g_ha * SOIL_MICRO_AVAILABILITY_FACTOR * stage_factor,
            "Mo": 0.0
        }
    
    if water_analysis:
        water_data = water_model_to_data(water_analysis)
        irrig_data = IrrigationData(
            system="goteo",
            frequency_days=request.irrigation_frequency_days,
            volume_m3_ha=request.irrigation_volume_m3_ha,
            area_ha=request.area_ha,
            num_applications=request.num_applications
        )
        water_contribution = fertiirrigation_calculator.calculate_water_contribution(water_data, irrig_data)
        
        num_apps = request.num_applications
        irr_volume = request.irrigation_volume_m3_ha
        micro_water_contribution = {
            "Fe": (water_analysis.micro_fe or 0) * irr_volume * num_apps,
            "Mn": (water_analysis.micro_mn or 0) * irr_volume * num_apps,
            "Zn": (water_analysis.micro_zn or 0) * irr_volume * num_apps,
            "Cu": (water_analysis.micro_cu or 0) * irr_volume * num_apps,
            "B": (water_analysis.micro_b or 0) * irr_volume * num_apps,
            "Mo": 0.0
        }
    
    base_requirements = {
        "N": request.requirements.get("n_kg_ha", 0.0),
        "P2O5": request.requirements.get("p2o5_kg_ha", 0.0),
        "K2O": request.requirements.get("k2o_kg_ha", 0.0),
        "Ca": request.requirements.get("ca_kg_ha", 0.0),
        "Mg": request.requirements.get("mg_kg_ha", 0.0),
        "S": request.requirements.get("s_kg_ha", 0.0)
    }

    if request.custom_extraction_percent:
        requirements = {
            nutrient: base_requirements.get(nutrient, 0) * (request.custom_extraction_percent.get(nutrient, 0) / 100)
            for nutrient in base_requirements
        }
    elif request.extraction_crop_id and request.extraction_stage_id:
        crop_data = CropData(
            name=request.crop_name or "Cultivo",
            n_kg_ha=base_requirements.get("N", 0),
            p2o5_kg_ha=base_requirements.get("P2O5", 0),
            k2o_kg_ha=base_requirements.get("K2O", 0),
            ca_kg_ha=base_requirements.get("Ca", 0),
            mg_kg_ha=base_requirements.get("Mg", 0),
            s_kg_ha=base_requirements.get("S", 0),
            extraction_crop_id=request.extraction_crop_id,
            extraction_stage_id=request.extraction_stage_id,
            previous_stage_id=request.previous_stage_id
        )
        requirements = fertiirrigation_calculator.calculate_stage_requirements(
            crop_data,
            request.extraction_crop_id,
            request.extraction_stage_id,
            previous_stage=request.previous_stage_id
        )
    else:
        requirements = base_requirements
    
    micro_req = request.micro_requirements or MicroRequirements()
    micro_requirements = {
        "Fe": micro_req.fe_g_ha,
        "Mn": micro_req.mn_g_ha,
        "Zn": micro_req.zn_g_ha,
        "Cu": micro_req.cu_g_ha,
        "B": micro_req.b_g_ha,
        "Mo": micro_req.mo_g_ha
    }
    
    if request.acid_treatment and request.acid_treatment.acid_type:
        liters_per_app = request.irrigation_volume_m3_ha * 1000
        apps = request.num_applications
        factor_per_app = liters_per_app / 1000
        
        acid_n_kg = (request.acid_treatment.n_g_per_1000L * factor_per_app * apps) / 1000
        acid_p_kg = (request.acid_treatment.p_g_per_1000L * factor_per_app * apps) / 1000
        acid_p2o5_kg = acid_p_kg * 2.29
        acid_s_kg = (request.acid_treatment.s_g_per_1000L * factor_per_app * apps) / 1000
        
        acid_contribution = {
            "N": acid_n_kg,
            "P2O5": acid_p2o5_kg,
            "K2O": 0.0,
            "Ca": 0.0,
            "Mg": 0.0,
            "S": acid_s_kg
        }
    
    # =================================================================
    # Obtener porcentajes de seguridad por cultivo/etapa
    # =================================================================
    safety_percentages = get_crop_minimums(
        crop_id=request.extraction_crop_id,
        stage=request.extraction_stage_id
    )
    
    # =================================================================
    # FACTORES DE EFICIENCIA POR NUTRIENTE
    # Basados en literatura científica para fertirriego por goteo
    # =================================================================
    EFFICIENCY_FACTORS = {
        # Efert: Eficiencia del fertilizante en fertirriego (80-90% típico)
        'Efert': {
            'N': 0.85, 'P2O5': 0.75, 'K2O': 0.85,
            'Ca': 0.90, 'Mg': 0.85, 'S': 0.80
        },
        # Esuelo: Eficiencia/disponibilidad del nutriente en suelo
        'Esuelo': {
            'N': 0.60, 'P2O5': 0.40, 'K2O': 0.70,
            'Ca': 0.85, 'Mg': 0.75, 'S': 0.70
        },
        # Eagua: Eficiencia del nutriente en agua de riego
        'Eagua': {
            'N': 0.95, 'P2O5': 0.50, 'K2O': 0.95,
            'Ca': 0.90, 'Mg': 0.95, 'S': 0.95
        }
    }
    
    # =================================================================
    # CÁLCULO DEL DÉFICIT CON EFICIENCIAS (Fórmula agronómica mejorada)
    # 
    # PASO 1 - Déficit base:
    # Déficit_base = max(0, Req/Efert - (Asuelo×Esuelo + Aagua×Eagua))
    #
    # PASO 2 - Déficit de seguridad:
    # Déficit_seguridad = Req × Pseguridad
    #
    # PASO 3 - Déficit final (siempre el mayor):
    # Déficit_final = max(Déficit_base, Déficit_seguridad)
    #
    # - NO se resta el ácido porque es un fertilizante más que el 
    #   optimizador selecciona para cubrir el déficit
    # - El max() garantiza que siempre se aplique al menos el mínimo
    #   de seguridad, incluso cuando suelo+agua cubren el requerimiento
    # =================================================================
    deficit_base = {}
    deficit_seguridad = {}
    deficit_final = {}
    efficiency_details = {}  # Para la nota técnica
    
    for nutrient in requirements:
        req = requirements[nutrient]
        pct = safety_percentages.get(nutrient, 0.10)  # Default 10%
        
        # Obtener eficiencias
        efert = EFFICIENCY_FACTORS['Efert'].get(nutrient, 0.85)
        esuelo = EFFICIENCY_FACTORS['Esuelo'].get(nutrient, 0.60)
        eagua = EFFICIENCY_FACTORS['Eagua'].get(nutrient, 0.90)
        
        # Contribuciones ajustadas por eficiencia
        soil_eff = soil_contribution.get(nutrient, 0) * esuelo
        water_eff = water_contribution.get(nutrient, 0) * eagua
        
        # PASO 1: Déficit base = max(0, Req/Efert - (Suelo×Esuelo + Agua×Eagua))
        req_adjusted = req / efert if efert > 0 else req
        deficit_real = max(0, req_adjusted - soil_eff - water_eff)
        
        # PASO 2: Mínimo de seguridad
        seguridad = round(req * pct, 2) if req > 0 else 0.0
        deficit_seguridad[nutrient] = seguridad
        
        # PASO 3: déficit_final = max(déficit_base, mínimo_seguridad)
        deficit_base[nutrient] = round(deficit_real, 2)
        deficit_final[nutrient] = round(max(deficit_real, seguridad), 2)
        
        # Guardar detalles para la nota técnica
        efficiency_details[nutrient] = {
            'Efert': efert,
            'Esuelo': esuelo,
            'Eagua': eagua,
            'req_original': round(req, 2),
            'req_adjusted': round(req_adjusted, 2),
            'soil_effective': round(soil_eff, 2),
            'water_effective': round(water_eff, 2)
        }
    
    # Micronutrients (keep simple for now, no safety percentages)
    micro_real_deficit = {}
    for micro in micro_requirements:
        deficit = micro_requirements[micro] - micro_soil_contribution.get(micro, 0) - micro_water_contribution.get(micro, 0)
        micro_real_deficit[micro] = round(max(0, deficit), 2)
    
    technical_note = (
        "FÓRMULA DE CÁLCULO DE DÉFICIT:\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "PASO 1 - Déficit Base:\n"
        "  Déficit_base = max(0, Req/Efert − (Asuelo×Esuelo + Aagua×Eagua))\n\n"
        "PASO 2 - Déficit de Seguridad:\n"
        "  Déficit_seguridad = Req × Pseguridad\n\n"
        "PASO 3 - Déficit Final:\n"
        "  Déficit_final = max(Déficit_base, Déficit_seguridad)\n\n"
        "FACTORES DE EFICIENCIA:\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "• Efert: Eficiencia del fertilizante en fertirriego (75-90%)\n"
        "• Esuelo: Disponibilidad del nutriente desde el suelo (40-85%)\n"
        "• Eagua: Disponibilidad del nutriente desde el agua (50-95%)\n"
        "• Pseguridad: Porcentaje mínimo obligatorio (5-15%)\n\n"
        "El déficit base representa el déficit fisiológico real.\n"
        "El déficit final SIEMPRE será al menos el mínimo de seguridad,\n"
        "garantizando aporte nutricional incluso cuando suelo y agua\n"
        "cubran el requerimiento teórico."
    )
    
    return NutrientContributionsResponse(
        requirements={k: round(v, 2) for k, v in requirements.items()},
        soil_contribution={k: round(v, 2) for k, v in soil_contribution.items()},
        water_contribution={k: round(v, 2) for k, v in water_contribution.items()},
        acid_contribution={k: round(v, 2) for k, v in acid_contribution.items()},
        deficit_base=deficit_base,
        deficit_seguridad=deficit_seguridad,
        deficit_final=deficit_final,
        safety_percentages={k: round(v * 100, 1) for k, v in safety_percentages.items()},
        efficiency_details=efficiency_details,
        technical_note=technical_note,
        real_deficit=deficit_base,
        agronomic_minimums=deficit_seguridad,
        micro_requirements={k: round(v, 2) for k, v in micro_requirements.items()},
        micro_soil_contribution={k: round(v, 2) for k, v in micro_soil_contribution.items()},
        micro_water_contribution={k: round(v, 2) for k, v in micro_water_contribution.items()},
        micro_real_deficit=micro_real_deficit
    )


@router.post("/calculate", response_model=FertiIrrigationCalculateResponse)
async def calculate_fertiirrigation(
    request: FertiIrrigationCalculateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Calculate fertigation requirements.
    
    Requires soil and water analysis IDs, crop requirements, and irrigation parameters.
    """
    # Check usage limits
    usage_service = UsageLimitService(db)
    can_use = usage_service.check_can_use(current_user, 'irrigation')
    if not can_use['can_use']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=can_use['reason']
        )
    
    # Load soil analysis
    if not request.soil_analysis_id:
        raise HTTPException(status_code=400, detail="Se requiere un análisis de suelo")
    
    soil_analysis = db.query(MySoilAnalysis).filter(
        MySoilAnalysis.id == request.soil_analysis_id,
        MySoilAnalysis.user_id == current_user.id
    ).first()
    
    if not soil_analysis:
        raise HTTPException(status_code=404, detail="Análisis de suelo no encontrado")
    
    # Load water analysis (optional but recommended)
    water_data = WaterData()  # Default empty water
    if request.water_analysis_id:
        water_analysis = db.query(WaterAnalysis).filter(
            WaterAnalysis.id == request.water_analysis_id,
            WaterAnalysis.user_id == current_user.id
        ).first()
        
        if not water_analysis:
            raise HTTPException(status_code=404, detail="Análisis de agua no encontrado")
        
        water_data = water_model_to_data(water_analysis)
    
    # Convert to calculator data classes
    soil_data = soil_model_to_data(soil_analysis)
    
    crop_data = CropData(
        name=request.crop.crop_name,
        variety=request.crop.crop_variety,
        growth_stage=request.crop.growth_stage,
        yield_target=request.crop.yield_target_ton_ha or 10.0,
        n_kg_ha=request.crop.n_kg_ha,
        p2o5_kg_ha=request.crop.p2o5_kg_ha,
        k2o_kg_ha=request.crop.k2o_kg_ha,
        ca_kg_ha=request.crop.ca_kg_ha,
        mg_kg_ha=request.crop.mg_kg_ha,
        s_kg_ha=request.crop.s_kg_ha,
        extraction_crop_id=request.crop.extraction_crop_id,
        extraction_stage_id=request.crop.extraction_stage_id,
        previous_stage_id=request.crop.previous_stage_id,
        custom_extraction_percent=request.crop.custom_extraction_percent,
    )

    if crop_data.custom_extraction_percent:
        for nutrient_key, pct in crop_data.custom_extraction_percent.items():
            if pct < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Curva de extracción inválida: delta negativo para {nutrient_key}."
                )
            if pct > 100:
                raise HTTPException(
                    status_code=400,
                    detail=f"Curva de extracción inválida: delta > 100% para {nutrient_key}."
                )

    if crop_data.extraction_crop_id and crop_data.extraction_stage_id:
        current_curve = fertiirrigation_calculator.get_extraction_curve(
            crop_data.extraction_crop_id,
            crop_data.extraction_stage_id
        )
        if crop_data.previous_stage_id:
            prev_curve = fertiirrigation_calculator.get_extraction_curve(
                crop_data.extraction_crop_id,
                crop_data.previous_stage_id
            )
        else:
            prev_curve = {"N": 0, "P2O5": 0, "K2O": 0, "Ca": 0, "Mg": 0, "S": 0}
        for nutrient_key in ["N", "P2O5", "K2O", "Ca", "Mg", "S"]:
            delta = current_curve.get(nutrient_key, 0) - prev_curve.get(nutrient_key, 0)
            if delta < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Curva de extracción inválida: delta negativo para {nutrient_key}."
                )
    
    irrigation_data = IrrigationData(
        system=request.irrigation.irrigation_system or "goteo",
        frequency_days=request.irrigation.irrigation_frequency_days,
        volume_m3_ha=request.irrigation.irrigation_volume_m3_ha,
        area_ha=request.irrigation.area_ha,
        num_applications=request.irrigation.num_applications,
    )
    
    acid_data = None
    if request.acid_treatment:
        acid_data = AcidData(
            acid_type=request.acid_treatment.acid_type,
            ml_per_1000L=request.acid_treatment.ml_per_1000L,
            cost_mxn_per_1000L=request.acid_treatment.cost_mxn_per_1000L,
            n_g_per_1000L=request.acid_treatment.n_g_per_1000L,
            p_g_per_1000L=request.acid_treatment.p_g_per_1000L,
            s_g_per_1000L=request.acid_treatment.s_g_per_1000L,
        )
    
    user_prices, user_currency = get_user_prices_for_calculator(db, current_user.id)
    
    # Calculate previous_cumulative_pct for soil depletion tracking
    previous_cumulative_pct = None
    if crop_data.extraction_crop_id and crop_data.previous_stage_id:
        stages = fertiirrigation_calculator.get_crop_stages(crop_data.extraction_crop_id)
        prev_stage = next((s for s in stages if s.get("id") == crop_data.previous_stage_id), None)
        if prev_stage and prev_stage.get("cumulative_percent"):
            # Previous stage's cumulative percentage (average of all nutrients)
            pct = prev_stage["cumulative_percent"]
            if isinstance(pct, dict):
                values = [v for v in pct.values() if isinstance(v, (int, float))]
                previous_cumulative_pct = sum(values) / len(values) if values else None
            else:
                previous_cumulative_pct = pct
    
    result = fertiirrigation_calculator.calculate(
        soil=soil_data,
        water=water_data,
        crop=crop_data,
        irrigation=irrigation_data,
        acid=acid_data,
        currency=user_currency,
        user_prices=user_prices,
        stage_extraction_pct=request.stage_extraction_pct,
        previous_cumulative_pct=previous_cumulative_pct
    )
    
    if request.optimization_profile:
        profile = request.optimization_profile
        profile_fertilizer_program = []
        num_apps = irrigation_data.num_applications
        volume_m3_ha = irrigation_data.volume_m3_ha
        volume_per_app_liters = (volume_m3_ha * 1000) / num_apps if (num_apps > 0 and volume_m3_ha) else 0
        
        for app_num in range(1, num_apps + 1):
            for fert in profile.fertilizers:
                dose_per_app = round(fert.dose_kg_ha / num_apps, 3)
                conc_g_l = round((dose_per_app * 1000) / volume_per_app_liters, 3) if volume_per_app_liters > 0 else 0
                profile_fertilizer_program.append({
                    "application_number": app_num,
                    "fertilizer_name": fert.name,
                    "fertilizer_slug": fert.slug,
                    "dose_kg_ha": dose_per_app,
                    "dose_per_application_kg_ha": dose_per_app,
                    "dose_kg_total": round(dose_per_app * irrigation_data.area_ha, 2),
                    "concentration_g_l": conc_g_l,
                    "cost_ha": round(fert.cost_ha / num_apps, 2),
                    "nutrients": fert.nutrients,
                })
        
        acid_program = None
        if profile.acid_recommendation:
            acid_rec = profile.acid_recommendation
            acid_program = {
                "acid_id": acid_rec.acid_id,
                "acid_name": acid_rec.acid_name,
                "ml_per_1000L": acid_rec.ml_per_1000L,
                "cost_per_1000L": acid_rec.cost_per_1000L,
                "nutrient_contribution": acid_rec.nutrient_contribution,
            }
        
        result["fertilizer_program"] = profile_fertilizer_program
        result["optimization_profile"] = {
            "profile_type": profile.profile_type,
            "total_cost_ha": profile.total_cost_ha,
            "coverage": profile.coverage,
            "fertilizer_count": len(profile.fertilizers),
        }
        if acid_program:
            result["acid_program"] = acid_program
        result["estimated_cost"] = profile.total_cost_ha
    
    # Save calculation if requested
    calculation_id = None
    created_at = None
    
    if request.save_calculation:
        calculation = FertiIrrigationCalculation(
            user_id=current_user.id,
            name=request.name,
            soil_analysis_id=request.soil_analysis_id,
            water_analysis_id=request.water_analysis_id,
            crop_name=request.crop.crop_name,
            crop_variety=request.crop.crop_variety,
            growth_stage=request.crop.growth_stage,
            irrigation_system=request.irrigation.irrigation_system,
            irrigation_frequency_days=request.irrigation.irrigation_frequency_days,
            irrigation_volume_m3_ha=request.irrigation.irrigation_volume_m3_ha,
            area_ha=request.irrigation.area_ha,
            yield_target_ton_ha=request.crop.yield_target_ton_ha,
            input_data={
                "soil_analysis_id": request.soil_analysis_id,
                "water_analysis_id": request.water_analysis_id,
                "crop": request.crop.model_dump(),
                "irrigation": request.irrigation.model_dump(),
            },
            results=result,
            fertilizer_program=result.get("fertilizer_program"),
            warnings=result.get("warnings"),
            total_n_kg_ha=result.get("total_n_kg_ha"),
            total_p2o5_kg_ha=result.get("total_p2o5_kg_ha"),
            total_k2o_kg_ha=result.get("total_k2o_kg_ha"),
        )
        
        db.add(calculation)
        db.commit()
        db.refresh(calculation)
        
        calculation_id = calculation.id
        created_at = calculation.created_at
    
    # Build response
    acid_program_result = None
    if result.get("acid_program"):
        acid_program_result = AcidProgramResult(**result["acid_program"])
    
    optimization_profile_result = None
    if result.get("optimization_profile"):
        optimization_profile_result = OptimizationProfileResult(**result["optimization_profile"])
    
    # Increment usage counter for analytics
    usage_service.increment_usage(current_user, 'irrigation')
    
    return FertiIrrigationCalculateResponse(
        id=calculation_id,
        name=request.name,
        status="success",
        result=FertiIrrigationResult(
            total_n_kg_ha=result["total_n_kg_ha"],
            total_p2o5_kg_ha=result["total_p2o5_kg_ha"],
            total_k2o_kg_ha=result["total_k2o_kg_ha"],
            nutrient_balance=[NutrientBalance(**nb) for nb in result["nutrient_balance"]],
            fertilizer_program=[FertilizerDose(**fd) for fd in result["fertilizer_program"]],
            acid_program=acid_program_result,
            optimization_profile=optimization_profile_result,
            warnings=result["warnings"],
            recommendations=result["recommendations"],
            estimated_cost=result.get("estimated_cost"),
        ),
        created_at=created_at,
    )


@router.get("/calculations", response_model=FertiIrrigationListResponse)
async def list_calculations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all saved fertigation calculations for the current user."""
    calculations = db.query(FertiIrrigationCalculation).filter(
        FertiIrrigationCalculation.user_id == current_user.id
    ).order_by(desc(FertiIrrigationCalculation.created_at)).all()
    
    items = []
    for calc in calculations:
        items.append(FertiIrrigationSummary(
            id=calc.id,
            name=calc.name,
            crop_name=calc.crop_name,
            created_at=calc.created_at,
            total_n_kg_ha=calc.total_n_kg_ha,
            total_p2o5_kg_ha=calc.total_p2o5_kg_ha,
            total_k2o_kg_ha=calc.total_k2o_kg_ha,
        ))
    
    return FertiIrrigationListResponse(items=items, total=len(items))


@router.get("/calculations/{calculation_id}")
async def get_calculation(
    calculation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific calculation by ID."""
    calculation = db.query(FertiIrrigationCalculation).filter(
        FertiIrrigationCalculation.id == calculation_id,
        FertiIrrigationCalculation.user_id == current_user.id
    ).first()
    
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found")
    
    return {
        "id": calculation.id,
        "name": calculation.name,
        "crop_name": calculation.crop_name,
        "crop_variety": calculation.crop_variety,
        "growth_stage": calculation.growth_stage,
        "irrigation_system": calculation.irrigation_system,
        "area_ha": calculation.area_ha,
        "total_n_kg_ha": calculation.total_n_kg_ha,
        "total_p2o5_kg_ha": calculation.total_p2o5_kg_ha,
        "total_k2o_kg_ha": calculation.total_k2o_kg_ha,
        "results": calculation.results,
        "fertilizer_program": calculation.fertilizer_program,
        "warnings": calculation.warnings,
        "input_data": calculation.input_data,
        "created_at": calculation.created_at,
    }


@router.delete("/calculations/{calculation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calculation(
    calculation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a calculation."""
    calculation = db.query(FertiIrrigationCalculation).filter(
        FertiIrrigationCalculation.id == calculation_id,
        FertiIrrigationCalculation.user_id == current_user.id
    ).first()
    
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found")
    
    db.delete(calculation)
    db.commit()
    
    return None


@router.get("/crop-requirements")
async def get_crop_requirements():
    """Get default crop nutrient requirements for common crops."""
    crops = [
        {
            "name": "Maíz",
            "yield_reference": 12,
            "n_kg_ha": 180,
            "p2o5_kg_ha": 80,
            "k2o_kg_ha": 150,
            "ca_kg_ha": 40,
            "mg_kg_ha": 30,
            "s_kg_ha": 25,
        },
        {
            "name": "Tomate",
            "yield_reference": 80,
            "n_kg_ha": 250,
            "p2o5_kg_ha": 120,
            "k2o_kg_ha": 350,
            "ca_kg_ha": 150,
            "mg_kg_ha": 50,
            "s_kg_ha": 40,
        },
        {
            "name": "Chile",
            "yield_reference": 40,
            "n_kg_ha": 220,
            "p2o5_kg_ha": 100,
            "k2o_kg_ha": 280,
            "ca_kg_ha": 120,
            "mg_kg_ha": 40,
            "s_kg_ha": 35,
        },
        {
            "name": "Fresa",
            "yield_reference": 50,
            "n_kg_ha": 180,
            "p2o5_kg_ha": 80,
            "k2o_kg_ha": 250,
            "ca_kg_ha": 100,
            "mg_kg_ha": 35,
            "s_kg_ha": 30,
        },
        {
            "name": "Aguacate",
            "yield_reference": 15,
            "n_kg_ha": 150,
            "p2o5_kg_ha": 60,
            "k2o_kg_ha": 200,
            "ca_kg_ha": 80,
            "mg_kg_ha": 40,
            "s_kg_ha": 25,
        },
        {
            "name": "Papa",
            "yield_reference": 40,
            "n_kg_ha": 200,
            "p2o5_kg_ha": 100,
            "k2o_kg_ha": 280,
            "ca_kg_ha": 60,
            "mg_kg_ha": 35,
            "s_kg_ha": 30,
        },
        {
            "name": "Cebolla",
            "yield_reference": 50,
            "n_kg_ha": 160,
            "p2o5_kg_ha": 80,
            "k2o_kg_ha": 180,
            "ca_kg_ha": 50,
            "mg_kg_ha": 25,
            "s_kg_ha": 40,
        },
        {
            "name": "Lechuga",
            "yield_reference": 30,
            "n_kg_ha": 120,
            "p2o5_kg_ha": 50,
            "k2o_kg_ha": 150,
            "ca_kg_ha": 60,
            "mg_kg_ha": 20,
            "s_kg_ha": 15,
        },
    ]
    
    return {"crops": crops}


# ============== Extraction Curves Endpoints ==============

@router.get("/extraction-crops")
async def get_extraction_crops():
    """Get list of crops with extraction curve data for stage-based fertilization."""
    from app.services.fertiirrigation_calculator import fertiirrigation_calculator
    
    crops = fertiirrigation_calculator.get_available_crops()
    return {"crops": crops}


@router.get("/extraction-crops/{crop_id}/stages")
async def get_crop_growth_stages(crop_id: str):
    """Get growth stages for a specific crop with extraction percentages."""
    from app.services.fertiirrigation_calculator import fertiirrigation_calculator
    
    stages = fertiirrigation_calculator.get_crop_stages(crop_id)
    if not stages:
        raise HTTPException(status_code=404, detail=f"Crop '{crop_id}' not found or has no extraction data")
    
    return {"crop_id": crop_id, "stages": stages}


@router.get("/extraction-crops/{crop_id}/curve/{stage_id}")
async def get_extraction_curve(crop_id: str, stage_id: str):
    """Get extraction curve percentages for a specific crop and stage."""
    from app.services.fertiirrigation_calculator import fertiirrigation_calculator
    
    curve = fertiirrigation_calculator.get_extraction_curve(crop_id, stage_id)
    if not curve:
        raise HTTPException(status_code=404, detail=f"Extraction curve not found for {crop_id}/{stage_id}")
    
    return {"crop_id": crop_id, "stage_id": stage_id, "cumulative_percent": curve}


@router.get("/soil-availability-factors")
async def get_soil_availability_factors(
    ph: float = 7.0,
    organic_matter_pct: float = 2.0,
    cic_cmol_kg: float = 20.0
):
    """
    Get soil nutrient availability adjustment factors based on soil properties.
    
    Returns factors that modify how much of the soil's nutrients are actually 
    available to the plant.
    """
    from app.services.fertiirrigation_calculator import fertiirrigation_calculator
    
    ph_factors = fertiirrigation_calculator.get_ph_availability_factors(ph)
    cic_factors = fertiirrigation_calculator.get_cic_availability_factors(cic_cmol_kg)
    om_n_release = fertiirrigation_calculator.get_om_nitrogen_release(organic_matter_pct)
    
    return {
        "ph": ph,
        "organic_matter_pct": organic_matter_pct,
        "cic_cmol_kg": cic_cmol_kg,
        "ph_availability_factors": ph_factors,
        "cic_availability_factors": cic_factors,
        "estimated_n_release_kg_ha": round(om_n_release, 1),
        "notes": {
            "ph": "Factors < 1.0 indicate reduced availability due to pH. Optimal range is 6.0-7.0.",
            "cic": "Factors < 1.0 indicate poor cation retention (leaching risk). > 1.0 indicates good retention.",
            "om_n_release": "Estimated kg N/ha released from organic matter mineralization during crop cycle."
        }
    }


# ============== Optimization Endpoints (IA Grower for FertiRiego) ==============

from app.services.fertiirrigation_optimizer import (
    FertiIrrigationOptimizer,
    NutrientDeficit,
    MicronutrientDeficit,
    get_fertigation_fertilizers,
)
from pydantic import BaseModel
from typing import Dict, Any


class AcidCostData(BaseModel):
    """Acid treatment cost data for optimization."""
    acid_type: str = ""
    ml_per_1000L: float = 0.0
    cost_mxn_per_1000L: float = 0.0
    n_g_per_1000L: float = 0.0
    p_g_per_1000L: float = 0.0
    s_g_per_1000L: float = 0.0


class MicronutrientDeficitInput(BaseModel):
    """Micronutrient deficit in g/ha."""
    fe_g_ha: float = 0.0
    mn_g_ha: float = 0.0
    zn_g_ha: float = 0.0
    cu_g_ha: float = 0.0
    b_g_ha: float = 0.0
    mo_g_ha: float = 0.0


class OptimizeRequest(BaseModel):
    """Request for fertilizer optimization."""
    deficit: Dict[str, float]  # n_kg_ha, p2o5_kg_ha, k2o_kg_ha, ca_kg_ha, mg_kg_ha, s_kg_ha (crop requirements)
    area_ha: float = 1.0
    num_applications: int = 10
    selected_fertilizer_slugs: Optional[List[str]] = None
    currency: str = "MXN"
    acid_treatment: Optional[AcidCostData] = None
    irrigation_volume_m3_ha: float = 50.0
    micro_deficit: Optional[MicronutrientDeficitInput] = None
    crop_name: Optional[str] = None
    growth_stage: Optional[str] = None
    soil_info: Optional[Dict[str, Any]] = None
    water_info: Optional[Dict[str, Any]] = None
    extraction_percent: Optional[Dict[str, float]] = None  # Stage extraction percentages
    soil_analysis_id: Optional[int] = None  # ID for loading full soil analysis
    water_analysis_id: Optional[int] = None  # ID for loading full water analysis
    stage_extraction_pct: Optional[float] = None  # Single percentage for current stage (0-100) for proportioning soil availability
    extraction_crop_id: Optional[str] = None  # Crop ID for agronomic minimums (e.g., 'tomato', 'maize')
    extraction_stage_id: Optional[str] = None  # Stage ID for stage-specific minimums (e.g., 'seedling', 'flowering')
    previous_stage_id: Optional[str] = None  # Previous stage ID for DELTA extraction calculation
    custom_extraction_percent: Optional[Dict[str, float]] = None  # Custom stage extraction percentages


class FertilizerDoseResponse(BaseModel):
    fertilizer_id: int
    fertilizer_slug: str
    fertilizer_name: str
    dose_kg_ha: float
    dose_kg_total: float
    cost_per_kg: float
    cost_total: float
    n_contribution: float
    p2o5_contribution: float
    k2o_contribution: float
    ca_contribution: float
    mg_contribution: float
    s_contribution: float


class MicronutrientDoseResponse(BaseModel):
    fertilizer_id: int
    fertilizer_slug: str
    fertilizer_name: str
    micronutrient: str
    dose_g_ha: float
    dose_g_total: float
    cost_per_kg: float
    cost_total: float
    contribution_g_ha: float


class IAGrowerVValidationResponse(BaseModel):
    """IA GROWER V Expert Validation Response."""
    is_valid: bool
    risk_level: str
    adjusted_doses: Optional[Dict[str, float]] = None
    macro_adjustments: Optional[Dict[str, Any]] = None
    micro_adjustments: Optional[Dict[str, Any]] = None
    acid_adjustments: Optional[Dict[str, Any]] = None
    compatibility_issues: List[str] = []
    warnings: List[str] = []
    recommendations: List[str] = []
    expert_notes: str = ""
    confidence_score: float = 0.0


class AcidTreatmentResponse(BaseModel):
    """Acid treatment data for profile response."""
    acid_name: str
    ml_per_1000L: float
    dose_liters_ha: float
    cost_per_1000L: float
    total_cost: float


class ProfileResult(BaseModel):
    profile_name: str
    profile_type: str
    fertilizers: List[FertilizerDoseResponse]
    macro_fertilizers: List[FertilizerDoseResponse] = []
    micronutrients: List[MicronutrientDoseResponse] = []
    total_cost_ha: float
    total_cost_total: float
    macro_cost_ha: float = 0.0
    macro_cost_total: float = 0.0
    micro_cost_ha: float = 0.0
    micro_cost_total: float = 0.0
    micronutrient_cost_ha: float = 0.0
    acid_cost_ha: float = 0.0
    acid_cost_total: float = 0.0
    grand_total_ha: float = 0.0
    grand_total_total: float = 0.0
    coverage: Dict[str, float]
    warnings: List[str]
    score: float
    ia_grower_v: Optional[IAGrowerVValidationResponse] = None
    acid_treatment: Optional[AcidTreatmentResponse] = None


class OptimizeResponse(BaseModel):
    profiles: List[ProfileResult]
    currency: str


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_fertigation(
    request: OptimizeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Optimize fertilizer selection for fertigation.
    
    Returns 3 profiles: Economic, Balanced, Complete.
    Uses user's custom fertilizer prices when available.
    Includes acid treatment cost when provided.
    Acid nutrient contributions are deducted from deficits before optimization.
    Soil and water contributions are deducted when analysis IDs are provided.
    """
    base_requirements = {
        "N": request.deficit.get("n_kg_ha", 0),
        "P2O5": request.deficit.get("p2o5_kg_ha", 0),
        "K2O": request.deficit.get("k2o_kg_ha", 0),
        "Ca": request.deficit.get("ca_kg_ha", 0),
        "Mg": request.deficit.get("mg_kg_ha", 0),
        "S": request.deficit.get("s_kg_ha", 0),
    }

    stage_pct_by_nutrient = None
    if request.custom_extraction_percent:
        stage_pct_by_nutrient = request.custom_extraction_percent
        stage_requirements = {
            nutrient: base_requirements.get(nutrient, 0) * (request.custom_extraction_percent.get(nutrient, 0) / 100)
            for nutrient in base_requirements
        }
    elif request.extraction_crop_id and request.extraction_stage_id:
        current_curve = fertiirrigation_calculator.get_extraction_curve(
            request.extraction_crop_id,
            request.extraction_stage_id
        )
        if request.previous_stage_id:
            prev_curve = fertiirrigation_calculator.get_extraction_curve(
                request.extraction_crop_id,
                request.previous_stage_id
            )
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
        crop_data = CropData(
            name=request.crop_name or "Cultivo",
            n_kg_ha=base_requirements.get("N", 0),
            p2o5_kg_ha=base_requirements.get("P2O5", 0),
            k2o_kg_ha=base_requirements.get("K2O", 0),
            ca_kg_ha=base_requirements.get("Ca", 0),
            mg_kg_ha=base_requirements.get("Mg", 0),
            s_kg_ha=base_requirements.get("S", 0),
            extraction_crop_id=request.extraction_crop_id,
            extraction_stage_id=request.extraction_stage_id,
            previous_stage_id=request.previous_stage_id,
        )
        stage_requirements = fertiirrigation_calculator.calculate_stage_requirements(
            crop_data,
            request.extraction_crop_id,
            request.extraction_stage_id,
            previous_stage=request.previous_stage_id
        )
    else:
        stage_requirements = base_requirements

    if stage_pct_by_nutrient:
        for nutrient_key, pct in stage_pct_by_nutrient.items():
            if pct < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Curva de extracción inválida: delta negativo para {nutrient_key}."
                )
            if pct > 100:
                raise HTTPException(
                    status_code=400,
                    detail=f"Curva de extracción inválida: delta > 100% para {nutrient_key}."
                )

    n_deficit = stage_requirements.get("N", 0)
    p2o5_deficit = stage_requirements.get("P2O5", 0)
    k2o_deficit = stage_requirements.get("K2O", 0)
    ca_deficit = stage_requirements.get("Ca", 0)
    mg_deficit = stage_requirements.get("Mg", 0)
    s_deficit = stage_requirements.get("S", 0)
    
    soil_contribution = {"N": 0, "P2O5": 0, "K2O": 0, "Ca": 0, "Mg": 0, "S": 0}
    water_contribution = {"N": 0, "P2O5": 0, "K2O": 0, "Ca": 0, "Mg": 0, "S": 0}
    
    if request.soil_analysis_id:
        soil_analysis = db.query(MySoilAnalysis).filter(
            MySoilAnalysis.id == request.soil_analysis_id,
            MySoilAnalysis.user_id == current_user.id
        ).first()
        if soil_analysis:
            soil_data = soil_model_to_data(soil_analysis)
            crop_name_for_factors = getattr(request, 'crop_name', None)
            soil_contribution = fertiirrigation_calculator.calculate_adjusted_soil_availability(
                soil_data,
                stage_extraction_pct=request.stage_extraction_pct,
                crop_name=crop_name_for_factors,
                stage_extraction_pct_by_nutrient=stage_pct_by_nutrient
            )
    
    if request.water_analysis_id:
        water_analysis = db.query(WaterAnalysis).filter(
            WaterAnalysis.id == request.water_analysis_id,
            WaterAnalysis.user_id == current_user.id
        ).first()
        if water_analysis:
            water_data = water_model_to_data(water_analysis)
            irrig_data = IrrigationData(
                system="goteo",
                frequency_days=7,
                volume_m3_ha=request.irrigation_volume_m3_ha,
                area_ha=request.area_ha,
                num_applications=request.num_applications
            )
            water_contribution = fertiirrigation_calculator.calculate_water_contribution(water_data, irrig_data)
    
    n_deficit = max(0, n_deficit - soil_contribution.get("N", 0) - water_contribution.get("N", 0))
    p2o5_deficit = max(0, p2o5_deficit - soil_contribution.get("P2O5", 0) - water_contribution.get("P2O5", 0))
    k2o_deficit = max(0, k2o_deficit - soil_contribution.get("K2O", 0) - water_contribution.get("K2O", 0))
    ca_deficit = max(0, ca_deficit - soil_contribution.get("Ca", 0) - water_contribution.get("Ca", 0))
    mg_deficit = max(0, mg_deficit - soil_contribution.get("Mg", 0) - water_contribution.get("Mg", 0))
    s_deficit = max(0, s_deficit - soil_contribution.get("S", 0) - water_contribution.get("S", 0))
    
    # Apply tolerance: deficits < 0.05 kg/ha are considered zero (rounding residuals)
    DEFICIT_TOLERANCE_KG_HA = 0.05
    n_deficit = 0 if n_deficit < DEFICIT_TOLERANCE_KG_HA else n_deficit
    p2o5_deficit = 0 if p2o5_deficit < DEFICIT_TOLERANCE_KG_HA else p2o5_deficit
    k2o_deficit = 0 if k2o_deficit < DEFICIT_TOLERANCE_KG_HA else k2o_deficit
    ca_deficit = 0 if ca_deficit < DEFICIT_TOLERANCE_KG_HA else ca_deficit
    mg_deficit = 0 if mg_deficit < DEFICIT_TOLERANCE_KG_HA else mg_deficit
    s_deficit = 0 if s_deficit < DEFICIT_TOLERANCE_KG_HA else s_deficit
    
    if request.acid_treatment and request.acid_treatment.acid_type:
        liters_per_app = request.irrigation_volume_m3_ha * 1000
        apps = request.num_applications
        factor_per_app = liters_per_app / 1000
        
        acid_n_kg = (request.acid_treatment.n_g_per_1000L * factor_per_app * apps) / 1000
        acid_p_kg = (request.acid_treatment.p_g_per_1000L * factor_per_app * apps) / 1000
        acid_p2o5_kg = acid_p_kg * 2.29
        acid_s_kg = (request.acid_treatment.s_g_per_1000L * factor_per_app * apps) / 1000
        
        n_deficit = max(0, n_deficit - acid_n_kg)
        p2o5_deficit = max(0, p2o5_deficit - acid_p2o5_kg)
        s_deficit = max(0, s_deficit - acid_s_kg)
        
        # Re-apply tolerance after acid contribution
        n_deficit = 0 if n_deficit < DEFICIT_TOLERANCE_KG_HA else n_deficit
        p2o5_deficit = 0 if p2o5_deficit < DEFICIT_TOLERANCE_KG_HA else p2o5_deficit
        s_deficit = 0 if s_deficit < DEFICIT_TOLERANCE_KG_HA else s_deficit
    
    # ============== AGRONOMIC MINIMUMS FOR ALL MACRONUTRIENTS ==============
    # v2.0: Apply minimums to ALL 6 macronutrients (N, P2O5, K2O, Ca, Mg, S) by stage
    # Formula: MAX(physiological_deficit, requirement × min_percentage_for_stage)
    crop_id_for_minimums = request.extraction_crop_id
    if not crop_id_for_minimums and request.crop_name:
        crop_id_for_minimums = infer_crop_id_from_name(request.crop_name)
    stage_for_minimums = request.extraction_stage_id
    crop_minimums = get_crop_minimums(crop_id_for_minimums, stage_for_minimums)
    
    # Original requirements from request (before any deductions)
    n_requirement = stage_requirements.get("N", 0)
    p2o5_requirement = stage_requirements.get("P2O5", 0)
    k2o_requirement = stage_requirements.get("K2O", 0)
    ca_requirement = stage_requirements.get("Ca", 0)
    mg_requirement = stage_requirements.get("Mg", 0)
    s_requirement = stage_requirements.get("S", 0)
    
    # Get minimum percentages for all macronutrients
    n_min_pct = crop_minimums.get("N")
    p2o5_min_pct = crop_minimums.get("P2O5")
    k2o_min_pct = crop_minimums.get("K2O")
    ca_min_pct = crop_minimums.get("Ca")
    mg_min_pct = crop_minimums.get("Mg")
    s_min_pct = crop_minimums.get("S")
    
    # Apply minimums to N, P2O5, K2O (new in v2.0)
    if n_min_pct is not None and n_requirement > 0:
        n_min_dose = n_requirement * n_min_pct
        if n_deficit < n_min_dose:
            logger.info(f"Security minimum applied for N: {n_deficit:.2f} -> {n_min_dose:.2f} kg/ha ({n_min_pct*100:.0f}% of {n_requirement:.2f})")
            n_deficit = n_min_dose
    
    if p2o5_min_pct is not None and p2o5_requirement > 0:
        p2o5_min_dose = p2o5_requirement * p2o5_min_pct
        if p2o5_deficit < p2o5_min_dose:
            logger.info(f"Security minimum applied for P2O5: {p2o5_deficit:.2f} -> {p2o5_min_dose:.2f} kg/ha ({p2o5_min_pct*100:.0f}% of {p2o5_requirement:.2f})")
            p2o5_deficit = p2o5_min_dose
    
    if k2o_min_pct is not None and k2o_requirement > 0:
        k2o_min_dose = k2o_requirement * k2o_min_pct
        if k2o_deficit < k2o_min_dose:
            logger.info(f"Security minimum applied for K2O: {k2o_deficit:.2f} -> {k2o_min_dose:.2f} kg/ha ({k2o_min_pct*100:.0f}% of {k2o_requirement:.2f})")
            k2o_deficit = k2o_min_dose
    
    # Apply minimums to Ca, Mg, S (existing behavior, now stage-aware)
    if ca_min_pct is not None and ca_requirement > 0:
        ca_min_dose = ca_requirement * ca_min_pct
        if ca_deficit < ca_min_dose:
            logger.info(f"Security minimum applied for Ca: {ca_deficit:.2f} -> {ca_min_dose:.2f} kg/ha ({ca_min_pct*100:.0f}% of {ca_requirement:.2f})")
            ca_deficit = ca_min_dose
    
    if mg_min_pct is not None and mg_requirement > 0:
        mg_min_dose = mg_requirement * mg_min_pct
        if mg_deficit < mg_min_dose:
            logger.info(f"Security minimum applied for Mg: {mg_deficit:.2f} -> {mg_min_dose:.2f} kg/ha ({mg_min_pct*100:.0f}% of {mg_requirement:.2f})")
            mg_deficit = mg_min_dose
    
    if s_min_pct is not None and s_requirement > 0:
        s_min_dose = s_requirement * s_min_pct
        if s_deficit < s_min_dose:
            logger.info(f"Security minimum applied for S: {s_deficit:.2f} -> {s_min_dose:.2f} kg/ha ({s_min_pct*100:.0f}% of {s_requirement:.2f})")
            s_deficit = s_min_dose
    # ============== END AGRONOMIC MINIMUMS ==============
    
    total_macro_deficit = n_deficit + p2o5_deficit + k2o_deficit + ca_deficit + mg_deficit + s_deficit
    
    total_micro_deficit = 0
    if request.micro_deficit:
        total_micro_deficit = (
            max(0, request.micro_deficit.fe_g_ha or 0) +
            max(0, request.micro_deficit.mn_g_ha or 0) +
            max(0, request.micro_deficit.zn_g_ha or 0) +
            max(0, request.micro_deficit.cu_g_ha or 0) +
            max(0, request.micro_deficit.b_g_ha or 0) +
            max(0, request.micro_deficit.mo_g_ha or 0)
        )
    
    has_macro_deficit = total_macro_deficit > 0
    has_micro_deficit = total_micro_deficit > 0
    
    # Calculate acid costs and build acid treatment response (needed for all scenarios including no-deficit)
    acid_cost_ha = 0.0
    acid_cost_total = 0.0
    acid_treatment_response = None
    if request.acid_treatment and request.acid_treatment.ml_per_1000L > 0:
        total_volume_m3 = request.irrigation_volume_m3_ha * request.num_applications * request.area_ha
        total_liters = total_volume_m3 * 1000
        acid_cost_total = (total_liters / 1000) * request.acid_treatment.cost_mxn_per_1000L
        acid_cost_ha = acid_cost_total / request.area_ha if request.area_ha > 0 else 0
        
        # Calculate dose in liters per hectare
        # irrigation_volume_m3_ha is per application in m³, we need total liters of acid
        # Formula: (m³/ha * 1000 L/m³) / 1000 * ml_per_1000L / 1000 * num_apps
        # Simplifies to: m³/ha * ml_per_1000L / 1000 * num_apps
        # Example: 50 m³/ha * 100 ml/1000L / 1000 * 10 apps = 50 L/ha
        dose_liters_ha = request.irrigation_volume_m3_ha * request.acid_treatment.ml_per_1000L / 1000 * request.num_applications
        
        acid_treatment_response = AcidTreatmentResponse(
            acid_name=request.acid_treatment.acid_type or "Ácido",
            ml_per_1000L=request.acid_treatment.ml_per_1000L,
            dose_liters_ha=round(dose_liters_ha, 2),
            cost_per_1000L=request.acid_treatment.cost_mxn_per_1000L,
            total_cost=round(acid_cost_total, 2)
        )
    
    if not has_macro_deficit and not has_micro_deficit:
        return OptimizeResponse(
            profiles=[
                ProfileResult(
                    profile_name="Sin Déficit",
                    profile_type="none",
                    fertilizers=[],
                    micronutrients=[],
                    total_cost_ha=0.0,
                    total_cost_total=0.0,
                    micronutrient_cost_ha=0.0,
                    acid_cost_ha=round(acid_cost_ha, 2),
                    acid_cost_total=round(acid_cost_total, 2),
                    grand_total_ha=round(acid_cost_ha, 2),
                    grand_total_total=round(acid_cost_total, 2),
                    coverage={"N": 100, "P2O5": 100, "K2O": 100, "Ca": 100, "Mg": 100, "S": 100},
                    warnings=["No se requiere fertilización adicional. El suelo y agua cubren los requerimientos del cultivo."],
                    score=100.0,
                    ia_grower_v=None,
                    acid_treatment=acid_treatment_response
                )
            ],
            currency=request.currency
        )
    
    optimizer = FertiIrrigationOptimizer(
        db=db,
        user_id=current_user.id,
        currency=request.currency
    )
    
    # CASE 1: Only micro deficit (no macro) - Don't call optimizer, just calculate micronutrients
    # Note: has_micro_deficit is only true when request.micro_deficit exists (see calculation above)
    if not has_macro_deficit and has_micro_deficit:
        micro_deficit_obj = MicronutrientDeficit(
            fe_g_ha=request.micro_deficit.fe_g_ha,
            mn_g_ha=request.micro_deficit.mn_g_ha,
            zn_g_ha=request.micro_deficit.zn_g_ha,
            cu_g_ha=request.micro_deficit.cu_g_ha,
            b_g_ha=request.micro_deficit.b_g_ha,
            mo_g_ha=request.micro_deficit.mo_g_ha,
        )
        micronutrient_doses = optimizer.calculate_micronutrients(
            micro_deficit_obj, request.area_ha, request.num_applications, None
        )
        micro_cost_ha = sum(m.cost_total for m in micronutrient_doses) / request.area_ha if request.area_ha > 0 else 0
        
        return OptimizeResponse(
            profiles=[
                ProfileResult(
                    profile_name="Solo Micronutrientes",
                    profile_type="micro_only",
                    fertilizers=[],
                    micronutrients=[
                        MicronutrientDoseResponse(
                            fertilizer_id=m.fertilizer_id,
                            fertilizer_slug=m.fertilizer_slug,
                            fertilizer_name=m.fertilizer_name,
                            micronutrient=m.micronutrient,
                            dose_g_ha=m.dose_g_ha,
                            dose_g_total=m.dose_g_total,
                            cost_per_kg=m.cost_per_kg,
                            cost_total=m.cost_total,
                            contribution_g_ha=m.contribution_g_ha,
                        ) for m in micronutrient_doses
                    ],
                    total_cost_ha=0.0,
                    total_cost_total=0.0,
                    micronutrient_cost_ha=round(micro_cost_ha, 2),
                    acid_cost_ha=round(acid_cost_ha, 2),
                    acid_cost_total=round(acid_cost_total, 2),
                    grand_total_ha=round(micro_cost_ha + acid_cost_ha, 2),
                    grand_total_total=round((micro_cost_ha * request.area_ha) + acid_cost_total, 2),
                    coverage={"N": 100, "P2O5": 100, "K2O": 100, "Ca": 100, "Mg": 100, "S": 100},
                    warnings=["Sin déficit de macronutrientes. Solo se recomienda fertilización con micronutrientes."],
                    score=100.0,
                    ia_grower_v=None,
                    acid_treatment=acid_treatment_response
                )
            ],
            currency=request.currency
        )
    
    # CASE 2: Has macro deficit (with or without micro)
    deficit = NutrientDeficit(
        n_kg_ha=n_deficit,
        p2o5_kg_ha=p2o5_deficit,
        k2o_kg_ha=k2o_deficit,
        ca_kg_ha=ca_deficit,
        mg_kg_ha=mg_deficit,
        s_kg_ha=s_deficit,
    )
    
    # Only pass micro_deficit if there's actual micro deficit
    micro_deficit = None
    if has_micro_deficit and request.micro_deficit:
        micro_deficit = MicronutrientDeficit(
            fe_g_ha=request.micro_deficit.fe_g_ha,
            mn_g_ha=request.micro_deficit.mn_g_ha,
            zn_g_ha=request.micro_deficit.zn_g_ha,
            cu_g_ha=request.micro_deficit.cu_g_ha,
            b_g_ha=request.micro_deficit.b_g_ha,
            mo_g_ha=request.micro_deficit.mo_g_ha,
        )
    
    results = optimizer.optimize(
        deficit=deficit,
        area_ha=request.area_ha,
        num_applications=request.num_applications,
        selected_slugs=request.selected_fertilizer_slugs,
        micro_deficit=micro_deficit
    )
    
    # Get IA GROWER V service for expert validation
    ia_grower_v = get_ia_grower_v_service()
    is_manual_mode = bool(request.selected_fertilizer_slugs)
    
    # Build context for IA GROWER V validation
    extraction_pct = request.extraction_percent or {}
    avg_extraction = sum(extraction_pct.values()) / len(extraction_pct) if extraction_pct else 100
    
    crop_info = {
        "name": request.crop_name or "Cultivo",
        "growth_stage": request.growth_stage or "General",
        "area_ha": request.area_ha,
        "num_applications": request.num_applications,
        "extraction_percent": extraction_pct,
        "avg_extraction_percent": round(avg_extraction, 1),
        "irrigation_volume_m3_ha": request.irrigation_volume_m3_ha
    }
    
    soil_info = request.soil_info or {}
    water_info = request.water_info or {}
    
    deficits_dict = {
        "N": n_deficit,
        "P2O5": p2o5_deficit,
        "K2O": k2o_deficit,
        "Ca": ca_deficit,
        "Mg": mg_deficit,
        "S": s_deficit
    }
    
    acid_treatment_info = None
    if request.acid_treatment and request.acid_treatment.acid_type:
        acid_treatment_info = {
            "acid_name": request.acid_treatment.acid_type,
            "dose_ml_per_1000l": request.acid_treatment.ml_per_1000L,
            "initial_ph": water_info.get("ph", 7.0),
            "target_ph": 6.0
        }
    
    profiles = []
    for r in results:
        # Add contextual warning when only macros are needed (no micro deficit)
        if has_macro_deficit and not has_micro_deficit:
            no_micro_warning = "Sin déficit de micronutrientes. Solo se recomienda fertilización con macronutrientes."
            r.warnings = [no_micro_warning] + (r.warnings or [])
        
        # Prepare data for IA GROWER V validation
        fertilizers_data = [
            {
                "fertilizer_name": f.fertilizer_name,
                "fertilizer_slug": f.fertilizer_slug,
                "dose_kg_ha": f.dose_kg_ha,
                "n_contribution": f.n_contribution,
                "p2o5_contribution": f.p2o5_contribution,
                "k2o_contribution": f.k2o_contribution,
                "ca_contribution": f.ca_contribution,
                "mg_contribution": f.mg_contribution,
                "s_contribution": f.s_contribution
            } for f in r.fertilizers
        ]
        
        micronutrients_data = [
            {
                "fertilizer_name": m.fertilizer_name,
                "dose_g_ha": m.dose_g_ha,
                "contributions": {m.micronutrient: m.contribution_g_ha}
            } for m in r.micronutrients
        ]
        
        # Call IA GROWER V for expert validation
        ia_validation = None
        try:
            validation_result = await ia_grower_v.validate_fertiirrigation(
                profile_name=r.profile_name,
                is_manual_mode=is_manual_mode,
                crop_info=crop_info,
                soil_info=soil_info,
                water_info=water_info,
                deficits=deficits_dict,
                fertilizers=fertilizers_data,
                micronutrients=micronutrients_data,
                acid_treatment=acid_treatment_info,
                coverage=r.coverage
            )
            
            # ==================== AUTO-APPLY IA GROWER V ADJUSTMENTS ====================
            adjustments_applied = 0
            if validation_result.adjusted_doses:
                for f in r.fertilizers:
                    fert_slug = f.fertilizer_slug.lower().replace(" ", "_").replace("-", "_")
                    fert_name_slug = f.fertilizer_name.lower().replace(" ", "_").replace("-", "_")
                    
                    adjusted_value = None
                    for adj_key, adj_val in validation_result.adjusted_doses.items():
                        adj_key_normalized = adj_key.lower().replace(" ", "_").replace("-", "_")
                        if adj_key_normalized == fert_slug or adj_key == f.fertilizer_slug or adj_key_normalized == fert_name_slug:
                            if isinstance(adj_val, (int, float)):
                                adjusted_value = adj_val
                            elif isinstance(adj_val, dict) and "dose" in adj_val:
                                adjusted_value = adj_val.get("dose")
                            break
                    
                    if adjusted_value is not None and isinstance(adjusted_value, (int, float)) and adjusted_value > 0:
                        original_dose = f.dose_kg_ha or 0.001
                        if original_dose > 0:
                            ratio = adjusted_value / original_dose
                            f.dose_kg_ha = adjusted_value
                            f.dose_kg_total = adjusted_value * request.area_ha
                            f.cost_total = f.cost_per_kg * f.dose_kg_total if f.cost_per_kg else 0
                            f.n_contribution = round((f.n_contribution or 0) * ratio, 2)
                            f.p2o5_contribution = round((f.p2o5_contribution or 0) * ratio, 2)
                            f.k2o_contribution = round((f.k2o_contribution or 0) * ratio, 2)
                            f.ca_contribution = round((f.ca_contribution or 0) * ratio, 2)
                            f.mg_contribution = round((f.mg_contribution or 0) * ratio, 2)
                            f.s_contribution = round((f.s_contribution or 0) * ratio, 2)
                            adjustments_applied += 1
                            logger.debug(f"[IA GROWER V AUTO] {f.fertilizer_name}: {original_dose:.2f} -> {adjusted_value:.2f} kg/ha (ratio={ratio:.3f})")
            
            if validation_result.micro_adjustments:
                for m in r.micronutrients:
                    for adj_key, adj_val in validation_result.micro_adjustments.items():
                        adj_key_normalized = adj_key.lower().replace(" ", "_").replace("-", "_")
                        fert_slug = m.fertilizer_slug.lower().replace(" ", "_").replace("-", "_") if m.fertilizer_slug else ""
                        if adj_key_normalized == fert_slug or adj_key.lower() == m.micronutrient.lower():
                            micro_dose = None
                            if isinstance(adj_val, (int, float)):
                                micro_dose = adj_val
                            elif isinstance(adj_val, dict):
                                micro_dose = adj_val.get("dose") or adj_val.get("suggested_dose")
                            
                            if micro_dose is not None and isinstance(micro_dose, (int, float)) and micro_dose > 0:
                                original_dose = m.dose_g_ha or 0.001
                                if original_dose > 0:
                                    ratio = micro_dose / original_dose
                                    m.dose_g_ha = micro_dose
                                    m.dose_g_total = micro_dose * request.area_ha
                                    m.cost_total = (m.cost_per_kg or 0) * m.dose_g_total / 1000
                                    m.contribution_g_ha = round((m.contribution_g_ha or 0) * ratio, 2)
                                    adjustments_applied += 1
                                    logger.debug(f"[IA GROWER V AUTO MICRO] {m.fertilizer_name}: {original_dose:.2f} -> {micro_dose:.2f} g/ha")
                            break
            
            if adjustments_applied > 0:
                logger.info(f"[IA GROWER V AUTO] Applied {adjustments_applied} adjustment(s) for {r.profile_name}")
                macro_cost_ha = sum(f.cost_per_kg * f.dose_kg_ha for f in r.fertilizers if f.cost_per_kg)
                macro_cost_total = sum(f.cost_total for f in r.fertilizers if f.cost_total)
                micro_cost_ha = sum((m.cost_per_kg or 0) * m.dose_g_ha / 1000 for m in r.micronutrients if m.cost_per_kg)
                r.total_cost_ha = macro_cost_ha
                r.total_cost_total = macro_cost_total
                r.micronutrient_cost_ha = micro_cost_ha
            
            ia_validation = IAGrowerVValidationResponse(
                is_valid=validation_result.is_valid,
                risk_level=validation_result.risk_level,
                adjusted_doses=validation_result.adjusted_doses,
                macro_adjustments=validation_result.macro_adjustments,
                micro_adjustments=validation_result.micro_adjustments,
                acid_adjustments=validation_result.acid_adjustments,
                compatibility_issues=validation_result.compatibility_issues,
                warnings=validation_result.warnings,
                recommendations=validation_result.recommendations,
                expert_notes=validation_result.expert_notes,
                confidence_score=validation_result.confidence_score
            )
            logger.info(f"[IA GROWER V] {r.profile_name}: valid={validation_result.is_valid}, risk={validation_result.risk_level}, auto_applied={adjustments_applied}")
        except Exception as e:
            logger.error(f"[IA GROWER V] Error validating {r.profile_name}: {e}")
        
        macro_fertilizers = []
        micro_from_macros = []
        micro_separated_cost_total = 0.0
        
        for f in r.fertilizers:
            slug = f.fertilizer_slug or ''
            name = f.fertilizer_name or ''
            if is_micronutrient_fertilizer(slug, name):
                micro_element = get_micronutrient_element(slug, name)
                dose_g_ha = (f.dose_kg_ha or 0) * 1000
                dose_g_total = (f.dose_kg_total or 0) * 1000
                fert_cost_total = f.cost_total if f.cost_total else ((f.cost_per_kg or 0) * (f.dose_kg_total or 0))
                micro_separated_cost_total += fert_cost_total
                micro_from_macros.append(MicronutrientDoseResponse(
                    fertilizer_id=f.fertilizer_id,
                    fertilizer_slug=f.fertilizer_slug,
                    fertilizer_name=f.fertilizer_name,
                    micronutrient=micro_element,
                    dose_g_ha=round(dose_g_ha, 1),
                    dose_g_total=round(dose_g_total, 1),
                    cost_per_kg=f.cost_per_kg or 0,
                    cost_total=fert_cost_total,
                    contribution_g_ha=round(dose_g_ha, 1),
                ))
            else:
                macro_fertilizers.append(f)
        
        existing_micros = [
            MicronutrientDoseResponse(
                fertilizer_id=m.fertilizer_id,
                fertilizer_slug=m.fertilizer_slug,
                fertilizer_name=m.fertilizer_name,
                micronutrient=m.micronutrient,
                dose_g_ha=m.dose_g_ha or 0,
                dose_g_total=m.dose_g_total or 0,
                cost_per_kg=m.cost_per_kg or 0,
                cost_total=m.cost_total or 0,
                contribution_g_ha=m.contribution_g_ha or 0,
            ) for m in r.micronutrients
        ]
        all_micronutrients = existing_micros + micro_from_macros
        
        original_total_cost_ha = r.total_cost_ha or 0
        original_total_cost_total = r.total_cost_total or 0
        original_micro_cost_ha = r.micronutrient_cost_ha or 0
        
        if original_total_cost_total == 0 and macro_fertilizers:
            original_total_cost_total = sum(
                (f.cost_total if f.cost_total else ((f.cost_per_kg or 0) * (f.dose_kg_total or 0)))
                for f in macro_fertilizers
            ) + micro_separated_cost_total
        if original_total_cost_ha == 0 and request.area_ha > 0:
            original_total_cost_ha = original_total_cost_total / request.area_ha
        
        separated_micro_cost_ha = micro_separated_cost_total / request.area_ha if request.area_ha > 0 else 0
        
        macro_cost_ha = max(0, original_total_cost_ha - separated_micro_cost_ha)
        macro_cost_total = max(0, original_total_cost_total - micro_separated_cost_total)
        
        micro_cost_ha = original_micro_cost_ha + separated_micro_cost_ha
        micro_cost_total = (original_micro_cost_ha * request.area_ha) + micro_separated_cost_total
        
        grand_total_ha = macro_cost_ha + micro_cost_ha + acid_cost_ha
        grand_total_total = macro_cost_total + micro_cost_total + acid_cost_total
        
        macro_fert_responses = [
            FertilizerDoseResponse(
                fertilizer_id=f.fertilizer_id,
                fertilizer_slug=f.fertilizer_slug,
                fertilizer_name=f.fertilizer_name,
                dose_kg_ha=f.dose_kg_ha,
                dose_kg_total=f.dose_kg_total,
                cost_per_kg=f.cost_per_kg,
                cost_total=f.cost_total,
                n_contribution=f.n_contribution,
                p2o5_contribution=f.p2o5_contribution,
                k2o_contribution=f.k2o_contribution,
                ca_contribution=f.ca_contribution,
                mg_contribution=f.mg_contribution,
                s_contribution=f.s_contribution,
            ) for f in macro_fertilizers
        ]
        
        profiles.append(ProfileResult(
            profile_name=r.profile_name,
            profile_type=r.profile_type,
            fertilizers=macro_fert_responses,
            macro_fertilizers=macro_fert_responses,
            micronutrients=all_micronutrients,
            total_cost_ha=round(macro_cost_ha, 2),
            total_cost_total=round(macro_cost_total, 2),
            macro_cost_ha=round(macro_cost_ha, 2),
            macro_cost_total=round(macro_cost_total, 2),
            micro_cost_ha=round(micro_cost_ha, 2),
            micro_cost_total=round(micro_cost_total, 2),
            micronutrient_cost_ha=round(micro_cost_ha, 2),
            acid_cost_ha=round(acid_cost_ha, 2),
            acid_cost_total=round(acid_cost_total, 2),
            grand_total_ha=round(grand_total_ha, 2),
            grand_total_total=round(grand_total_total, 2),
            coverage=r.coverage,
            warnings=r.warnings,
            score=r.score,
            ia_grower_v=ia_validation,
            acid_treatment=acid_treatment_response,
        ))
    
    return OptimizeResponse(profiles=profiles, currency=request.currency)


class FertilizerListItem(BaseModel):
    id: int
    slug: str
    name: str
    category: str
    n_pct: float
    p2o5_pct: float
    k2o_pct: float
    ca_pct: float
    mg_pct: float
    s_pct: float
    price: float
    unit: str
    physical_state: str


class FertilizerListResponse(BaseModel):
    fertilizers: List[FertilizerListItem]
    total: int


@router.get("/fertilizers", response_model=FertilizerListResponse)
async def list_fertigation_fertilizers(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all fertilizers suitable for fertigation with user prices.
    
    Returns fertilizer catalog filtered for fertirriego use.
    Prices include user custom prices when available.
    """
    fertilizers = get_fertigation_fertilizers(db, current_user.id)
    
    return FertilizerListResponse(
        fertilizers=[FertilizerListItem(**f) for f in fertilizers],
        total=len(fertilizers)
    )


# ============== PDF Generation Endpoint ==============

from app.services.fertiirrigation_pdf_service import create_fertiirrigation_pdf_report
from app.routers.fertilizer_prices import build_price_map, load_default_fertilizers, get_user_currency


@router.get("/pdf/{calculation_id}")
async def generate_fertiirrigation_pdf(
    calculation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate a PDF report for a saved fertigation calculation.
    
    Returns the PDF file as a downloadable response.
    """
    calculation = db.query(FertiIrrigationCalculation).filter(
        FertiIrrigationCalculation.id == calculation_id,
        FertiIrrigationCalculation.user_id == current_user.id
    ).first()
    
    if not calculation:
        raise HTTPException(status_code=404, detail="Cálculo no encontrado")
    
    # Build price map from user's configured prices
    catalog_fertilizers = load_default_fertilizers(db)
    price_map = build_price_map(db, current_user.id, catalog_fertilizers)
    user_currency = get_user_currency(db, current_user.id)
    
    result_data = calculation.results or {}
    input_data = calculation.input_data or {}
    crop_input = input_data.get('crop', {})
    
    calc_dict = {
        "id": calculation.id,
        "name": calculation.name,
        "created_at": calculation.created_at,
        "soil_analysis_name": "Análisis de suelo",
        "water_analysis_name": "Agua de riego",
        "crop_name": calculation.crop_name,
        "area_ha": calculation.area_ha,
        "num_applications": result_data.get("num_applications", 10),
        "irrigation_frequency_days": calculation.irrigation_frequency_days,
        "irrigation_volume_m3_ha": calculation.irrigation_volume_m3_ha,
        "result": result_data,
        "price_map": price_map,
        "user_currency": user_currency
    }
    
    extraction_crop_id = crop_input.get('extraction_crop_id')
    extraction_stage_id = crop_input.get('extraction_stage_id')
    
    if extraction_crop_id and extraction_stage_id:
        crops = fertiirrigation_calculator.get_available_crops()
        crop_info = next((c for c in crops if c.get("id") == extraction_crop_id), None)
        stages = fertiirrigation_calculator.get_crop_stages(extraction_crop_id) if crop_info else []
        stage_info = next((s for s in stages if s.get("id") == extraction_stage_id), None)
        curve_percentages = fertiirrigation_calculator.get_extraction_curve(extraction_crop_id, extraction_stage_id)
        
        if crop_info and stage_info:
            calc_dict["extraction_curve_info"] = {
                "crop_id": extraction_crop_id,
                "stage_id": extraction_stage_id,
                "crop_name": crop_info.get("name", extraction_crop_id),
                "stage_name": stage_info.get("name", extraction_stage_id),
                "percentages": curve_percentages,
                "duration_days": stage_info.get("duration_days")
            }
    
    if calculation.soil_analysis_id:
        soil = db.query(MySoilAnalysis).filter(MySoilAnalysis.id == calculation.soil_analysis_id).first()
        if soil:
            calc_dict["soil_analysis_name"] = soil.name
    
    if calculation.water_analysis_id:
        water = db.query(WaterAnalysis).filter(WaterAnalysis.id == calculation.water_analysis_id).first()
        if water:
            calc_dict["water_analysis_name"] = water.name
    
    user_name = current_user.full_name or current_user.email
    
    pdf_bytes = create_fertiirrigation_pdf_report(
        calculation=calc_dict,
        user_name=user_name,
        include_optimization=False
    )
    
    filename = f"fertirriego_{calculation.name.replace(' ', '_')}_{calculation.id}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# ============== Excel Export Endpoint ==============

from app.services.fertiirrigation_excel_service import fertiirrigation_excel_service


@router.get("/excel/{calculation_id}")
async def generate_fertiirrigation_excel(
    calculation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate an Excel report for a saved fertigation calculation.
    
    Returns the Excel file as a downloadable response.
    """
    calculation = db.query(FertiIrrigationCalculation).filter(
        FertiIrrigationCalculation.id == calculation_id,
        FertiIrrigationCalculation.user_id == current_user.id
    ).first()
    
    if not calculation:
        raise HTTPException(status_code=404, detail="Cálculo no encontrado")
    
    result_data = calculation.results or {}
    input_data = calculation.input_data or {}
    crop_input = input_data.get('crop', {})
    
    calc_dict = {
        "id": calculation.id,
        "name": calculation.name,
        "created_at": calculation.created_at,
        "soil_analysis_name": "Análisis de suelo",
        "water_analysis_name": "Agua de riego",
        "crop_name": calculation.crop_name,
        "area_ha": calculation.area_ha,
        "num_applications": result_data.get("num_applications", 10),
        "irrigation_frequency_days": calculation.irrigation_frequency_days,
        "irrigation_volume_m3_ha": calculation.irrigation_volume_m3_ha,
        "result": result_data,
        "fertilizer_program": calculation.fertilizer_program or []
    }
    
    extraction_curve_info = None
    extraction_crop_id = crop_input.get('extraction_crop_id')
    extraction_stage_id = crop_input.get('extraction_stage_id')
    
    if extraction_crop_id and extraction_stage_id:
        crops = fertiirrigation_calculator.get_available_crops()
        crop_info = next((c for c in crops if c.get("id") == extraction_crop_id), None)
        stages = fertiirrigation_calculator.get_crop_stages(extraction_crop_id) if crop_info else []
        stage_info = next((s for s in stages if s.get("id") == extraction_stage_id), None)
        curve_percentages = fertiirrigation_calculator.get_extraction_curve(extraction_crop_id, extraction_stage_id)
        
        if crop_info and stage_info:
            extraction_curve_info = {
                "crop_id": extraction_crop_id,
                "stage_id": extraction_stage_id,
                "crop_name": crop_info.get("name", extraction_crop_id),
                "stage_name": stage_info.get("name", extraction_stage_id),
                "percentages": curve_percentages,
                "duration_days": stage_info.get("duration_days")
            }
    
    if calculation.soil_analysis_id:
        soil = db.query(MySoilAnalysis).filter(MySoilAnalysis.id == calculation.soil_analysis_id).first()
        if soil:
            calc_dict["soil_analysis_name"] = soil.name
    
    if calculation.water_analysis_id:
        water = db.query(WaterAnalysis).filter(WaterAnalysis.id == calculation.water_analysis_id).first()
        if water:
            calc_dict["water_analysis_name"] = water.name
    
    user_name = current_user.full_name or current_user.email
    
    excel_buffer = fertiirrigation_excel_service.generate_fertiirrigation_excel(
        calculation=calc_dict,
        user_name=user_name,
        extraction_curve_info=extraction_curve_info
    )
    
    filename = f"fertirriego_{calculation.name.replace(' ', '_')}_{calculation.id}.xlsx"
    
    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.post("/acid-recommendation")
def get_acid_recommendation(
    bicarbonates_meq: float,
    target_bicarbonates_meq: float = 1.0,
    volume_liters: float = 1000,
    p_deficit: float = 0,
    n_deficit: float = 0,
    s_deficit: float = 0,
    current_user: User = Depends(get_current_active_user)
):
    """
    Calculate acid recommendation for neutralizing bicarbonates in irrigation water.
    
    Args:
        bicarbonates_meq: Current bicarbonate level in meq/L
        target_bicarbonates_meq: Target bicarbonate level (default 1.0 meq/L)
        volume_liters: Volume of water to treat (default 1000L)
        p_deficit: Phosphorus deficit in kg/ha (for acid selection)
        n_deficit: Nitrogen deficit in kg/ha (for acid selection)
        s_deficit: Sulfur deficit in kg/ha (for acid selection)
    """
    from app.services.acid_calculator import calculate_acid_dosage
    
    nutrient_deficit = None
    if p_deficit or n_deficit or s_deficit:
        nutrient_deficit = {"P": p_deficit, "N": n_deficit, "S": s_deficit}
    
    result = calculate_acid_dosage(
        bicarbonates_meq=bicarbonates_meq,
        target_bicarbonates_meq=target_bicarbonates_meq,
        volume_liters=volume_liters,
        nutrient_deficit=nutrient_deficit
    )
    
    return result


@router.get("/acid-fertilizer-compatibility")
def get_acid_fertilizer_compatibility(
    acid_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get fertilizer compatibility rules for acid treatments.
    
    Args:
        acid_type: Optional acid type to filter (phosphoric_acid, nitric_acid, sulfuric_acid)
    
    Returns compatibility rules and warnings.
    """
    from pathlib import Path
    
    data_path = Path(__file__).parent.parent / "data" / "acid_fertilizer_compatibility.json"
    with open(data_path, "r", encoding="utf-8") as f:
        compatibility_data = json.load(f)
    
    if acid_type and acid_type in compatibility_data["compatibility_rules"]:
        return {
            "acid_type": acid_type,
            "rules": compatibility_data["compatibility_rules"][acid_type],
            "safe_combinations": compatibility_data["safe_combinations"].get(acid_type, []),
            "general_warnings": compatibility_data["general_warnings"]
        }
    
    return compatibility_data


class CompatibilityCheckRequest(BaseModel):
    acid_type: str
    fertilizer_slugs: List[str]


@router.post("/check-fertilizer-compatibility")
def check_fertilizer_compatibility(
    request: CompatibilityCheckRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Check if selected fertilizers are compatible with the recommended acid.
    
    Args:
        request.acid_type: The acid type (phosphoric_acid, nitric_acid, sulfuric_acid)
        request.fertilizer_slugs: List of selected fertilizer slugs
    
    Returns list of incompatible fertilizers with warnings.
    """
    from pathlib import Path
    
    acid_type = request.acid_type
    fertilizer_slugs = request.fertilizer_slugs
    
    data_path = Path(__file__).parent.parent / "data" / "acid_fertilizer_compatibility.json"
    with open(data_path, "r", encoding="utf-8") as f:
        compatibility_data = json.load(f)
    
    fert_path = Path(__file__).parent.parent / "data" / "fertilizer_products.json"
    with open(fert_path, "r", encoding="utf-8") as f:
        fertilizer_products = json.load(f)
    
    fert_by_slug = {f["slug"]: f for f in fertilizer_products}
    
    rules = compatibility_data["compatibility_rules"].get(acid_type, {})
    incompatible_categories = set(rules.get("incompatible_categories", []))
    incompatible_slugs = set(rules.get("incompatible_slugs", []))
    
    incompatible_fertilizers = []
    
    for slug in fertilizer_slugs:
        fert = fert_by_slug.get(slug)
        if not fert:
            continue
        
        is_incompatible = False
        reasons = []
        
        if slug in incompatible_slugs:
            is_incompatible = True
            reasons.append("Incompatibilidad directa conocida")
        
        if fert.get("category") in incompatible_categories:
            is_incompatible = True
            reasons.append(f"Categoría incompatible: {fert.get('category')}")
        
        ca_pct = fert.get("ca_pct", 0)
        if ca_pct and ca_pct > 5 and acid_type in ["phosphoric_acid", "sulfuric_acid"]:
            is_incompatible = True
            reasons.append(f"Alto contenido de calcio ({ca_pct}%)")
        
        if is_incompatible:
            incompatible_fertilizers.append({
                "slug": slug,
                "name": fert.get("name", slug),
                "reasons": reasons
            })
    
    return {
        "acid_type": acid_type,
        "has_incompatibilities": len(incompatible_fertilizers) > 0,
        "incompatible_fertilizers": incompatible_fertilizers,
        "mitigation": rules.get("mitigation") if incompatible_fertilizers else None,
        "warning": rules.get("reason") if incompatible_fertilizers else None
    }


from pydantic import BaseModel

class ABTanksRequest(BaseModel):
    fertilizers: List[dict]
    acid_treatment: Optional[dict] = None
    tank_a_volume: float = 1000
    tank_b_volume: float = 1000
    dilution_factor: int = 100
    num_applications: int = 10
    irrigation_flow_lph: float = 1000
    area_ha: float = 1.0


@router.post("/calculate-ab-tanks")
def calculate_ab_tanks(
    request: ABTanksRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Calculate A/B tank separation and concentrations for fertigation.
    
    Separates fertilizers into Tank A (calcium, micronutrients) and 
    Tank B (phosphates, sulfates, magnesium) based on chemical compatibility.
    
    Returns stock solution concentrations and injection program.
    """
    # Check usage limits
    usage_service = UsageLimitService(db)
    can_use = usage_service.check_can_use(current_user, 'irrigation')
    if not can_use['can_use']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=can_use['reason']
        )
    
    from app.services.fertiirrigation_ab_tanks_service import calculate_ab_tanks_complete
    
    try:
        result = calculate_ab_tanks_complete(
            fertilizers=request.fertilizers,
            acid_treatment=request.acid_treatment,
            tank_a_volume=request.tank_a_volume,
            tank_b_volume=request.tank_b_volume,
            dilution_factor=request.dilution_factor,
            num_applications=request.num_applications,
            irrigation_flow_lph=request.irrigation_flow_lph,
            area_ha=request.area_ha
        )
        # Increment usage counter for analytics
        usage_service.increment_usage(current_user, 'irrigation')
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error calculating A/B tanks: {str(e)}"
        )


class AIOptimizeRequest(BaseModel):
    """Request for AI-powered fertilization optimization."""
    deficits: Dict[str, float]
    micro_deficits: Dict[str, float] = {}
    crop_name: str
    growth_stage: str
    irrigation_system: str = "goteo"
    num_applications: int = 1
    currency: str = "MXN"
    selected_fertilizer_slugs: List[str] = []
    is_manual_mode: bool = False
    water_analysis: Optional[Dict[str, Any]] = None
    water_volume_m3_ha: float = 50.0
    area_ha: float = 1.0
    user_acid_prices: Optional[Dict[str, float]] = None
    traceability: Optional[Dict[str, Any]] = None


class AIFertilizerDose(BaseModel):
    id: str
    name: str
    dose_kg_ha: float
    dose_per_application: float
    price_per_kg: float = 0
    subtotal: float = 0
    tank: str = "A"


class AIMicronutrientDose(BaseModel):
    element: str
    fertilizer_name: str
    fertilizer_slug: str
    dose_g_ha: float
    dose_g_per_application: float
    price_per_kg: float = 0
    subtotal: float = 0


class AIProfileResult(BaseModel):
    profile_name: str
    fertilizers: List[AIFertilizerDose]
    macro_fertilizers: List[AIFertilizerDose] = []
    micronutrients: List[AIMicronutrientDose] = []
    total_cost_per_ha: float
    macro_cost_per_ha: float = 0
    micro_cost_per_ha: float = 0
    coverage: Dict[str, float]
    notes: str = ""
    traceability: Optional[Dict[str, Any]] = None


class AIAcidRecommendation(BaseModel):
    acid_id: str
    acid_name: str
    formula: str
    dose_ml_per_1000L: float
    total_volume_L: float
    cost_per_1000L: float
    total_cost: float
    nutrient_contribution: Dict[str, float]
    meq_neutralized: float
    primary_nutrient: str


class AIAcidProgram(BaseModel):
    recommended: bool
    reason: str
    hco3_meq_l: float = 0
    target_neutralization_pct: float = 70
    acids: List[AIAcidRecommendation] = []
    total_neutralization_meq: float = 0
    total_contributions: Dict[str, float] = {}


class AIOptimizeResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    economic: Optional[AIProfileResult] = None
    balanced: Optional[AIProfileResult] = None
    complete: Optional[AIProfileResult] = None
    acid_program: Optional[AIAcidProgram] = None


@router.post("/ai-optimize", response_model=AIOptimizeResponse)
async def ai_optimize_fertigation(
    request: AIOptimizeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Deterministic fertilization optimization.

    Generates 3 fertilization profiles (Economic, Balanced, Complete) based on:
    - Nutrient deficits to cover
    - Available fertilizers from user's catalog
    - Drip irrigation compatibility

    Returns fertilizer recommendations with doses in kg/ha.
    """
    usage_service = UsageLimitService(db)
    can_use = usage_service.check_can_use(current_user, 'irrigation')
    if not can_use['can_use']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=can_use['reason']
        )
    
    from app.services.fertiirrigation_ai_optimizer import (
        optimize_deterministic,
        get_available_fertilizers_for_user
    )
    from app.services.fertiirrigation_optimizer import optimize_manual_deterministic
    
    try:
        available_fertilizers = get_available_fertilizers_for_user(
            db, 
            current_user.id, 
            request.currency
        )
        
        logger.info(f"AI Optimize: Total available fertilizers: {len(available_fertilizers)}")
        logger.info(f"AI Optimize: Selected slugs received: {request.selected_fertilizer_slugs}")
        
        if request.selected_fertilizer_slugs:
            selected_set = set(request.selected_fertilizer_slugs)
            filtered_fertilizers = [
                f for f in available_fertilizers 
                if f.get('id') in selected_set or f.get('slug') in selected_set
            ]
            logger.info(f"AI Optimize: Filtered to {len(filtered_fertilizers)} fertilizers")
        else:
            filtered_fertilizers = available_fertilizers
        
        is_manual = request.is_manual_mode or (len(request.selected_fertilizer_slugs) > 0)
        logger.info(f"AI Optimize: is_manual_mode={is_manual}")
        
        if is_manual:
            # Use deterministic optimizer for manual mode (no GPT-4o)
            result = optimize_manual_deterministic(
                db=db,
                user_id=current_user.id,
                deficits=request.deficits,
                micro_deficits=request.micro_deficits,
                selected_fertilizer_ids=request.selected_fertilizer_slugs,
                num_applications=request.num_applications,
                area_ha=request.area_ha or 1.0,
                currency=request.currency,
                available_fertilizers=filtered_fertilizers
            )
        else:
            agronomic_context = None
            if request.water_analysis:
                agronomic_context = {'water': request.water_analysis}
            
            result = optimize_deterministic(
                deficits=request.deficits,
                micro_deficits=request.micro_deficits,
                available_fertilizers=available_fertilizers,
                crop_name=request.crop_name,
                growth_stage=request.growth_stage,
                irrigation_system=request.irrigation_system,
                num_applications=request.num_applications,
                agronomic_context=agronomic_context,
                water_volume_m3_ha=request.water_volume_m3_ha,
                area_ha=request.area_ha,
                user_acid_prices=request.user_acid_prices,
                traceability_context=request.traceability
            )
        
        if not result.get("success"):
            return AIOptimizeResponse(
                success=False,
                error=result.get("error", "Error desconocido")
            )
        
        profiles = result.get("profiles", {})
        
        def parse_profile(profile_data: dict) -> AIProfileResult:
            all_fertilizers = []
            macro_fertilizers = []
            micronutrients = []
            macro_cost = 0.0
            micro_cost = 0.0
            
            for f in profile_data.get("fertilizers", []):
                fert_id = f.get("id", "")
                fert_name = f.get("name", "")
                dose_kg_ha = f.get("dose_kg_ha", 0)
                dose_per_app = f.get("dose_per_application", 0)
                price_per_kg = f.get("price_per_kg", 0)
                subtotal = f.get("subtotal", 0)
                tank = f.get("tank", "A")
                
                fert_dose = AIFertilizerDose(
                    id=fert_id,
                    name=fert_name,
                    dose_kg_ha=dose_kg_ha,
                    dose_per_application=dose_per_app,
                    price_per_kg=price_per_kg,
                    subtotal=subtotal,
                    tank=tank
                )
                all_fertilizers.append(fert_dose)
                
                if is_micronutrient_fertilizer(fert_id, fert_name):
                    element = get_micronutrient_element(fert_id, fert_name)
                    dose_g_ha = dose_kg_ha * 1000
                    dose_g_per_app = dose_per_app * 1000
                    micronutrients.append(AIMicronutrientDose(
                        element=element,
                        fertilizer_name=fert_name,
                        fertilizer_slug=fert_id,
                        dose_g_ha=round(dose_g_ha, 1),
                        dose_g_per_application=round(dose_g_per_app, 1),
                        price_per_kg=price_per_kg,
                        subtotal=subtotal
                    ))
                    micro_cost += subtotal
                else:
                    macro_fertilizers.append(fert_dose)
                    macro_cost += subtotal
            
            return AIProfileResult(
                profile_name=profile_data.get("profile_name", ""),
                fertilizers=all_fertilizers,
                macro_fertilizers=macro_fertilizers,
                micronutrients=micronutrients,
                total_cost_per_ha=profile_data.get("total_cost_per_ha", 0),
                macro_cost_per_ha=round(macro_cost, 2),
                micro_cost_per_ha=round(micro_cost, 2),
                coverage=profile_data.get("coverage", {}),
                notes=profile_data.get("notes", ""),
                traceability=profile_data.get("traceability")
            )
        
        usage_service.increment_usage(current_user, 'irrigation')
        
        economic_data = profiles.get("economic")
        balanced_data = profiles.get("balanced")
        complete_data = profiles.get("complete")
        
        acid_program_response = None
        acid_rec = result.get("acid_recommendation")
        if acid_rec and acid_rec.get("recommended"):
            acids_list = []
            for acid in acid_rec.get("acids", []):
                acids_list.append(AIAcidRecommendation(
                    acid_id=acid.get("acid_id", ""),
                    acid_name=acid.get("acid_name", ""),
                    formula=acid.get("formula", ""),
                    dose_ml_per_1000L=acid.get("dose_ml_per_1000L", 0),
                    total_volume_L=acid.get("total_volume_L", 0),
                    cost_per_1000L=acid.get("cost_per_1000L", 0),
                    total_cost=acid.get("total_cost", 0),
                    nutrient_contribution=acid.get("nutrient_contribution", {}),
                    meq_neutralized=acid.get("meq_neutralized", 0),
                    primary_nutrient=acid.get("primary_nutrient", "")
                ))
            acid_program_response = AIAcidProgram(
                recommended=True,
                reason=acid_rec.get("reason", ""),
                hco3_meq_l=acid_rec.get("hco3_meq_l", 0),
                target_neutralization_pct=acid_rec.get("target_neutralization_pct", 70),
                acids=acids_list,
                total_neutralization_meq=acid_rec.get("total_neutralization_meq", 0),
                total_contributions=acid_rec.get("total_contributions", {})
            )
        
        return AIOptimizeResponse(
            success=True,
            economic=parse_profile(economic_data) if economic_data else None,
            balanced=parse_profile(balanced_data) if balanced_data else None,
            complete=parse_profile(complete_data) if complete_data else None,
            acid_program=acid_program_response
        )
        
    except Exception as e:
        logger.error(f"Error in AI optimization: {e}")
        return AIOptimizeResponse(
            success=False,
            error=f"Error al optimizar: {str(e)}"
        )

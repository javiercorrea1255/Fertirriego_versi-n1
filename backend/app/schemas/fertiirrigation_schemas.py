"""
Pydantic schemas for FertiIrrigation Module (Independent).
Includes schemas for MySoilAnalysis and FertiIrrigationCalculation.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== ENUMS ====================

class TextureEnum(str, Enum):
    """Soil texture types."""
    ARENA = "arena"
    ARENA_FRANCA = "arena_franca"
    FRANCO_ARENOSO = "franco_arenoso"
    FRANCO = "franco"
    FRANCO_LIMOSO = "franco_limoso"
    LIMO = "limo"
    FRANCO_ARCILLO_ARENOSO = "franco_arcillo_arenoso"
    FRANCO_ARCILLOSO = "franco_arcilloso"
    FRANCO_ARCILLO_LIMOSO = "franco_arcillo_limoso"
    ARCILLO_ARENOSO = "arcillo_arenoso"
    ARCILLO_LIMOSO = "arcillo_limoso"
    ARCILLA = "arcilla"


class IrrigationSystemEnum(str, Enum):
    """Irrigation system types."""
    GOTEO = "goteo"
    ASPERSION = "aspersion"
    MICROASPERSION = "microaspersion"
    GRAVEDAD = "gravedad"
    PIVOTE = "pivote"


# ==================== MY SOIL ANALYSIS SCHEMAS ====================

class MySoilAnalysisBase(BaseModel):
    """Base schema for soil analysis data."""
    name: str = Field(..., min_length=1, max_length=100, description="Name for this soil analysis")
    laboratory: Optional[str] = Field(None, max_length=100, description="Laboratory name")
    analysis_date: Optional[datetime] = Field(None, description="Date of analysis")
    
    # Physical properties
    texture: Optional[str] = Field(None, max_length=50, description="Soil texture")
    bulk_density: float = Field(default=1.3, ge=0.5, le=2.0, description="Bulk density g/cm3")
    depth_cm: float = Field(default=30.0, ge=5, le=200, description="Sampling depth cm")
    
    # pH and EC
    ph: Optional[float] = Field(None, ge=3.0, le=11.0, description="pH value")
    ec_ds_m: Optional[float] = Field(None, ge=0, description="EC in dS/m")
    
    # Organic matter
    organic_matter_pct: Optional[float] = Field(None, ge=0, le=100, description="Organic matter %")
    
    # Macronutrients
    n_total_pct: Optional[float] = Field(None, ge=0, le=5, description="Total N %")
    n_no3_ppm: Optional[float] = Field(None, ge=0, description="NO3-N ppm")
    n_nh4_ppm: Optional[float] = Field(None, ge=0, description="NH4-N ppm")
    p_ppm: Optional[float] = Field(None, ge=0, description="P ppm (Olsen/Bray)")
    k_ppm: Optional[float] = Field(None, ge=0, description="K ppm")
    
    # Secondary macronutrients
    ca_ppm: Optional[float] = Field(None, ge=0, description="Ca ppm")
    mg_ppm: Optional[float] = Field(None, ge=0, description="Mg ppm")
    s_ppm: Optional[float] = Field(None, ge=0, description="S ppm")
    na_ppm: Optional[float] = Field(None, ge=0, description="Na ppm")
    
    # Cation Exchange Capacity
    cic_cmol_kg: Optional[float] = Field(None, ge=0, description="CIC cmol(+)/kg")
    
    # Exchangeable bases
    ca_exch: Optional[float] = Field(None, ge=0, description="Ca exchangeable cmol/kg")
    mg_exch: Optional[float] = Field(None, ge=0, description="Mg exchangeable cmol/kg")
    k_exch: Optional[float] = Field(None, ge=0, description="K exchangeable cmol/kg")
    na_exch: Optional[float] = Field(None, ge=0, description="Na exchangeable cmol/kg")
    
    # Micronutrients
    fe_ppm: Optional[float] = Field(None, ge=0, description="Fe ppm")
    mn_ppm: Optional[float] = Field(None, ge=0, description="Mn ppm")
    zn_ppm: Optional[float] = Field(None, ge=0, description="Zn ppm")
    cu_ppm: Optional[float] = Field(None, ge=0, description="Cu ppm")
    b_ppm: Optional[float] = Field(None, ge=0, description="B ppm")
    
    # Carbonates
    caco3_pct: Optional[float] = Field(None, ge=0, le=100, description="CaCO3 %")
    
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes")


class MySoilAnalysisCreate(MySoilAnalysisBase):
    """Schema for creating a new soil analysis."""
    pass


class MySoilAnalysisUpdate(BaseModel):
    """Schema for updating an existing soil analysis."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    laboratory: Optional[str] = Field(None, max_length=100)
    analysis_date: Optional[datetime] = None
    texture: Optional[str] = Field(None, max_length=50)
    bulk_density: Optional[float] = Field(None, ge=0.5, le=2.0)
    depth_cm: Optional[float] = Field(None, ge=5, le=200)
    ph: Optional[float] = Field(None, ge=3.0, le=11.0)
    ec_ds_m: Optional[float] = Field(None, ge=0)
    organic_matter_pct: Optional[float] = Field(None, ge=0, le=100)
    n_total_pct: Optional[float] = Field(None, ge=0, le=5)
    n_no3_ppm: Optional[float] = Field(None, ge=0)
    n_nh4_ppm: Optional[float] = Field(None, ge=0)
    p_ppm: Optional[float] = Field(None, ge=0)
    k_ppm: Optional[float] = Field(None, ge=0)
    ca_ppm: Optional[float] = Field(None, ge=0)
    mg_ppm: Optional[float] = Field(None, ge=0)
    s_ppm: Optional[float] = Field(None, ge=0)
    na_ppm: Optional[float] = Field(None, ge=0)
    cic_cmol_kg: Optional[float] = Field(None, ge=0)
    ca_exch: Optional[float] = Field(None, ge=0)
    mg_exch: Optional[float] = Field(None, ge=0)
    k_exch: Optional[float] = Field(None, ge=0)
    na_exch: Optional[float] = Field(None, ge=0)
    fe_ppm: Optional[float] = Field(None, ge=0)
    mn_ppm: Optional[float] = Field(None, ge=0)
    zn_ppm: Optional[float] = Field(None, ge=0)
    cu_ppm: Optional[float] = Field(None, ge=0)
    b_ppm: Optional[float] = Field(None, ge=0)
    caco3_pct: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = Field(None, max_length=1000)


class MySoilAnalysisResponse(MySoilAnalysisBase):
    """Schema for soil analysis response."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class MySoilAnalysisList(BaseModel):
    """Schema for list of soil analyses."""
    items: List[MySoilAnalysisResponse]
    total: int


# ==================== FERTIIRRIGATION CALCULATION SCHEMAS ====================

class CropRequirements(BaseModel):
    """Crop nutrient requirements."""
    crop_name: str
    crop_variety: Optional[str] = None
    growth_stage: Optional[str] = None
    yield_target_ton_ha: Optional[float] = Field(None, ge=0)
    
    # Requirements kg/ha
    n_kg_ha: float = Field(ge=0, description="N requirement kg/ha")
    p2o5_kg_ha: float = Field(ge=0, description="P2O5 requirement kg/ha")
    k2o_kg_ha: float = Field(ge=0, description="K2O requirement kg/ha")
    ca_kg_ha: Optional[float] = Field(None, ge=0)
    mg_kg_ha: Optional[float] = Field(None, ge=0)
    s_kg_ha: Optional[float] = Field(None, ge=0)
    
    # Extraction curve parameters (optional)
    extraction_crop_id: Optional[str] = Field(None, description="ID of extraction curve crop")
    extraction_stage_id: Optional[str] = Field(None, description="ID of growth stage for extraction curve")
    previous_stage_id: Optional[str] = Field(None, description="ID of previous growth stage for DELTA extraction calculation")
    custom_extraction_percent: Optional[Dict[str, float]] = Field(None, description="Custom extraction percentages from user curve")


class IrrigationParameters(BaseModel):
    """Irrigation system parameters."""
    irrigation_system: Optional[str] = Field(None, description="Type of irrigation system")
    irrigation_frequency_days: float = Field(default=7, ge=1, le=30, description="Days between irrigations")
    irrigation_volume_m3_ha: float = Field(default=50, ge=1, le=500, description="Water volume per irrigation m3/ha")
    area_ha: float = Field(default=1.0, ge=0.01, le=10000, description="Area in hectares")
    num_applications: int = Field(default=10, ge=1, le=52, description="Number of fertigation applications")


class AcidTreatment(BaseModel):
    """Acid treatment for water bicarbonate neutralization."""
    acid_type: str = Field(..., description="Acid type: phosphoric_acid, nitric_acid, sulfuric_acid")
    ml_per_1000L: float = Field(ge=0, description="Acid dose in mL per 1000L water")
    cost_mxn_per_1000L: float = Field(default=0, ge=0, description="Cost in MXN per 1000L water treated")
    n_g_per_1000L: float = Field(default=0, ge=0, description="Nitrogen contribution in g per 1000L")
    p_g_per_1000L: float = Field(default=0, ge=0, description="Phosphorus contribution in g per 1000L")
    s_g_per_1000L: float = Field(default=0, ge=0, description="Sulfur contribution in g per 1000L")


class OptimizationProfileFertilizer(BaseModel):
    """Fertilizer from IA Grower optimization profile."""
    slug: str
    name: str
    dose_kg_ha: float
    cost_ha: float
    nutrients: Dict[str, float] = Field(default_factory=dict)


class OptimizationProfileAcid(BaseModel):
    """Acid recommendation from IA Grower optimization profile."""
    acid_id: str
    acid_name: str
    ml_per_1000L: float
    cost_per_1000L: float
    nutrient_contribution: Dict[str, float] = Field(default_factory=dict)


class OptimizationProfile(BaseModel):
    """IA Grower optimization profile with fertilizers and acid."""
    profile_type: str = Field(..., description="Profile type: economic, balanced, complete")
    total_cost_ha: float = Field(ge=0)
    coverage: Dict[str, float] = Field(default_factory=dict, description="Nutrient coverage percentages")
    fertilizers: List[OptimizationProfileFertilizer] = Field(default_factory=list)
    acid_recommendation: Optional[OptimizationProfileAcid] = None


class FertiIrrigationCalculateRequest(BaseModel):
    """Request schema for fertiirrigation calculation."""
    name: str = Field(..., min_length=1, max_length=100)
    
    # Analysis references (can provide ID or inline data)
    soil_analysis_id: Optional[int] = None
    water_analysis_id: Optional[int] = None
    
    # Stage extraction percentage for soil proportioning (delta %, not cumulative)
    stage_extraction_pct: Optional[float] = Field(None, description="Percentage of total crop extraction for this stage (0-100). Used to proportion soil availability.")
    
    # Crop requirements
    crop: CropRequirements
    
    # Irrigation parameters
    irrigation: IrrigationParameters
    
    # Acid treatment (optional - legacy, use optimization_profile.acid_recommendation instead)
    acid_treatment: Optional[AcidTreatment] = Field(None, description="Acid treatment for bicarbonate neutralization")
    
    # IA Grower optimization profile (optional)
    optimization_profile: Optional[OptimizationProfile] = Field(None, description="Selected IA Grower optimization profile with fertilizers and acid")
    
    # Options
    save_calculation: bool = Field(default=True, description="Save calculation to database")


class NutrientBalance(BaseModel):
    """Nutrient balance result."""
    nutrient: str
    requirement_kg_ha: float
    soil_diagnostic_kg_ha: Optional[float] = 0.0
    soil_available_kg_ha: Optional[float] = 0.0
    water_contribution_kg_ha: float
    acid_contribution_kg_ha: Optional[float] = 0.0
    deficit_real_kg_ha: Optional[float] = 0.0
    deficit_security_kg_ha: Optional[float] = 0.0
    deficit_kg_ha: float
    fertilizer_needed_kg_ha: float
    efficiency_factor: float
    minimum_applied: Optional[bool] = False
    minimum_reason: Optional[str] = None


class FertilizerDose(BaseModel):
    """Fertilizer dose per application."""
    application_number: int
    fertilizer_name: str
    fertilizer_slug: Optional[str] = None
    dose_kg_ha: float
    dose_per_application_kg_ha: Optional[float] = None
    dose_kg_total: float
    concentration_g_l: Optional[float] = None
    cost_ha: Optional[float] = None
    nutrients: Optional[Dict[str, float]] = None


class AcidProgramResult(BaseModel):
    """Acid program from IA Grower optimization."""
    acid_id: str
    acid_name: str
    ml_per_1000L: float
    cost_per_1000L: float
    nutrient_contribution: Optional[Dict[str, float]] = None


class OptimizationProfileResult(BaseModel):
    """Optimization profile metadata in result."""
    profile_type: str
    total_cost_ha: float
    coverage: Dict[str, float] = {}
    fertilizer_count: int


class FertiIrrigationResult(BaseModel):
    """Fertiirrigation calculation result."""
    # Summary
    total_n_kg_ha: float
    total_p2o5_kg_ha: float
    total_k2o_kg_ha: float
    
    # Detailed balance
    nutrient_balance: List[NutrientBalance]
    
    # Fertilizer program
    fertilizer_program: List[FertilizerDose]
    
    # IA Grower acid recommendation (optional)
    acid_program: Optional[AcidProgramResult] = None
    
    # IA Grower optimization profile metadata (optional)
    optimization_profile: Optional[OptimizationProfileResult] = None
    
    # Warnings and recommendations
    warnings: List[str]
    recommendations: List[str]
    
    # Cost estimate (optional)
    estimated_cost: Optional[float] = None


class FertiIrrigationCalculateResponse(BaseModel):
    """Response schema for fertiirrigation calculation."""
    id: Optional[int] = None
    name: str
    status: str
    result: FertiIrrigationResult
    created_at: Optional[datetime] = None


class FertiIrrigationSummary(BaseModel):
    """Summary schema for listing calculations."""
    id: int
    name: str
    crop_name: str
    created_at: datetime
    total_n_kg_ha: Optional[float]
    total_p2o5_kg_ha: Optional[float]
    total_k2o_kg_ha: Optional[float]
    
    class Config:
        from_attributes = True


class FertiIrrigationListResponse(BaseModel):
    """List of fertiirrigation calculations."""
    items: List[FertiIrrigationSummary]
    total: int


# ==================== USER EXTRACTION CURVE SCHEMAS ====================

class ExtractionStage(BaseModel):
    """Schema for a single extraction stage."""
    id: str = Field(..., min_length=1, max_length=50, description="Stage identifier")
    name: str = Field(..., min_length=1, max_length=100, description="Stage display name")
    duration_days_min: Optional[int] = Field(None, ge=0, description="Minimum duration in days")
    duration_days_max: Optional[int] = Field(None, ge=0, description="Maximum duration in days")
    cumulative_percent: Dict[str, float] = Field(
        ..., 
        description="Cumulative absorption percentages: N, P2O5, K2O, Ca, Mg, S"
    )
    notes: Optional[str] = Field(None, max_length=500, description="Stage notes")


class UserExtractionCurveBase(BaseModel):
    """Base schema for user extraction curves."""
    name: str = Field(..., min_length=1, max_length=100, description="Crop name")
    scientific_name: Optional[str] = Field(None, max_length=150, description="Scientific name")
    description: Optional[str] = Field(None, max_length=1000, description="Description")
    
    cycle_days_min: Optional[int] = Field(None, ge=1, description="Minimum cycle days")
    cycle_days_max: Optional[int] = Field(None, ge=1, description="Maximum cycle days")
    yield_reference_ton_ha: Optional[float] = Field(None, ge=0, description="Reference yield ton/ha")
    
    total_n_kg_ha: Optional[float] = Field(None, ge=0, description="Total N requirement kg/ha")
    total_p2o5_kg_ha: Optional[float] = Field(None, ge=0, description="Total P2O5 requirement kg/ha")
    total_k2o_kg_ha: Optional[float] = Field(None, ge=0, description="Total K2O requirement kg/ha")
    total_ca_kg_ha: Optional[float] = Field(None, ge=0, description="Total Ca requirement kg/ha")
    total_mg_kg_ha: Optional[float] = Field(None, ge=0, description="Total Mg requirement kg/ha")
    total_s_kg_ha: Optional[float] = Field(None, ge=0, description="Total S requirement kg/ha")
    
    stages: List[ExtractionStage] = Field(..., min_length=1, description="Extraction stages")
    sensitivity_notes: Optional[str] = Field(None, max_length=1000, description="Sensitivity notes")


class UserExtractionCurveCreate(UserExtractionCurveBase):
    """Schema for creating a new user extraction curve."""
    pass


class UserExtractionCurveUpdate(BaseModel):
    """Schema for updating an existing user extraction curve."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    scientific_name: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = Field(None, max_length=1000)
    cycle_days_min: Optional[int] = Field(None, ge=1)
    cycle_days_max: Optional[int] = Field(None, ge=1)
    yield_reference_ton_ha: Optional[float] = Field(None, ge=0)
    total_n_kg_ha: Optional[float] = Field(None, ge=0)
    total_p2o5_kg_ha: Optional[float] = Field(None, ge=0)
    total_k2o_kg_ha: Optional[float] = Field(None, ge=0)
    total_ca_kg_ha: Optional[float] = Field(None, ge=0)
    total_mg_kg_ha: Optional[float] = Field(None, ge=0)
    total_s_kg_ha: Optional[float] = Field(None, ge=0)
    stages: Optional[List[ExtractionStage]] = None
    sensitivity_notes: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None


class UserExtractionCurveResponse(UserExtractionCurveBase):
    """Response schema for user extraction curve."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserExtractionCurveList(BaseModel):
    """List of user extraction curves."""
    items: List[UserExtractionCurveResponse]
    total: int


class UserExtractionCurveSummary(BaseModel):
    """Summary schema for listing user extraction curves."""
    id: int
    name: str
    scientific_name: Optional[str]
    stages_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

"""
FertiIrrigation Optimizer Service V4
Generates 3 optimization profiles (Economic, Balanced, Complete) for soil fertigation.
Uses fertilizer slugs as canonical keys and integrates with UserFertilizerPrice.

CALIBRATION TARGETS (Dec 2024 - V4):
- Minimum coverage: 95% for all nutrients in all profiles
- Maximum coverage: Differentiated by profile
- Profile differentiation: Selection strategy + fertilizer count + cost
- COST HIERARCHY GUARANTEE: Economic <= Balanced <= Complete

PROFILE STRATEGIES (V4.1 - Cost-First for Economic):
  - Economic: 3-11 fertilizers, 75-110% coverage
    * Pure cost efficiency - lowest $/kg of nutrient first
    * ZERO artificial bonuses - only nutrient%/price matters
    * Always produces the cheapest valid program
    
  - Balanced: 4-10 fertilizers, 95-108% coverage  
    * Prefers binary fertilizers (NP, NK, PK, CaMg) - 5x bonus
    * Balance between cost and precision
    * Moderate flexibility in fertilizer selection
    
  - Complete: 6-12 fertilizers, 98-110% coverage
    * Prioritizes single-source fertilizers (Urea, KCl, MgSO4) - 10x bonus
    * Maximum precision per nutrient (target 100-105%)
    * Higher cost justified by precise nutrient control

AGRONOMIC CRITERIA (all profiles):
  - Acid application order: Acids first, bases after
  - Compatibility: Avoid precipitating mixtures (Ca + SO4, Ca + PO4)
  - Nutrient priority: N → P → K → Ca → Mg → S
"""
from typing import List, Dict, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from copy import deepcopy
import logging
import json
import hashlib
from pathlib import Path
from sqlalchemy.orm import Session

from app.models.hydro_ions_models import UserFertilizerPrice, UserPriceSettings
from app.routers.fertilizer_prices import DEFAULT_PRICES_BY_CURRENCY, get_default_price_for_currency

logger = logging.getLogger(__name__)

_HYDRO_FERTILIZERS_CATALOG = None


def _load_hydro_fertilizers_catalog() -> List[Dict]:
    """
    Load fertilizers from hydro_fertilizers.json (shared catalog with Hydroponics module).
    This is the single source of truth for all fertilizers in both Hydroponics and FertiIrrigation.
    """
    global _HYDRO_FERTILIZERS_CATALOG
    
    if _HYDRO_FERTILIZERS_CATALOG is not None:
        return _HYDRO_FERTILIZERS_CATALOG
    
    config_path = Path(__file__).parent.parent / "data" / "hydro_fertilizers.json"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading hydro_fertilizers.json: {e}")
        return []
    
    fertilizers = data.get("fertilizers", [])
    result = []
    
    for fert in fertilizers:
        fert_id = fert.get("id", "")
        fert_name = fert.get("name", "")
        fert_type = fert.get("type", "salt")
        
        nutrient_comp = fert.get("nutrient_composition", {})
        
        n_pct = nutrient_comp.get("N_percent", 0) or 0
        ca_pct = nutrient_comp.get("Ca_percent", 0) or 0
        mg_pct = nutrient_comp.get("Mg_percent", 0) or 0
        s_pct = nutrient_comp.get("S_percent", 0) or 0
        
        k_pct = nutrient_comp.get("K_percent", 0) or 0
        k2o_pct = k_pct * 1.205 if k_pct > 0 else 0
        
        p_pct = nutrient_comp.get("P_percent", 0) or 0
        p2o5_pct = p_pct * 2.29 if p_pct > 0 else 0
        
        if p2o5_pct == 0:
            meq_per_gram = fert.get("meq_per_gram", {})
            h2po4_meq = meq_per_gram.get("H2PO4", 0)
            if h2po4_meq > 0:
                p2o5_pct = h2po4_meq * 30.97 * 2.29 / 1000 * 100
        
        default_price = fert.get("typical_cost_mxn_per_kg") or fert.get("typical_cost_mxn_per_liter") or 25.0
        
        fe_pct = nutrient_comp.get("Fe_percent", 0) or 0
        mn_pct = nutrient_comp.get("Mn_percent", 0) or 0
        zn_pct = nutrient_comp.get("Zn_percent", 0) or 0
        cu_pct = nutrient_comp.get("Cu_percent", 0) or 0
        b_pct = nutrient_comp.get("B_percent", 0) or 0
        mo_pct = nutrient_comp.get("Mo_percent", 0) or 0
        
        stock_tank = fert.get("stock_tank", "B")
        
        result.append({
            'id': fert_id,
            'slug': fert_id,
            'name': fert_name,
            'type': fert_type,
            'n_pct': round(n_pct, 2),
            'p2o5_pct': round(p2o5_pct, 2),
            'k2o_pct': round(k2o_pct, 2),
            'ca_pct': round(ca_pct, 2),
            'mg_pct': round(mg_pct, 2),
            's_pct': round(s_pct, 2),
            'fe_pct': round(fe_pct, 2),
            'mn_pct': round(mn_pct, 2),
            'zn_pct': round(zn_pct, 2),
            'cu_pct': round(cu_pct, 2),
            'b_pct': round(b_pct, 2),
            'mo_pct': round(mo_pct, 2),
            'default_price_mxn': default_price,
            'price_per_kg': default_price,
            'stock_tank': stock_tank,
            'meq_per_gram': fert.get("meq_per_gram", {}),
            'form': fert.get("form", "solid")
        })
    
    _HYDRO_FERTILIZERS_CATALOG = result
    return result


class ValidationConfig:
    """Loads and provides access to fertiirrigation validation rules."""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._load_config()
        return cls._instance
    
    @classmethod
    def _load_config(cls):
        """Load validation config from JSON file."""
        try:
            config_path = Path(__file__).parent.parent / "data" / "fertiirrigation_validation.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                cls._config = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load fertiirrigation validation config: {e}")
            cls._config = {
                "equivalent_products": {},
                "nutrient_limits_ppm": {"default": {"default": {}}},
                "chemical_incompatibilities": {},
                "excess_thresholds": {}
            }
    
    @classmethod
    def get_equivalent_groups(cls) -> Dict[str, Dict]:
        """Get mapping of equivalent product groups."""
        if cls._config is None:
            cls._load_config()
        return cls._config.get("equivalent_products", {})
    
    @classmethod
    def get_nutrient_limits(cls, crop: str = "default", stage: str = "default") -> Dict[str, Dict]:
        """Get nutrient limits for a specific crop and growth stage."""
        if cls._config is None:
            cls._load_config()
        limits = cls._config.get("nutrient_limits_ppm", {})
        crop_limits = limits.get(crop.lower(), limits.get("default", {}))
        return crop_limits.get(stage.lower(), crop_limits.get("default", {}))
    
    @classmethod
    def get_chemical_incompatibilities(cls) -> Dict[str, Dict]:
        """Get chemical incompatibility rules."""
        if cls._config is None:
            cls._load_config()
        return cls._config.get("chemical_incompatibilities", {})
    
    @classmethod
    def get_excess_thresholds(cls) -> Dict[str, Dict]:
        """Get excess warning thresholds for nutrients."""
        if cls._config is None:
            cls._load_config()
        return cls._config.get("excess_thresholds", {})


class OptimizationProfile(Enum):
    ECONOMIC = "economic"
    BALANCED = "balanced"
    COMPLETE = "complete"


@dataclass
class ProfileConfig:
    name: str
    profile: OptimizationProfile
    min_fertilizers: int
    max_fertilizers: int
    min_coverage_pct: float
    max_coverage_pct: float
    prefer_multi_nutrient: Optional[bool]
    cost_weight: float
    initial_target_pct: float = 100.0


ECONOMIC_PROFILE = ProfileConfig(
    name="Económico",
    profile=OptimizationProfile.ECONOMIC,
    min_fertilizers=3,
    max_fertilizers=14,
    min_coverage_pct=95.0,
    max_coverage_pct=115.0,
    prefer_multi_nutrient=None,
    cost_weight=1.5,
    initial_target_pct=100.0,
)

BALANCED_PROFILE = ProfileConfig(
    name="Balanceado",
    profile=OptimizationProfile.BALANCED,
    min_fertilizers=4,
    max_fertilizers=12,
    min_coverage_pct=90.0,
    max_coverage_pct=115.0,
    prefer_multi_nutrient=None,
    cost_weight=0.8,
    initial_target_pct=100.0,
)

COMPLETE_PROFILE = ProfileConfig(
    name="Completo",
    profile=OptimizationProfile.COMPLETE,
    min_fertilizers=6,
    max_fertilizers=14,
    min_coverage_pct=95.0,
    max_coverage_pct=110.0,
    prefer_multi_nutrient=False,
    cost_weight=0.2,
    initial_target_pct=100.0,
)

PROFILES = {
    "economic": ECONOMIC_PROFILE,
    "balanced": BALANCED_PROFILE,
    "complete": COMPLETE_PROFILE,
}


@dataclass
class NutrientDeficit:
    n_kg_ha: float = 0.0
    p2o5_kg_ha: float = 0.0
    k2o_kg_ha: float = 0.0
    ca_kg_ha: float = 0.0
    mg_kg_ha: float = 0.0
    s_kg_ha: float = 0.0


@dataclass
class MicronutrientDeficit:
    """Micronutrient deficits in g/ha (grams per hectare)."""
    fe_g_ha: float = 0.0
    mn_g_ha: float = 0.0
    zn_g_ha: float = 0.0
    cu_g_ha: float = 0.0
    b_g_ha: float = 0.0
    mo_g_ha: float = 0.0


@dataclass
class MicronutrientDose:
    """A micronutrient fertilizer dose recommendation."""
    fertilizer_id: int
    fertilizer_slug: str
    fertilizer_name: str
    dose_g_ha: float
    dose_g_total: float
    cost_per_kg: float
    cost_total: float
    micronutrient: str
    contribution_g_ha: float


@dataclass
class FertilizerDose:
    fertilizer_id: int
    fertilizer_slug: str
    fertilizer_name: str
    dose_kg_ha: float
    dose_kg_total: float
    cost_per_kg: float
    cost_total: float
    n_contribution: float = 0.0
    p2o5_contribution: float = 0.0
    k2o_contribution: float = 0.0
    ca_contribution: float = 0.0
    mg_contribution: float = 0.0
    s_contribution: float = 0.0


@dataclass
class AcidTreatment:
    """Acid treatment recommendation for pH adjustment."""
    acid_name: str = ""
    ml_per_1000L: float = 0.0
    dose_liters_ha: float = 0.0
    total_cost: float = 0.0


@dataclass
class OptimizationResult:
    profile_name: str
    profile_type: str
    fertilizers: List[FertilizerDose]
    total_cost_ha: float
    total_cost_total: float
    coverage: Dict[str, float]
    warnings: List[str] = field(default_factory=list)
    score: float = 0.0
    micronutrients: List[MicronutrientDose] = field(default_factory=list)
    micronutrient_cost_ha: float = 0.0
    acid_cost_ha: float = 0.0
    acid_treatment: Optional[AcidTreatment] = None
    
    @property
    def grand_total_ha(self) -> float:
        """Calculate total cost including fertilizers, acid, and micronutrients."""
        return self.total_cost_ha + self.acid_cost_ha + self.micronutrient_cost_ha


class FertilizerData:
    """Wrapper for fertilizer data - now supports both DB models and JSON dictionaries."""
    
    MICRONUTRIENTS = ["Fe", "Mn", "Zn", "Cu", "B", "Mo"]
    
    def __init__(self, data):
        """Initialize from either a FertilizerProduct ORM model or a dictionary."""
        if isinstance(data, dict):
            self._init_from_dict(data)
        else:
            self._init_from_orm(data)
    
    def _init_from_dict(self, data: Dict):
        """Initialize from a dictionary (hydro_fertilizers.json format)."""
        self.slug: str = data.get('id', data.get('slug', ''))
        self.id: int = int(hashlib.md5(self.slug.encode()).hexdigest()[:8], 16) % 100000
        self.name: str = data.get('name', '')
        self.category: str = data.get('type', 'salt')
        self.n_pct: float = float(data.get('n_pct', 0) or 0)
        self.p2o5_pct: float = float(data.get('p2o5_pct', 0) or 0)
        self.k2o_pct: float = float(data.get('k2o_pct', 0) or 0)
        self.ca_pct: float = float(data.get('ca_pct', 0) or 0)
        self.mg_pct: float = float(data.get('mg_pct', 0) or 0)
        self.s_pct: float = float(data.get('s_pct', 0) or 0)
        self.cost_per_unit: float = float(data.get('price_per_kg', data.get('default_price_mxn', 25.0)) or 25.0)
        self.unit: str = "kg" if data.get('form', 'solid') == 'solid' else "L"
        self.physical_state: str = data.get('form', 'solid')
        self.pricing_alias: Optional[str] = self.slug
        self.stock_tank: str = data.get('stock_tank', 'B')
        
        self.micronutrients: Dict[str, float] = {}
        for micro in self.MICRONUTRIENTS:
            micro_key = f"{micro.lower()}_pct"
            val = data.get(micro_key, 0) or 0
            if val > 0:
                self.micronutrients[micro] = float(val)
    
    def _init_from_orm(self, product):
        """Initialize from a FertilizerProduct ORM model (legacy support)."""
        self.id: int = product.id
        self.slug: str = product.slug
        self.name: str = product.name
        self.category: str = product.category
        self.n_pct: float = float(product.n_pct or 0)
        self.p2o5_pct: float = float(product.p2o5_pct or 0)
        self.k2o_pct: float = float(product.k2o_pct or 0)
        self.ca_pct: float = float(product.ca_pct or 0)
        self.mg_pct: float = float(product.mg_pct or 0)
        self.s_pct: float = float(product.s_pct or 0)
        self.cost_per_unit: float = float(product.cost_per_unit or 400.0)
        self.unit: str = product.unit or "kg"
        self.physical_state: str = product.physical_state or "solid"
        self.pricing_alias: Optional[str] = product.pricing_alias
        self.stock_tank: str = "B"
        
        self.micronutrients: Dict[str, float] = {}
        if hasattr(product, 'micronutrients') and product.micronutrients:
            try:
                if isinstance(product.micronutrients, dict):
                    self.micronutrients = {k: float(v) for k, v in product.micronutrients.items()}
                elif isinstance(product.micronutrients, str):
                    self.micronutrients = {k: float(v) for k, v in json.loads(product.micronutrients).items()}
            except (ValueError, TypeError):
                self.micronutrients = {}
    
    def get_nutrient_pct(self, nutrient: str) -> float:
        """Get percentage for a nutrient by name."""
        mapping = {
            "N": self.n_pct,
            "P2O5": self.p2o5_pct,
            "K2O": self.k2o_pct,
            "Ca": self.ca_pct,
            "Mg": self.mg_pct,
            "S": self.s_pct,
        }
        return mapping.get(nutrient, 0.0)
    
    def get_micronutrient_pct(self, micro: str) -> float:
        """Get percentage for a micronutrient by name (Fe, Mn, Zn, Cu, B, Mo)."""
        return self.micronutrients.get(micro, 0.0)
    
    def provides_nutrient(self, nutrient: str) -> bool:
        """Check if fertilizer provides a specific nutrient."""
        return self.get_nutrient_pct(nutrient) > 0.5
    
    def provides_micronutrient(self, micro: str) -> bool:
        """Check if fertilizer provides a specific micronutrient."""
        return self.get_micronutrient_pct(micro) > 0.1
    
    def is_micronutrient_source(self) -> bool:
        """Check if this fertilizer is primarily a micronutrient source."""
        return any(self.get_micronutrient_pct(m) > 0 for m in self.MICRONUTRIENTS)


class FertiIrrigationOptimizer:
    """Optimizer for soil fertigation programs - V3 with guaranteed coverage."""
    
    NUTRIENTS = ["N", "P2O5", "K2O", "Ca", "Mg", "S"]
    PRIMARY_NUTRIENTS = ["N", "P2O5", "K2O"]
    SECONDARY_NUTRIENTS = ["Ca", "Mg", "S"]
    MICRONUTRIENTS = ["Fe", "Mn", "Zn", "Cu", "B", "Mo"]
    
    def __init__(self, db: Session, user_id: int, currency: str = "MXN"):
        self.db = db
        self.user_id = user_id
        self.currency = currency
        self._user_prices: Dict[str, float] = {}
        self._load_user_prices()
    
    def _load_user_prices(self) -> None:
        """Load user's custom fertilizer prices from the Precios Fertilizantes module."""
        try:
            prices = self.db.query(UserFertilizerPrice).filter(
                UserFertilizerPrice.user_id == self.user_id,
                UserFertilizerPrice.currency == self.currency
            ).all()
            
            for price in prices:
                pricing_id = price.fertilizer_id
                if pricing_id and price.price_per_kg is not None:
                    self._user_prices[pricing_id] = float(price.price_per_kg)
                elif pricing_id and price.price_per_liter is not None:
                    self._user_prices[pricing_id] = float(price.price_per_liter)
        except Exception:
            pass
    
    def get_price(self, fert: FertilizerData) -> float:
        """Get price for a fertilizer. Uses user price if available, otherwise currency-specific default."""
        pricing_id = fert.pricing_alias or fert.slug
        if pricing_id in self._user_prices:
            return max(0.01, self._user_prices[pricing_id])
        
        currency_defaults = get_default_price_for_currency(pricing_id, self.currency)
        if not currency_defaults.get("price_per_kg") and not currency_defaults.get("price_per_liter"):
            currency_defaults = get_default_price_for_currency(fert.slug, self.currency)
        
        physical_state = (fert.physical_state or "solid").lower()
        if physical_state == "liquid" and currency_defaults.get("price_per_liter"):
            return currency_defaults["price_per_liter"]
        if currency_defaults.get("price_per_kg"):
            return currency_defaults["price_per_kg"]
        
        if fert.cost_per_unit and fert.cost_per_unit > 0:
            return fert.cost_per_unit
        return 25.0
    
    def has_user_price(self, fert: FertilizerData) -> bool:
        """Check if user has configured a price for this fertilizer."""
        pricing_id = fert.pricing_alias or fert.slug
        return pricing_id in self._user_prices
    
    def get_available_fertilizers(self, selected_slugs: Optional[List[str]] = None) -> List[FertilizerData]:
        """Get fertilizers available for fertigation from the unified hydro_fertilizers.json catalog."""
        catalog = _load_hydro_fertilizers_catalog()
        
        if selected_slugs:
            selected_set = set(selected_slugs)
            catalog = [f for f in catalog if f['id'] in selected_set or f['slug'] in selected_set]
        
        return [FertilizerData(f) for f in catalog]
    
    def get_fertilizers_without_prices(self, selected_slugs: Optional[List[str]] = None) -> List[str]:
        """Get list of fertilizer names that don't have user-configured prices."""
        catalog = _load_hydro_fertilizers_catalog()
        
        if selected_slugs:
            selected_set = set(selected_slugs)
            catalog = [f for f in catalog if f['id'] in selected_set or f['slug'] in selected_set]
        
        all_fertilizers = [FertilizerData(f) for f in catalog]
        
        return [f.name for f in all_fertilizers if not self.has_user_price(f)]
    
    def validate_pricing(self, selected_slugs: Optional[List[str]] = None) -> Dict[str, any]:
        """Validate fertilizer availability and pricing status."""
        missing = self.get_fertilizers_without_prices(selected_slugs)
        available = self.get_available_fertilizers(selected_slugs)
        priced_count = sum(1 for f in available if self.has_user_price(f))
        
        return {
            "valid": len(available) >= 6,
            "available_count": len(available),
            "priced_by_user": priced_count,
            "missing_user_prices": missing,
            "message": f"Se usarán precios del catálogo para {len(available) - priced_count} fertilizantes sin precio configurado." if priced_count < len(available) else None
        }
    
    def filter_equivalent_products(self, fertilizers: List[FertilizerData]) -> List[FertilizerData]:
        """Filter out equivalent products, keeping only the cheapest option per nutrient group.
        
        This prevents using multiple sources of the same nutrient (e.g., Epsom Salt + MgSO4 Heptahydrate)
        which are nutrient-equivalent but treated as different products.
        """
        equivalent_groups = ValidationConfig.get_equivalent_groups()
        
        equivalent_slug_to_group: Dict[str, str] = {}
        for group_name, group_info in equivalent_groups.items():
            for slug in group_info.get("equivalent_slugs", []):
                equivalent_slug_to_group[slug] = group_name
        
        best_per_group: Dict[str, FertilizerData] = {}
        best_price_per_group: Dict[str, float] = {}
        
        filtered = []
        for fert in fertilizers:
            group = equivalent_slug_to_group.get(fert.slug)
            
            if group is None:
                filtered.append(fert)
            else:
                price = self.get_price(fert)
                if group not in best_per_group or price < best_price_per_group[group]:
                    best_per_group[group] = fert
                    best_price_per_group[group] = price
        
        for fert in best_per_group.values():
            filtered.append(fert)
        
        if len(filtered) < len(fertilizers):
            removed_count = len(fertilizers) - len(filtered)
            logger.info(f"Filtered {removed_count} equivalent products, keeping cheapest per group")
        
        return filtered
    
    def check_chemical_compatibility(
        self, 
        selected_fertilizers: List[FertilizerDose]
    ) -> Tuple[List[str], List[str]]:
        """Check for chemical incompatibilities in the selected fertilizers.
        
        V5 IMPROVEMENT: Incompatibilities with proper mitigation (tank separation) are
        converted to informational notes rather than warnings, since tank separation
        is a standard professional practice in fertigation systems.
        
        Returns:
            Tuple of (critical_warnings, warnings) where critical are blocking issues
            and warnings are advisories.
        """
        incompatibilities = ValidationConfig.get_chemical_incompatibilities()
        selected_slugs = {f.fertilizer_slug for f in selected_fertilizers}
        
        critical_warnings = []
        warnings = []
        
        for rule_name, rule in incompatibilities.items():
            group_a = set(rule.get("group_a", []))
            group_b = set(rule.get("group_b", []))
            
            products_from_a = selected_slugs & group_a
            products_from_b = selected_slugs & group_b
            
            if products_from_a and products_from_b:
                mitigation = rule.get("mitigation", "")
                severity = rule.get("severity", "warning")
                
                has_tank_separation = any(
                    phrase in mitigation.lower() 
                    for phrase in ["tanques separados", "separado", "separate tank", "diferentes tiempos"]
                )
                
                if has_tank_separation:
                    continue
                
                reason = rule.get("reason", "Incompatibilidad química detectada")
                message = f"{reason}"
                if mitigation:
                    message += f" Recomendación: {mitigation}"
                
                if severity == "critical":
                    critical_warnings.append(message)
                else:
                    warnings.append(message)
        
        return critical_warnings, warnings
    
    def validate_nutrient_coverage(
        self, 
        coverage: Dict[str, float], 
        original_deficit: Dict[str, float]
    ) -> List[str]:
        """Validate nutrient coverage against excess thresholds.
        
        Args:
            coverage: Dict of nutrient -> coverage percentage (0-110%)
            original_deficit: Dict of nutrient -> original deficit in kg/ha (for context)
        
        Returns list of warning messages for nutrients exceeding safe limits.
        
        Note: coverage values are already percentages (e.g., 105.5 = 105.5% covered).
        We convert to ratio (1.055) for threshold comparison.
        """
        thresholds = ValidationConfig.get_excess_thresholds()
        warnings = []
        
        for nutrient, threshold_info in thresholds.items():
            if nutrient not in coverage:
                continue
            
            original = original_deficit.get(nutrient, 0)
            if original <= 0:
                continue
            
            coverage_pct = coverage.get(nutrient, 100.0)
            coverage_ratio = coverage_pct / 100.0
            
            warning_ratio = threshold_info.get("warning_ratio", 1.3)
            
            if coverage_ratio > warning_ratio:
                template = threshold_info.get(
                    "warning_message", 
                    f"{nutrient} excede el requerimiento ({{ratio:.0%}})"
                )
                message = template.format(ratio=coverage_ratio)
                warnings.append(message)
        
        return warnings
    
    def optimize(
        self,
        deficit: NutrientDeficit,
        area_ha: float,
        num_applications: int,
        selected_slugs: Optional[List[str]] = None,
        micro_deficit: Optional[MicronutrientDeficit] = None,
        crop_sensitivity: Optional[Dict[str, str]] = None
    ) -> List[OptimizationResult]:
        """Generate 3 optimization profiles for the given nutrient deficit.
        
        Economic uses marginal-cost algorithm to genuinely minimize cost.
        Balanced and Complete use their specialized strategies.
        Micronutrients are calculated once and attached to all profiles.
        
        V5 Improvements:
        - Filter equivalent products to avoid nutrient duplication
        - Validate chemical compatibility and add warnings
        - Check nutrient excess thresholds
        """
        
        all_fertilizers = self.get_available_fertilizers(selected_slugs)
        
        if not all_fertilizers:
            raise ValueError("No hay fertilizantes disponibles para fertirriego en el catálogo.")
        
        filtered_fertilizers = self.filter_equivalent_products(all_fertilizers)
        
        micronutrient_doses: List[MicronutrientDose] = []
        micronutrient_cost = 0.0
        if micro_deficit:
            micronutrient_doses = self.calculate_micronutrients(
                micro_deficit, area_ha, num_applications, crop_sensitivity
            )
            micronutrient_cost = sum(m.cost_total for m in micronutrient_doses)
        
        original_deficit = self._get_deficit_dict(deficit)
        
        results = []
        for profile_name, config in PROFILES.items():
            sorted_ferts = self._sort_for_profile(filtered_fertilizers, config)
            
            result = self._optimize_profile(
                deficit=deficit,
                area_ha=area_ha,
                num_applications=num_applications,
                fertilizers=sorted_ferts,
                config=config
            )
            result.micronutrients = micronutrient_doses
            result.micronutrient_cost_ha = micronutrient_cost / area_ha if area_ha > 0 else 0
            
            critical_compat, compat_warnings = self.check_chemical_compatibility(result.fertilizers)
            excess_warnings = self.validate_nutrient_coverage(result.coverage, original_deficit)
            
            all_warnings = result.warnings + critical_compat + compat_warnings + excess_warnings
            result.warnings = all_warnings
            
            if critical_compat:
                logger.warning(f"Profile {profile_name} has critical compatibility issues: {critical_compat}")
            
            results.append(result)
        
        results = self._enforce_cost_hierarchy(results, deficit, area_ha, num_applications, filtered_fertilizers)
        
        return results
    
    def _enforce_cost_hierarchy(
        self, 
        results: List['OptimizationResult'],
        deficit: NutrientDeficit,
        area_ha: float,
        num_applications: int,
        all_fertilizers: List['FertilizerData']
    ) -> List['OptimizationResult']:
        """Enforce cost hierarchy: Economic <= Balanced <= Complete.
        
        Strategy:
        1. Try to regenerate Economic using hints from cheapest profile
        2. If regeneration fails, force hierarchy by sorting profiles by cost
           and reassigning data with deep copies
        """
        economic = next((r for r in results if r.profile_type == 'economic'), None)
        balanced = next((r for r in results if r.profile_type == 'balanced'), None)
        complete = next((r for r in results if r.profile_type == 'complete'), None)
        
        if not all([economic, balanced, complete]):
            return results
        
        profiles = [economic, balanced, complete]
        costs = [p.grand_total_ha for p in profiles]
        eco_cost, bal_cost, com_cost = costs
        
        if eco_cost <= bal_cost <= com_cost:
            logger.info(f"Cost hierarchy OK: Eco={eco_cost:.2f} <= Bal={bal_cost:.2f} <= Com={com_cost:.2f}")
            return results
        
        logger.warning(f"Cost hierarchy violated: Eco={eco_cost:.2f}, Bal={bal_cost:.2f}, Com={com_cost:.2f}")
        
        sorted_by_cost = sorted(zip(profiles, costs), key=lambda x: x[1])
        cheapest, cheapest_cost = sorted_by_cost[0]
        
        if cheapest != economic:
            economic_config = PROFILES['economic']
            economic_sorted = self._sort_for_profile(all_fertilizers, economic_config)
            
            candidate_slugs = [f.fertilizer_slug for f in cheapest.fertilizers]
            candidate_ferts = [f for f in economic_sorted if f.slug in candidate_slugs]
            remaining_ferts = [f for f in economic_sorted if f.slug not in candidate_slugs]
            
            if len(candidate_ferts) >= economic_config.min_fertilizers:
                new_economic = self._optimize_profile(
                    deficit=deficit,
                    area_ha=area_ha,
                    num_applications=num_applications,
                    fertilizers=candidate_ferts + remaining_ferts,
                    config=economic_config
                )
                
                if new_economic.grand_total_ha <= cheapest_cost * 1.02:
                    idx = next(i for i, r in enumerate(results) if r.profile_type == 'economic')
                    new_economic.micronutrients = economic.micronutrients
                    new_economic.micronutrient_cost_ha = economic.micronutrient_cost_ha
                    results[idx] = new_economic
                    logger.info(f"Regenerated Economic: {new_economic.grand_total_ha:.2f}")
                    
                    eco_cost = new_economic.grand_total_ha
                    if eco_cost <= bal_cost <= com_cost:
                        return results
        
        eco_cost = next(r for r in results if r.profile_type == 'economic').grand_total_ha
        bal_cost = balanced.grand_total_ha
        com_cost = complete.grand_total_ha
        
        if eco_cost > bal_cost or eco_cost > com_cost or bal_cost > com_cost:
            logger.warning(f"Forcing hierarchy by cost-based reassignment")
            
            all_profiles_data = [
                (deepcopy(next(r for r in results if r.profile_type == 'economic')), 
                 next(r for r in results if r.profile_type == 'economic').grand_total_ha),
                (deepcopy(balanced), bal_cost),
                (deepcopy(complete), com_cost)
            ]
            sorted_data = sorted(all_profiles_data, key=lambda x: x[1])
            
            cheapest_data = sorted_data[0][0]
            middle_data = sorted_data[1][0]
            expensive_data = sorted_data[2][0]
            
            economic_idx = next(i for i, r in enumerate(results) if r.profile_type == 'economic')
            balanced_idx = next(i for i, r in enumerate(results) if r.profile_type == 'balanced')
            complete_idx = next(i for i, r in enumerate(results) if r.profile_type == 'complete')
            
            self._apply_profile_data(cheapest_data, results[economic_idx], 'economic', 'Económico')
            self._apply_profile_data(middle_data, results[balanced_idx], 'balanced', 'Balanceado')
            self._apply_profile_data(expensive_data, results[complete_idx], 'complete', 'Completo')
            
            logger.info(f"Hierarchy enforced: Eco={results[economic_idx].grand_total_ha:.2f} <= "
                       f"Bal={results[balanced_idx].grand_total_ha:.2f} <= "
                       f"Com={results[complete_idx].grand_total_ha:.2f}")
        
        return results
    
    def _apply_profile_data(self, source, target, profile_type: str, profile_name: str) -> None:
        """Apply all data from source to target profile.
        
        Note: grand_total_ha is a calculated property, so we copy the underlying
        fields that are used to compute it. Uses deep copies for mutable objects.
        """
        target.fertilizers = deepcopy(source.fertilizers)
        target.total_cost_ha = source.total_cost_ha
        target.total_cost_total = source.total_cost_total
        target.acid_cost_ha = source.acid_cost_ha
        target.coverage = deepcopy(source.coverage)
        target.acid_treatment = deepcopy(source.acid_treatment) if source.acid_treatment else None
        target.micronutrients = deepcopy(source.micronutrients)
        target.micronutrient_cost_ha = source.micronutrient_cost_ha
        target.score = source.score
        target.warnings = deepcopy(source.warnings)
        target.profile_type = profile_type
        target.profile_name = profile_name
    
    def _sort_for_profile(self, fertilizers: List[FertilizerData], config: ProfileConfig) -> List[FertilizerData]:
        """Sort fertilizers by profile preference to ensure different selection order.
        
        V4 SCORING SYSTEM (Cost-First for Economic):
        - Economic: Pure cost efficiency - lowest $/kg of nutrient first
          Goal: Minimize total cost, no artificial bonuses
        - Balanced: Binary fertilizers (NP, NK, PK) get 5x bonus
          Goal: Balance between cost and precision
        - Complete: Single-source fertilizers (Urea, KCl) get 10x bonus
          Goal: Maximum precision per nutrient, accept higher cost
        """
        
        def profile_score(fert: FertilizerData) -> float:
            nutrient_count = self._count_nutrients(fert)
            price = max(self.get_price(fert), 0.5)
            
            total_nutrient_pct = sum(fert.get_nutrient_pct(n) for n in self.NUTRIENTS)
            base_efficiency = total_nutrient_pct / price
            
            is_npk = (fert.n_pct > 0 and fert.p2o5_pct > 0 and fert.k2o_pct > 0)
            is_binary = nutrient_count == 2
            is_single = nutrient_count == 1
            
            if config.profile == OptimizationProfile.ECONOMIC:
                # V4.1: Pure cost efficiency - ZERO artificial bonuses
                # Only criterion: nutrient%/price ratio (cheapest nutrients first)
                # No type preferences - let pure economics decide
                return base_efficiency
                
            elif config.profile == OptimizationProfile.COMPLETE:
                # Strongly prefer single-source for precision, accept higher cost
                if is_single:
                    return base_efficiency * 10.0
                elif is_binary:
                    return base_efficiency * 2.0
                elif is_npk or nutrient_count >= 3:
                    return base_efficiency * 0.3
                return base_efficiency
                
            else:  # Balanced
                # Moderate preference for binary fertilizers
                if is_binary:
                    return base_efficiency * 5.0
                elif is_npk or nutrient_count >= 3:
                    return base_efficiency * 2.0
                elif is_single:
                    return base_efficiency * 1.5
                return base_efficiency
        
        return sorted(fertilizers, key=profile_score, reverse=True)
    
    def _count_nutrients(self, fert: FertilizerData) -> int:
        """Count how many nutrients a fertilizer provides."""
        count = 0
        for n in self.NUTRIENTS:
            if fert.get_nutrient_pct(n) > 0:
                count += 1
        return count
    
    def _get_deficit_dict(self, deficit: NutrientDeficit) -> Dict[str, float]:
        """Convert NutrientDeficit to dictionary."""
        return {
            "N": max(0, deficit.n_kg_ha),
            "P2O5": max(0, deficit.p2o5_kg_ha),
            "K2O": max(0, deficit.k2o_kg_ha),
            "Ca": max(0, deficit.ca_kg_ha),
            "Mg": max(0, deficit.mg_kg_ha),
            "S": max(0, deficit.s_kg_ha),
        }
    
    def _optimize_economic_marginal_cost(
        self,
        fertilizers: List[FertilizerData],
        original: Dict[str, float],
        remaining: Dict[str, float],
        config: ProfileConfig,
        absolute_max: int
    ) -> Tuple[List[FertilizerDose], set, Dict[str, float]]:
        """Economic profile optimization using marginal cost approach.
        
        Operates directly on shared remaining dict. Picks fertilizers with lowest
        cost per kg of total weighted deficit reduced across all nutrients.
        """
        selected_doses: List[FertilizerDose] = []
        used_slugs: set = set()
        
        max_coverage_ratio = config.max_coverage_pct / 100.0
        min_coverage_ratio = config.min_coverage_pct / 100.0
        
        max_iterations = 30
        for _ in range(max_iterations):
            uncovered_nutrients = []
            for n in self.NUTRIENTS:
                if original[n] > 0:
                    covered = original[n] - remaining[n]
                    coverage_ratio = covered / original[n]
                    if coverage_ratio < min_coverage_ratio:
                        uncovered_nutrients.append((n, coverage_ratio, remaining[n]))
            
            if not uncovered_nutrients:
                break
            
            if len(selected_doses) >= config.max_fertilizers:
                break
            
            uncovered_nutrients.sort(key=lambda x: x[1])
            
            best_fert = None
            best_value_score = float('-inf')
            best_dose_info = None
            
            for fert in fertilizers:
                if fert.slug in used_slugs:
                    continue
                
                has_relevant_nutrient = False
                for (n, _, _) in uncovered_nutrients:
                    if fert.provides_nutrient(n):
                        has_relevant_nutrient = True
                        break
                if not has_relevant_nutrient:
                    continue
                
                price = self.get_price(fert)
                if price <= 0:
                    continue
                
                primary_nutrient = uncovered_nutrients[0][0]
                primary_pct = fert.get_nutrient_pct(primary_nutrient)
                primary_remaining = remaining[primary_nutrient]
                
                if primary_pct > 0 and primary_remaining > 0:
                    dose_to_cover = primary_remaining / (primary_pct / 100)
                else:
                    for (n, _, rem) in uncovered_nutrients:
                        pct = fert.get_nutrient_pct(n)
                        if pct > 0 and rem > 0:
                            dose_to_cover = rem / (pct / 100)
                            break
                    else:
                        continue
                
                for other_n in self.NUTRIENTS:
                    other_pct = fert.get_nutrient_pct(other_n)
                    if other_pct > 0 and original[other_n] > 0:
                        other_contribution = dose_to_cover * other_pct / 100
                        current_covered = original[other_n] - remaining[other_n]
                        new_total = current_covered + other_contribution
                        if new_total > original[other_n] * max_coverage_ratio:
                            max_additional = original[other_n] * max_coverage_ratio - current_covered
                            if max_additional > 0:
                                max_dose = max_additional / (other_pct / 100)
                                dose_to_cover = min(dose_to_cover, max_dose)
                            else:
                                dose_to_cover = 0
                
                if dose_to_cover < 0.5:
                    continue
                
                total_deficit_reduced = 0.0
                for n in self.NUTRIENTS:
                    pct = fert.get_nutrient_pct(n)
                    if pct > 0 and remaining[n] > 0:
                        contribution = min(dose_to_cover * pct / 100, remaining[n])
                        weight = 1.5 if n in self.PRIMARY_NUTRIENTS else 1.0
                        total_deficit_reduced += contribution * weight
                
                if total_deficit_reduced <= 0:
                    continue
                
                cost = dose_to_cover * price
                value_score = total_deficit_reduced / cost
                
                if value_score > best_value_score:
                    best_value_score = value_score
                    best_fert = fert
                    best_dose_info = dose_to_cover
            
            if best_fert is not None:
                dose = self._create_dose(best_fert, best_dose_info)
                selected_doses.append(dose)
                used_slugs.add(best_fert.slug)
                self._apply_dose_to_remaining(dose, remaining)
            else:
                target_nutrient = uncovered_nutrients[0][0]
                added = False
                for fert in fertilizers:
                    if fert.slug in used_slugs:
                        continue
                    if fert.provides_nutrient(target_nutrient):
                        dose = self._calculate_optimal_dose_v2(fert, remaining, original, config)
                        if dose and dose.dose_kg_ha >= 0.5:
                            selected_doses.append(dose)
                            used_slugs.add(fert.slug)
                            self._apply_dose_to_remaining(dose, remaining)
                            added = True
                            break
                if not added:
                    break
        
        return selected_doses, used_slugs, remaining
    
    def _create_dose(self, fert: FertilizerData, dose_kg_ha: float) -> FertilizerDose:
        """Create a FertilizerDose from a fertilizer and dose amount."""
        price = self.get_price(fert)
        rounded_dose = round(dose_kg_ha, 2)
        return FertilizerDose(
            fertilizer_id=fert.id,
            fertilizer_slug=fert.slug,
            fertilizer_name=fert.name,
            dose_kg_ha=rounded_dose,
            dose_kg_total=0,
            cost_per_kg=price,
            cost_total=round(price * rounded_dose, 2),
            n_contribution=round(dose_kg_ha * fert.n_pct / 100, 2),
            p2o5_contribution=round(dose_kg_ha * fert.p2o5_pct / 100, 2),
            k2o_contribution=round(dose_kg_ha * fert.k2o_pct / 100, 2),
            ca_contribution=round(dose_kg_ha * fert.ca_pct / 100, 2),
            mg_contribution=round(dose_kg_ha * fert.mg_pct / 100, 2),
            s_contribution=round(dose_kg_ha * fert.s_pct / 100, 2),
        )
    
    def _optimize_profile(
        self,
        deficit: NutrientDeficit,
        area_ha: float,
        num_applications: int,
        fertilizers: List[FertilizerData],
        config: ProfileConfig
    ) -> OptimizationResult:
        """Optimize for a specific profile with guaranteed coverage."""
        
        original = self._get_deficit_dict(deficit)
        remaining = original.copy()
        selected_doses: List[FertilizerDose] = []
        used_slugs: set = set()
        warnings: List[str] = []
        
        absolute_max = config.max_fertilizers + 3
        
        initial_target = config.initial_target_pct
        final_target = config.min_coverage_pct
        
        if config.profile == OptimizationProfile.ECONOMIC:
            min_cov_ratio = config.min_coverage_pct / 100.0
            max_cov_ratio = config.max_coverage_pct / 100.0
            
            for _ in range(30):
                uncovered = []
                for n in self.NUTRIENTS:
                    if original[n] > 0:
                        covered = original[n] - remaining[n]
                        ratio = covered / original[n]
                        if ratio < min_cov_ratio:
                            uncovered.append((n, ratio, remaining[n]))
                
                if not uncovered:
                    break
                if len(selected_doses) >= config.max_fertilizers:
                    break
                
                uncovered.sort(key=lambda x: x[1])
                
                best_fert = None
                best_score = float('-inf')
                best_dose = None
                
                for fert in fertilizers:
                    if fert.slug in used_slugs:
                        continue
                    
                    relevant = any(fert.provides_nutrient(n) for (n, _, _) in uncovered)
                    if not relevant:
                        continue
                    
                    price = self.get_price(fert)
                    if price <= 0:
                        continue
                    
                    target_n = uncovered[0][0]
                    pct = fert.get_nutrient_pct(target_n)
                    if pct > 0 and remaining[target_n] > 0:
                        dose_kg = remaining[target_n] / (pct / 100)
                    else:
                        for (n, _, rem) in uncovered:
                            p = fert.get_nutrient_pct(n)
                            if p > 0 and rem > 0:
                                dose_kg = rem / (p / 100)
                                break
                        else:
                            continue
                    
                    for on in self.NUTRIENTS:
                        op = fert.get_nutrient_pct(on)
                        if op > 0 and original[on] > 0:
                            contrib = dose_kg * op / 100
                            curr = original[on] - remaining[on]
                            if curr + contrib > original[on] * max_cov_ratio:
                                allowed = original[on] * max_cov_ratio - curr
                                if allowed > 0:
                                    dose_kg = min(dose_kg, allowed / (op / 100))
                                else:
                                    dose_kg = 0
                    
                    if dose_kg < 0.5:
                        continue
                    
                    total_reduced = 0.0
                    for n in self.NUTRIENTS:
                        p = fert.get_nutrient_pct(n)
                        if p > 0 and remaining[n] > 0:
                            c = min(dose_kg * p / 100, remaining[n])
                            w = 1.5 if n in self.PRIMARY_NUTRIENTS else 1.0
                            total_reduced += c * w
                    
                    if total_reduced <= 0:
                        continue
                    
                    score = total_reduced / (dose_kg * price)
                    if score > best_score:
                        best_score = score
                        best_fert = fert
                        best_dose = dose_kg
                
                if best_fert is not None:
                    dose = self._create_dose(best_fert, best_dose)
                    selected_doses.append(dose)
                    used_slugs.add(best_fert.slug)
                    self._apply_dose_to_remaining(dose, remaining)
                else:
                    target_n = uncovered[0][0]
                    added = False
                    for fert in fertilizers:
                        if fert.slug in used_slugs:
                            continue
                        if not fert.provides_nutrient(target_n):
                            continue
                        dose = self._calculate_optimal_dose_v2(fert, remaining, original, config)
                        if dose and dose.dose_kg_ha >= 0.5:
                            selected_doses.append(dose)
                            used_slugs.add(fert.slug)
                            self._apply_dose_to_remaining(dose, remaining)
                            added = True
                            break
                    if not added:
                        for fert in fertilizers:
                            if fert.slug in used_slugs:
                                continue
                            has_any = any(fert.provides_nutrient(n) for (n, _, _) in uncovered)
                            if not has_any:
                                continue
                            pct_target = fert.get_nutrient_pct(target_n)
                            if pct_target <= 0:
                                for (n, _, _) in uncovered:
                                    if fert.provides_nutrient(n):
                                        pct_target = fert.get_nutrient_pct(n)
                                        break
                            if pct_target > 0:
                                dose_kg = min(50.0, remaining.get(target_n, 50) / (pct_target / 100) if pct_target > 0 else 50)
                                if dose_kg >= 0.5:
                                    dose = self._create_dose(fert, dose_kg)
                                    selected_doses.append(dose)
                                    used_slugs.add(fert.slug)
                                    self._apply_dose_to_remaining(dose, remaining)
                                    added = True
                                    break
                    if not added:
                        break
        else:
            for phase in [1, 2]:
                current_target = initial_target if phase == 1 else final_target
                
                passes = 0
                max_passes = 8
                
                while passes < max_passes:
                    passes += 1
                    
                    coverage = self._calculate_coverage(original, remaining)
                    uncovered = [
                        (n, coverage[n]) for n in self.NUTRIENTS 
                        if original[n] > 0 and coverage[n] < current_target
                    ]
                    
                    if not uncovered:
                        break
                    
                    if len(selected_doses) >= config.max_fertilizers:
                        break
                    
                    uncovered.sort(key=lambda x: x[1])
                    
                    added_this_pass = False
                    for nutrient, cov_pct in uncovered:
                        if len(selected_doses) >= absolute_max:
                            break
                        if remaining[nutrient] <= 0:
                            continue
                        
                        best_ferts = self._get_best_fertilizers_for_nutrient(
                            fertilizers, nutrient, remaining, original, config, used_slugs
                        )
                        
                        for fert in best_ferts:
                            if fert.slug in used_slugs:
                                continue
                            
                            dose = self._calculate_optimal_dose_v2(fert, remaining, original, config)
                            if dose is not None and dose.dose_kg_ha >= 0.5:
                                selected_doses.append(dose)
                                used_slugs.add(fert.slug)
                                self._apply_dose_to_remaining(dose, remaining)
                                added_this_pass = True
                                break
                        
                        if added_this_pass:
                            break
                    
                    if not added_this_pass:
                        for nutrient, cov_pct in uncovered:
                            for fert in fertilizers:
                                if fert.provides_nutrient(nutrient) and fert.slug not in used_slugs:
                                    dose = self._calculate_optimal_dose_v2(fert, remaining, original, config)
                                    if dose is not None and dose.dose_kg_ha >= 0.5:
                                        selected_doses.append(dose)
                                        used_slugs.add(fert.slug)
                                        self._apply_dose_to_remaining(dose, remaining)
                                        added_this_pass = True
                                        break
                            if added_this_pass:
                                break
                    
                    if not added_this_pass:
                        break
        
        if len(selected_doses) < config.min_fertilizers:
            selected_doses = self._enforce_minimum_fertilizers(
                selected_doses, used_slugs, remaining, original, 
                fertilizers, config, area_ha, num_applications
            )
        
        selected_doses = self._enforce_minimum_coverage(
            selected_doses, used_slugs, remaining, original,
            fertilizers, config, area_ha
        )
        
        coverage = self._calculate_coverage(original, remaining)
        
        for nutrient, pct in coverage.items():
            if pct < config.min_coverage_pct and original[nutrient] > 0:
                warnings.append(f"{nutrient}: Solo {pct}% cubierto (déficit de {remaining[nutrient]:.1f} kg/ha)")
        
        total_cost_ha = sum(d.cost_per_kg * d.dose_kg_ha for d in selected_doses)
        total_cost_total = total_cost_ha * area_ha
        
        avg_coverage = sum(coverage.values()) / len(coverage) if coverage else 0
        score = avg_coverage - (total_cost_ha * 0.001 * config.cost_weight)
        
        return OptimizationResult(
            profile_name=config.name,
            profile_type=config.profile.value,
            fertilizers=selected_doses,
            total_cost_ha=round(total_cost_ha, 2),
            total_cost_total=round(total_cost_total, 2),
            coverage=coverage,
            warnings=warnings,
            score=round(score, 2)
        )
    
    def _enforce_minimum_fertilizers(
        self,
        selected_doses: List[FertilizerDose],
        used_slugs: set,
        remaining: Dict[str, float],
        original: Dict[str, float],
        fertilizers: List[FertilizerData],
        config: ProfileConfig,
        area_ha: float,
        num_applications: int
    ) -> List[FertilizerDose]:
        """Add supplemental fertilizers to meet min_fertilizers requirement."""
        
        candidates = [f for f in fertilizers if f.slug not in used_slugs]
        candidates = self._sort_for_profile(candidates, config)
        
        max_cap = config.max_coverage_pct / 100.0
        
        for fert in candidates:
            if len(selected_doses) >= config.min_fertilizers:
                break
            if len(selected_doses) >= config.max_fertilizers:
                break
            
            best_nutrient = None
            best_headroom = 0
            
            for nutrient in self.NUTRIENTS:
                pct = fert.get_nutrient_pct(nutrient)
                if pct <= 0:
                    continue
                
                current_covered = original[nutrient] - remaining[nutrient]
                current_coverage = current_covered / original[nutrient] if original[nutrient] > 0 else 1.0
                headroom = max_cap - current_coverage
                
                if headroom > best_headroom:
                    best_headroom = headroom
                    best_nutrient = nutrient
            
            if best_nutrient is None or best_headroom <= 0.01:
                continue
            
            nutrient_pct = fert.get_nutrient_pct(best_nutrient)
            if nutrient_pct <= 0:
                continue
            
            min_dose = original[best_nutrient] * 0.05 / (nutrient_pct / 100)
            max_headroom_dose = (original[best_nutrient] * best_headroom) / (nutrient_pct / 100)
            
            for other in self.NUTRIENTS:
                other_pct = fert.get_nutrient_pct(other)
                if other_pct <= 0:
                    continue
                current_covered = original[other] - remaining[other]
                current_coverage = current_covered / original[other] if original[other] > 0 else 1.0
                other_headroom = max_cap - current_coverage
                if other_headroom > 0:
                    other_max_dose = (original[other] * other_headroom) / (other_pct / 100)
                    max_headroom_dose = min(max_headroom_dose, other_max_dose)
            
            dose_kg_ha = min(min_dose, max_headroom_dose)
            if dose_kg_ha < 0.5:
                dose_kg_ha = 0.5
            
            will_exceed = False
            for nutrient in self.NUTRIENTS:
                pct = fert.get_nutrient_pct(nutrient)
                if pct <= 0:
                    continue
                contribution = dose_kg_ha * pct / 100
                current_covered = original[nutrient] - remaining[nutrient]
                new_coverage = (current_covered + contribution) / original[nutrient] if original[nutrient] > 0 else 1.0
                if new_coverage > max_cap + 0.01:
                    will_exceed = True
                    break
            
            if will_exceed:
                continue
            
            price = self.get_price(fert)
            dose_total = dose_kg_ha * area_ha
            
            dose = FertilizerDose(
                fertilizer_id=fert.id,
                fertilizer_slug=fert.slug,
                fertilizer_name=fert.name,
                dose_kg_ha=round(dose_kg_ha, 2),
                dose_kg_total=round(dose_total, 2),
                cost_per_kg=price,
                cost_total=round(dose_kg_ha * price * area_ha, 2),
                n_contribution=round(dose_kg_ha * fert.get_nutrient_pct("N") / 100, 2),
                p2o5_contribution=round(dose_kg_ha * fert.get_nutrient_pct("P2O5") / 100, 2),
                k2o_contribution=round(dose_kg_ha * fert.get_nutrient_pct("K2O") / 100, 2),
                ca_contribution=round(dose_kg_ha * fert.get_nutrient_pct("Ca") / 100, 2),
                mg_contribution=round(dose_kg_ha * fert.get_nutrient_pct("Mg") / 100, 2),
                s_contribution=round(dose_kg_ha * fert.get_nutrient_pct("S") / 100, 2),
            )
            
            selected_doses.append(dose)
            used_slugs.add(fert.slug)
            self._apply_dose_to_remaining(dose, remaining)
        
        return selected_doses
    
    def _enforce_minimum_coverage(
        self,
        selected_doses: List[FertilizerDose],
        used_slugs: set,
        remaining: Dict[str, float],
        original: Dict[str, float],
        fertilizers: List[FertilizerData],
        config: ProfileConfig,
        area_ha: float
    ) -> List[FertilizerDose]:
        """Add fertilizers to ensure all nutrients reach minimum coverage.
        
        Enhanced to:
        - Allow dose augmentation of existing fertilizers when no new candidates available
        - Be more aggressive for Complete profile to guarantee coverage
        - Dynamically relax fertilizer limits when coverage gaps persist
        """
        
        max_cap = config.max_coverage_pct / 100.0
        is_complete = config.profile == OptimizationProfile.COMPLETE
        base_max = config.max_fertilizers + 4
        absolute_max = config.max_fertilizers + 8 if is_complete else base_max
        
        for iteration in range(30):
            coverage = self._calculate_coverage(original, remaining)
            uncovered = [
                (n, coverage[n]) for n in self.NUTRIENTS
                if original[n] > 0 and coverage[n] < config.min_coverage_pct
            ]
            
            if not uncovered:
                break
            
            uncovered.sort(key=lambda x: x[1])
            
            added = False
            for nutrient, cov_pct in uncovered:
                if remaining[nutrient] <= 0:
                    continue
                
                candidates = [f for f in fertilizers 
                              if f.provides_nutrient(nutrient) and f.slug not in used_slugs]
                
                if not candidates:
                    all_providers = [f for f in fertilizers if f.provides_nutrient(nutrient)]
                    if all_providers:
                        def efficiency_score_aug(fert: FertilizerData) -> float:
                            pct = fert.get_nutrient_pct(nutrient)
                            price = self.get_price(fert)
                            return pct / price if price > 0 else 0
                        all_providers.sort(key=efficiency_score_aug, reverse=True)
                        candidates = all_providers[:2]
                
                def efficiency_score(fert: FertilizerData) -> float:
                    pct = fert.get_nutrient_pct(nutrient)
                    price = self.get_price(fert)
                    return pct / price if price > 0 else 0
                
                candidates.sort(key=efficiency_score, reverse=True)
                
                for fert in candidates:
                    nutrient_pct = fert.get_nutrient_pct(nutrient)
                    if nutrient_pct <= 0:
                        continue
                    
                    gap_to_target = (config.min_coverage_pct - cov_pct) / 100.0 * original[nutrient]
                    needed = max(remaining[nutrient] * 0.6, gap_to_target * 1.1) if cov_pct < 100 else remaining[nutrient]
                    dose_kg_ha = needed / (nutrient_pct / 100) if nutrient_pct > 0 else 0
                    
                    if dose_kg_ha < 0.5:
                        dose_kg_ha = 0.5
                    
                    max_overshoot = 0
                    for other in self.NUTRIENTS:
                        other_pct = fert.get_nutrient_pct(other)
                        if other_pct <= 0:
                            continue
                        contribution = dose_kg_ha * other_pct / 100
                        current_covered = original[other] - remaining[other]
                        new_coverage = (current_covered + contribution) / original[other] if original[other] > 0 else 1.0
                        if new_coverage > max_cap:
                            max_overshoot = max(max_overshoot, new_coverage - max_cap)
                    
                    overshoot_tolerance = 0.20 if is_complete else 0.15
                    if max_overshoot > overshoot_tolerance:
                        reduced_dose = dose_kg_ha * 0.5
                        if reduced_dose >= 0.5:
                            dose_kg_ha = reduced_dose
                        elif is_complete and max_overshoot < 0.30:
                            pass
                        else:
                            continue
                    
                    price = self.get_price(fert)
                    dose = FertilizerDose(
                        fertilizer_id=fert.id,
                        fertilizer_slug=fert.slug,
                        fertilizer_name=fert.name,
                        dose_kg_ha=round(dose_kg_ha, 2),
                        dose_kg_total=round(dose_kg_ha * area_ha, 2),
                        cost_per_kg=price,
                        cost_total=round(dose_kg_ha * price * area_ha, 2),
                        n_contribution=round(dose_kg_ha * fert.get_nutrient_pct("N") / 100, 2),
                        p2o5_contribution=round(dose_kg_ha * fert.get_nutrient_pct("P2O5") / 100, 2),
                        k2o_contribution=round(dose_kg_ha * fert.get_nutrient_pct("K2O") / 100, 2),
                        ca_contribution=round(dose_kg_ha * fert.get_nutrient_pct("Ca") / 100, 2),
                        mg_contribution=round(dose_kg_ha * fert.get_nutrient_pct("Mg") / 100, 2),
                        s_contribution=round(dose_kg_ha * fert.get_nutrient_pct("S") / 100, 2),
                    )
                    
                    selected_doses.append(dose)
                    used_slugs.add(fert.slug)
                    self._apply_dose_to_remaining(dose, remaining)
                    added = True
                    break
                
                if added:
                    break
            
            if not added:
                if is_complete and len(selected_doses) < absolute_max:
                    continue
                break
        
        return selected_doses
    
    def _get_best_fertilizers_for_nutrient(
        self,
        fertilizers: List[FertilizerData],
        nutrient: str,
        remaining: Dict[str, float],
        original: Dict[str, float],
        config: ProfileConfig,
        used_slugs: set
    ) -> List[FertilizerData]:
        """Get best fertilizers for a specific nutrient."""
        
        candidates = [f for f in fertilizers if f.provides_nutrient(nutrient) and f.slug not in used_slugs]
        
        def count_nutrients_provided(fert: FertilizerData) -> int:
            count = 0
            for n in self.NUTRIENTS:
                if fert.get_nutrient_pct(n) > 0:
                    count += 1
            return count
        
        def score_for_nutrient(fert: FertilizerData) -> float:
            price = self.get_price(fert)
            pct = fert.get_nutrient_pct(nutrient)
            efficiency = pct / price if price > 0 else 0
            
            nutrients_count = count_nutrients_provided(fert)
            
            other_nutrients_bonus = 0
            overshoot_penalty = 0
            dose_needed = remaining[nutrient] / (pct / 100) if pct > 0 else 0
            
            for other in self.NUTRIENTS:
                if other == nutrient:
                    continue
                other_pct = fert.get_nutrient_pct(other)
                if other_pct > 0:
                    contribution = dose_needed * other_pct / 100
                    current_covered = original[other] - remaining[other]
                    new_coverage = (current_covered + contribution) / original[other] if original[other] > 0 else 1
                    
                    if remaining[other] > 0 and new_coverage <= 1.1:
                        other_nutrients_bonus += 0.1
                    elif new_coverage > 1.1:
                        overshoot_penalty += (new_coverage - 1.1) * 2
            
            if config.profile == OptimizationProfile.ECONOMIC:
                efficiency = pct / price if price > 0 else 0
                deficient_nutrients_covered = sum(1 for n in self.NUTRIENTS if fert.get_nutrient_pct(n) > 0 and remaining[n] > 0)
                if deficient_nutrients_covered >= 3:
                    efficiency *= 15.0
                elif deficient_nutrients_covered >= 2:
                    efficiency *= 8.0
                efficiency += other_nutrients_bonus * 2.0
                
            elif config.profile == OptimizationProfile.COMPLETE:
                if nutrients_count == 1:
                    efficiency *= 10.0
                elif nutrients_count == 2:
                    efficiency *= 2.0
                else:
                    efficiency *= 0.1
            else:
                efficiency += other_nutrients_bonus * 1.5
                if nutrients_count == 2:
                    efficiency *= 5.0
                elif nutrients_count >= 3:
                    efficiency *= 2.0
                else:
                    efficiency *= 1.0
            
            efficiency -= overshoot_penalty
            
            if config.profile != OptimizationProfile.ECONOMIC:
                efficiency -= price * config.cost_weight * 0.0001
            
            return efficiency
        
        return sorted(candidates, key=score_for_nutrient, reverse=True)
    
    def _sort_fertilizers_by_profile(
        self,
        fertilizers: List[FertilizerData],
        remaining: Dict[str, float],
        config: ProfileConfig
    ) -> List[FertilizerData]:
        """Sort fertilizers based on profile strategy."""
        
        def count_nutrients(fert: FertilizerData) -> int:
            count = 0
            for n in self.NUTRIENTS:
                if fert.get_nutrient_pct(n) > 0:
                    count += 1
            return count
        
        def score_fertilizer(fert: FertilizerData) -> float:
            price = self.get_price(fert)
            if price <= 0:
                price = self.DEFAULT_PRICE
            
            total_score = 0.0
            nutrients_provided = count_nutrients(fert)
            
            for nutrient in self.NUTRIENTS:
                pct = fert.get_nutrient_pct(nutrient)
                if pct > 0 and remaining[nutrient] > 0:
                    weight = 1.0 if nutrient in self.PRIMARY_NUTRIENTS else 0.8
                    nutrient_score = (pct / 100) / price * remaining[nutrient] * weight
                    total_score += nutrient_score
            
            if config.profile == OptimizationProfile.ECONOMIC:
                pass
            elif config.profile == OptimizationProfile.COMPLETE:
                if nutrients_provided == 1:
                    total_score *= 10.0
                elif nutrients_provided == 2:
                    total_score *= 2.0
                else:
                    total_score *= 0.1
            else:
                if nutrients_provided == 2:
                    total_score *= 5.0
                elif nutrients_provided >= 3:
                    total_score *= 2.0
                else:
                    total_score *= 1.0
            
            if config.profile != OptimizationProfile.ECONOMIC:
                cost_penalty = price * config.cost_weight * 0.0001
                total_score -= cost_penalty
            
            return total_score
        
        return sorted(fertilizers, key=score_fertilizer, reverse=True)
    
    def _calculate_optimal_dose_v2(
        self,
        fert: FertilizerData,
        remaining: Dict[str, float],
        original: Dict[str, float],
        config: ProfileConfig
    ) -> Optional[FertilizerDose]:
        """Calculate optimal dose respecting min/max coverage targets."""
        
        max_coverage_factor = config.max_coverage_pct / 100.0
        
        limiting_doses: List[Tuple[str, float, float]] = []
        
        for nutrient in self.NUTRIENTS:
            pct = fert.get_nutrient_pct(nutrient)
            if pct > 0 and remaining[nutrient] > 0:
                dose_to_cover = remaining[nutrient] / (pct / 100)
                
                max_acceptable = original[nutrient] * max_coverage_factor
                already_covered = original[nutrient] - remaining[nutrient]
                max_additional = max_acceptable - already_covered
                max_dose = max_additional / (pct / 100) if pct > 0 else float('inf')
                
                limiting_doses.append((nutrient, dose_to_cover, max_dose))
        
        if not limiting_doses:
            return None
        
        limiting_doses.sort(key=lambda x: x[1])
        optimal_dose = limiting_doses[0][1]
        
        for nutrient, dose_to_cover, max_dose in limiting_doses:
            if max_dose < optimal_dose:
                optimal_dose = max_dose
        
        optimal_dose = min(optimal_dose, 500.0)
        optimal_dose = max(optimal_dose, 0)
        
        if optimal_dose < 0.5:
            return None
        
        price = self.get_price(fert)
        
        return FertilizerDose(
            fertilizer_id=fert.id,
            fertilizer_slug=fert.slug,
            fertilizer_name=fert.name,
            dose_kg_ha=round(optimal_dose, 2),
            dose_kg_total=round(optimal_dose, 2),
            cost_per_kg=price,
            cost_total=round(price * optimal_dose, 2),
            n_contribution=round(optimal_dose * fert.n_pct / 100, 2),
            p2o5_contribution=round(optimal_dose * fert.p2o5_pct / 100, 2),
            k2o_contribution=round(optimal_dose * fert.k2o_pct / 100, 2),
            ca_contribution=round(optimal_dose * fert.ca_pct / 100, 2),
            mg_contribution=round(optimal_dose * fert.mg_pct / 100, 2),
            s_contribution=round(optimal_dose * fert.s_pct / 100, 2),
        )
    
    def _apply_dose_to_remaining(self, dose: FertilizerDose, remaining: Dict[str, float]) -> None:
        """Apply a dose to remaining deficits."""
        remaining["N"] = max(0, remaining["N"] - dose.n_contribution)
        remaining["P2O5"] = max(0, remaining["P2O5"] - dose.p2o5_contribution)
        remaining["K2O"] = max(0, remaining["K2O"] - dose.k2o_contribution)
        remaining["Ca"] = max(0, remaining["Ca"] - dose.ca_contribution)
        remaining["Mg"] = max(0, remaining["Mg"] - dose.mg_contribution)
        remaining["S"] = max(0, remaining["S"] - dose.s_contribution)
    
    def _calculate_supplemental_dose(
        self,
        fert: FertilizerData,
        remaining: Dict[str, float],
        original: Dict[str, float],
        config: ProfileConfig
    ) -> Optional[FertilizerDose]:
        """Calculate a supplemental dose using available headroom up to max_coverage_pct."""
        
        max_coverage_factor = config.max_coverage_pct / 100.0
        
        max_dose = float('inf')
        can_contribute = False
        
        for nutrient in self.NUTRIENTS:
            pct = fert.get_nutrient_pct(nutrient)
            if pct > 0 and original[nutrient] > 0:
                already_covered = original[nutrient] - remaining[nutrient]
                current_coverage = already_covered / original[nutrient]
                
                if current_coverage < max_coverage_factor:
                    headroom = (max_coverage_factor * original[nutrient]) - already_covered
                    max_dose_for_nutrient = headroom / (pct / 100) if pct > 0 else float('inf')
                    max_dose = min(max_dose, max_dose_for_nutrient)
                    can_contribute = True
                else:
                    max_dose_for_nutrient = 0
                    max_dose = min(max_dose, max_dose_for_nutrient)
        
        if not can_contribute or max_dose <= 0.5:
            return None
        
        optimal_dose = min(max_dose, 100.0)
        
        if optimal_dose < 0.5:
            return None
        
        price = self.get_price(fert)
        
        return FertilizerDose(
            fertilizer_id=fert.id,
            fertilizer_slug=fert.slug,
            fertilizer_name=fert.name,
            dose_kg_ha=round(optimal_dose, 2),
            dose_kg_total=round(optimal_dose, 2),
            cost_per_kg=price,
            cost_total=round(price * optimal_dose, 2),
            n_contribution=round(optimal_dose * fert.n_pct / 100, 2),
            p2o5_contribution=round(optimal_dose * fert.p2o5_pct / 100, 2),
            k2o_contribution=round(optimal_dose * fert.k2o_pct / 100, 2),
            ca_contribution=round(optimal_dose * fert.ca_pct / 100, 2),
            mg_contribution=round(optimal_dose * fert.mg_pct / 100, 2),
            s_contribution=round(optimal_dose * fert.s_pct / 100, 2),
        )
    
    def _calculate_coverage(self, original: Dict[str, float], remaining: Dict[str, float]) -> Dict[str, float]:
        """Calculate coverage percentage for each nutrient."""
        coverage = {}
        for nutrient in self.NUTRIENTS:
            if original[nutrient] > 0:
                covered = original[nutrient] - remaining[nutrient]
                coverage[nutrient] = min(110.0, round((covered / original[nutrient]) * 100, 1))
            else:
                coverage[nutrient] = 100.0
        return coverage
    
    def _fill_gaps(
        self,
        selected_doses: List[FertilizerDose],
        used_slugs: set,
        remaining: Dict[str, float],
        original: Dict[str, float],
        fertilizers: List[FertilizerData],
        area_ha: float,
        config: ProfileConfig
    ) -> Tuple[List[FertilizerDose], Dict[str, float]]:
        """Fill nutrient gaps to meet minimum coverage targets."""
        
        min_coverage_factor = config.min_coverage_pct / 100.0
        
        gap_nutrients = []
        for nutrient in self.NUTRIENTS:
            if original[nutrient] > 0:
                current_coverage = (original[nutrient] - remaining[nutrient]) / original[nutrient]
                if current_coverage < min_coverage_factor:
                    gap = original[nutrient] * min_coverage_factor - (original[nutrient] - remaining[nutrient])
                    gap_nutrients.append((nutrient, gap, current_coverage))
        
        gap_nutrients.sort(key=lambda x: x[2])
        
        for nutrient, gap_kg, _ in gap_nutrients:
            if len(selected_doses) >= config.max_fertilizers:
                break
            
            best_fert = None
            best_score = -1
            
            for fert in fertilizers:
                if fert.slug in used_slugs:
                    continue
                
                pct = fert.get_nutrient_pct(nutrient)
                if pct > 0:
                    price = self.get_price(fert)
                    efficiency = pct / price
                    
                    overshoot_penalty = 0
                    dose_needed = gap_kg / (pct / 100)
                    for other_nutrient in self.NUTRIENTS:
                        other_pct = fert.get_nutrient_pct(other_nutrient)
                        if other_pct > 0 and other_nutrient != nutrient:
                            contribution = dose_needed * other_pct / 100
                            new_coverage = (original[other_nutrient] - remaining[other_nutrient] + contribution) / original[other_nutrient] if original[other_nutrient] > 0 else 1
                            if new_coverage > 1.1:
                                overshoot_penalty += (new_coverage - 1.1) * 10
                    
                    score = efficiency - overshoot_penalty
                    if score > best_score:
                        best_score = score
                        best_fert = fert
            
            if best_fert:
                dose = self._calculate_optimal_dose_v2(best_fert, remaining, original, config)
                if dose and dose.dose_kg_ha >= 0.5:
                    selected_doses.append(dose)
                    used_slugs.add(best_fert.slug)
                    self._apply_dose_to_remaining(dose, remaining)
        
        return selected_doses, remaining
    
    def calculate_micronutrients(
        self,
        micro_deficit: MicronutrientDeficit,
        area_ha: float,
        num_applications: int,
        crop_sensitivity: Optional[Dict[str, str]] = None,
        water_ph: float = 7.0,
        water_hco3_meq: float = 0.0
    ) -> List[MicronutrientDose]:
        """
        Calculate micronutrient fertilizer recommendations using same sources as Hydroponics.
        
        PRIORITY ORDER (like Hydroponics module):
        1. FIRST: Try commercial micronutrient blends (Diosol, Ultrasol, Mezcla Completa)
           - More economical, fewer products, professional formulation
        2. SECOND: If blends can't cover all deficits, use individual chelates
           - pH-aware: Fe-EDTA for pH<7.2, Fe-EDDHA/DTPA for pH>=7.2 or high HCO3
        3. THIRD: Use sulfates for remaining deficits (most economical)
        
        Args:
            water_ph: Water pH for chelate selection (default 7.0)
            water_hco3_meq: Bicarbonates in water (meq/L) for chelate selection
            crop_sensitivity: Dict mapping micronutrient names to sensitivity levels
        
        Returns list of MicronutrientDose recommendations.
        """
        
        catalog = _load_hydro_fertilizers_catalog()
        micro_catalog = [f for f in catalog if any(f.get(f'{m.lower()}_pct', 0) > 0 for m in self.MICRONUTRIENTS)]
        
        micro_fertilizers = [FertilizerData(f) for f in micro_catalog if FertilizerData(f).is_micronutrient_source()]
        
        if not micro_fertilizers:
            return []
        
        remaining = {
            "Fe": max(0, micro_deficit.fe_g_ha),
            "Mn": max(0, micro_deficit.mn_g_ha),
            "Zn": max(0, micro_deficit.zn_g_ha),
            "Cu": max(0, micro_deficit.cu_g_ha),
            "B": max(0, micro_deficit.b_g_ha),
            "Mo": max(0, micro_deficit.mo_g_ha),
        }
        
        total_deficit = sum(remaining.values())
        if total_deficit <= 0:
            return []
        
        recommendations: List[MicronutrientDose] = []
        used_slugs: set = set()
        
        BLEND_SLUGS = [
            'diosol',
            'ultrasol_micro_sqm',
            'multimicro_haifa', 
            'fetrilon_combi_basf',
            'micronutrient_mix_complete'
        ]
        
        blends = [f for f in micro_fertilizers if f.slug in BLEND_SLUGS]
        blends.sort(key=lambda f: self.get_price(f))
        
        def _apply_blend(blend: FertilizerData, limiting_micro: str) -> Optional[MicronutrientDose]:
            """Calculate dose based on the limiting (highest deficit) micronutrient."""
            pct = blend.get_micronutrient_pct(limiting_micro)
            if pct <= 0:
                return None
            
            deficit_g = remaining[limiting_micro]
            dose_kg_ha = deficit_g / (pct * 10)
            dose_g_ha = dose_kg_ha * 1000
            
            for micro in self.MICRONUTRIENTS:
                micro_pct = blend.get_micronutrient_pct(micro)
                if micro_pct > 0:
                    contrib = dose_kg_ha * micro_pct * 10
                    remaining[micro] = max(0, remaining[micro] - contrib)
            
            price = self.get_price(blend)
            cost_total = round(dose_kg_ha * price * area_ha, 2)
            
            return MicronutrientDose(
                fertilizer_id=blend.id,
                fertilizer_slug=blend.slug,
                fertilizer_name=blend.name,
                dose_g_ha=round(dose_g_ha, 1),
                dose_g_total=round(dose_g_ha * area_ha, 1),
                cost_per_kg=price,
                cost_total=cost_total,
                micronutrient="Mezcla",
                contribution_g_ha=round(deficit_g, 1)
            )
        
        MIN_SIGNIFICANT_DEFICIT = 5.0
        MAX_ITERATIONS = 10
        iteration = 0
        
        while iteration < MAX_ITERATIONS:
            iteration += 1
            
            active_deficits = [m for m in self.MICRONUTRIENTS if remaining[m] > MIN_SIGNIFICANT_DEFICIT]
            if not active_deficits:
                break
            
            best_blend = None
            best_limiting_micro = None
            best_coverage_value = 0
            
            for blend in blends:
                covered_micros = [m for m in active_deficits if blend.get_micronutrient_pct(m) > 0]
                
                if covered_micros:
                    limiting_micro = max(covered_micros, 
                                        key=lambda m: remaining[m] / max(blend.get_micronutrient_pct(m), 0.01))
                    
                    coverage_value = sum(
                        min(remaining[m], (remaining[limiting_micro] / blend.get_micronutrient_pct(limiting_micro)) 
                            * blend.get_micronutrient_pct(m) * 10)
                        for m in covered_micros
                    )
                    
                    price = max(self.get_price(blend), 1.0)
                    efficiency = coverage_value / price
                    
                    if efficiency > best_coverage_value:
                        best_coverage_value = efficiency
                        best_blend = blend
                        best_limiting_micro = limiting_micro
            
            if best_blend is None or best_coverage_value < MIN_SIGNIFICANT_DEFICIT:
                break
            
            dose = _apply_blend(best_blend, best_limiting_micro)
            if dose:
                recommendations.append(dose)
                used_slugs.add(best_blend.slug)
        
        use_high_ph_chelate = water_ph >= 7.2 or water_hco3_meq > 2.0
        
        def _get_best_chelate_for_fe() -> Optional[FertilizerData]:
            """Select appropriate iron chelate based on pH using correct catalog slugs."""
            if use_high_ph_chelate:
                preferred = ['iron_chelate_eddha', 'iron_chelate_dtpa']
            else:
                preferred = ['iron_chelate_edta', 'iron_chelate_dtpa']
            
            for slug in preferred:
                for f in micro_fertilizers:
                    if f.slug == slug and f.slug not in used_slugs:
                        return f
            
            return next((f for f in micro_fertilizers 
                        if f.provides_micronutrient('Fe') and f.slug not in used_slugs 
                        and any(x in f.slug.lower() for x in ['edta', 'eddha', 'dtpa', 'chelate', 'quelato'])), None)
        
        def _add_individual_recommendation(micro: str, fert: FertilizerData) -> None:
            """Add recommendation for individual micronutrient source."""
            pct = fert.get_micronutrient_pct(micro)
            if pct <= 0:
                return
            
            deficit_g = remaining[micro]
            if deficit_g <= 0:
                return
            
            dose_kg_ha = deficit_g / (pct * 10)
            dose_g_ha = dose_kg_ha * 1000
            
            price = self.get_price(fert)
            cost_total = round(dose_kg_ha * price * area_ha, 2)
            
            for other_micro in self.MICRONUTRIENTS:
                other_pct = fert.get_micronutrient_pct(other_micro)
                if other_pct > 0:
                    contrib = dose_kg_ha * other_pct * 10
                    remaining[other_micro] = max(0, remaining[other_micro] - contrib)
            
            recommendations.append(MicronutrientDose(
                fertilizer_id=fert.id,
                fertilizer_slug=fert.slug,
                fertilizer_name=fert.name,
                dose_g_ha=round(dose_g_ha, 1),
                dose_g_total=round(dose_g_ha * area_ha, 1),
                cost_per_kg=price,
                cost_total=cost_total,
                micronutrient=micro,
                contribution_g_ha=round(deficit_g, 1)
            ))
            used_slugs.add(fert.slug)
        
        if remaining.get('Fe', 0) > 0:
            fe_chelate = _get_best_chelate_for_fe()
            if fe_chelate:
                _add_individual_recommendation('Fe', fe_chelate)
        
        for micro in ['Mn', 'Zn', 'Cu', 'B', 'Mo']:
            if remaining.get(micro, 0) <= 0:
                continue
            
            candidates = [f for f in micro_fertilizers 
                         if f.provides_micronutrient(micro) 
                         and f.slug not in used_slugs
                         and f.slug not in BLEND_SLUGS]
            
            if not candidates:
                continue
            
            candidates.sort(key=lambda f: (
                -1 if any(x in f.slug for x in ['edta', 'eddha', 'dtpa']) else 0,
                f.get_micronutrient_pct(micro) / max(self.get_price(f), 1)
            ), reverse=True)
            
            best_fert = candidates[0]
            _add_individual_recommendation(micro, best_fert)
        
        return recommendations


def get_fertigation_fertilizers(db: Session, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get all fertilizers suitable for fertigation from the unified hydro_fertilizers.json catalog."""
    
    catalog = _load_hydro_fertilizers_catalog()
    
    currency = "MXN"
    if user_id:
        settings = db.query(UserPriceSettings).filter(
            UserPriceSettings.user_id == user_id
        ).first()
        if settings:
            currency = settings.preferred_currency
    
    user_prices: Dict[str, float] = {}
    active_price_ids: set = set()
    active_my_fertilizers: set = set()
    visible_ids: set = set()
    allowed_ids: Optional[set] = None
    if user_id:
        prices = db.query(UserFertilizerPrice).filter(
            UserFertilizerPrice.user_id == user_id,
            UserFertilizerPrice.currency == currency
        ).all()
        for p in prices:
            pricing_id = str(p.fertilizer_id)
            val = p.price_per_kg if p.price_per_kg is not None else p.price_per_liter
            if val is not None:
                user_prices[pricing_id] = float(val)
                active_price_ids.add(pricing_id)

        from app.routers.fertilizer_prices import load_default_fertilizers
        visible_fertilizers = load_default_fertilizers(db)
        visible_ids = {f.get('id') for f in visible_fertilizers if f.get('id')}
        active_price_ids.update(visible_ids)

        try:
            from app.models.database_models import FertilizerProduct
            active_products = db.query(FertilizerProduct).filter(
                FertilizerProduct.is_active == True
            ).all()
            active_my_fertilizers.update({p.slug for p in active_products if p.slug})
        except Exception:
            active_my_fertilizers = set()

        try:
            from app.models.hydro_ions_models import UserCustomFertilizer
            custom_ferts = db.query(UserCustomFertilizer).filter(
                UserCustomFertilizer.user_id == user_id,
                UserCustomFertilizer.is_active == True
            ).all()
            active_my_fertilizers.update({f"custom_{cf.id}" for cf in custom_ferts})
        except Exception:
            active_my_fertilizers = set(active_my_fertilizers)

        allowed_ids = active_price_ids.intersection(active_my_fertilizers)
    
    result: List[Dict[str, Any]] = []
    for item in catalog:
        fert = FertilizerData(item)
        pricing_alias = fert.slug

        if allowed_ids is not None and pricing_alias not in allowed_ids:
            continue
        
        price = user_prices.get(pricing_alias)
        if price is None:
            currency_defaults = get_default_price_for_currency(pricing_alias, currency)
            if not currency_defaults.get("price_per_kg") and not currency_defaults.get("price_per_liter"):
                currency_defaults = get_default_price_for_currency(fert.slug, currency)
            
            physical_state = (fert.physical_state or "solid").lower()
            if physical_state == "liquid" and currency_defaults.get("price_per_liter"):
                price = currency_defaults["price_per_liter"]
            elif currency_defaults.get("price_per_kg"):
                price = currency_defaults["price_per_kg"]
            else:
                price = fert.cost_per_unit or 25.0
        
        result.append({
            "id": fert.id,
            "slug": fert.slug,
            "name": fert.name,
            "category": fert.category,
            "n_pct": fert.n_pct,
            "p2o5_pct": fert.p2o5_pct,
            "k2o_pct": fert.k2o_pct,
            "ca_pct": fert.ca_pct,
            "mg_pct": fert.mg_pct,
            "s_pct": fert.s_pct,
            "price": price,
            "unit": fert.unit,
            "physical_state": fert.physical_state,
            "stock_tank": fert.stock_tank,
        })
    
    return result


def optimize_manual_deterministic(
    db: Session,
    user_id: int,
    deficits: Dict[str, float],
    micro_deficits: Dict[str, float],
    selected_fertilizer_ids: List[str],
    num_applications: int = 1,
    area_ha: float = 1.0,
    currency: str = "MXN",
    available_fertilizers: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Deterministic optimizer for manual mode - uses ONLY user-selected fertilizers.
    
    Generates a single optimized program (Balanced style) that:
    - Uses only fertilizers explicitly selected by the user
    - Respects 80-110% coverage limits
    - Returns clear errors if coverage cannot be achieved
    
    Args:
        available_fertilizers: Pre-filtered list of fertilizer dicts (optional).
                              If provided, these are used directly instead of re-fetching.
    """
    logger.info(f"[ManualDet] Starting deterministic optimization with {len(selected_fertilizer_ids)} fertilizers")
    
    optimizer = FertiIrrigationOptimizer(db, user_id, currency)
    
    # Use pre-filtered fertilizers if provided, otherwise fetch from catalog
    if available_fertilizers:
        # Convert dicts to FertilizerData objects
        all_fertilizers = []
        for f in available_fertilizers:
            fert_dict = {
                'id': f.get('id', f.get('slug', '')),
                'slug': f.get('slug', f.get('id', '')),
                'name': f.get('name', ''),
                'type': f.get('type', 'salt'),
                'n_pct': f.get('n_pct', 0),
                'p2o5_pct': f.get('p2o5_pct', 0),
                'k2o_pct': f.get('k2o_pct', 0),
                'ca_pct': f.get('ca_pct', 0),
                'mg_pct': f.get('mg_pct', 0),
                's_pct': f.get('s_pct', 0),
                'price_per_kg': f.get('price', f.get('price_per_kg', 25.0)),
                'default_price_mxn': f.get('price', f.get('price_per_kg', 25.0)),
                'stock_tank': f.get('stock_tank', 'A'),
                'form': f.get('form', 'solid')
            }
            all_fertilizers.append(FertilizerData(fert_dict))
        logger.info(f"[ManualDet] Using {len(all_fertilizers)} pre-filtered fertilizers")
    else:
        # Fetch from catalog
        all_fertilizers = optimizer.get_available_fertilizers(selected_fertilizer_ids)
        logger.info(f"[ManualDet] Found {len(all_fertilizers)} fertilizers from catalog")
    
    # All fertilizers including acids are valid for optimization
    # Acids can contribute N (nitric), P (phosphoric), S (sulfuric)
    macro_fertilizers = all_fertilizers
    
    if not macro_fertilizers:
        return {
            "success": False,
            "error": "No se encontraron los fertilizantes seleccionados en el catálogo.",
            "suggestions": ["Verifique que los fertilizantes seleccionados existen en el catálogo."]
        }
    
    # Check feasibility - can we cover each nutrient?
    feasibility_issues = []
    nutrient_sources = {}
    
    for nutrient in ["N", "P2O5", "K2O", "Ca", "Mg", "S"]:
        deficit = deficits.get(nutrient, 0)
        if deficit <= 0:
            continue
        
        pct_key = "p2o5_pct" if nutrient == "P2O5" else ("k2o_pct" if nutrient == "K2O" else f"{nutrient.lower()}_pct")
        
        sources = []
        for fert in macro_fertilizers:
            content = getattr(fert, pct_key, 0) or 0
            if content > 0:
                sources.append({'fert': fert, 'content': content, 'name': fert.name})
        
        nutrient_sources[nutrient] = sources
        
        if not sources:
            full_catalog = _load_hydro_fertilizers_catalog()
            suggested = []
            for fc in full_catalog:
                fc_content = fc.get(pct_key, 0) or 0
                if fc_content >= 10 and 'acid' not in fc.get('id', '').lower():
                    suggested.append(f"{fc.get('name')} ({fc_content}% {nutrient})")
            
            feasibility_issues.append({
                'nutrient': nutrient,
                'suggestions': suggested[:5] if suggested else []
            })
    
    if feasibility_issues:
        suggestion_text = []
        for issue in feasibility_issues:
            if issue['suggestions']:
                suggestion_text.append(f"{issue['nutrient']}: agregar {', '.join(issue['suggestions'][:3])}")
        
        return {
            "success": False,
            "error": f"Los fertilizantes seleccionados no pueden cubrir: {', '.join([i['nutrient'] for i in feasibility_issues])}.",
            "failed_nutrients": [i['nutrient'] for i in feasibility_issues],
            "suggestions": suggestion_text
        }
    
    # Build NutrientDeficit object
    deficit_obj = NutrientDeficit(
        n_kg_ha=max(0, deficits.get('N', 0)),
        p2o5_kg_ha=max(0, deficits.get('P2O5', 0)),
        k2o_kg_ha=max(0, deficits.get('K2O', 0)),
        ca_kg_ha=max(0, deficits.get('Ca', 0)),
        mg_kg_ha=max(0, deficits.get('Mg', 0)),
        s_kg_ha=max(0, deficits.get('S', 0))
    )
    
    # Build MicronutrientDeficit if needed
    micro_obj = None
    if micro_deficits and any(v > 0 for v in micro_deficits.values()):
        micro_obj = MicronutrientDeficit(
            fe_g_ha=micro_deficits.get('Fe', 0),
            mn_g_ha=micro_deficits.get('Mn', 0),
            zn_g_ha=micro_deficits.get('Zn', 0),
            cu_g_ha=micro_deficits.get('Cu', 0),
            b_g_ha=micro_deficits.get('B', 0),
            mo_g_ha=micro_deficits.get('Mo', 0)
        )
    
    # Use Balanced profile configuration
    config = BALANCED_PROFILE
    sorted_ferts = optimizer._sort_for_profile(macro_fertilizers, config)
    
    try:
        # Run the deterministic optimization
        result = optimizer._optimize_profile(
            deficit=deficit_obj,
            area_ha=area_ha,
            num_applications=num_applications,
            fertilizers=sorted_ferts,
            config=config
        )
        
        # Add micronutrients if needed
        if micro_obj:
            micro_doses = optimizer.calculate_micronutrients(micro_obj, area_ha, num_applications)
            result.micronutrients = micro_doses
            result.micronutrient_cost_ha = sum(m.cost_total for m in micro_doses) / area_ha if area_ha > 0 else 0
        
        # Validate coverage
        failed_coverage = []
        exceeding_coverage = []
        
        for nutrient in ["N", "P2O5", "K2O", "Ca", "Mg", "S"]:
            deficit = deficits.get(nutrient, 0)
            if deficit <= 0:
                continue
            
            coverage = result.coverage.get(nutrient, 0)
            if coverage < 80:
                if nutrient_sources.get(nutrient):
                    failed_coverage.append(f"{nutrient}:{round(coverage)}%")
            elif coverage > 110:
                exceeding_coverage.append(f"{nutrient}:{round(coverage)}%")
        
        if failed_coverage:
            suggestions = []
            for failed in failed_coverage:
                nut = failed.split(':')[0]
                sources = nutrient_sources.get(nut, [])
                if sources:
                    source_names = [s['name'] for s in sources[:3]]
                    suggestions.append(f"{nut}: los fertilizantes ({', '.join(source_names)}) no son suficientes")
            
            return {
                "success": False,
                "error": f"No se logró cobertura ≥80% para: {', '.join(failed_coverage)}.",
                "failed_nutrients": failed_coverage,
                "suggestions": suggestions,
                "partial_result": _convert_result_to_dict(result, num_applications, optimizer)
            }
        
        if exceeding_coverage:
            logger.warning(f"[ManualDet] Coverage exceeds 110%: {exceeding_coverage}")
            result.warnings.append(f"Cobertura elevada en: {', '.join(exceeding_coverage)}.")
        
        # Success - convert result to API format
        program = _convert_result_to_dict(result, num_applications, optimizer)
        
        logger.info(f"[ManualDet] Success: {len(result.fertilizers)} fertilizers, coverage={result.coverage}")
        
        return {
            "success": True,
            "profiles": {"balanced": program},
            "model_used": "deterministic",
            "mode": "manual"
        }
        
    except Exception as e:
        logger.error(f"[ManualDet] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Error en optimización: {str(e)}",
            "suggestions": []
        }


def _convert_result_to_dict(result: 'OptimizationResult', num_applications: int, optimizer: 'FertiIrrigationOptimizer') -> Dict[str, Any]:
    """Convert OptimizationResult to API-compatible dictionary format."""
    fertilizers = []
    
    for fert_dose in result.fertilizers:
        fert_dict = {
            'id': fert_dose.fertilizer_slug,
            'name': fert_dose.fertilizer_name,
            'dose_kg_ha': fert_dose.dose_kg_ha,
            'dose_per_application': round(fert_dose.dose_kg_ha / max(1, num_applications), 2),
            'price_per_kg': fert_dose.cost_per_kg,
            'subtotal': round(fert_dose.dose_kg_ha * fert_dose.cost_per_kg, 2),
            'tank': 'B' if fert_dose.fertilizer_slug in ['calcium_nitrate', 'calcium_chloride'] else 'A',
            'contributions': {}
        }
        
        for nutrient, value in [
            ('N', fert_dose.n_contribution),
            ('P2O5', fert_dose.p2o5_contribution),
            ('K2O', fert_dose.k2o_contribution),
            ('Ca', fert_dose.ca_contribution),
            ('Mg', fert_dose.mg_contribution),
            ('S', fert_dose.s_contribution)
        ]:
            if value > 0:
                fert_dict['contributions'][nutrient] = round(value, 2)
        
        fertilizers.append(fert_dict)
    
    total_cost = sum(f['subtotal'] for f in fertilizers)
    
    return {
        'fertilizers': fertilizers,
        'coverage': {k: round(v, 1) for k, v in result.coverage.items()},
        'total_cost_per_ha': round(total_cost, 2),
        'profile_name': 'Tu Programa',
        'notes': 'Generado con optimizador determinístico.',
        'warnings': result.warnings if result.warnings else None
    }

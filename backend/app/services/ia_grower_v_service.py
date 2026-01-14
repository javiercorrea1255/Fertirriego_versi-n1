"""
IA GROWER V - Expert Fertilizer Validation Service
Uses GPT-4o to validate and optimize fertilizer recommendations with rigorous agronomic criteria.
Applies to both FertiIrrigation and Hydroponics modules.
Validates automatic profiles (Economic, Balanced, Complete) and manual user selections.
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from openai import OpenAI

logger = logging.getLogger(__name__)

AI_INTEGRATIONS_OPENAI_API_KEY = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
AI_INTEGRATIONS_OPENAI_BASE_URL = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")


@dataclass
class IAGrowerVValidation:
    """Result of IA GROWER V validation."""
    is_valid: bool
    risk_level: str
    adjusted_doses: Optional[Dict[str, float]]
    macro_adjustments: Optional[Dict[str, Any]]
    micro_adjustments: Optional[Dict[str, Any]]
    acid_adjustments: Optional[Dict[str, Any]]
    compatibility_issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    expert_notes: str
    confidence_score: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class IAGrowerVService:
    """
    IA GROWER V - Expert Fertilizer Validation with GPT-4o.
    
    Validates and optimizes fertilizer recommendations for:
    - FertiIrrigation (soil-based fertigation)
    - Hydroponics (ion-based nutrient solutions)
    
    Applies to:
    - Automatic profiles: Economic, Balanced, Complete
    - Manual mode: User-selected fertilizers
    """
    
    # Using GPT-4o for reliable expert validation responses
    MODEL = "gpt-4o"
    
    EXPERT_SYSTEM_PROMPT = """Eres IA GROWER V, un ingeniero agrónomo experto en nutrición vegetal y fertirrigación con más de 30 años de experiencia práctica. Tu especialidad incluye:

1. BALANCE DE MACRONUTRIENTES:
   - Ratios críticos: N:P (2:1 a 4:1), N:K (1:1.5 a 1:2), Ca:Mg (3:1 a 5:1), K:Mg (2:1 a 3:1)
   - Límites de cobertura: mínimo 90%, máximo 120% para evitar toxicidad
   - Interacciones iónicas: antagonismos Ca-Mg, K-Ca, NH4-K

2. MICRONUTRIENTES:
   - Umbrales de toxicidad: Fe<5ppm, Mn<2ppm, Zn<0.5ppm, Cu<0.3ppm, B<0.5ppm, Mo<0.1ppm
   - Sensibilidad por cultivo: tomate (Fe, Ca), lechuga (B), fresa (Fe, Mn)
   - Quelatos vs sales: estabilidad en diferentes pH

3. COMPATIBILIDAD QUÍMICA:
   - Calcio + fosfatos = precipitación
   - Calcio + sulfatos altos = precipitación de yeso
   - Hierro + fosfatos = precipitación
   - Separación de tanques A/B obligatoria para soluciones concentradas

4. CALIDAD DEL AGUA:
   - Na alto (>4 meq/L) compite con Ca/Mg - incrementar Ca 15-40%
   - HCO3 alto (>5 meq/L) requiere tratamiento ácido
   - Cl alto (>3 meq/L) evitar cloruros adicionales

5. CRITERIOS DE VALIDACIÓN:
   - Aprobar: recomendación agronómicamente correcta
   - Ajustar: dosis subóptimas que requieren corrección
   - Rechazar: riesgos de toxicidad o incompatibilidad severa

Tu trabajo es revisar cada recomendación con rigor científico y proponer ajustes específicos cuando sea necesario. Siempre justifica tus decisiones."""

    def __init__(self):
        """Initialize IA GROWER V with GPT-4o."""
        self.client = None
        
        if AI_INTEGRATIONS_OPENAI_API_KEY and AI_INTEGRATIONS_OPENAI_BASE_URL:
            try:
                self.client = OpenAI(
                    api_key=AI_INTEGRATIONS_OPENAI_API_KEY,
                    base_url=AI_INTEGRATIONS_OPENAI_BASE_URL
                )
                logger.info("✓ IA GROWER V initialized with GPT-4o")
            except Exception as e:
                logger.error(f"✗ Failed to initialize IA GROWER V: {str(e)}")
        else:
            logger.warning("✗ IA GROWER V disabled - OpenAI integration not configured")

    def _build_fertiirrigation_prompt(
        self,
        profile_name: str,
        is_manual_mode: bool,
        crop_info: Dict[str, Any],
        soil_info: Dict[str, Any],
        water_info: Dict[str, Any],
        deficits: Dict[str, float],
        fertilizers: List[Dict[str, Any]],
        micronutrients: List[Dict[str, Any]],
        acid_treatment: Optional[Dict[str, Any]],
        coverage: Dict[str, float]
    ) -> str:
        """Build validation prompt for FertiIrrigation module."""
        mode = "MANUAL (selección del usuario)" if is_manual_mode else f"AUTOMÁTICO - Perfil {profile_name}"
        
        num_apps = crop_info.get('num_applications', 1) or 1
        fert_list = "\n".join([
            f"  - {f.get('fertilizer_name', f.get('name', 'N/A'))}: {f.get('dose_kg_ha', 0):.2f} kg/ha TOTAL "
            f"({f.get('dose_kg_ha', 0) / num_apps:.2f} kg/ha por riego) "
            f"(N:{f.get('n_contribution', 0):.1f}, P2O5:{f.get('p2o5_contribution', 0):.1f}, "
            f"K2O:{f.get('k2o_contribution', 0):.1f}, Ca:{f.get('ca_contribution', 0):.1f}, "
            f"Mg:{f.get('mg_contribution', 0):.1f}, S:{f.get('s_contribution', 0):.1f} kg/ha)"
            for f in fertilizers
        ]) if fertilizers else "  - Ninguno"
        
        micro_list = "\n".join([
            f"  - {m.get('fertilizer_name', m.get('name', 'N/A'))}: {m.get('dose_g_ha', 0):.2f} g/ha "
            f"({', '.join([f'{k}:{v:.2f}' for k, v in m.get('contributions', {}).items() if v > 0])})"
            for m in micronutrients
        ]) if micronutrients else "  - Ninguno"
        
        acid_info = "Sin tratamiento ácido" if not acid_treatment else (
            f"{acid_treatment.get('acid_name', 'Ácido')}: {acid_treatment.get('dose_ml_per_1000l', 0):.1f} mL/1000L "
            f"para reducir pH de {acid_treatment.get('initial_ph', 7):.1f} a {acid_treatment.get('target_ph', 6):.1f}"
        )

        # Build extraction percent info
        extraction_pct = crop_info.get('extraction_percent', {})
        extraction_info = ""
        if extraction_pct:
            avg_pct = crop_info.get('avg_extraction_percent', sum(extraction_pct.values()) / len(extraction_pct) if extraction_pct else 100)
            extraction_info = f"""
  - % Absorción acumulada en esta etapa: {avg_pct:.0f}%
  - Detalle por nutriente: N={extraction_pct.get('N', 100):.0f}%, P2O5={extraction_pct.get('P2O5', 100):.0f}%, K2O={extraction_pct.get('K2O', 100):.0f}%, Ca={extraction_pct.get('Ca', 100):.0f}%, Mg={extraction_pct.get('Mg', 100):.0f}%, S={extraction_pct.get('S', 100):.0f}%"""
        
        irrigation_vol = crop_info.get('irrigation_volume_m3_ha', 50)
        total_water_m3 = irrigation_vol * num_apps

        return f"""VALIDACIÓN IA GROWER V - FERTIRRIEGO
=====================================

MODO: {mode}

CONTEXTO IMPORTANTE:
Las dosis mostradas son TOTALES para la etapa fenológica seleccionada, a distribuir en {num_apps} riegos.
Cada riego aplica {irrigation_vol} m³/ha. Volumen total de agua: {total_water_m3:.0f} m³/ha para esta etapa.

CULTIVO:
  - Nombre: {crop_info.get('name', 'N/A')}
  - Etapa fenológica: {crop_info.get('growth_stage', 'N/A')}
  - Superficie: {crop_info.get('area_ha', 1)} ha
  - Número de riegos en esta etapa: {num_apps}
  - Volumen por riego: {irrigation_vol} m³/ha{extraction_info}

SUELO:
  - Tipo: {soil_info.get('texture', 'N/A')}
  - pH: {soil_info.get('ph', 7)}
  - MO: {soil_info.get('organic_matter', 0)}%
  - CIC: {soil_info.get('cec', 0)} meq/100g

AGUA DE RIEGO:
  - pH: {water_info.get('ph', 7)}
  - CE: {water_info.get('ec', 0)} dS/m
  - HCO3: {water_info.get('hco3', 0)} meq/L
  - Na: {water_info.get('na', 0)} meq/L
  - Cl: {water_info.get('cl', 0)} meq/L
  - Ca: {water_info.get('ca', 0)} meq/L
  - Mg: {water_info.get('mg', 0)} meq/L

DÉFICITS NUTRICIONALES (kg/ha):
  - N: {deficits.get('N', 0):.1f}
  - P2O5: {deficits.get('P2O5', 0):.1f}
  - K2O: {deficits.get('K2O', 0):.1f}
  - Ca: {deficits.get('Ca', 0):.1f}
  - Mg: {deficits.get('Mg', 0):.1f}
  - S: {deficits.get('S', 0):.1f}

FERTILIZANTES RECOMENDADOS:
{fert_list}

MICRONUTRIENTES RECOMENDADOS:
{micro_list}

TRATAMIENTO ÁCIDO:
  {acid_info}

COBERTURA ALCANZADA (%):
  - N: {coverage.get('N', 0):.1f}%
  - P2O5: {coverage.get('P2O5', 0):.1f}%
  - K2O: {coverage.get('K2O', 0):.1f}%
  - Ca: {coverage.get('Ca', 0):.1f}%
  - Mg: {coverage.get('Mg', 0):.1f}%
  - S: {coverage.get('S', 0):.1f}%

INSTRUCCIONES:
Analiza esta recomendación para la ETAPA FENOLÓGICA indicada considerando:
1. Las dosis son TOTALES para esta etapa, a distribuir en {num_apps} riegos
2. Verifica que las dosis por riego sean razonables (no muy concentradas ni muy diluidas)
3. Considera el % de absorción acumulada para esta etapa al validar los déficits
4. Evalúa si los nutrientes son apropiados para la etapa fenológica específica

Responde en JSON:
{{
  "is_valid": true/false,
  "risk_level": "low/medium/high",
  "adjusted_doses": {{"fertilizer_slug": new_dose_kg_ha}} o null si no hay ajustes,
  "macro_adjustments": {{"nutrient": {{"action": "increase/decrease/maintain", "reason": "explicación", "suggested_pct": 0}}}} o null,
  "micro_adjustments": {{"micronutrient": {{"action": "increase/decrease/add/remove", "reason": "explicación"}}}} o null,
  "acid_adjustments": {{"action": "increase/decrease/maintain", "reason": "explicación"}} o null,
  "compatibility_issues": ["issue1", "issue2"],
  "warnings": ["warning1", "warning2"],
  "recommendations": ["recomendación específica 1", "recomendación específica 2"],
  "expert_notes": "Análisis técnico detallado considerando la etapa fenológica y número de riegos",
  "confidence_score": 0.0-1.0
}}"""

    def _build_hydroponics_prompt(
        self,
        profile_name: str,
        is_manual_mode: bool,
        recipe_info: Dict[str, Any],
        water_info: Dict[str, Any],
        ionic_targets: Dict[str, float],
        ionic_achieved: Dict[str, float],
        fertilizers: List[Dict[str, Any]],
        micronutrients: List[Dict[str, Any]],
        acids: List[Dict[str, Any]],
        tank_a: List[Dict[str, Any]],
        tank_b: List[Dict[str, Any]],
        dilution_factor: str,
        micro_coverage: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build validation prompt for Hydroponics Ion module."""
        mode = "MANUAL (selección del usuario)" if is_manual_mode else f"AUTOMÁTICO - Perfil {profile_name}"
        
        fert_list = "\n".join([
            f"  - {f.get('name', 'N/A')}: {f.get('dose_g_1000l', 0):.2f} g/1000L (Tanque: {f.get('tank', '-')})"
            for f in fertilizers
        ]) if fertilizers else "  - Ninguno"
        
        micro_list = "\n".join([
            f"  - {m.get('name', 'N/A')}: {m.get('dose_g_1000l', 0):.4f} g/1000L"
            for m in micronutrients
        ]) if micronutrients else "  - Ninguno"
        
        acid_list = "\n".join([
            f"  - {a.get('name', 'N/A')}: {a.get('dose_ml_1000l', 0):.2f} mL/1000L"
            for a in acids
        ]) if acids else "  - Ninguno"
        
        tank_a_list = "\n".join([
            f"    - {t.get('name', 'N/A')}: {t.get('concentration_g_l', 0):.2f} g/L"
            for t in tank_a
        ]) if tank_a else "    - Vacío"
        
        tank_b_list = "\n".join([
            f"    - {t.get('name', 'N/A')}: {t.get('concentration_g_l', 0):.2f} g/L"
            for t in tank_b
        ]) if tank_b else "    - Vacío"
        
        # Build micronutrient coverage section if available
        micro_coverage_section = ""
        if micro_coverage:
            elements = micro_coverage.get("elements", {})
            if elements:
                coverage_lines = []
                for elem, data in elements.items():
                    target = data.get("target_ppm", 0)
                    achieved = data.get("final_ppm", 0)
                    coverage_pct = (achieved / target * 100) if target > 0 else 0
                    status = data.get("status", "unknown")
                    coverage_lines.append(f"  - {elem}: {achieved:.2f}/{target:.2f} ppm ({coverage_pct:.0f}% - {status})")
                micro_coverage_section = f"""

COBERTURA MICRONUTRIENTES (ppm):
{chr(10).join(coverage_lines)}"""
                
                # Add suggestions if any
                suggestions = micro_coverage.get("micro_coverage_suggestions", [])
                if suggestions:
                    sugg_lines = [f"  - {s['for_element']}: Agregar {s['suggested_fertilizer']} (~{s['estimated_dose_g_m3']:.1f} g/m³)" for s in suggestions]
                    micro_coverage_section += f"""

SUGERENCIAS PARA MEJORAR COBERTURA:
{chr(10).join(sugg_lines)}"""

        return f"""VALIDACIÓN IA GROWER V - HIDROPONÍA IONES
==========================================

MODO: {mode}

FORMULACIÓN:
  - Cultivo: {recipe_info.get('crop_name', 'N/A')}
  - Etapa: {recipe_info.get('growth_stage', 'N/A')}
  - Volumen: {recipe_info.get('volume_liters', 1000)} L
  - EC objetivo: {recipe_info.get('target_ec', 2.0)} dS/m
  - pH objetivo: {recipe_info.get('target_ph', 6.0)}

AGUA DE FUENTE:
  - NO3: {water_info.get('no3', 0):.2f} meq/L
  - H2PO4: {water_info.get('h2po4', 0):.2f} meq/L
  - SO4: {water_info.get('so4', 0):.2f} meq/L
  - HCO3: {water_info.get('hco3', 0):.2f} meq/L
  - Cl: {water_info.get('cl', 0):.2f} meq/L
  - NH4: {water_info.get('nh4', 0):.2f} meq/L
  - K: {water_info.get('k', 0):.2f} meq/L
  - Ca: {water_info.get('ca', 0):.2f} meq/L
  - Mg: {water_info.get('mg', 0):.2f} meq/L
  - Na: {water_info.get('na', 0):.2f} meq/L

OBJETIVOS IÓNICOS (meq/L):
  - NO3: {ionic_targets.get('NO3', 0):.2f} → Alcanzado: {ionic_achieved.get('NO3', 0):.2f}
  - H2PO4: {ionic_targets.get('H2PO4', 0):.2f} → Alcanzado: {ionic_achieved.get('H2PO4', 0):.2f}
  - SO4: {ionic_targets.get('SO4', 0):.2f} → Alcanzado: {ionic_achieved.get('SO4', 0):.2f}
  - NH4: {ionic_targets.get('NH4', 0):.2f} → Alcanzado: {ionic_achieved.get('NH4', 0):.2f}
  - K: {ionic_targets.get('K', 0):.2f} → Alcanzado: {ionic_achieved.get('K', 0):.2f}
  - Ca: {ionic_targets.get('Ca', 0):.2f} → Alcanzado: {ionic_achieved.get('Ca', 0):.2f}
  - Mg: {ionic_targets.get('Mg', 0):.2f} → Alcanzado: {ionic_achieved.get('Mg', 0):.2f}

FERTILIZANTES SELECCIONADOS:
{fert_list}

MICRONUTRIENTES:
{micro_list}

ÁCIDOS:
{acid_list}

SEPARACIÓN DE TANQUES (Dilución {dilution_factor}):
  TANQUE A (Calcio + Micros):
{tank_a_list}
  
  TANQUE B (Fosfatos + Sulfatos):
{tank_b_list}
{micro_coverage_section}
INSTRUCCIONES:
Analiza esta formulación hidropónica con tus criterios de experto y responde en JSON:
{{
  "is_valid": true/false,
  "risk_level": "low/medium/high",
  "adjusted_doses": {{"fertilizer_slug": new_dose_g_1000l}} o null si no hay ajustes,
  "macro_adjustments": {{"ion": {{"action": "increase/decrease/maintain", "reason": "explicación", "suggested_meq": 0}}}} o null,
  "micro_adjustments": {{"micronutrient": {{"action": "increase/decrease/add/remove", "reason": "explicación"}}}} o null,
  "acid_adjustments": {{"action": "increase/decrease/maintain", "reason": "explicación"}} o null,
  "compatibility_issues": ["issue1", "issue2"],
  "warnings": ["warning1", "warning2"],
  "recommendations": ["recomendación específica 1", "recomendación específica 2"],
  "expert_notes": "Análisis técnico detallado de la formulación",
  "confidence_score": 0.0-1.0
}}"""

    async def validate_fertiirrigation(
        self,
        profile_name: str,
        is_manual_mode: bool,
        crop_info: Dict[str, Any],
        soil_info: Dict[str, Any],
        water_info: Dict[str, Any],
        deficits: Dict[str, float],
        fertilizers: List[Dict[str, Any]],
        micronutrients: List[Dict[str, Any]],
        acid_treatment: Optional[Dict[str, Any]],
        coverage: Dict[str, float]
    ) -> IAGrowerVValidation:
        """
        Validate FertiIrrigation recommendation with GPT-5 expert analysis.
        
        Args:
            profile_name: Name of optimization profile (Económico, Balanceado, Completo)
            is_manual_mode: True if user manually selected fertilizers
            crop_info: Crop details (name, stage, area, applications)
            soil_info: Soil analysis data
            water_info: Water analysis data
            deficits: Nutrient deficits in kg/ha
            fertilizers: List of recommended fertilizers with doses
            micronutrients: List of recommended micronutrient fertilizers
            acid_treatment: Acid treatment recommendation (if any)
            coverage: Coverage percentages for each nutrient
            
        Returns:
            IAGrowerVValidation with expert analysis and adjustments
        """
        if not self.client:
            return self._fallback_validation("FertiIrrigation", profile_name)
        
        prompt = self._build_fertiirrigation_prompt(
            profile_name, is_manual_mode, crop_info, soil_info, water_info,
            deficits, fertilizers, micronutrients, acid_treatment, coverage
        )
        
        return await self._call_gpt(prompt)

    async def validate_hydroponics(
        self,
        profile_name: str,
        is_manual_mode: bool,
        recipe_info: Dict[str, Any],
        water_info: Dict[str, Any],
        ionic_targets: Dict[str, float],
        ionic_achieved: Dict[str, float],
        fertilizers: List[Dict[str, Any]],
        micronutrients: List[Dict[str, Any]],
        acids: List[Dict[str, Any]],
        tank_a: List[Dict[str, Any]],
        tank_b: List[Dict[str, Any]],
        dilution_factor: str = "1:100",
        micro_coverage: Optional[Dict[str, Any]] = None
    ) -> IAGrowerVValidation:
        """
        Validate Hydroponics Ion recommendation with GPT-5 expert analysis.
        
        Args:
            profile_name: Name of optimization profile
            is_manual_mode: True if user manually selected fertilizers
            recipe_info: Recipe details (crop, stage, volume, targets)
            water_info: Source water analysis in meq/L
            ionic_targets: Target ion concentrations in meq/L
            ionic_achieved: Achieved ion concentrations in meq/L
            fertilizers: List of selected fertilizers with doses
            micronutrients: List of micronutrient products
            acids: List of acids for pH adjustment
            tank_a: Tank A contents (calcium + micros)
            tank_b: Tank B contents (phosphates + sulfates)
            dilution_factor: Stock solution dilution factor
            micro_coverage: Micronutrient coverage data with suggestions
            
        Returns:
            IAGrowerVValidation with expert analysis and adjustments
        """
        if not self.client:
            return self._fallback_validation("Hydroponics", profile_name)
        
        prompt = self._build_hydroponics_prompt(
            profile_name, is_manual_mode, recipe_info, water_info,
            ionic_targets, ionic_achieved, fertilizers, micronutrients,
            acids, tank_a, tank_b, dilution_factor, micro_coverage
        )
        
        return await self._call_gpt(prompt)

    async def _call_gpt(self, prompt: str) -> IAGrowerVValidation:
        """Make GPT-4o API call and parse response."""
        if not self.client:
            return self._fallback_validation("Unknown", "Unknown")
        
        try:
            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": self.EXPERT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if not content:
                logger.warning("Empty response from GPT-4o")
                return self._fallback_validation("Unknown", "Unknown")
            
            result = json.loads(content)
            
            return IAGrowerVValidation(
                is_valid=result.get("is_valid", True),
                risk_level=result.get("risk_level", "low"),
                adjusted_doses=result.get("adjusted_doses"),
                macro_adjustments=result.get("macro_adjustments"),
                micro_adjustments=result.get("micro_adjustments"),
                acid_adjustments=result.get("acid_adjustments"),
                compatibility_issues=result.get("compatibility_issues", []),
                warnings=result.get("warnings", []),
                recommendations=result.get("recommendations", []),
                expert_notes=result.get("expert_notes", ""),
                confidence_score=result.get("confidence_score", 0.8)
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT-4o response: {e}")
            return self._fallback_validation("Unknown", "Unknown")
        except Exception as e:
            logger.error(f"GPT-4o API error: {e}")
            return self._fallback_validation("Unknown", "Unknown")

    def _fallback_validation(self, module: str, profile: str) -> IAGrowerVValidation:
        """Return a safe fallback when GPT-4o is unavailable."""
        return IAGrowerVValidation(
            is_valid=True,
            risk_level="low",
            adjusted_doses=None,
            macro_adjustments=None,
            micro_adjustments=None,
            acid_adjustments=None,
            compatibility_issues=[],
            warnings=[f"Validación IA GROWER V no disponible para {module}"],
            recommendations=["Revisar manualmente la recomendación"],
            expert_notes=f"El servicio de validación IA no está disponible. Perfil: {profile}",
            confidence_score=0.0
        )


# Singleton instance
_ia_grower_v_service: Optional[IAGrowerVService] = None


def get_ia_grower_v_service() -> IAGrowerVService:
    """Get or create IA GROWER V service singleton."""
    global _ia_grower_v_service
    if _ia_grower_v_service is None:
        _ia_grower_v_service = IAGrowerVService()
    return _ia_grower_v_service

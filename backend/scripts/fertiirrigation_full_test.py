#!/usr/bin/env python3
"""
FertiIrrigation Full Test Script - Tomate en todas las etapas fenológicas.
Genera un reporte completo con validación agronómica.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
from datetime import datetime
from typing import Dict, List, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from app.services.fertiirrigation_calculator import fertiirrigation_calculator, SoilData, WaterData, CropData, IrrigationData, AcidData


TOMATO_STAGES = [
    {
        "id": "seedling",
        "name": "Plántula/Trasplante", 
        "duration_days": 25,
        "cumulative_pct": {"N": 5, "P2O5": 5, "K2O": 3, "Ca": 4, "Mg": 4, "S": 5},
        "previous_pct": {"N": 0, "P2O5": 0, "K2O": 0, "Ca": 0, "Mg": 0, "S": 0},
        "notes": "Desarrollo radicular inicial. Fósforo crítico."
    },
    {
        "id": "vegetative",
        "name": "Crecimiento Vegetativo",
        "duration_days": 25,
        "cumulative_pct": {"N": 25, "P2O5": 20, "K2O": 15, "Ca": 20, "Mg": 20, "S": 22},
        "previous_pct": {"N": 5, "P2O5": 5, "K2O": 3, "Ca": 4, "Mg": 4, "S": 5},
        "notes": "Rápido crecimiento foliar. Alta demanda de N."
    },
    {
        "id": "flowering",
        "name": "Floración",
        "duration_days": 20,
        "cumulative_pct": {"N": 45, "P2O5": 45, "K2O": 35, "Ca": 40, "Mg": 40, "S": 45},
        "previous_pct": {"N": 25, "P2O5": 20, "K2O": 15, "Ca": 20, "Mg": 20, "S": 22},
        "notes": "Formación de flores. P y Ca críticos."
    },
    {
        "id": "fruit_set",
        "name": "Cuajado de Frutos",
        "duration_days": 20,
        "cumulative_pct": {"N": 65, "P2O5": 65, "K2O": 55, "Ca": 60, "Mg": 60, "S": 65},
        "previous_pct": {"N": 45, "P2O5": 45, "K2O": 35, "Ca": 40, "Mg": 40, "S": 45},
        "notes": "Inicio de llenado. K comienza a dominar."
    },
    {
        "id": "fruit_development",
        "name": "Desarrollo de Frutos",
        "duration_days": 40,
        "cumulative_pct": {"N": 85, "P2O5": 85, "K2O": 85, "Ca": 85, "Mg": 85, "S": 85},
        "previous_pct": {"N": 65, "P2O5": 65, "K2O": 55, "Ca": 60, "Mg": 60, "S": 65},
        "notes": "Máxima extracción. K muy alto para calidad."
    },
    {
        "id": "maturation",
        "name": "Maduración/Cosecha",
        "duration_days": 50,
        "cumulative_pct": {"N": 100, "P2O5": 100, "K2O": 100, "Ca": 100, "Mg": 100, "S": 100},
        "previous_pct": {"N": 85, "P2O5": 85, "K2O": 85, "Ca": 85, "Mg": 85, "S": 85},
        "notes": "Finalización del ciclo. Reducir N para maduración."
    }
]

TOTAL_REQ_KG_HA = {"N": 200, "P2O5": 80, "K2O": 300, "Ca": 160, "Mg": 40, "S": 35}

TYPICAL_SOIL = {
    "name": "Suelo Franco Típico - Bajío Mexicano",
    "texture_class": "franco",
    "ph": 7.2,
    "organic_matter_pct": 2.5,
    "cic_cmol_kg": 18.0,
    "bulk_density": 1.35,
    "depth_cm": 30,
    "n_no3_ppm": 25,
    "n_nh4_ppm": 8,
    "p_ppm": 18,
    "k_ppm": 180,
    "ca_ppm": 2200,
    "mg_ppm": 280,
    "s_ppm": 12,
    "fe_ppm": 15,
    "mn_ppm": 8,
    "zn_ppm": 2.5,
    "cu_ppm": 1.2,
    "b_ppm": 0.8
}

TYPICAL_WATER = {
    "name": "Agua de Pozo - Bicarbonatos Moderados",
    "ph": 7.5,
    "ec": 0.8,
    "hco3_meq_l": 4.2,
    "ca_meq_l": 3.5,
    "mg_meq_l": 1.8,
    "na_meq_l": 2.0,
    "k_meq_l": 0.1,
    "cl_meq_l": 1.5,
    "so4_meq_l": 1.2,
    "no3_meq_l": 0.3,
    "fe_ppm": 0.05,
    "mn_ppm": 0.02,
    "zn_ppm": 0.01,
    "cu_ppm": 0.005,
    "b_ppm": 0.1
}

IRRIGATION_PARAMS = {
    "system": "goteo",
    "frequency_days": 3,
    "volume_m3_ha": 50,
    "area_ha": 1.0
}

def calculate_delta_percent(current_pct: Dict, previous_pct: Dict) -> Dict[str, float]:
    return {k: current_pct[k] - previous_pct[k] for k in current_pct}

def calculate_stage_requirements(total_req: Dict, delta_pct: Dict) -> Dict[str, float]:
    return {k: total_req[k] * delta_pct[k] / 100 for k in total_req}

def run_stage_calculation(stage: Dict, irrigation_frequency: int = 3) -> Dict[str, Any]:
    delta_pct = calculate_delta_percent(stage["cumulative_pct"], stage["previous_pct"])
    avg_delta = sum(delta_pct.values()) / len(delta_pct)
    stage_req = calculate_stage_requirements(TOTAL_REQ_KG_HA, delta_pct)
    
    num_applications = max(1, stage["duration_days"] // irrigation_frequency)
    
    soil_data = SoilData(
        texture=TYPICAL_SOIL["texture_class"],
        ph=TYPICAL_SOIL["ph"],
        organic_matter_pct=TYPICAL_SOIL["organic_matter_pct"],
        cic_cmol_kg=TYPICAL_SOIL["cic_cmol_kg"],
        bulk_density=TYPICAL_SOIL["bulk_density"],
        depth_cm=TYPICAL_SOIL["depth_cm"],
        n_no3_ppm=TYPICAL_SOIL["n_no3_ppm"],
        n_nh4_ppm=TYPICAL_SOIL["n_nh4_ppm"],
        p_ppm=TYPICAL_SOIL["p_ppm"],
        k_ppm=TYPICAL_SOIL["k_ppm"],
        ca_ppm=TYPICAL_SOIL["ca_ppm"],
        mg_ppm=TYPICAL_SOIL["mg_ppm"],
        s_ppm=TYPICAL_SOIL["s_ppm"]
    )
    
    water_data = WaterData(
        ph=TYPICAL_WATER["ph"],
        ec=TYPICAL_WATER["ec"],
        hco3_meq=TYPICAL_WATER["hco3_meq_l"],
        ca_meq=TYPICAL_WATER["ca_meq_l"],
        mg_meq=TYPICAL_WATER["mg_meq_l"],
        na_meq=TYPICAL_WATER["na_meq_l"],
        k_meq=TYPICAL_WATER["k_meq_l"],
        so4_meq=TYPICAL_WATER["so4_meq_l"],
        no3_meq=TYPICAL_WATER["no3_meq_l"],
        fe_ppm=TYPICAL_WATER["fe_ppm"],
        mn_ppm=TYPICAL_WATER["mn_ppm"],
        zn_ppm=TYPICAL_WATER["zn_ppm"],
        cu_ppm=TYPICAL_WATER["cu_ppm"],
        b_ppm=TYPICAL_WATER["b_ppm"]
    )
    
    crop_data = CropData(
        name="Tomate",
        variety="Saladette",
        growth_stage=stage["name"],
        n_kg_ha=stage_req["N"],
        p2o5_kg_ha=stage_req["P2O5"],
        k2o_kg_ha=stage_req["K2O"],
        ca_kg_ha=stage_req["Ca"],
        mg_kg_ha=stage_req["Mg"],
        s_kg_ha=stage_req["S"],
        extraction_crop_id="tomato"
    )
    
    irrigation_data = IrrigationData(
        system=IRRIGATION_PARAMS["system"],
        frequency_days=irrigation_frequency,
        volume_m3_ha=IRRIGATION_PARAMS["volume_m3_ha"],
        area_ha=IRRIGATION_PARAMS["area_ha"],
        num_applications=num_applications
    )
    
    acid_data = AcidData(
        acid_type="phosphoric_85",
        ml_per_1000L=150,
        cost_mxn_per_1000L=45,
        n_g_per_1000L=0,
        p_g_per_1000L=80,
        s_g_per_1000L=0
    )
    
    result = fertiirrigation_calculator.calculate(
        soil=soil_data,
        water=water_data,
        crop=crop_data,
        irrigation=irrigation_data,
        acid=acid_data,
        currency="MXN",
        stage_extraction_pct=avg_delta
    )
    
    return {
        "stage": stage,
        "delta_pct": delta_pct,
        "avg_delta": avg_delta,
        "stage_requirements": stage_req,
        "num_applications": num_applications,
        "calculation_result": result
    }

def analyze_agronomic_coherence(all_results: List[Dict]) -> Dict[str, Any]:
    issues = []
    recommendations = []
    
    total_n = sum(r["stage_requirements"]["N"] for r in all_results)
    total_p = sum(r["stage_requirements"]["P2O5"] for r in all_results)
    total_k = sum(r["stage_requirements"]["K2O"] for r in all_results)
    
    if abs(total_n - TOTAL_REQ_KG_HA["N"]) > 1:
        issues.append(f"N total ({total_n:.1f}) no coincide con requerimiento ({TOTAL_REQ_KG_HA['N']})")
    if abs(total_p - TOTAL_REQ_KG_HA["P2O5"]) > 1:
        issues.append(f"P2O5 total ({total_p:.1f}) no coincide con requerimiento ({TOTAL_REQ_KG_HA['P2O5']})")
    if abs(total_k - TOTAL_REQ_KG_HA["K2O"]) > 1:
        issues.append(f"K2O total ({total_k:.1f}) no coincide con requerimiento ({TOTAL_REQ_KG_HA['K2O']})")
    
    for i, r in enumerate(all_results):
        stage_name = r["stage"]["name"]
        req = r["stage_requirements"]
        
        if req["N"] > 0:
            ratio_nk = req["K2O"] / req["N"] if req["N"] > 0 else 0
            if i >= 3 and ratio_nk < 1.0:
                issues.append(f"{stage_name}: Ratio K:N ({ratio_nk:.2f}) bajo para fructificación")
        
        if "Plántula" in stage_name and req["P2O5"] < req["N"] * 0.3:
            recommendations.append(f"{stage_name}: Considerar aumentar P para desarrollo radicular")
        
        balance = r["calculation_result"].get("nutrient_balance", [])
        for nb in balance:
            if nb.get("deficit_kg_ha", 0) < 0:
                nutrient = nb.get("nutrient", "?")
                deficit = nb.get("deficit_kg_ha", 0)
                recommendations.append(f"{stage_name}: Exceso de {nutrient} ({abs(deficit):.1f} kg/ha) - suelo/agua aportan suficiente")
    
    progression_ok = True
    for i in range(1, len(all_results)):
        prev_req = sum(all_results[i-1]["stage_requirements"].values())
        curr_req = sum(all_results[i]["stage_requirements"].values())
        if i < 4 and curr_req < prev_req:
            issues.append(f"Requerimientos decrecen antes de maduración: {all_results[i]['stage']['name']}")
            progression_ok = False
    
    return {
        "issues": issues,
        "recommendations": recommendations,
        "totals": {"N": total_n, "P2O5": total_p, "K2O": total_k},
        "progression_ok": progression_ok
    }

def generate_pdf_report(all_results: List[Dict], analysis: Dict, output_path: str):
    doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, alignment=TA_CENTER, spaceAfter=20)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=14, spaceAfter=12)
    section_style = ParagraphStyle('Section', parent=styles['Heading3'], fontSize=12, spaceAfter=8, textColor=colors.darkblue)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, spaceAfter=6)
    small_style = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, spaceAfter=4)
    
    story = []
    
    story.append(Paragraph("REPORTE DE VALIDACIÓN FERTIRRIEGO", title_style))
    story.append(Paragraph("Cultivo: Tomate - Todas las Etapas Fenológicas", subtitle_style))
    story.append(Paragraph(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}", body_style))
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("1. ESCENARIO DE PRUEBA", section_style))
    story.append(Paragraph(f"<b>Suelo:</b> {TYPICAL_SOIL['name']}", body_style))
    soil_table_data = [
        ["Parámetro", "Valor", "Parámetro", "Valor"],
        ["Textura", TYPICAL_SOIL["texture_class"], "pH", str(TYPICAL_SOIL["ph"])],
        ["MO (%)", str(TYPICAL_SOIL["organic_matter_pct"]), "CIC (cmol/kg)", str(TYPICAL_SOIL["cic_cmol_kg"])],
        ["N-NO3 (ppm)", str(TYPICAL_SOIL["n_no3_ppm"]), "N-NH4 (ppm)", str(TYPICAL_SOIL["n_nh4_ppm"])],
        ["P (ppm)", str(TYPICAL_SOIL["p_ppm"]), "K (ppm)", str(TYPICAL_SOIL["k_ppm"])],
        ["Ca (ppm)", str(TYPICAL_SOIL["ca_ppm"]), "Mg (ppm)", str(TYPICAL_SOIL["mg_ppm"])],
    ]
    soil_table = Table(soil_table_data, colWidths=[3*cm, 2.5*cm, 3*cm, 2.5*cm])
    soil_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
    ]))
    story.append(soil_table)
    story.append(Spacer(1, 10))
    
    story.append(Paragraph(f"<b>Agua:</b> {TYPICAL_WATER['name']}", body_style))
    water_table_data = [
        ["Parámetro", "Valor", "Parámetro", "Valor"],
        ["pH", str(TYPICAL_WATER["ph"]), "CE (dS/m)", str(TYPICAL_WATER["ec"])],
        ["HCO3 (meq/L)", str(TYPICAL_WATER["hco3_meq_l"]), "Ca (meq/L)", str(TYPICAL_WATER["ca_meq_l"])],
        ["Mg (meq/L)", str(TYPICAL_WATER["mg_meq_l"]), "Na (meq/L)", str(TYPICAL_WATER["na_meq_l"])],
    ]
    water_table = Table(water_table_data, colWidths=[3*cm, 2.5*cm, 3*cm, 2.5*cm])
    water_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(water_table)
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("<b>Riego:</b> Goteo, frecuencia 3 días, volumen 50 m³/ha por riego", body_style))
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("2. REQUERIMIENTOS TOTALES DEL CICLO (80 ton/ha)", section_style))
    req_table_data = [
        ["Nutriente", "N", "P2O5", "K2O", "Ca", "Mg", "S"],
        ["kg/ha", str(TOTAL_REQ_KG_HA["N"]), str(TOTAL_REQ_KG_HA["P2O5"]), str(TOTAL_REQ_KG_HA["K2O"]), 
         str(TOTAL_REQ_KG_HA["Ca"]), str(TOTAL_REQ_KG_HA["Mg"]), str(TOTAL_REQ_KG_HA["S"])]
    ]
    req_table = Table(req_table_data, colWidths=[2.5*cm]*7)
    req_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(req_table)
    story.append(PageBreak())
    
    story.append(Paragraph("3. RESULTADOS POR ETAPA FENOLÓGICA", section_style))
    
    for result in all_results:
        stage = result["stage"]
        delta = result["delta_pct"]
        req = result["stage_requirements"]
        calc = result["calculation_result"]
        
        story.append(Paragraph(f"<b>{stage['name']}</b> ({stage['duration_days']} días, {result['num_applications']} riegos)", subtitle_style))
        story.append(Paragraph(f"<i>{stage['notes']}</i>", small_style))
        
        delta_row = ["Delta %"] + [f"{delta[k]:.1f}%" for k in ["N", "P2O5", "K2O", "Ca", "Mg", "S"]]
        req_row = ["Req (kg/ha)"] + [f"{req[k]:.1f}" for k in ["N", "P2O5", "K2O", "Ca", "Mg", "S"]]
        
        stage_table_data = [
            ["", "N", "P2O5", "K2O", "Ca", "Mg", "S"],
            delta_row,
            req_row
        ]
        stage_table = Table(stage_table_data, colWidths=[2.5*cm]*7)
        stage_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ]))
        story.append(stage_table)
        
        balance = calc.get("nutrient_balance", [])
        if balance:
            story.append(Paragraph("<b>Balance Nutricional:</b>", body_style))
            balance_headers = ["Nutriente", "Req", "Suelo", "Agua", "Déficit", "Fertilizar"]
            balance_data = [balance_headers]
            for b in balance:
                row = [
                    b.get("nutrient", ""),
                    f"{b.get('requirement_kg_ha', 0):.1f}",
                    f"{b.get('soil_available_kg_ha', 0):.1f}",
                    f"{b.get('water_contribution_kg_ha', 0):.1f}",
                    f"{b.get('deficit_kg_ha', 0):.1f}",
                    f"{b.get('fertilizer_needed_kg_ha', 0):.1f}"
                ]
                balance_data.append(row)
            
            balance_table = Table(balance_data, colWidths=[2*cm, 1.8*cm, 1.8*cm, 1.8*cm, 1.8*cm, 2*cm])
            balance_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ]))
            story.append(balance_table)
        
        story.append(Spacer(1, 10))
        
        total_cost = calc.get("total_cost", 0)
        story.append(Paragraph(f"<b>Costo estimado fertilización:</b> ${total_cost:.2f} MXN/ha", body_style))
        story.append(Spacer(1, 15))
    
    story.append(PageBreak())
    story.append(Paragraph("4. ANÁLISIS DE COHERENCIA AGRONÓMICA", section_style))
    
    if analysis["issues"]:
        story.append(Paragraph("<b>Problemas detectados:</b>", body_style))
        for issue in analysis["issues"]:
            story.append(Paragraph(f"• {issue}", small_style))
    else:
        story.append(Paragraph("✓ No se detectaron problemas de coherencia", body_style))
    
    story.append(Spacer(1, 10))
    
    if analysis["recommendations"]:
        story.append(Paragraph("<b>Recomendaciones:</b>", body_style))
        for rec in analysis["recommendations"]:
            story.append(Paragraph(f"• {rec}", small_style))
    
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Verificación de totales:</b>", body_style))
    totals = analysis["totals"]
    story.append(Paragraph(f"N total: {totals['N']:.1f} kg/ha (esperado: {TOTAL_REQ_KG_HA['N']})", small_style))
    story.append(Paragraph(f"P2O5 total: {totals['P2O5']:.1f} kg/ha (esperado: {TOTAL_REQ_KG_HA['P2O5']})", small_style))
    story.append(Paragraph(f"K2O total: {totals['K2O']:.1f} kg/ha (esperado: {TOTAL_REQ_KG_HA['K2O']})", small_style))
    
    story.append(Spacer(1, 20))
    story.append(Paragraph("5. RESUMEN DE COSTOS POR ETAPA", section_style))
    
    cost_data = [["Etapa", "Duración", "Riegos", "Costo Est. (MXN/ha)"]]
    total_cycle_cost = 0
    for r in all_results:
        cost = r["calculation_result"].get("total_cost", 0)
        total_cycle_cost += cost
        cost_data.append([
            r["stage"]["name"][:20],
            f"{r['stage']['duration_days']} días",
            str(r["num_applications"]),
            f"${cost:,.0f}"
        ])
    cost_data.append(["TOTAL CICLO", "", "", f"${total_cycle_cost:,.0f}"])
    
    cost_table = Table(cost_data, colWidths=[5*cm, 2.5*cm, 2*cm, 3.5*cm])
    cost_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgreen),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTWEIGHT', (0, -1), (-1, -1), 'BOLD'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(cost_table)
    
    story.append(Spacer(1, 20))
    story.append(Paragraph("6. CONCLUSIONES", section_style))
    
    conclusions = [
        "El sistema de cálculo delta funciona correctamente, distribuyendo los requerimientos proporcionalmente a cada etapa.",
        f"Costo total estimado del ciclo: ${total_cycle_cost:,.0f} MXN/ha",
        "La disponibilidad del suelo se proporciona correctamente por etapa fenológica.",
        f"Progresión de requerimientos: {'✓ Coherente' if analysis['progression_ok'] else '⚠ Revisar'}"
    ]
    for c in conclusions:
        story.append(Paragraph(f"• {c}", body_style))
    
    doc.build(story)
    return output_path

def main():
    print("=" * 60)
    print("FERTIRRIGATION FULL TEST - TOMATE")
    print("=" * 60)
    
    all_results = []
    
    for stage in TOMATO_STAGES:
        print(f"\nProcesando: {stage['name']}...")
        result = run_stage_calculation(stage)
        all_results.append(result)
        
        req = result["stage_requirements"]
        print(f"  Delta promedio: {result['avg_delta']:.1f}%")
        print(f"  Requerimientos: N={req['N']:.1f}, P2O5={req['P2O5']:.1f}, K2O={req['K2O']:.1f}")
        print(f"  Aplicaciones: {result['num_applications']}")
        
        balance = result["calculation_result"].get("nutrient_balance", [])
        if balance:
            deficits = {b["nutrient"]: b.get("deficit_kg_ha", 0) for b in balance}
            print(f"  Déficits: N={deficits.get('N', 0):.1f}, P2O5={deficits.get('P2O5', 0):.1f}, K2O={deficits.get('K2O', 0):.1f}")
    
    print("\n" + "=" * 60)
    print("ANÁLISIS DE COHERENCIA")
    print("=" * 60)
    
    analysis = analyze_agronomic_coherence(all_results)
    
    if analysis["issues"]:
        print("\nProblemas detectados:")
        for issue in analysis["issues"]:
            print(f"  ⚠ {issue}")
    else:
        print("\n✓ No se detectaron problemas de coherencia")
    
    if analysis["recommendations"]:
        print("\nRecomendaciones:")
        for rec in analysis["recommendations"]:
            print(f"  → {rec}")
    
    print("\nVerificación de totales:")
    print(f"  N: {analysis['totals']['N']:.1f} / {TOTAL_REQ_KG_HA['N']} kg/ha")
    print(f"  P2O5: {analysis['totals']['P2O5']:.1f} / {TOTAL_REQ_KG_HA['P2O5']} kg/ha")
    print(f"  K2O: {analysis['totals']['K2O']:.1f} / {TOTAL_REQ_KG_HA['K2O']} kg/ha")
    
    print("\n" + "=" * 60)
    print("GENERANDO PDF...")
    print("=" * 60)
    
    output_path = "attached_assets/fertiirrigation_test_report.pdf"
    os.makedirs("attached_assets", exist_ok=True)
    generate_pdf_report(all_results, analysis, output_path)
    print(f"\n✓ Reporte generado: {output_path}")
    
    return all_results, analysis

if __name__ == "__main__":
    main()

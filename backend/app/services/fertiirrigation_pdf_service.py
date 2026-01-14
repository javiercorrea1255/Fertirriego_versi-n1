"""
FertiIrrigation PDF Report Service.
Generates professional PDF reports for fertigation calculations.
"""
import io
from datetime import datetime
from typing import Dict, Any, Optional, List
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import logging

from app.services.pdf_branding import (
    PDFBrandingContext, 
    draw_professional_letterhead,
    draw_professional_footer,
    BRAND_GREEN
)
from app.services.fertiirrigation_ab_tanks_service import separate_fertilizers_ab
from app.services.fertiirrigation_report_utils import (
    CONTRIBUTION_KEYS,
    compute_contributions,
    get_fertilizer_composition,
)
from app.routers.fertilizer_prices import DEFAULT_PRICES_BY_CURRENCY

logger = logging.getLogger(__name__)


def normalize_slug(name: str) -> str:
    """Normalize a name to a slug format for matching."""
    import re
    if not name:
        return ""
    slug = name.lower().strip()
    slug = re.sub(r'[áàäâ]', 'a', slug)
    slug = re.sub(r'[éèëê]', 'e', slug)
    slug = re.sub(r'[íìïî]', 'i', slug)
    slug = re.sub(r'[óòöô]', 'o', slug)
    slug = re.sub(r'[úùüû]', 'u', slug)
    slug = re.sub(r'[ñ]', 'n', slug)
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    return slug


# Common name mappings for Spanish fertilizer names to pricing module IDs
NAME_TO_PRICE_ID = {
    "cloruro_de_calcio": "calcium_chloride",
    "cloruro_calcio": "calcium_chloride",
    "sulfato_de_magnesio": "magnesium_sulfate",
    "sulfato_magnesio": "magnesium_sulfate",
    "sal_de_epsom": "magnesium_sulfate",
    "nitrato_de_potasio": "potassium_nitrate",
    "nitrato_potasio": "potassium_nitrate",
    "nitrato_de_calcio": "calcium_nitrate",
    "nitrato_calcio": "calcium_nitrate",
    "nitrato_de_magnesio": "magnesium_nitrate",
    "nitrato_magnesio": "magnesium_nitrate",
    "nitrato_de_amonio": "ammonium_nitrate",
    "nitrato_amonio": "ammonium_nitrate",
    "sulfato_de_amonio": "ammonium_sulfate",
    "sulfato_amonio": "ammonium_sulfate",
    "sulfato_de_potasio": "potassium_sulfate",
    "sulfato_potasio": "potassium_sulfate",
    "cloruro_de_potasio": "potassium_chloride",
    "cloruro_potasio": "potassium_chloride",
    "fosfato_monoamonico": "map",
    "fosfato_diamonico": "dap_18_46_0",
    "fosfonitrato": "fosfonitrato",
    "urea": "urea_46_0_0",
    "acido_fosforico": "phosphoric_acid_75",
    "acido_nitrico": "nitric_acid_70",
    "acido_sulfurico": "sulfuric_acid_98",
    "sulfuric_acid": "sulfuric_acid_98",
    "phosphoric_acid": "phosphoric_acid_75",
    "nitric_acid": "nitric_acid_70",
    "acido_sulfurico_h2so4": "sulfuric_acid_98",
    "acido_fosforico_h3po4": "phosphoric_acid_75",
    "acido_nitrico_hno3": "nitric_acid_70",
}

ACID_DEFAULT_PRICES = {
    "sulfuric_acid_98": {"MXN": 25.0, "USD": 1.45, "EUR": 1.33, "form": "liquid"},
    "sulfuric_acid": {"MXN": 25.0, "USD": 1.45, "EUR": 1.33, "form": "liquid"},
    "phosphoric_acid_75": {"MXN": 45.0, "USD": 2.60, "EUR": 2.40, "form": "liquid"},
    "phosphoric_acid": {"MXN": 45.0, "USD": 2.60, "EUR": 2.40, "form": "liquid"},
    "nitric_acid_70": {"MXN": 35.0, "USD": 2.00, "EUR": 1.85, "form": "liquid"},
    "nitric_acid": {"MXN": 35.0, "USD": 2.00, "EUR": 1.85, "form": "liquid"},
}


def get_fertilizer_price(
    fertilizer_id: str, 
    fertilizer_name: str, 
    currency: str = "MXN", 
    is_liquid: bool = False,
    price_map: dict = None
) -> float:
    """
    Get the price for a fertilizer from the pricing module.
    
    Priority order:
    1. User price_map (if provided) - respects user overrides
    2. DEFAULT_PRICES_BY_CURRENCY - module defaults
    
    Args:
        fertilizer_id: The fertilizer ID or slug
        fertilizer_name: The display name of the fertilizer
        currency: The currency code (default: MXN)
        is_liquid: Whether to return price per liter (for acids/liquids)
        price_map: Optional dict from build_price_map with user prices
    
    Returns:
        Price per kg (or per liter if is_liquid) in the specified currency, or 0 if not found
    """
    if not fertilizer_id and not fertilizer_name:
        return 0.0
    
    def get_from_price_map(pm: dict) -> float:
        """Extract price from price_map entry."""
        if is_liquid and pm.get("price_per_liter"):
            return pm["price_per_liter"]
        return pm.get("price_per_kg", 0) or 0
    
    # PRIORITY 1: Check user price_map first (includes user overrides)
    if price_map:
        # Build normalized key map for faster lookups
        normalized_price_map = {normalize_slug(k): v for k, v in price_map.items()}
        
        # Try exact match on fertilizer_id
        if fertilizer_id and fertilizer_id in price_map:
            return get_from_price_map(price_map[fertilizer_id])
        
        # Try normalized match on fertilizer_id
        if fertilizer_id:
            normalized_id = normalize_slug(fertilizer_id)
            if normalized_id in normalized_price_map:
                return get_from_price_map(normalized_price_map[normalized_id])
        
        # Try name mappings (Spanish → English) in user price_map
        if fertilizer_name:
            normalized_name = normalize_slug(fertilizer_name)
            for spanish_slug, english_key in NAME_TO_PRICE_ID.items():
                if spanish_slug in normalized_name or normalized_name in spanish_slug:
                    # Try exact english key
                    if english_key in price_map:
                        return get_from_price_map(price_map[english_key])
                    # Try normalized english key
                    norm_eng = normalize_slug(english_key)
                    if norm_eng in normalized_price_map:
                        return get_from_price_map(normalized_price_map[norm_eng])
        
        # Try partial match on normalized name in price_map
        if fertilizer_name:
            normalized_name = normalize_slug(fertilizer_name)
            for norm_key, pm in normalized_price_map.items():
                if norm_key in normalized_name or normalized_name in norm_key:
                    return get_from_price_map(pm)
    
    # PRIORITY 2: Fallback to DEFAULT_PRICES_BY_CURRENCY
    def get_price_from_data(price_data: dict) -> float:
        """Extract the correct price considering liquid/solid form."""
        base_price = price_data.get(currency, price_data.get("MXN", 0))
        if is_liquid and price_data.get("form") == "liquid":
            liter_factor = price_data.get("liter_factor", 1.0)
            return base_price * liter_factor
        return base_price
    
    # Try exact match first
    if fertilizer_id and fertilizer_id in DEFAULT_PRICES_BY_CURRENCY:
        return get_price_from_data(DEFAULT_PRICES_BY_CURRENCY[fertilizer_id])
    
    # Try lowercase/normalized match on ID
    if fertilizer_id:
        normalized_id = normalize_slug(fertilizer_id)
        for key, price_data in DEFAULT_PRICES_BY_CURRENCY.items():
            if normalize_slug(key) == normalized_id:
                return get_price_from_data(price_data)
    
    # Try matching by name using mappings
    if fertilizer_name:
        normalized_name = normalize_slug(fertilizer_name)
        
        # Check direct mappings
        for spanish_slug, english_key in NAME_TO_PRICE_ID.items():
            if spanish_slug in normalized_name or normalized_name in spanish_slug:
                if english_key in DEFAULT_PRICES_BY_CURRENCY:
                    return get_price_from_data(DEFAULT_PRICES_BY_CURRENCY[english_key])
        
        # Try partial match in DEFAULT_PRICES_BY_CURRENCY
        for key, price_data in DEFAULT_PRICES_BY_CURRENCY.items():
            normalized_key = normalize_slug(key)
            if normalized_key in normalized_name or normalized_name in normalized_key:
                return get_price_from_data(price_data)
    
    # PRIORITY 3: Check ACID_DEFAULT_PRICES for acids
    if fertilizer_id:
        # Direct match
        if fertilizer_id in ACID_DEFAULT_PRICES:
            return get_price_from_data(ACID_DEFAULT_PRICES[fertilizer_id])
        # Check name mapping
        mapped_id = NAME_TO_PRICE_ID.get(normalize_slug(fertilizer_id))
        if mapped_id and mapped_id in ACID_DEFAULT_PRICES:
            return get_price_from_data(ACID_DEFAULT_PRICES[mapped_id])
    
    if fertilizer_name:
        normalized_name = normalize_slug(fertilizer_name)
        # Check if name maps to an acid
        for slug, mapped_id in NAME_TO_PRICE_ID.items():
            if slug in normalized_name or normalized_name in slug:
                if mapped_id in ACID_DEFAULT_PRICES:
                    return get_price_from_data(ACID_DEFAULT_PRICES[mapped_id])
        # Partial match in acid prices
        for acid_id, price_data in ACID_DEFAULT_PRICES.items():
            if normalize_slug(acid_id) in normalized_name or normalized_name in normalize_slug(acid_id):
                return get_price_from_data(price_data)
    
    logger.debug(f"No price found for fertilizer: {fertilizer_id} / {fertilizer_name}")
    return 0.0

CURRENCY_SYMBOLS = {
    'MXN': '$',
    'USD': 'US$',
    'EUR': '€',
    'BRL': 'R$',
    'PEN': 'S/',
    'ARS': 'AR$',
    'CLP': 'CLP$',
    'COP': 'COP$'
}

def get_currency_symbol(currency) -> str:
    """Get the symbol for a currency code."""
    if isinstance(currency, dict):
        currency = currency.get('code', 'MXN')
    if not isinstance(currency, str):
        currency = 'MXN'
    return CURRENCY_SYMBOLS.get(currency, '$')

FERTIRRIEGO_COLOR = HexColor("#10b981")
PRIMARY_COLOR = HexColor("#1e3a5f")
SECONDARY_COLOR = HexColor("#059669")
SUCCESS_COLOR = HexColor("#22c55e")
WARNING_COLOR = HexColor("#f59e0b")
DANGER_COLOR = HexColor("#ef4444")
TEXT_COLOR = HexColor("#374151")
LIGHT_BG = HexColor("#f0fdf4")
HEADER_BG = HexColor("#d1fae5")


def create_fertiirrigation_pdf_report(
    calculation: Dict[str, Any],
    user_name: str = "Usuario",
    include_optimization: bool = False,
    optimization_result: Optional[Dict[str, Any]] = None
) -> bytes:
    """
    Generate a professional PDF report for fertigation calculation.
    
    Args:
        calculation: The fertigation calculation result
        user_name: Name of the user
        include_optimization: Whether to include optimization results
        optimization_result: The optimization results (3 profiles)
    
    Returns:
        PDF file as bytes
    """
    buffer = io.BytesIO()
    
    branding = PDFBrandingContext()
    
    def header_footer(canvas, doc):
        draw_professional_letterhead(
            canvas, doc, branding,
            report_title="REPORTE DE FERTIRRIEGO",
            folio=f"FR-{calculation.get('id', '0'):05d}",
            module_color=FERTIRRIEGO_COLOR
        )
        draw_professional_footer(canvas, doc, branding)
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.6*inch,
        leftMargin=0.6*inch,
        topMargin=1.35*inch,
        bottomMargin=0.6*inch
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=16,
        textColor=FERTIRRIEGO_COLOR,
        spaceAfter=6,
        spaceBefore=0,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=FERTIRRIEGO_COLOR,
        spaceBefore=8,
        spaceAfter=4
    )
    
    subheading_style = ParagraphStyle(
        'SubHeading',
        parent=styles['Heading3'],
        fontSize=10,
        textColor=SECONDARY_COLOR,
        spaceBefore=6,
        spaceAfter=3
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=8,
        textColor=TEXT_COLOR,
        spaceAfter=3
    )
    
    small_style = ParagraphStyle(
        'SmallText',
        parent=styles['Normal'],
        fontSize=7,
        textColor=TEXT_COLOR,
        spaceAfter=2
    )
    
    story = []
    
    story.append(Paragraph("PROGRAMA DE FERTILIZACIÓN", title_style))
    story.append(Spacer(1, 4))
    
    calc_name = calculation.get('name', 'Cálculo de FertiRiego')
    created_at = calculation.get('created_at', datetime.now())
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    date_str = created_at.strftime("%d/%m/%Y %H:%M") if created_at else datetime.now().strftime("%d/%m/%Y")
    
    header_data = [
        ["Nombre:", calc_name, "Fecha:", date_str],
        ["Usuario:", user_name, "Generado por:", "AgriDoser"],
    ]
    
    header_table = Table(header_data, colWidths=[0.9*inch, 2.5*inch, 0.85*inch, 2.5*inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_BG),
        ('BACKGROUND', (2, 0), (2, -1), LIGHT_BG),
        ('TEXTCOLOR', (0, 0), (-1, -1), TEXT_COLOR),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#d1d5db")),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))
    
    result = calculation.get('result', calculation)
    
    exec_currency = result.get('currency', 'MXN')
    exec_symbol = get_currency_symbol(exec_currency)
    exec_crop = result.get('crop_name', calculation.get('crop_name', 'Cultivo'))
    exec_area = result.get('area_ha', calculation.get('area_ha', 1.0))
    exec_apps = result.get('num_applications', calculation.get('num_applications', 10))
    
    fertilizer_program = result.get('fertilizer_program', [])
    price_map = calculation.get('price_map', {})
    
    # ============================================
    # UNIFIED COST CALCULATION (for entire PDF)
    # ============================================
    # Calculate fertilizer costs by consolidating and applying current prices
    consolidated_ferts_for_cost = {}
    for fd in fertilizer_program:
        name = fd.get('fertilizer_name', '')
        fert_id = fd.get('fertilizer_id', fd.get('id', fd.get('slug', '')))
        if name in consolidated_ferts_for_cost:
            consolidated_ferts_for_cost[name]['dose_kg_ha'] += fd.get('dose_kg_ha', 0)
            consolidated_ferts_for_cost[name]['cost_total'] += fd.get('cost_total', fd.get('cost_ha', 0))
        else:
            consolidated_ferts_for_cost[name] = {
                'fertilizer_name': name,  # Include name for price lookup
                'fertilizer_id': fert_id,
                'dose_kg_ha': fd.get('dose_kg_ha', 0),
                'cost_total': fd.get('cost_total', fd.get('cost_ha', 0)),
                'price_per_kg': fd.get('price_per_kg', 0),
            }
    
    unified_fert_cost = 0.0
    for fert in consolidated_ferts_for_cost.values():
        fert_name = fert.get('fertilizer_name', '')
        fert_id = fert.get('fertilizer_id', '')
        dose_per_ha = fert.get('dose_kg_ha', 0)
        original_cost = fert.get('cost_total', 0)
        original_price = fert.get('price_per_kg', 0)
        
        # Pass name for user price lookup (same as shopping list)
        price_kg = get_fertilizer_price(fert_id, fert_name, exec_currency, is_liquid=False, price_map=price_map)
        if price_kg == 0 and original_price > 0:
            price_kg = original_price
        
        total_dose = dose_per_ha * exec_area
        if price_kg > 0:
            unified_fert_cost += price_kg * total_dose
        else:
            unified_fert_cost += original_cost * exec_area
    
    # Calculate acid cost (supports single acid or multiple acids from optimizer)
    acid_treatment_temp = result.get('acid_treatment')
    acid_program = result.get('acid_program')
    unified_acid_cost = 0.0
    water_volume_1000L = calculation.get('water_volume_1000L', result.get('water_volume_1000L', 4))
    
    # Check for multi-acid structure from optimizer (acids array)
    if acid_program and acid_program.get('acids'):
        # Multi-acid from optimizer - use pre-calculated total_cost from optimizer
        # The optimizer's total_cost is already the full project cost
        for acid in acid_program.get('acids', []):
            # Prefer optimizer's total_cost as it's already calculated for the entire scenario
            if acid.get('total_cost', 0) > 0:
                unified_acid_cost += acid.get('total_cost', 0)
            else:
                # Fallback: calculate from dose and price
                acid_id = acid.get('acid_id', '')
                acid_name = acid.get('acid_name', '')
                ml_per_1000L = acid.get('dose_ml_per_1000L', 0)
                volume_l_per_app = (ml_per_1000L / 1000.0) * water_volume_1000L
                acid_vol_per_ha = volume_l_per_app * exec_apps
                
                acid_price = get_fertilizer_price(acid_id, acid_name, exec_currency, is_liquid=True, price_map=price_map)
                acid_vol_total = acid_vol_per_ha * exec_area
                if acid_price > 0:
                    unified_acid_cost += acid_price * acid_vol_total
    elif not acid_treatment_temp and acid_program:
        # Single acid from acid_program (legacy optimizer format)
        ml_per_1000L = acid_program.get('ml_per_1000L', 0)
        volume_l_per_app = (ml_per_1000L / 1000.0) * water_volume_1000L
        volume_l_ha = volume_l_per_app * exec_apps
        acid_treatment_temp = {
            'acid_id': acid_program.get('acid_id', ''),
            'acid_name': acid_program.get('acid_name', ''),
            'volume_l_ha': volume_l_ha,
            'cost_per_1000L': acid_program.get('cost_per_1000L', 0),
            'price_per_l': 0,
            'cost_total': 0,
        }
    
    # Handle single acid from acid_treatment or converted acid_program
    if unified_acid_cost == 0 and acid_treatment_temp:
        acid_id = acid_treatment_temp.get('acid_id', acid_treatment_temp.get('acid_type', ''))
        acid_name = acid_treatment_temp.get('acid_name', '')
        acid_vol_per_ha = acid_treatment_temp.get('volume_l_ha', 0)
        original_acid_cost = acid_treatment_temp.get('cost_total', acid_treatment_temp.get('cost_l_ha', 0) * acid_vol_per_ha)
        original_acid_price = acid_treatment_temp.get('price_per_l', 0)
        
        acid_price = get_fertilizer_price(acid_id, acid_name, exec_currency, is_liquid=True, price_map=price_map)
        if acid_price == 0 and original_acid_price > 0:
            acid_price = original_acid_price
        
        acid_vol_total = acid_vol_per_ha * exec_area
        if acid_price > 0:
            unified_acid_cost = acid_price * acid_vol_total
        elif original_acid_cost > 0:
            unified_acid_cost = original_acid_cost * exec_area
    
    # UNIFIED TOTAL COST (used throughout the PDF)
    unified_total_cost = unified_fert_cost + unified_acid_cost
    unified_cost_per_ha = unified_total_cost / exec_area if exec_area > 0 else 0
    unified_cost_per_app = unified_total_cost / exec_apps if exec_apps > 0 else 0
    
    # Calculate fertilizer percentage
    fert_pct = (unified_fert_cost / unified_total_cost * 100) if unified_total_cost > 0 else 0
    acid_pct = (unified_acid_cost / unified_total_cost * 100) if unified_total_cost > 0 else 0
    
    exec_total_cost = unified_total_cost  # Use unified cost for header
    exec_total_dose = sum(fd.get('dose_kg_ha', 0) for fd in fertilizer_program)
    unique_fert_count = len(set(fd.get('fertilizer_name', '') for fd in fertilizer_program))
    
    exec_summary_style = ParagraphStyle(
        'ExecSummary',
        parent=styles['Normal'],
        fontSize=10,
        textColor=PRIMARY_COLOR,
        alignment=TA_CENTER,
        spaceAfter=5
    )
    
    summary_value_style = ParagraphStyle(
        'SummaryValue',
        parent=styles['Normal'],
        fontSize=11,
        textColor=HexColor("#ffffff"),
        alignment=TA_CENTER
    )
    summary_label_style = ParagraphStyle(
        'SummaryLabel',
        parent=styles['Normal'],
        fontSize=8,
        textColor=TEXT_COLOR,
        alignment=TA_CENTER
    )
    
    summary_data = [
        [
            Paragraph(f"<b>{exec_crop}</b>", summary_value_style),
            Paragraph(f"<b>{exec_area} ha</b>", summary_value_style),
            Paragraph(f"<b>{exec_apps} riegos</b>", summary_value_style),
            Paragraph(f"<b>{exec_symbol}{exec_total_cost:,.2f} {exec_currency}</b>", summary_value_style)
        ],
        [
            Paragraph("Cultivo", summary_label_style),
            Paragraph("Superficie", summary_label_style),
            Paragraph("Aplicaciones", summary_label_style),
            Paragraph("COSTO TOTAL", summary_label_style)
        ]
    ]
    
    summary_table = Table(summary_data, colWidths=[1.7*inch, 1.4*inch, 1.4*inch, 2.2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), FERTIRRIEGO_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#ffffff")),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, 1), 7),
        ('TEXTCOLOR', (0, 1), (-1, 1), TEXT_COLOR),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#d1d5db")),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('BACKGROUND', (0, 1), (-1, 1), LIGHT_BG),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))
    
    # === RESUMEN FINANCIERO (NEW UNIFIED COST BREAKDOWN) ===
    if unified_total_cost > 0:
        story.append(Paragraph("RESUMEN FINANCIERO", heading_style))
        story.append(Paragraph(
            "Desglose de la inversión total del programa de fertilización.",
            small_style
        ))
        story.append(Spacer(1, 4))
        
        finance_value_style = ParagraphStyle(
            'FinanceValue',
            parent=styles['Normal'],
            fontSize=9,
            textColor=TEXT_COLOR,
            alignment=TA_RIGHT
        )
        finance_label_style = ParagraphStyle(
            'FinanceLabel',
            parent=styles['Normal'],
            fontSize=9,
            textColor=TEXT_COLOR,
            alignment=TA_LEFT
        )
        finance_pct_style = ParagraphStyle(
            'FinancePct',
            parent=styles['Normal'],
            fontSize=8,
            textColor=HexColor("#6b7280"),
            alignment=TA_CENTER
        )
        
        finance_data = []
        
        # Fertilizers row
        if unified_fert_cost > 0:
            finance_data.append([
                Paragraph("Fertilizantes:", finance_label_style),
                Paragraph(f"{exec_symbol}{unified_fert_cost:,.2f}", finance_value_style),
                Paragraph(f"({fert_pct:.0f}%)", finance_pct_style)
            ])
        
        # Acid row
        if unified_acid_cost > 0:
            finance_data.append([
                Paragraph("Tratamiento con ácido:", finance_label_style),
                Paragraph(f"{exec_symbol}{unified_acid_cost:,.2f}", finance_value_style),
                Paragraph(f"({acid_pct:.0f}%)", finance_pct_style)
            ])
        
        # Total row
        finance_data.append([
            Paragraph("<b>TOTAL PROGRAMA:</b>", finance_label_style),
            Paragraph(f"<b>{exec_symbol}{unified_total_cost:,.2f}</b>", finance_value_style),
            Paragraph("", finance_pct_style)
        ])
        
        # Cost per ha row
        finance_data.append([
            Paragraph("Costo por hectárea:", finance_label_style),
            Paragraph(f"{exec_symbol}{unified_cost_per_ha:,.2f}/ha", finance_value_style),
            Paragraph("", finance_pct_style)
        ])
        
        # Cost per application row
        finance_data.append([
            Paragraph("Costo por riego:", finance_label_style),
            Paragraph(f"{exec_symbol}{unified_cost_per_app:,.2f}/aplicación", finance_value_style),
            Paragraph("", finance_pct_style)
        ])
        
        finance_table = Table(finance_data, colWidths=[2.5*inch, 1.8*inch, 0.8*inch])
        finance_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor("#f0fdf4")),
            ('TEXTCOLOR', (0, 0), (-1, -1), TEXT_COLOR),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#d1d5db")),
            ('PADDING', (0, 0), (-1, -1), 6),
            # Style for total row
            ('BACKGROUND', (0, -3), (-1, -3), HexColor("#dcfce7")),
            ('FONTNAME', (0, -3), (-1, -3), 'Helvetica-Bold'),
            # Subtle divider before totals
            ('LINEABOVE', (0, -3), (-1, -3), 1, HexColor("#059669")),
        ]))
        story.append(finance_table)
        story.append(Spacer(1, 10))

    # === EXECUTIVE SUMMARY ===
    exec_crop = calculation.get('crop_name') or calculation.get('crop', {}).get('crop_name') or result.get('crop_name')
    exec_stage = calculation.get('growth_stage') or calculation.get('crop', {}).get('growth_stage') or result.get('growth_stage')
    exec_yield = calculation.get('yield_target_ton_ha') or calculation.get('crop', {}).get('yield_target_ton_ha')
    exec_num_apps = calculation.get('num_applications', result.get('num_applications', 10))
    exec_balance = result.get('nutrient_balance', [])
    top_deficits = sorted(
        [
            (nb.get('nutrient', ''), nb.get('deficit_kg_ha', 0))
            for nb in exec_balance
            if nb.get('deficit_kg_ha', 0) > 0
        ],
        key=lambda item: item[1],
        reverse=True,
    )[:3]

    story.append(Paragraph("RESUMEN EJECUTIVO", heading_style))
    exec_rows = [
        ["Cultivo", exec_crop or "N/A", "Etapa", exec_stage or "N/A"],
        ["Meta de rendimiento", f"{exec_yield} t/ha" if exec_yield else "N/A", "Aplicaciones", str(exec_num_apps)],
    ]
    if top_deficits:
        deficit_text = ", ".join([f"{nutr}: {val:.1f} kg/ha" for nutr, val in top_deficits])
    else:
        deficit_text = "Sin déficits relevantes en esta etapa."
    exec_rows.append(["Déficits críticos", deficit_text, "Unidades", "kg/ha (etapa actual)"])

    exec_table = Table(exec_rows, colWidths=[1.3*inch, 2.4*inch, 1.0*inch, 1.6*inch])
    exec_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor("#f8fafc")),
        ('TEXTCOLOR', (0, 0), (-1, -1), TEXT_COLOR),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor("#e2e8f0")),
    ]))
    story.append(exec_table)
    story.append(Paragraph(
        "Referencia: los aportes y déficits se reportan por etapa. Por riego = total / Nº aplicaciones.",
        small_style
    ))
    story.append(Spacer(1, 10))
    
    # === SHOPPING LIST SECTION (NEW - Similar to Hydroponics) ===
    result = calculation.get('result', calculation)
    fertilizer_program = result.get('fertilizer_program', [])
    
    # Support both acid_treatment (legacy) and acid_program (optimizer output)
    acid_treatment = result.get('acid_treatment')
    acid_program = result.get('acid_program')
    
    # Normalize acid data from acid_program if acid_treatment is not present
    if not acid_treatment and acid_program:
        # acid_program structure: acid_id, acid_name, ml_per_1000L, cost_per_1000L, nutrient_contribution
        # Convert to acid_treatment format for consistent processing
        ml_per_1000L = acid_program.get('ml_per_1000L', 0)
        # water_volume_1000L is the volume of water PER APPLICATION in thousands of liters (e.g., 4 = 4000L)
        water_volume_1000L = calculation.get('water_volume_1000L', result.get('water_volume_1000L', 4))
        num_apps = result.get('num_applications', calculation.get('num_applications', 10))
        area = result.get('area_ha', calculation.get('area_ha', 1.0))
        
        # Calculate volume_l_ha:
        # ml_per_1000L = ml of acid per 1000L of water
        # water_volume_1000L = thousands of liters per application (so water_volume_1000L * 1000 = actual liters)
        # volume_l_per_app = (ml_per_1000L / 1000) * (water_volume_1000L * 1000 / 1000)
        #                  = (ml_per_1000L / 1000) * water_volume_1000L (liters per application)
        volume_l_per_app = (ml_per_1000L / 1000.0) * water_volume_1000L  # L per application
        volume_l_ha = volume_l_per_app * num_apps  # Total L for all applications
        
        acid_treatment = {
            'acid_id': acid_program.get('acid_id', ''),
            'acid_name': acid_program.get('acid_name', ''),
            'acid_type': acid_program.get('acid_id', ''),
            'ml_per_1000L': ml_per_1000L,
            'volume_l_ha': volume_l_ha,
            'cost_per_1000L': acid_program.get('cost_per_1000L', 0),
            'nutrient_contribution': acid_program.get('nutrient_contribution', {}),
            'nutrient_in_kg_ha': True,
        }
    
    # Use user's preferred currency if available
    currency = calculation.get('user_currency', result.get('currency', 'MXN'))
    symbol = get_currency_symbol(currency)
    num_applications = result.get('num_applications', calculation.get('num_applications', 10))
    area_ha = result.get('area_ha', calculation.get('area_ha', 1.0))
    # Get price_map from calculation (passed from endpoint with user prices)
    price_map = calculation.get('price_map', {})
    
    # Check if we have valid fertilizer data
    has_fertilizers = len(fertilizer_program) > 0
    has_acid = acid_treatment and (
        acid_treatment.get('acid_name') or 
        acid_treatment.get('ml_per_1000L', 0) > 0 or
        acid_treatment.get('volume_l_ha', 0) > 0
    )
    
    if has_fertilizers or has_acid:
        story.append(Paragraph("LISTA DE COMPRAS", heading_style))
        story.append(Paragraph(
            f"Resumen de productos necesarios para {area_ha} ha en {num_applications} aplicaciones.",
            small_style
        ))
        story.append(Spacer(1, 4))
        
        shopping_data = [["Producto", "Tipo", "Cantidad Total", "Precio Unit.", "Costo Total"]]
        grand_total = 0.0
        
        # Consolidate fertilizers
        consolidated_ferts = {}
        for fd in fertilizer_program:
            name = fd.get('fertilizer_name', '')
            fert_id = fd.get('fertilizer_id', fd.get('id', fd.get('slug', '')))
            if name in consolidated_ferts:
                consolidated_ferts[name]['dose_kg_ha'] += fd.get('dose_kg_ha', 0)
                consolidated_ferts[name]['cost_total'] += fd.get('cost_total', fd.get('cost_ha', 0))
            else:
                consolidated_ferts[name] = {
                    'fertilizer_name': name,
                    'fertilizer_id': fert_id,
                    'dose_kg_ha': fd.get('dose_kg_ha', 0),
                    'cost_total': fd.get('cost_total', fd.get('cost_ha', 0)),
                    'price_per_kg': fd.get('price_per_kg', 0),
                }
        
        for fert in consolidated_ferts.values():
            name = fert.get('fertilizer_name', '')
            fert_id = fert.get('fertilizer_id', '')
            dose_per_ha = fert.get('dose_kg_ha', 0)
            original_cost = fert.get('cost_total', fert.get('cost_ha', 0))
            original_price = fert.get('price_per_kg', 0)
            
            # Get price from the Fertilizer Prices module (user prices first, then defaults)
            price_kg = get_fertilizer_price(fert_id, name, currency, is_liquid=False, price_map=price_map)
            
            # Fallback: use original price if pricing module returns 0
            if price_kg == 0 and original_price > 0:
                price_kg = original_price
            
            # Scale by area for total quantities
            total_dose = dose_per_ha * area_ha
            
            # Calculate cost: prefer module price, fallback to original cost
            if price_kg > 0:
                total_cost = price_kg * total_dose
            else:
                total_cost = original_cost * area_ha
                if dose_per_ha > 0:
                    price_kg = original_cost / dose_per_ha
            
            grand_total += total_cost
            shopping_data.append([
                name,
                "Fertilizante",
                f"{total_dose:.1f} kg",
                f"{symbol}{price_kg:.2f}/kg",
                f"{symbol}{total_cost:,.2f}"
            ])
        
        # Add acid if present
        if has_acid:
            acid_name = acid_treatment.get('acid_name', 'Ácido')
            acid_id = acid_treatment.get('acid_id', acid_treatment.get('acid_type', ''))
            acid_vol_per_ha = acid_treatment.get('volume_l_ha', 0)
            original_acid_cost = acid_treatment.get('cost_total', acid_treatment.get('cost_l_ha', 0) * acid_vol_per_ha)
            original_acid_price = acid_treatment.get('price_per_l', 0)
            
            # Get acid price from pricing module (is_liquid=True for L conversion)
            acid_price = get_fertilizer_price(acid_id, acid_name, currency, is_liquid=True, price_map=price_map)
            
            # Fallback: use original price if pricing module returns 0
            if acid_price == 0 and original_acid_price > 0:
                acid_price = original_acid_price
            
            # Scale by area for total quantities
            acid_vol_total = acid_vol_per_ha * area_ha
            
            # Calculate cost: prefer module price, fallback to original cost
            if acid_price > 0:
                acid_cost_total = acid_price * acid_vol_total
            else:
                acid_cost_total = original_acid_cost * area_ha
                if acid_vol_per_ha > 0:
                    acid_price = original_acid_cost / acid_vol_per_ha
            
            grand_total += acid_cost_total
            shopping_data.append([
                acid_name,
                "Ácido",
                f"{acid_vol_total:.2f} L",
                f"{symbol}{acid_price:.2f}/L",
                f"{symbol}{acid_cost_total:,.2f}"
            ])
        
        # Total row - use unified_total_cost for consistency with header
        shopping_data.append([
            "TOTAL", "", "", "", f"{symbol}{unified_total_cost:,.2f}"
        ])
        
        shopping_table = Table(shopping_data, colWidths=[2.4*inch, 0.9*inch, 1.0*inch, 1.0*inch, 1.0*inch])
        shopping_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor("#059669")),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#ffffff")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#d1d5db")),
            ('PADDING', (0, 0), (-1, -1), 3),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [HexColor("#ffffff"), LIGHT_BG]),
            ('BACKGROUND', (0, -1), (-1, -1), HexColor("#dcfce7")),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        story.append(shopping_table)
        story.append(Spacer(1, 10))
    
    # === ACID TREATMENT SECTION (NEW) ===
    if has_acid:
        story.append(Paragraph("TRATAMIENTO CON ÁCIDO", heading_style))
        story.append(Paragraph(
            "Información del ácido utilizado para neutralización de bicarbonatos y/o aporte nutricional.",
            small_style
        ))
        story.append(Spacer(1, 4))
        
        acid_name = acid_treatment.get('acid_name', 'Ácido')
        acid_id = acid_treatment.get('acid_id', acid_treatment.get('acid_type', ''))
        acid_vol_per_ha = acid_treatment.get('volume_l_ha', 0)
        acid_vol_total = acid_vol_per_ha * area_ha
        acid_vol_per_app = acid_vol_total / num_applications if num_applications > 0 else acid_vol_total
        ml_per_1000L = acid_treatment.get('ml_per_1000L', 0)
        
        # Support both legacy fields (n_kg_ha, p2o5_kg_ha, s_kg_ha) and new nutrient_contribution dict
        nutrient_contrib = acid_treatment.get('nutrient_contribution', {})
        nutrient_in_kg_ha = acid_treatment.get('nutrient_in_kg_ha', False)
        
        if nutrient_contrib and nutrient_in_kg_ha:
            # New optimizer format: nutrient_contribution already contains values in kg/ha
            acid_n = nutrient_contrib.get('N', nutrient_contrib.get('NO3_N', 0)) * area_ha
            acid_p = nutrient_contrib.get('P', nutrient_contrib.get('P2O5', 0)) * area_ha
            acid_s = nutrient_contrib.get('S', nutrient_contrib.get('SO4_S', 0)) * area_ha
        elif nutrient_contrib:
            # Legacy format: nutrient_contribution contains values in g/1000L of water
            # To convert to total kg for all area:
            # 1. water_vol_1000L = thousands of liters per application per ha (e.g., 4 means 4000L/ha/app)
            # 2. Total water per ha = water_vol_1000L * num_applications (in 1000L units)
            # 3. Total water for all area = total_water_per_ha * area_ha
            # 4. g/1000L * (total 1000L units) / 1000 = kg
            water_vol_1000L = calculation.get('water_volume_1000L', result.get('water_volume_1000L', 4))
            total_water_1000L = water_vol_1000L * num_applications * area_ha  # Total water in 1000L units for all area
            acid_n = (nutrient_contrib.get('N', nutrient_contrib.get('NO3_N', 0)) * total_water_1000L) / 1000.0
            acid_p = (nutrient_contrib.get('P', nutrient_contrib.get('P2O5', 0)) * total_water_1000L) / 1000.0
            acid_s = (nutrient_contrib.get('S', nutrient_contrib.get('SO4_S', 0)) * total_water_1000L) / 1000.0
        else:
            acid_n = acid_treatment.get('n_kg_ha', 0) * area_ha
            acid_p = acid_treatment.get('p2o5_kg_ha', 0) * area_ha
            acid_s = acid_treatment.get('s_kg_ha', 0) * area_ha
        
        # Get acid price from pricing module with fallback
        original_acid_cost = acid_treatment.get('cost_total', acid_treatment.get('cost_l_ha', 0) * acid_vol_per_ha)
        original_acid_price = acid_treatment.get('price_per_l', 0)
        acid_price_per_l = get_fertilizer_price(acid_id, acid_name, currency, is_liquid=True, price_map=price_map)
        
        # Fallback: use original price if pricing module returns 0
        if acid_price_per_l == 0 and original_acid_price > 0:
            acid_price_per_l = original_acid_price
        
        # Calculate cost with fallback
        if acid_price_per_l > 0:
            acid_cost_total = acid_price_per_l * acid_vol_total
        else:
            acid_cost_total = original_acid_cost * area_ha
        
        acid_info_data = [
            ["Ácido utilizado:", acid_name],
        ]
        
        # Add ml/1000L if available (from acid_program)
        if ml_per_1000L > 0:
            acid_info_data.append(["Dosis de inyección:", f"{ml_per_1000L:.1f} ml/1000L de agua"])
        
        acid_info_data.extend([
            ["Dosis por hectárea:", f"{acid_vol_per_ha:.2f} L/ha"],
            ["Dosis total ({:.1f} ha):".format(area_ha), f"{acid_vol_total:.2f} L"],
            ["Dosis por riego:", f"{acid_vol_per_app:.3f} L/aplicación"],
        ])
        
        # Add nutrient contributions (total for all area)
        if acid_n > 0:
            acid_info_data.append(["Aporte de N:", f"{acid_n:.2f} kg (total)"])
        if acid_p > 0:
            acid_info_data.append(["Aporte de P₂O₅:", f"{acid_p:.2f} kg (total)"])
        if acid_s > 0:
            acid_info_data.append(["Aporte de S:", f"{acid_s:.2f} kg (total)"])
        
        if acid_cost_total > 0:
            acid_info_data.append(["Costo total:", f"{symbol}{acid_cost_total:,.2f}"])
        
        acid_info_table = Table(acid_info_data, colWidths=[1.6*inch, 3.5*inch])
        acid_info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), HexColor("#fef3c7")),
            ('TEXTCOLOR', (0, 0), (-1, -1), TEXT_COLOR),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#fcd34d")),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(acid_info_table)
        story.append(Spacer(1, 4))
        
        # Acid safety warning
        acid_warning_style = ParagraphStyle(
            'AcidWarning',
            parent=small_style,
            textColor=HexColor("#b45309"),
            backColor=HexColor("#fffbeb"),
        )
        story.append(Paragraph(
            "<b>⚠ PRECAUCIÓN:</b> Usar guantes de nitrilo y gafas de protección. "
            "SIEMPRE agregar ácido al agua, NUNCA al revés. Trabajar en área ventilada.",
            acid_warning_style
        ))
        story.append(Spacer(1, 10))
    
    story.append(Paragraph("PARÁMETROS DE ENTRADA", heading_style))
    
    soil_info = calculation.get('soil_analysis_name', 'Análisis de suelo')
    water_info = calculation.get('water_analysis_name', 'Agua de riego')
    crop_info = result.get('crop_name', calculation.get('crop_name', 'Cultivo'))
    area_ha = result.get('area_ha', calculation.get('area_ha', 1.0))
    num_apps = result.get('num_applications', calculation.get('num_applications', 10))
    
    extraction_info = calculation.get('extraction_curve_info', {})
    extraction_crop_name = extraction_info.get('crop_name')
    extraction_stage_name = extraction_info.get('stage_name')
    extraction_percentages = extraction_info.get('percentages', {})
    extraction_stage_duration = extraction_info.get('duration_days')

    irrigation_frequency_days = result.get(
        'irrigation_frequency_days',
        calculation.get('irrigation_frequency_days', calculation.get('irrigation', {}).get('irrigation_frequency_days'))
    )
    irrigation_volume_m3_ha = result.get(
        'irrigation_volume_m3_ha',
        calculation.get('irrigation_volume_m3_ha', calculation.get('irrigation', {}).get('irrigation_volume_m3_ha'))
    )
    
    params_data = [
        ["Análisis de Suelo:", soil_info],
        ["Análisis de Agua:", water_info],
        ["Cultivo:", crop_info],
        ["Área:", f"{area_ha} ha"],
        ["Aplicaciones:", str(num_apps)],
    ]

    if irrigation_frequency_days:
        params_data.append(["Frecuencia de riego:", f"{irrigation_frequency_days} días"])
    if irrigation_volume_m3_ha:
        params_data.append(["Volumen por riego:", f"{irrigation_volume_m3_ha} m³/ha"])
    if irrigation_frequency_days and num_apps:
        params_data.append(["Recomendación de riegos:", f"{num_apps} riegos cada {irrigation_frequency_days} días"])

    if extraction_crop_name and extraction_stage_name:
        params_data.append(["Curva Extracción:", f"{extraction_crop_name} - {extraction_stage_name}"])
        if extraction_stage_duration:
            if isinstance(extraction_stage_duration, dict):
                min_days = extraction_stage_duration.get('min')
                max_days = extraction_stage_duration.get('max')
                if min_days is not None and max_days is not None:
                    duration_label = f"{min_days}-{max_days} días"
                else:
                    duration_label = str(extraction_stage_duration)
            else:
                duration_label = str(extraction_stage_duration)
            params_data.append(["Duración de etapa:", duration_label])
    
    params_table = Table(params_data, colWidths=[1.6*inch, 5.1*inch])
    params_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, -1), TEXT_COLOR),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#d1d5db")),
        ('PADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(params_table)
    story.append(Spacer(1, 8))
    
    if extraction_crop_name and extraction_stage_name and extraction_percentages:
        story.append(Paragraph("CURVA DE EXTRACCIÓN", heading_style))
        
        norm_pct = {k.upper(): v for k, v in extraction_percentages.items()}
        curve_headers = []
        curve_values = []
        
        nutrients_to_show = [("N", "N"), ("P2O5", "P2O5"), ("K2O", "K2O"), ("CA", "Ca"), ("MG", "Mg"), ("S", "S")]
        for key, display in nutrients_to_show:
            val = norm_pct.get(key, 0)
            if val > 0:
                curve_headers.append(display)
                curve_values.append(f"{val}%")
        
        if curve_headers:
            curve_data = [curve_headers, curve_values]
            col_width = 6.7 * inch / len(curve_headers)
            curve_table = Table(curve_data, colWidths=[col_width] * len(curve_headers))
            curve_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor("#22c55e")),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#ffffff")),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#d1d5db")),
                ('PADDING', (0, 0), (-1, -1), 4),
                ('BACKGROUND', (0, 1), (-1, 1), HexColor("#f0fdf4")),
            ]))
            story.append(curve_table)
            story.append(Spacer(1, 8))
    
    story.append(Paragraph("BALANCE NUTRICIONAL", heading_style))
    story.append(Paragraph(
        f"<i>Requerimientos y aportes para la etapa: {extraction_stage_name or 'General'}</i>",
        small_style
    ))
    story.append(Spacer(1, 4))
    
    nutrient_balance = result.get('nutrient_balance', [])
    
    def normalize_nutrient_name(name):
        """Normalize nutrient name by removing all Unicode subscripts and standardizing."""
        if not name:
            return ''
        subscript_map = {'₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4', 
                        '₅': '5', '₆': '6', '₇': '7', '₈': '8', '₉': '9'}
        normalized = name.upper()
        for sub, num in subscript_map.items():
            normalized = normalized.replace(sub, num)
        return normalized.replace(' ', '')
    
    def get_nutrient_total(balance, nutrient_name, fallback_key=None):
        """Get fertilizer_needed_kg_ha for a specific nutrient with fallback to result totals."""
        target = normalize_nutrient_name(nutrient_name)
        for nb in balance:
            current = normalize_nutrient_name(nb.get('nutrient', ''))
            if current == target:
                return round(nb.get('fertilizer_needed_kg_ha', 0), 2)
        if fallback_key:
            return result.get(fallback_key, 0)
        return 0
    
    n_total = get_nutrient_total(nutrient_balance, 'N', 'total_n_kg_ha')
    p_total = get_nutrient_total(nutrient_balance, 'P2O5', 'total_p2o5_kg_ha')
    k_total = get_nutrient_total(nutrient_balance, 'K2O', 'total_k2o_kg_ha')
    ca_total = get_nutrient_total(nutrient_balance, 'Ca', 'total_ca_kg_ha')
    mg_total = get_nutrient_total(nutrient_balance, 'Mg', 'total_mg_kg_ha')
    s_total = get_nutrient_total(nutrient_balance, 'S', 'total_s_kg_ha')
    
    # Simplified balance table: Nutrient, Requirement, Soil, Water, Deficit
    nutrients_data = [
        ["Nutriente", "Requerimiento\n(kg/ha)", "Aporte Suelo\n(kg/ha)", "Aporte Agua\n(kg/ha)", "Déficit\n(kg/ha)"],
    ]
    for nb in nutrient_balance:
        soil_val = nb.get('soil_contribution_kg_ha', 0) or nb.get('soil_available_kg_ha', 0) or 0
        water_val = nb.get('water_contribution_kg_ha', 0)
        deficit_val = nb.get('deficit_kg_ha', 0)
        nutrients_data.append([
            nb.get('nutrient', ''),
            f"{nb.get('requirement_kg_ha', 0):.1f}",
            f"{soil_val:.1f}",
            f"{water_val:.1f}",
            f"{deficit_val:.1f}",
        ])
    nutrients_table = Table(
        nutrients_data,
        colWidths=[1.0*inch, 1.3*inch, 1.3*inch, 1.3*inch, 1.3*inch]
    )
    nutrients_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), FERTIRRIEGO_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#ffffff")),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#d1d5db")),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor("#ffffff"), LIGHT_BG]),
    ]))
    story.append(nutrients_table)
    story.append(Paragraph(
        "<i>* Déficit = Requerimiento - Aporte Suelo - Aporte Agua. Este déficit debe cubrirse con fertilizantes.</i>",
        small_style
    ))
    story.append(Spacer(1, 12))
    
    # === SOIL DEPLETION TRACKING SECTION ===
    has_soil_depletion = any(
        nb.get('soil_total_kg_ha', 0) > 0 or nb.get('soil_remaining_kg_ha', 0) > 0
        for nb in nutrient_balance
    )
    if has_soil_depletion and extraction_crop_name:
        story.append(Paragraph("AGOTAMIENTO PROGRESIVO DEL SUELO", heading_style))
        story.append(Paragraph(
            f"Visualización del consumo del suelo a través de las etapas fenológicas para {extraction_crop_name}.",
            small_style
        ))
        story.append(Spacer(1, 4))
        
        depletion_header = ["Nutriente", "Total\nDisp.", "Consumido\nAntes", "Consumido\nEtapa", "Restante", "% Acum."]
        depletion_data = [depletion_header]
        
        for nb in nutrient_balance:
            soil_total = nb.get('soil_total_kg_ha', 0)
            soil_before = nb.get('soil_consumed_before_kg_ha', 0)
            soil_this = nb.get('soil_consumed_this_stage_kg_ha', 0)
            soil_remaining = nb.get('soil_remaining_kg_ha', 0)
            cumulative_pct = nb.get('cumulative_extraction_pct', 0)
            
            if soil_total > 0 or soil_remaining > 0:
                depletion_data.append([
                    nb.get('nutrient', ''),
                    f"{soil_total:.1f}",
                    f"{soil_before:.1f}",
                    f"{soil_this:.1f}",
                    f"{soil_remaining:.1f}",
                    f"{cumulative_pct:.0f}%"
                ])
        
        if len(depletion_data) > 1:
            depletion_table = Table(depletion_data, colWidths=[0.9*inch, 0.9*inch, 1.0*inch, 1.0*inch, 0.9*inch, 0.8*inch])
            depletion_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), HexColor("#7c3aed")),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#ffffff")),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#d1d5db")),
                ('PADDING', (0, 0), (-1, -1), 3),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#f5f3ff")]),
            ]))
            story.append(depletion_table)
            story.append(Paragraph(
                "<i>Nota: El suelo disponible se consume proporcionalmente según la curva de extracción de cada etapa.</i>",
                small_style
            ))
            story.append(Spacer(1, 8))
    
    fertilizer_program = result.get('fertilizer_program', [])
    num_applications = calculation.get('num_applications', result.get('num_applications', 10))
    
    consolidated_ferts = {}
    for fd in fertilizer_program:
        name = fd.get('fertilizer_name', '')
        if name in consolidated_ferts:
            consolidated_ferts[name]['dose_kg_ha'] += fd.get('dose_kg_ha', 0)
            consolidated_ferts[name]['cost_total'] += fd.get('cost_total', fd.get('cost_ha', 0))
            for key in ['n_contribution', 'p2o5_contribution', 'k2o_contribution', 'ca_contribution', 'mg_contribution', 's_contribution']:
                consolidated_ferts[name][key] = consolidated_ferts[name].get(key, 0) + fd.get(key, 0)
        else:
            consolidated_ferts[name] = {
                'fertilizer_name': name,
                'fertilizer_id': fd.get('fertilizer_id', fd.get('id', '')),
                'dose_kg_ha': fd.get('dose_kg_ha', 0),
                'cost_total': fd.get('cost_total', fd.get('cost_ha', 0)),
                'n_contribution': fd.get('n_contribution', 0),
                'p2o5_contribution': fd.get('p2o5_contribution', 0),
                'k2o_contribution': fd.get('k2o_contribution', 0),
                'ca_contribution': fd.get('ca_contribution', 0),
                'mg_contribution': fd.get('mg_contribution', 0),
                's_contribution': fd.get('s_contribution', 0),
                'nutrient_composition': fd.get('nutrient_composition', {})
            }
    
    unique_fertilizers = list(consolidated_ferts.values())
    
    if unique_fertilizers:
        story.append(Paragraph(f"PROGRAMA DE FERTILIZACIÓN ({num_applications} Riegos)", heading_style))
        story.append(Paragraph(
            "Detalle de fertilizantes. El costo indicado corresponde solo a fertilizantes (sin ácido).",
            small_style
        ))
        story.append(Spacer(1, 2))
        
        program_data = [["Fertilizante", "Total\n(kg/ha)", "Por Riego", "Costo"]]
        
        # Use user's preferred currency if available
        currency = calculation.get('user_currency', result.get('currency', 'MXN'))
        symbol = get_currency_symbol(currency)
        # Get price_map from calculation (passed from endpoint with user prices)
        price_map = calculation.get('price_map', {})
        
        total_dose = 0
        total_cost = 0
        
        max_fertilizers = 15
        display_fertilizers = unique_fertilizers[:max_fertilizers]

        for fd in display_fertilizers:
            name = fd.get('fertilizer_name', '')
            fert_id = fd.get('fertilizer_id', fd.get('id', fd.get('slug', '')))
            dose = fd.get('dose_kg_ha', 0)
            dose_per_app = dose / num_applications if num_applications > 0 else dose
            original_cost = fd.get('cost_total', 0)
            
            # If original cost is 0, calculate from Fertilizer Prices module
            if original_cost == 0 and dose > 0:
                price_kg = get_fertilizer_price(fert_id, name, currency, is_liquid=False, price_map=price_map)
                cost = price_kg * dose if price_kg > 0 else 0
            else:
                cost = original_cost
            
            total_dose += dose
            total_cost += cost
            program_data.append([
                name,
                f"{dose:.1f}",
                f"{dose_per_app:.2f}",
                f"{symbol}{cost:.2f}",
            ])
        
        total_per_app = total_dose / num_applications if num_applications > 0 else total_dose
        program_data.append([
            "TOTAL",
            f"{total_dose:.1f}",
            f"{total_per_app:.2f}",
            f"{symbol}{total_cost:.2f}"
        ])
        
        program_table = Table(program_data, colWidths=[3.2*inch, 1.0*inch, 0.95*inch, 1.2*inch])
        program_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), SECONDARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#ffffff")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#d1d5db")),
            ('PADDING', (0, 0), (-1, -1), 3),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [HexColor("#ffffff"), LIGHT_BG]),
            ('BACKGROUND', (0, -1), (-1, -1), HexColor("#dcfce7")),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        story.append(program_table)
        if len(unique_fertilizers) > max_fertilizers:
            story.append(Paragraph(
                f"Nota: se muestran los primeros {max_fertilizers} fertilizantes para mantener el reporte legible.",
                small_style
            ))
        story.append(Spacer(1, 8))
        
        # === NUTRIENT CONTRIBUTIONS TABLE ===
        story.append(Paragraph("APORTES NUTRIMENTALES POR FERTILIZANTE (kg/ha por etapa)", heading_style))
        story.append(Paragraph(
            "Desglose de nutrientes aportados por cada fertilizante seleccionado.",
            small_style
        ))
        story.append(Spacer(1, 4))
        
        nutrient_cols = ["N", "NH4", "P2O5", "K2O", "Ca", "Mg", "S"]
        contrib_keys = CONTRIBUTION_KEYS
        
        contrib_header = ["Fertilizante", "kg/ha"] + nutrient_cols
        contrib_data = [contrib_header]
        nutrient_totals = {k: 0.0 for k in contrib_keys}
        
        for fd in display_fertilizers:
            fert_name = fd.get('fertilizer_name', '')
            fert_id = fd.get('fertilizer_id', '')
            dose_kg = fd.get('dose_kg_ha', 0)
            
            row = [fert_name, f"{dose_kg:.1f}"]
            has_any_contrib = False

            composition = get_fertilizer_composition(
                fert_id,
                fert_name,
                fallback=fd.get('nutrient_composition', {}),
            )
            contributions = compute_contributions(fd, dose_kg, composition)

            for key in contrib_keys:
                contrib_kg = contributions.get(key, 0) or 0
                nutrient_totals[key] += contrib_kg
                if contrib_kg > 0.05:
                    row.append(f"{contrib_kg:.1f}")
                    has_any_contrib = True
                else:
                    row.append("-")
            
            if has_any_contrib or dose_kg > 0:
                contrib_data.append(row)
        
        totals_row = ["TOTAL", ""]
        for key in contrib_keys:
            total_val = nutrient_totals[key]
            totals_row.append(f"{total_val:.1f}" if total_val > 0 else "–")
        contrib_data.append(totals_row)
        
        contrib_table = Table(contrib_data, colWidths=[1.8*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.55*inch, 0.55*inch, 0.5*inch])
        contrib_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor("#1e3a5f")),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#ffffff")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#94a3b8")),
            ('PADDING', (0, 0), (-1, -1), 3),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [HexColor("#ffffff"), HexColor("#f0f4f8")]),
            ('BACKGROUND', (0, -1), (-1, -1), HexColor("#e2e8f0")),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        story.append(contrib_table)
        story.append(Paragraph(
            "Guía de lectura: los aportes están expresados en kg/ha para toda la etapa. "
            "Por riego = total / Nº aplicaciones. Un guion indica que el fertilizante no aporta ese nutriente.",
            small_style
        ))
        story.append(Spacer(1, 8))
        
        # === A/B TANKS SECTION ===
        # Use pre-computed A/B tank data if available (from 'tanks' or 'ab_tanks_separation')
        ab_tanks_precomputed = result.get('tanks') or result.get('ab_tanks_separation')
        if ab_tanks_precomputed:
            tank_a = ab_tanks_precomputed.get('tank_a', [])
            tank_b = ab_tanks_precomputed.get('tank_b', [])
        else:
            # Compute from fertilizer program - pass full dicts to preserve all metadata
            acid_treatment = result.get('acid_treatment')
            ab_tanks_data = separate_fertilizers_ab(fertilizer_program, acid_treatment)
            tank_a = ab_tanks_data.get('tank_a', [])
            tank_b = ab_tanks_data.get('tank_b', [])
        
        if tank_a or tank_b:
            story.append(Paragraph("PROGRAMA DE INYECCIÓN - TANQUES A/B", heading_style))
            story.append(Paragraph(
                "Separación de fertilizantes por compatibilidad química. Tanque A: calcio y micronutrientes. "
                "Tanque B: fosfatos, sulfatos y ácidos.",
                small_style
            ))
            story.append(Spacer(1, 4))
            
            # Tank A Table
            if tank_a:
                story.append(Paragraph("TANQUE A (Calcio + Micronutrientes)", subheading_style))
                tank_a_data = [["Fertilizante", "Dosis Total (kg/ha)", "Por Riego"]]
                for fert in tank_a:
                    dose = fert.get('dose_kg_ha', 0)
                    dose_per_app = dose / num_applications if num_applications > 0 else dose
                    unit = fert.get('dose_unit', 'kg')
                    tank_a_data.append([
                        fert.get('fertilizer_name', ''),
                        f"{dose:.2f} {unit}",
                        f"{dose_per_app:.3f} {unit}"
                    ])
                
                tank_a_table = Table(tank_a_data, colWidths=[3.2*inch, 1.5*inch, 1.5*inch])
                tank_a_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), HexColor("#3b82f6")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#ffffff")),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 7),
                    ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#d1d5db")),
                    ('PADDING', (0, 0), (-1, -1), 3),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#eff6ff")]),
                ]))
                story.append(tank_a_table)
                story.append(Spacer(1, 6))
            
            # Tank B Table
            if tank_b:
                story.append(Paragraph("TANQUE B (Fosfatos + Sulfatos + Ácido)", subheading_style))
                tank_b_data = [["Fertilizante", "Dosis Total (kg/ha)", "Por Riego"]]
                for fert in tank_b:
                    dose = fert.get('dose_kg_ha', 0)
                    dose_per_app = dose / num_applications if num_applications > 0 else dose
                    unit = fert.get('dose_unit', 'kg')
                    if fert.get('is_acid'):
                        unit = 'L'
                    tank_b_data.append([
                        fert.get('fertilizer_name', ''),
                        f"{dose:.2f} {unit}",
                        f"{dose_per_app:.3f} {unit}"
                    ])
                
                tank_b_table = Table(tank_b_data, colWidths=[3.2*inch, 1.5*inch, 1.5*inch])
                tank_b_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), HexColor("#f59e0b")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#ffffff")),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 7),
                    ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#d1d5db")),
                    ('PADDING', (0, 0), (-1, -1), 3),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#fffbeb")]),
                ]))
                story.append(tank_b_table)
                story.append(Spacer(1, 6))
            
            # Compatibility warning
            story.append(Paragraph(
                "<b>⚠ Importante:</b> No mezclar fertilizantes de Tanque A con Tanque B en la misma solución madre. "
                "El calcio precipita con fosfatos y sulfatos.",
                small_style
            ))
            story.append(Spacer(1, 8))
    
    if include_optimization and optimization_result:
        story.append(PageBreak())
        story.append(Paragraph("OPTIMIZACIÓN IA GROWER", heading_style))
        story.append(Paragraph(
            "Resultados de la optimización inteligente de fertilizantes basada en sus productos disponibles.",
            body_style
        ))
        story.append(Spacer(1, 10))
        
        opt_currency = optimization_result.get('currency', result.get('currency', 'MXN'))
        opt_symbol = get_currency_symbol(opt_currency)
        
        profiles = optimization_result.get('profiles', [])
        for profile in profiles:
            profile_name = profile.get('profile_name', 'Perfil')
            profile_type = profile.get('profile_type', 'balanced')
            
            color_map = {
                'economic': HexColor("#f59e0b"),
                'balanced': FERTIRRIEGO_COLOR,
                'complete': HexColor("#8b5cf6")
            }
            profile_color = color_map.get(profile_type, FERTIRRIEGO_COLOR)
            
            story.append(Paragraph(f"Perfil: {profile_name}", subheading_style))
            
            total_cost = profile.get('total_cost_ha', 0)
            coverage = profile.get('coverage', {})
            
            profile_info = [
                ["Costo por Hectárea:", f"{opt_symbol}{total_cost:,.2f} {opt_currency}"],
            ]
            
            for nutrient, pct in coverage.items():
                status = "✓" if pct >= 95 else "⚠" if pct >= 80 else "✗"
                profile_info.append([f"Cobertura {nutrient}:", f"{pct}% {status}"])
            
            profile_table = Table(profile_info, colWidths=[1.5*inch, 2*inch])
            profile_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), HexColor("#f3f4f6")),
                ('TEXTCOLOR', (0, 0), (-1, -1), TEXT_COLOR),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#e5e7eb")),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(profile_table)
            story.append(Spacer(1, 5))
            
            fertilizers = profile.get('fertilizers', [])
            opt_num_apps = optimization_result.get('num_applications', num_applications)
            if fertilizers:
                fert_data = [["Fertilizante", "Dosis Total\n(kg/ha)", "Por Riego\n(kg)", "Costo"]]
                for fert in fertilizers[:12]:
                    dose = fert.get('dose_kg_ha', 0)
                    dose_per_app = dose / opt_num_apps if opt_num_apps > 0 else dose
                    fert_data.append([
                        fert.get('fertilizer_name', ''),
                        f"{dose:.1f}",
                        f"{dose_per_app:.2f}",
                        f"{opt_symbol}{fert.get('cost_total', 0):,.2f}",
                    ])
                
                fert_table = Table(fert_data, colWidths=[2.2*inch, 0.9*inch, 0.9*inch, 1.0*inch])
                fert_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), profile_color),
                    ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#ffffff")),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#e5e7eb")),
                    ('PADDING', (0, 0), (-1, -1), 3),
                ]))
                story.append(fert_table)
            
            story.append(Spacer(1, 12))
    
    recommendations = result.get('recommendations', [])
    warnings_list = result.get('warnings', [])
    
    if recommendations or warnings_list:
        story.append(Paragraph("RECOMENDACIONES Y NOTAS", heading_style))
        
        for rec in recommendations[:6]:
            bullet_text = f"• {rec}"
            story.append(Paragraph(bullet_text, small_style))
        
        if warnings_list:
            warn_style = ParagraphStyle(
                'Warning',
                parent=small_style,
                textColor=HexColor("#b45309"),
            )
            for warn in warnings_list[:4]:
                story.append(Paragraph(f"⚠ {warn}", warn_style))
        
        story.append(Spacer(1, 6))
    
    # === SAFETY MEASURES SECTION (NEW - Similar to Hydroponics) ===
    story.append(Paragraph("MEDIDAS DE SEGURIDAD", heading_style))
    
    safety_items = [
        ("<b>Fertilizantes sólidos:</b> Usar guantes al manipular. Evitar inhalar polvo. "
         "Disolver completamente antes de agregar el siguiente producto."),
        ("<b>Orden de disolución:</b> Siempre agregar fertilizantes al agua (no al revés). "
         "Agitar hasta disolución completa antes de agregar el siguiente."),
        ("<b>Compatibilidad química:</b> No mezclar fertilizantes de calcio con fosfatos o sulfatos "
         "en la misma solución madre. Usar sistema de tanques A/B si es necesario."),
        ("<b>Almacenamiento:</b> Mantener fertilizantes en lugar fresco, seco y ventilado. "
         "Mantener fuera del alcance de niños y animales."),
    ]
    
    # Check if acid is used and add acid safety
    if has_acid:
        safety_items.insert(0, 
            "<b>⚠ ÁCIDOS - PRECAUCIÓN MÁXIMA:</b> Usar guantes de nitrilo y gafas de protección. "
            "SIEMPRE agregar ácido al agua, NUNCA al revés. Trabajar en área ventilada. "
            "Tener bicarbonato de sodio (neutralizador) a la mano. En caso de contacto con piel, "
            "lavar inmediatamente con abundante agua."
        )
    
    safety_list_style = ParagraphStyle(
        'SafetyList',
        parent=small_style,
        spaceBefore=2,
        spaceAfter=2,
        leftIndent=10,
    )
    
    for item in safety_items:
        story.append(Paragraph(f"• {item}", safety_list_style))
    
    story.append(Spacer(1, 8))
    
    story.append(Paragraph(
        "<b>Nota:</b> Balance nutricional = Requerimiento - Suelo - Agua. "
        "Eficiencias: Arenoso (N 50%, P 15%, K 60%) | Franco (N 70%, P 25%, K 70%) | Arcilloso (N 80%, P 35%, K 75%). "
        "<i>Ajustar según condiciones de parcela.</i>",
        small_style
    ))
    
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    
    return buffer.getvalue()

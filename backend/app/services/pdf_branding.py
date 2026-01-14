"""Professional PDF branding helpers with logo and letterhead."""
from dataclasses import dataclass
from typing import Optional
import uuid
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter

BRAND_GREEN = "#16a34a"
LIGHT_GRAY = "#f0f0f0"

LOGO_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'logo.png')
if not os.path.exists(LOGO_PATH):
    LOGO_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'static', 'logo.png')

SMEAP_LOGO_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'smeap_logo.png')
if not os.path.exists(SMEAP_LOGO_PATH):
    SMEAP_LOGO_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'logo_smeap.png')


@dataclass
class PDFBrandingContext:
    company_name: str = "AgriDoser"
    company_tagline: Optional[str] = "Optimización Agrícola Inteligente"
    company_address: Optional[str] = None
    company_email: Optional[str] = "soporte@agridoser.com"
    company_phone: Optional[str] = None
    company_website: str = "www.agridoser.com"


branding_context = PDFBrandingContext()


def draw_professional_letterhead(
    canvas, 
    doc, 
    branding: PDFBrandingContext = None,
    report_title: str = "REPORTE PROFESIONAL",
    folio: str = None,
    module_color = None
) -> None:
    """Draw professional letterhead with logo, title and folio."""
    if branding is None:
        branding = branding_context
    
    if module_color is None:
        module_color = colors.HexColor(BRAND_GREEN)
    elif isinstance(module_color, str):
        module_color = colors.HexColor(module_color)
    
    width, height = letter
    canvas.saveState()
    
    canvas.setFillColor(module_color)
    canvas.rect(0, height - 0.8*inch, width, 0.8*inch, fill=1, stroke=0)
    
    if os.path.exists(LOGO_PATH):
        try:
            canvas.drawImage(
                LOGO_PATH, 
                0.5*inch, 
                height - 0.7*inch, 
                width=0.5*inch, 
                height=0.5*inch,
                preserveAspectRatio=True,
                mask='auto'
            )
        except Exception:
            pass
    
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(1.1*inch, height - 0.45*inch, branding.company_name.upper())
    
    if branding.company_tagline:
        canvas.setFont("Helvetica", 8)
        canvas.drawString(1.1*inch, height - 0.6*inch, branding.company_tagline)
    
    if os.path.exists(SMEAP_LOGO_PATH):
        try:
            canvas.drawImage(
                SMEAP_LOGO_PATH, 
                width - 1.8*inch,
                height - 0.7*inch, 
                width=1.2*inch, 
                height=0.5*inch,
                preserveAspectRatio=True,
                mask='auto'
            )
        except Exception:
            pass
    
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawCentredString(width/2, height - 0.45*inch, report_title)
    
    if folio:
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(width/2, height - 0.6*inch, f"Folio: {folio}")
    
    canvas.setStrokeColor(module_color)
    canvas.setLineWidth(2)
    canvas.line(0.5*inch, height - 0.95*inch, width - 0.5*inch, height - 0.95*inch)
    
    canvas.restoreState()


def draw_professional_footer(
    canvas, 
    doc, 
    branding: PDFBrandingContext = None
) -> None:
    """Draw professional footer with company info and page number."""
    if branding is None:
        branding = branding_context
    
    width, height = letter
    canvas.saveState()
    
    canvas.setStrokeColor(colors.HexColor("#e5e7eb"))
    canvas.setLineWidth(0.5)
    canvas.line(0.5*inch, 0.5*inch, width - 0.5*inch, 0.5*inch)
    
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.setFont("Helvetica", 7)
    
    footer_text = f"{branding.company_name}"
    if branding.company_website:
        footer_text += f" | {branding.company_website}"
    if branding.company_email:
        footer_text += f" | {branding.company_email}"
    
    canvas.drawString(0.5*inch, 0.35*inch, footer_text)
    
    page_num = canvas.getPageNumber()
    canvas.drawRightString(width - 0.5*inch, 0.35*inch, f"Página {page_num}")
    
    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y %H:%M")
    canvas.drawCentredString(width/2, 0.35*inch, f"Generado: {date_str}")
    
    canvas.restoreState()


def create_professional_callback(
    branding: PDFBrandingContext = None,
    report_title: str = "REPORTE PROFESIONAL",
    folio: str = None,
    module_color = None
):
    """Return a callback for PDF generation with header and footer."""
    def callback(canvas, doc):
        draw_professional_letterhead(canvas, doc, branding, report_title, folio, module_color)
        draw_professional_footer(canvas, doc, branding)
    return callback


def create_header_footer_callback(
    branding: PDFBrandingContext = None,
    report_title: str = "REPORTE PROFESIONAL",
    folio: str = None,
    module_color = None
):
    """Return a callback for header/footer generation."""
    return create_professional_callback(branding, report_title, folio, module_color)


def generate_folio(prefix: str = "AGR", session_id: int = 0) -> str:
    """Generate a unique folio number for reports."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    if session_id:
        return f"{prefix}-{session_id:05d}-{timestamp[-6:]}"
    short_uuid = str(uuid.uuid4())[:8].upper()
    return f"{prefix}-{timestamp}-{short_uuid}"
